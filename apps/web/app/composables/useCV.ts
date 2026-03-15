import { io, Socket } from "socket.io-client";
import { ref } from "vue";

interface WebRTCState {
  pc: RTCPeerConnection | null;
}

interface FramePayload {
  image: Blob;
  mode: string;
}

const socket = ref<Socket | null>(null);
const processedImage = ref<Blob | null>(null);
const isConnected = ref(false);
const webrtc: WebRTCState = {
  pc: null
};

export const useCV = () => {
  const connectToServer = () => {
    if (socket.value?.connected) return;

    const serverUrl = `https://${window.location.hostname}:8000`;
    console.log("Trying to connect to CV server:", serverUrl);
    socket.value = io(serverUrl,{
      transports: ['websocket'],
      secure: true,
      rejectUnauthorized: false
    });

    socket.value.on("connect", () => {
      isConnected.value = true;
      console.log("🚀 WebSocket Connected!");
    });

    socket.value.on("disconnect", () => {
      isConnected.value = false;
      console.log("❌ WebSocket Disconnected");
      if (webrtc.pc) {
        webrtc.pc.close();
        webrtc.pc = null;
      }
    });

    socket.value.on("processed_frame", (data: ArrayBuffer) => {
      processedImage.value = new Blob([data], { type: "image/webp" });
    });

    socket.value.on("connect_error", (err) => {
      console.error("🌐 Connection Error:", err.message);
    });

    socket.value.on("webrtc_ice", async (msg: any) => {
      if (!webrtc.pc) return;
      try {
        await webrtc.pc.addIceCandidate({
          candidate: msg.candidate,
          sdpMid: msg.sdpMid,
          sdpMLineIndex: msg.sdpMLineIndex
        });
      } catch (err) {
        console.error("ICE add error:", err);
      }
    });
  };

  const sendFrame = (payload: FramePayload) => {
    // no-op: legacy API kept for compatibility; WebRTC transports video now
    if (socket.value?.connected) {
      socket.value.emit("set_mode", { mode: payload.mode });
    }
  };

  const startWebRTC = async (stream: MediaStream) => {
    if (!socket.value?.connected) return;
    if (webrtc.pc) return;

    // Для локальной разработки достаточно host-кандидатов без STUN/TURN.
    // Это убирает лишнюю сложность с внешними адресами и ICE-ошибками.
    const pc = new RTCPeerConnection();

    stream.getVideoTracks().forEach(track => {
      pc.addTrack(track, stream);
    });

    pc.onicecandidate = (event) => {
      if (!event.candidate || !socket.value) return;
      socket.value.emit("webrtc_ice", {
        candidate: event.candidate.candidate,
        sdpMid: event.candidate.sdpMid,
        sdpMLineIndex: event.candidate.sdpMLineIndex
      });
    };

    webrtc.pc = pc;

    const offer = await pc.createOffer({
      offerToReceiveVideo: false,
      offerToReceiveAudio: false
    });
    await pc.setLocalDescription(offer);

    try {
      const answer = await socket.value.emitWithAck("webrtc_offer", {
        sdp: offer.sdp,
        type: offer.type
      });

      if (answer && answer.sdp && answer.type) {
        await pc.setRemoteDescription(new RTCSessionDescription(answer));
      }
    } catch (err) {
      console.error("WebRTC offer failed:", err);
    }
  };

  const stopWebRTC = () => {
    if (webrtc.pc) {
      webrtc.pc.close();
      webrtc.pc = null;
    }
  };

  return { connectToServer, sendFrame, processedImage, isConnected, startWebRTC, stopWebRTC };
};