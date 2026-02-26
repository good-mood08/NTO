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


  const { stream, start, stop } = useUserMedia({

    constraints: {

      video: {

        facingMode: 'environment',

        // width: { ideal: 1280 },

        // height: { ideal: 720 },

        frameRate: { ideal: 40 }

      }

    }

  })


  const { connectToServer, sendFrame, processedImage, isConnected } = useCV()


  const videoRef = ref<HTMLVideoElement | null>(null)

  const canvasRef = ref<HTMLCanvasElement | null>(null)

  const isStreaming = ref(false)

  const value = ref<CameraMode>('yolo')


  let isLocked = false

  let offscreenCanvas: HTMLCanvasElement | null = null

  let reconnectInterval: any = null


  const items = [

    { label: 'Нейросеть', value: 'yolo' },

    { label: 'Фильтр', value: 'gray' },

    { label: 'Оригинал', value: 'none' },

    { label: 'Линейка', value: 'ruler' },

    { label: 'Маркер', value: 'aruco' },

    { label: 'Игра', value: 'ar_game' }

  ] as const


  const captureAndSend = () => {

    if (!videoRef.value || !isStreaming.value || !isConnected.value || isLocked) return

    if (value.value === 'none') return


    const v = videoRef.value


    if (!offscreenCanvas) {

      offscreenCanvas = document.createElement('canvas')

      const scale = 640 / v.videoWidth

      offscreenCanvas.width = 640

      offscreenCanvas.height = v.videoHeight * scale

    }


    isLocked = true

    const octx = offscreenCanvas.getContext('2d')

    octx?.drawImage(v, 0, 0, offscreenCanvas.width, offscreenCanvas.height)


    offscreenCanvas.toBlob(

      blob => {

        if (blob && isStreaming.value && value.value !== 'none') {

          sendFrame({ image: blob, mode: value.value })

        } else {

          isLocked = false

        }

      },

      'image/jpeg',

      0.6

    )

  }


  watch(processedImage, newUrl => {

    if (!newUrl) return

    const canvas = canvasRef.value

    const ctx = canvas?.getContext('2d')

    if (!ctx || !canvas) return


    const img = new Image()

    img.onload = () => {

      if (value.value !== 'none') {

        if (canvas.width !== videoRef.value!.videoWidth) {

          canvas.width = videoRef.value!.videoWidth

          canvas.height = videoRef.value!.videoHeight

        }


        ctx.clearRect(0, 0, canvas.width, canvas.height)

        ctx.drawImage(img, 0, 0, canvas.width, canvas.height)

      }

      URL.revokeObjectURL(newUrl)

      isLocked = false

      requestAnimationFrame(captureAndSend)

    }

    img.src = newUrl

  })


  watch(value, newMode => {

    const ctx = canvasRef.value?.getContext('2d')

    ctx?.clearRect(0, 0, canvasRef.value!.width, canvasRef.value!.height)


    if (newMode !== 'none' && isStreaming.value) {

      isLocked = false

      captureAndSend()

    }

  })


  watchEffect(() => {

    if (videoRef.value) videoRef.value.srcObject = stream.value || null

  })


  const startProcessing = async () => {

    try {

      if (!isConnected.value) {

        connectToServer()

      }


      if (!reconnectInterval) {

        reconnectInterval = setInterval(() => {

          if (!isConnected.value) connectToServer()

        }, 3000)

      }


      await start()

      isStreaming.value = true

      if (videoRef.value) {

        videoRef.value.onloadedmetadata = () => {

          if (canvasRef.value) {

            canvasRef.value.width = videoRef.value!.videoWidth

            canvasRef.value.height = videoRef.value!.videoHeight

          }

          captureAndSend()

        }

      }

    } catch (e) {

      console.error(e)

    }

  }


  const stopProcessing = () => {

    isStreaming.value = false

    isLocked = false

    stop()

  }


  onMounted(() => {

    if (redirectMobileTo && isMobileDevice()) {

      navigateTo(redirectMobileTo)

      return

    }

  })


  onUnmounted(() => {

    clearInterval(reconnectInterval)

    stop()

  })


  return {

    videoRef,

    canvasRef,

    isStreaming,

    value,

    items,

    isConnected,

    startProcessing,

    stopProcessing

  }

}