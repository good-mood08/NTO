FROM python:3.12-slim

WORKDIR /app

# Системные библиотеки (OpenCV без них не запустится)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libx11-6 \
 && rm -rf /var/lib/apt/lists/*

# Ставим зависимости
COPY apps/server/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходники сервера (включая main.py и процессоры)
COPY apps/server/ .

CMD ["python", "main.py"]