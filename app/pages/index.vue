<script setup lang="ts">
const { stream, start, stop } = useUserMedia({
  constraints: { video: { width: { ideal: 1280 }, height: { ideal: 720 } } }
})

const videoRef = ref<HTMLVideoElement | null>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)
const { connectToServer, sendFrame, processedImage, isConnected } = useCV()
const isStreaming = ref(false)

// Замок: не шлем новый кадр, пока сервер не ответил на старый
let isLocked = false 

const items = [
  { label: 'Нейросеть', value: 'yolo' },
  { label: 'Фильтр', value: 'gray' },
  { label: 'Оригинал', value: 'none' },
  { label: 'Линейка', value: 'ruler' },
  { label: 'Маркер', value: 'aruco' },
  {label: 'Игра', value: 'ar_game'}


]
const value = ref('yolo')

// 1. ПОЛУЧЕНИЕ МАСКИ С СЕРВЕРА
watch(processedImage, async (newUrl) => {
  if (!newUrl || !isStreaming.value || value.value === 'none') {
    isLocked = false
    return
  }

  const canvas = canvasRef.value
  const ctx = canvas?.getContext('2d')
  if (!ctx || !canvas) return

  const img = new Image()
  img.onload = () => {
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    // Рисуем маску, растягивая её на весь размер канваса (под размер видео)
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
    
    isLocked = false // Разблокируем отправку следующего кадра
    requestAnimationFrame(captureAndSend)
  }
  img.src = newUrl
})

// 2. ОТПРАВКА КАДРА (Легкая версия)
const captureAndSend = () => {
  if (!videoRef.value || !isStreaming.value || isLocked || value.value === 'none') return

  isLocked = true 

  // Создаем временный невидимый канвас для сжатия
  const offscreen = document.createElement("canvas")
  offscreen.width = 640 // Маленький размер для сервера
  offscreen.height = 480 
  const octx = offscreen.getContext("2d")
  octx?.drawImage(videoRef.value, 0, 0, offscreen.width, offscreen.height)

  offscreen.toBlob((blob) => {
    if (blob) {
      sendFrame({ image: blob, mode: value.value })
    } else {
      isLocked = false
    }
  }, "image/jpeg", 1) // Максимальное сжатие
}

// 3. УПРАВЛЕНИЕ
const startProcessing = async () => {
  await start()
  if (!stream.value) return
  isStreaming.value = true
  
  // Подгоняем размер канваса под видео один раз
  setTimeout(() => {
    if (videoRef.value && canvasRef.value) {
      canvasRef.value.width = videoRef.value.videoWidth
      canvasRef.value.height = videoRef.value.videoHeight
      captureAndSend()
    }
  }, 1000)
}

const stopProcessing = () => {
  isStreaming.value = false
  isLocked = false
  const ctx = canvasRef.value?.getContext('2d')
  ctx?.clearRect(0, 0, canvasRef.value?.width || 0, canvasRef.value?.height || 0)
  stop() 
}

// Если переключили режим - сбрасываем замок
watch(value, (val) => {
  const ctx = canvasRef.value?.getContext('2d')
  ctx?.clearRect(0, 0, canvasRef.value?.width || 0, canvasRef.value?.height || 0)
  isLocked = false
  if (val !== 'none') captureAndSend()
})

watchEffect(() => {
  if (videoRef.value && stream.value) videoRef.value.srcObject = stream.value
})

onMounted(() => connectToServer("http://localhost:8000"))
</script>

<template>
  <UContainer class="h-screen flex items-center justify-center bg-slate-950 p-4">
    <UCard class="w-full max-w-4xl bg-slate-900 border-slate-800 shadow-2xl overflow-hidden">
      
      <template #header>
        <div class="flex justify-between items-center text-white">
          <div class="flex gap-5 items-center">
            <h1 class="text-xl font-bold tracking-tight">OpenCV <span class="text-primary-500">Live</span></h1>
            <USelect v-model="value" :items="items" color="success" variant="outline" class="w-48 px-5" />
          </div>
          <UBadge :color="isConnected ? 'success' : 'error'" variant="solid" class="font-mono uppercase">
            {{ isConnected ? 'Connected' : 'Disconnected' }}
          </UBadge>
        </div>
      </template>

      <div class="relative w-full aspect-video bg-black rounded-lg overflow-hidden border border-slate-700 shadow-2xl">
        
        <video 
          ref="videoRef" 
          autoplay 
          playsinline 
          class="absolute inset-0 w-full h-full object-cover"
          :class="{ 'hidden': !isStreaming || value == 'gray'}"
        />

        <canvas 
          ref="canvasRef" 
          class="absolute inset-0 w-full h-full object-cover pointer-events-none"
          :style="value === 'yolo' || 'ruler' ? 'mix-blend-mode: screen' : ''"
          v-show="isStreaming && value !== 'none'" 
        />

        <div v-if="!isStreaming" class="absolute inset-0 flex flex-col items-center justify-center text-slate-500 bg-slate-900">
          <UIcon name="i-heroicons-video-camera" class="w-16 h-16 mb-4 animate-pulse text-slate-700" />
          <p class="text-lg font-medium">Система готова к запуску</p>
        </div>
      </div>

      <template #footer>
        <div class="flex gap-4 justify-center">
          <UButton 
            size="xl" 
            :color="isStreaming ? 'error' : 'success'" 
            :label="isStreaming ? 'Остановить' : 'Запустить камеру'" 
            @click="isStreaming ? stopProcessing() : startProcessing()" 
            class="px-10 py-3 font-bold"
          />
        </div>
      </template>
    </UCard>
  </UContainer>
</template>