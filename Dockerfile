FROM python:3.11-slim

# Tesseract + সব ভাষার প্যাকেজ (১২০+ ভাষা)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-all \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 10000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "10000"]
