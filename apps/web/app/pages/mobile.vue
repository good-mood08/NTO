<script setup lang="ts">

const {
  videoRef,
  canvasRef,
  isStreaming,
  value,
  items,
  isConnected,
  startProcessing,
  stopProcessing,
  toggleCamera
} = useCameraProcessing()

</script>

<template>
  <div class="h-[100dvh] bg-slate-950 text-white flex flex-col">
    <header class="px-4 pt-4 pb-3 flex items-center justify-between border-b border-slate-800">
      <div class="flex flex-col">
        <h1 class="text-lg font-semibold leading-tight">
          OpenCV <span class="text-primary-500">Live</span>
        </h1>
      </div>
      <div class="flex justify-center">
        <USelect
          v-model="value"
          :items="items"
          color="primary"
          size="sm"
          class="w-full max-w-xs"
        />
      </div>

      
      <UBadge 
      :color="isConnected ? 'success' : 'error'" 
      variant="solid" 
      class="text-xs px-1 py-1 transition-all duration-500"
      :class="{ 'animate-pulse': isConnected }">

      </UBadge>
    </header>

    <main class="flex-1 flex flex-col gap-3 px-3 py-3">
      

      <div class="relative w-full flex-1 bg-black rounded-xl overflow-hidden border border-slate-800">
        <video
          ref="videoRef"
          autoplay
          playsinline
          class="absolute inset-0 w-full h-full object-contain"
          :class="{ 'opacity-0': value === 'gray' }"
        />

        <canvas
          ref="canvasRef"
          class="absolute inset-0 w-full h-full object-contain pointer-events-none z-10"
          v-show="isStreaming && value !== 'none'"
        />

        <div
          v-if="!isStreaming"
          class="absolute inset-0 flex flex-col items-center justify-center text-slate-400 bg-slate-900/80 z-20 text-center px-6"
        >
          <UIcon name="i-heroicons-video-camera" class="w-14 h-14 mb-3 text-slate-600" />
          <p class="text-sm">Нажмите кнопку ниже, чтобы запустить камеру</p>
        </div>
      </div>
    </main>

    <footer class="fixed bottom-0 left-0 right-0 p-6 z-40">
      <div class="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/80 to-transparent pointer-events-none"></div>

      <div class="relative max-w-md mx-auto flex gap-3">
        <UButton
          block
          size="xl"
          :variant="isStreaming ? 'soft' : 'solid'"
          :color="isStreaming ? 'red' : 'primary'"
          @click="isStreaming ? stopProcessing() : startProcessing()"
          class="flex-1 rounded-2xl py-4 transition-all duration-300 active:scale-95 shadow-xl ring-1 ring-white/10"
          :class="isStreaming ? 'bg-red-500/10 backdrop-blur-md' : 'shadow-primary-500/20'"
        >
          <template #leading>
            <div class="relative flex items-center justify-center">
              <UIcon 
                :name="isStreaming ? 'i-heroicons-stop-circle' : 'i-heroicons-play-circle'" 
                class="w-6 h-6" 
              />
            </div>
          </template>
          
          <span class="font-bold tracking-tight text-base">
            {{ isStreaming ? 'Остановить' : 'Запустить камеру' }}
          </span>
        </UButton>

        <UButton
          v-if="isStreaming"
          color="white"
          variant="soft"
          size="xl"
          icon="i-heroicons-arrow-path"
          class="rounded-2xl px-4 backdrop-blur-md border border-white/10 active:scale-95"
          @click="toggleCamera" 
        />
      </div>
    </footer>
  </div>
</template>
