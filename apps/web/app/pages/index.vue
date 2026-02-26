<script setup lang="ts">
const {
  videoRef,
  canvasRef,
  isStreaming,
  value,
  items,
  isConnected,
  startProcessing,
  stopProcessing
} = useCameraProcessing({ redirectMobileTo: '/mobile' })
</script>

<template>
  <UContainer class="h-screen flex items-center justify-center bg-slate-950 p-4">
    <UCard class="w-full max-w-4xl bg-slate-900 border-slate-800 shadow-2xl overflow-hidden">
      <template #header>
        <div class="flex justify-between items-center text-white">
          <div class="flex gap-5 items-center">
            <h1 class="text-xl font-bold tracking-tight">
              OpenCV <span class="text-primary-500">Live</span>
            </h1>
            <USelect v-model="value" :items="items" color="success" variant="outline" class="w-48" />
          </div>
            <UBadge :color="isConnected ? 'success' : 'error'" variant="solid" class="text-xs px-2 py-1">
              {{ isConnected ? 'Online' : 'Offline' }}
            </UBadge>
        </div>
      </template>

      <div class="relative w-full aspect-video bg-black rounded-lg overflow-hidden border border-slate-700">
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
          class="absolute inset-0 flex flex-col items-center justify-center text-slate-500 bg-slate-900 z-20"
        >
          <UIcon name="i-heroicons-video-camera" class="w-16 h-16 mb-4 text-slate-700" />
          <p>Система готова к запуску</p>
        </div>
      </div>

      <template #footer>
        <div class="flex justify-center">
          <UButton
            size="xl"
            :color="isStreaming ? 'error' : 'success'"
            @click="isStreaming ? stopProcessing() : startProcessing()"
            class="px-10 font-bold"
          >
            {{ isStreaming ? 'Остановить' : 'Запустить камеру' }}
          </UButton>
        </div>
      </template>
    </UCard>
  </UContainer>
</template>

