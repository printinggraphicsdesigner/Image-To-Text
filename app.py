from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pytesseract
from PIL import Image
import io
import time
from datetime import datetime

app = FastAPI(title="Image to Text OCR")

# CORS — WordPress থেকে কল করার জন্য
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # প্রোডাকশনে আপনার ওয়ার্ডপ্রেস ডোমেইন দিন
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory rate limiter (কোনো ডাটাবেস লাগবে না)
rate_limit = {}  # ip: [timestamp1, timestamp2, ...]

def check_rate_limit(client_ip: str):
    now = time.time()
    window = 6 * 3600  # 6 hours in seconds
    max_requests = 10

    if client_ip not in rate_limit:
        rate_limit[client_ip] = []
    
    # পুরনো টাইমস্ট্যাম্প সরিয়ে ফেলুন
    rate_limit[client_ip] = [ts for ts in rate_limit[client_ip] if now - ts < window]
    
    if len(rate_limit[client_ip]) >= max_requests:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. You can upload 10 images every 6 hours."
        )
    
    rate_limit[client_ip].append(now)

@app.post("/extract-text")
async def extract_text(request: Request, file: UploadFile = File(...)):
    client_ip = request.client.host
    check_rate_limit(client_ip)

    if not file.content_type.startswith("image/"):
        raise HTTPException(400, detail="Only image files allowed")

    # ইমেজ মেমরিতে লোড (কোনো ডিস্কে সেভ নয়)
    contents = await file.read()
    image = Image.open(io.BytesIO(contents))

    # Tesseract OCR
    text = pytesseract.image_to_string(image, lang='eng')

    return {"text": text.strip(), "filename": file.filename}

@app.get("/health")
async def health():
    return {"status": "ok", "time": datetime.now().isoformat()}
