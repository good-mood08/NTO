import {

  ref,

  watch,

  watchEffect,

  onMounted,

  onUnmounted,

  navigateTo,

  useUserMedia

} from '#imports'

import { useCV } from '#imports'


type CameraMode = 'yolo' | 'gray' | 'none' | 'ruler' | 'aruco' | 'ar_game'


interface UseCameraProcessingOptions {

  redirectMobileTo?: string | null

}


const isMobileDevice = () => {

  if (typeof window === 'undefined' || typeof navigator === 'undefined') return false


  const ua = navigator.userAgent || ''

  const isSmallScreen = window.innerWidth <= 768

  const isMobileUA = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(ua)


  return isMobileUA || isSmallScreen

}

export const useCameraProcessing = (options: UseCameraProcessingOptions = {}) => {
  const { redirectMobileTo = null } = options
  const facingMode = ref<'user' | 'environment'>('environment')
  const isSwitching = ref(false)

   
  // 1. Инициализация Media и CV
  const { stream, start, stop } = useUserMedia({
    constraints: computed(() =>({
      video: { facingMode: facingMode.value, frameRate: { ideal: 40 } }
    
    }))
  })

  const { connectToServer, sendFrame, processedImage, isConnected } = useCV()

  const videoRef = ref<HTMLVideoElement | null>(null)
  const canvasRef = ref<HTMLCanvasElement | null>(null)
  const isStreaming = ref(false)
  const value = ref<CameraMode>('yolo')

  let isLocked = false
  let offscreenCanvas: HTMLCanvasElement | null = null
  let reconnectInterval: ReturnType<typeof setInterval> | null = null

  const items = [
    { label: 'Нейросеть', value: 'yolo' },
    { label: 'Фильтр', value: 'gray' },
    { label: 'Оригинал', value: 'none' },
    { label: 'Линейка', value: 'ruler' },
    { label: 'Маркер', value: 'aruco' },
    { label: 'Игра', value: 'ar_game' }
  ] as const


  const toggleCamera = async () => {
    if (isSwitching.value) return
    const wasStreaming = isStreaming.value
    
    if (!wasStreaming) {
        facingMode.value = facingMode.value === 'environment' ? 'user' : 'environment'
        return
      }
    
    isSwitching.value = true
    isLocked = true

    stop()

    facingMode.value = facingMode.value === 'environment' ? 'user' : 'environment'
    // 2. Меняем режим

    try {
      await start()
      
      if (videoRef.value) {
        // Ждем, когда новая камера реально отдаст картинку
        videoRef.value.onloadedmetadata = () => {
          isLocked = false
          isSwitching.value = false // КОНЕЦ ПЕРЕКЛЮЧЕНИЯ
          captureAndSend()
        }
      }
    } catch (err) {
      console.error("Ошибка переключения:", err)
      isStreaming.value = false // Если совсем всё плохо, тогда выкидываем
      isSwitching.value = false
    }
  
  }


  let lastSendTime = 0
  const SEND_INTERVAL = 10

  // 2. Оптимизированная отправка кадра
  const captureAndSend = () => {
    // Проверка isConnected.value теперь будет работать, так как мы запустили коннект в onMounted
    if (!videoRef.value || !isStreaming.value || !isConnected.value || isLocked || value.value === 'none') {
      return
    }

     

    if (Date.now() - lastSendTime < SEND_INTERVAL) {
      // Если время еще не пришло, планируем следующую проверку через requestAnimationFrame
      requestAnimationFrame(captureAndSend)
      return
    }
    const v = videoRef.value
    if (!v.videoWidth) return

    if (!offscreenCanvas) {
      offscreenCanvas = document.createElement('canvas')
      const scale = 640 / v.videoWidth
      offscreenCanvas.width = 640
      offscreenCanvas.height = v.videoHeight * scale
    }

    isLocked = true
    lastSendTime = Date.now()
    const octx = offscreenCanvas.getContext('2d')
    octx?.drawImage(v, 0, 0, offscreenCanvas.width, offscreenCanvas.height)

    offscreenCanvas.toBlob(
      blob => {
        if (blob && isStreaming.value && value.value !== 'none') {
          sendFrame({ image: blob, mode: value.value })
        } else {
          isLocked = false // Важно разлочить, если условия не пошли
        }
      },
      'image/jpeg',
      0.4
    )
  }

  // 3. Обработка входящего кадра
  watch(processedImage, newUrl => {
    if (!newUrl) {
      isLocked = false
      return
    }
    
    const canvas = canvasRef.value
    const v = videoRef.value
    if (!canvas || !v) return

    const img = new Image()
    img.onload = () => {
      if (value.value !== 'none' && isStreaming.value) {
        if (canvas.width !== v.videoWidth) {
          canvas.width = v.videoWidth
          canvas.height = v.videoHeight
        }
        const ctx = canvas.getContext('2d')
        ctx?.clearRect(0, 0, canvas.width, canvas.height)
        ctx?.drawImage(img, 0, 0, canvas.width, canvas.height)
      }
      URL.revokeObjectURL(newUrl)
      isLocked = false
      requestAnimationFrame(captureAndSend)
    }
    img.onerror = () => {
      isLocked = false
      URL.revokeObjectURL(newUrl)
    }
    img.src = newUrl
  })

  // 4. Логика жизненного цикла (ИСПРАВЛЕНИЕ СТАТУСА)
  onMounted(() => {
    if (redirectMobileTo && isMobileDevice()) {
      navigateTo(redirectMobileTo)
      return
    }

    // Запускаем попытку подключения сразу при загрузке страницы
    if (!isConnected.value) connectToServer()

    // Интервал работает всегда, пока компонент жив
    reconnectInterval = setInterval(() => {
      if (!isConnected.value) {
        console.log('Попытка переподключения к OpenCV...')
        connectToServer()
      }
    }, 10000)
  })

  onUnmounted(() => {
    if (reconnectInterval) clearInterval(reconnectInterval)
    stop()
    offscreenCanvas = null
  })

  // 5. Управление стримом
  const startProcessing = async () => {
    try {
      await start()
      isStreaming.value = true
      
      if (videoRef.value) {
        videoRef.value.onloadedmetadata = () => {
          captureAndSend()
        }
      }
    } catch (e) {
      console.error('Ошибка запуска камеры:', e)
    }
  }

  const stopProcessing = () => {
    isStreaming.value = false
    isLocked = false
    stop()
  }

  // watchEffect для привязки стрима к видео-тегу
  watchEffect(() => {
    if (videoRef.value) videoRef.value.srcObject = stream.value || null
  })

  return {
    videoRef,
    canvasRef,
    isStreaming,
    value,
    items,
    isConnected,
    startProcessing,
    stopProcessing,
    toggleCamera
  }
}