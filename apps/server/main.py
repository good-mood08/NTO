import socketio
import uvicorn
import cv2
import numpy as np
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor

from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.sdp import candidate_from_sdp, candidate_to_sdp

import processor_ar_game, processor_yolo, processor_effects, processor_ruler, processor_aruco

sio = socketio.AsyncServer(
    async_mode='asgi', 
    cors_allowed_origins='*',
    engineio_logger=False
)
app = socketio.ASGIApp(sio)

executor = ThreadPoolExecutor(max_workers=4)

# WebRTC state (per Socket.IO client)
pcs = {}
video_tasks = {}
client_modes = {}

# Some processing code (e.g. YOLO/Torch) can be unsafe concurrently.
yolo_lock = threading.Lock()

def get_delta_mask(original, processed):
    """
    Сравнивает два кадра и возвращает RGBA-маску, 
    где неизмененные пиксели — прозрачные.
    """
    # 1. Находим разницу между кадрами
    diff = cv2.absdiff(original, processed)
    # 2. Переводим в градации серого и создаем маску прозрачности (Alpha)
    gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    _, alpha = cv2.threshold(gray_diff, 10, 255, cv2.THRESH_BINARY)
    
    # 3. Разделяем обработанный кадр на каналы и добавляем Alpha
    b, g, r = cv2.split(processed)
    rgba = cv2.merge([b, g, r, alpha])
    
    # 4. Сжимаем в WebP (он поддерживает прозрачность и весит копейки)
    _, buffer = cv2.imencode('.webp', rgba, [int(cv2.IMWRITE_WEBP_QUALITY), 65])
    return buffer.tobytes()

def process_frame_bgr(original_frame: np.ndarray, mode: str):
    """
    original_frame: BGR uint8 ndarray (H, W, 3)
    returns: webp bytes (RGBA delta mask) or None
    """
    processors = {
        'yolo': processor_yolo.process_yolo,
        'gray': processor_effects.process_gray,
        'ruler': processor_ruler.process_ruler,
        'aruco': processor_aruco.process_aruco,
        'ar_game': processor_ar_game.process_ar_game
    }

    process_func = processors.get(mode)
    if not process_func:
        return None

    frame_to_draw = original_frame.copy()

    if mode == 'yolo':
        with yolo_lock:
            processed_frame = process_func(frame_to_draw)
    else:
        processed_frame = process_func(frame_to_draw)

    if processed_frame is None:
        return None

    return get_delta_mask(original_frame, processed_frame)

async def run_webrtc_video_processor(sid: str, track):
    """
    Read frames from WebRTC track, process only the latest frame, and emit `processed_frame`.
    """
    loop = asyncio.get_running_loop()

    q: asyncio.Queue = asyncio.Queue(maxsize=1)

    async def recv_loop():
        while True:
            frame = await track.recv()
            if q.full():
                try:
                    _ = q.get_nowait()
                    q.task_done()
                except Exception:
                    pass
            q.put_nowait(frame)

    async def process_loop():
        while True:
            frame = await q.get()
            q.task_done()

            mode = client_modes.get(sid, 'none')
            if mode == 'none':
                continue

            try:
                # Convert to ndarray on event loop thread, run heavy CV in executor thread.
                img = frame.to_ndarray(format="bgr24")
                processed_bytes = await loop.run_in_executor(executor, process_frame_bgr, img, mode)
                if processed_bytes:
                    await sio.emit('processed_frame', processed_bytes, to=sid)
            except Exception as e:
                print(f"Processing error: {e}")

    await asyncio.gather(recv_loop(), process_loop())


@sio.on("set_mode")
async def set_mode(sid, data):
    mode = None
    if isinstance(data, dict):
        mode = data.get("mode")
    if not isinstance(mode, str):
        mode = "none"
    client_modes[sid] = mode


@sio.on("webrtc_offer")
async def webrtc_offer(sid, data):
    """
    Socket.IO signaling: client sends SDP offer, server responds with SDP answer.
    """
    # Cleanup previous PC if any
    old_pc = pcs.pop(sid, None)
    if old_pc:
        try:
            await old_pc.close()
        except Exception:
            pass

    client_modes.setdefault(sid, "none")

    pc = RTCPeerConnection()
    pcs[sid] = pc

    @pc.on("icecandidate")
    def on_icecandidate(candidate):
        if candidate is None:
            return
        asyncio.create_task(
            sio.emit(
                "webrtc_ice",
                {
                    "candidate": candidate_to_sdp(candidate),
                    "sdpMid": candidate.sdpMid,
                    "sdpMLineIndex": candidate.sdpMLineIndex,
                },
                to=sid,
            )
        )

    @pc.on("track")
    def on_track(track):
        if track.kind != "video":
            return

        # Ensure only one task per client
        old_task = video_tasks.pop(sid, None)
        if old_task:
            old_task.cancel()

        video_tasks[sid] = asyncio.create_task(run_webrtc_video_processor(sid, track))

    offer = RTCSessionDescription(sdp=data["sdp"], type=data["type"])
    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}


@sio.on("webrtc_ice")
async def webrtc_ice(sid, data):
    pc = pcs.get(sid)
    if not pc:
        return

    cand = data.get("candidate") if isinstance(data, dict) else None
    if not isinstance(cand, str) or not cand:
        return

    try:
        candidate = candidate_from_sdp(cand)
        candidate.sdpMid = data.get("sdpMid")
        candidate.sdpMLineIndex = data.get("sdpMLineIndex")
        await pc.addIceCandidate(candidate)
    except Exception as e:
        print(f"ICE error: {e}")


@sio.event
async def disconnect(sid):
    client_modes.pop(sid, None)

    task = video_tasks.pop(sid, None)
    if task:
        task.cancel()

    pc = pcs.pop(sid, None)
    if pc:
        try:
            await pc.close()
        except Exception:
            pass

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        ssl_keyfile="./key.pem",  # Путь к ключу (возьми из Nuxt)
        ssl_certfile="./cert.pem", # Путь к сертификату
        log_level="warning",
    )