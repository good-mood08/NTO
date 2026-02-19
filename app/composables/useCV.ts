import { io, Socket } from "socket.io-client";
import { ref } from "vue";

// Типизация для отправки
interface FramePayload {
  image: Blob;
  mode: string;
}

// Глобальные состояния (Singleton)
const socket = ref<Socket | null>(null);
const processedImage = ref<string | null>(null);
const isConnected = ref(false);

export const useCV = () => {
  const connectToServer = (url: string) => {
    if (socket.value?.connected) return;

    socket.value = io(url, {
      reconnection: true,
      reconnectionAttempts: 10,
      reconnectionDelay: 1000
    });

    socket.value.on("connect", () => {
      isConnected.value = true;
      console.log("Connected to Python Server");
    });

    socket.value.on("disconnect", () => {
      isConnected.value = false;
      clearProcessedImage();
    });

    // Прием обработанного кадра (или полной картинки, или маски)
    socket.value.on("processed_frame", (data: ArrayBuffer) => {
      const blob = new Blob([data], { type: "image/jpeg" });
      const newUrl = URL.createObjectURL(blob);

      // КРИТИЧНО: Удаляем старую ссылку из памяти перед заменой
      if (processedImage.value) {
        URL.revokeObjectURL(processedImage.value);
      }
      
      processedImage.value = newUrl;
    });
  };

  const sendFrame = (payload: FramePayload) => {
    if (socket.value?.connected) {
      // Отправляем объект: { image: Blob, mode: string }
      socket.value.emit("video_frame", payload);
    }
  };

  const clearProcessedImage = () => {
    if (processedImage.value) {
      URL.revokeObjectURL(processedImage.value);
      processedImage.value = null;
    }
  };

  return { 
    connectToServer, 
    sendFrame, 
    processedImage, 
    isConnected 
  };
};