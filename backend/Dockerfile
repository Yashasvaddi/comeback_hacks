FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime

# System dependencies for PaddleOCR, Pillow, OpenCV, and healthchecks.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# Install project dependencies, including edge-tts.
# PyTorch is already included in the base image.
RUN pip install --no-cache-dir --default-timeout=300 --retries=10 \
    -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]