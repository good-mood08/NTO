import cv2
import numpy as np
from ultralytics import YOLO
import json
import time

# Загружаем один раз при старте сервера
model = YOLO('yolov8n.pt')


def process_yolo(frame):
    # 1. Инференс
    # imgsz=480 — отличный выбор для скорости
    results = model(frame, verbose=False, imgsz=480)

    # 2. РИСУЕМ ИЗ КОРОБКИ
    # Вместо img=mask подставляем img=frame.
    # Теперь YOLO нарисует боксы и подписи прямо поверх видеопотока.
    annotated_frame = results[0].plot(
        img=frame,
        conf=True,
        labels=True,
        boxes=True,
        line_width=2,
    )

    # #region agent log
    try:
        with open("debug-80eebb.log", "a", encoding="utf-8") as f:
            boxes = len(getattr(results[0], "boxes", []) or [])
            log = {
                "sessionId": "80eebb",
                "runId": "initial",
                "hypothesisId": "H4",
                "location": "processor_yolo.py:process_yolo",
                "message": "yolo processed frame",
                "data": {
                    "boxes": int(boxes),
                },
                "timestamp": int(time.time() * 1000),
            }
            f.write(json.dumps(log, ensure_ascii=False) + "\n")
    except Exception:
        pass
    # #endregion

    return annotated_frame