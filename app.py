from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import io
import time

app = FastAPI(title="Image to Text Converter")

# CORS Fix
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate Limiter
rate_limit = {}

def check_rate_limit(client_ip: str):
    now = time.time()
    window = 6 * 3600  # 6 hours
    max_requests = 10

    if client_ip not in rate_limit:
        rate_limit[client_ip] = []
    
    rate_limit[client_ip] = [ts for ts in rate_limit[client_ip] if now - ts < window]
    
    if len(rate_limit[client_ip]) >= max_requests:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. You can upload 10 images every 6 hours."
        )
    
    rate_limit[client_ip].append(now)

def preprocess_image(image):
    """বাংলা টেক্সটের জন্য ইমেজ পরিষ্কার করা"""
    # Grayscale
    image = image.convert('L')
    # Contrast বাড়ানো
    image = ImageEnhance.Contrast(image).enhance(2.5)
    # Sharpen
    image = image.filter(ImageFilter.SHARPEN)
    # কিছুটা resize যদি দরকার হয়
    image = image.resize((image.width * 2, image.height * 2), Image.LANCZOS)
    return image

@app.post("/extract-text")
async def extract_text(request: Request, file: UploadFile = File(...)):
    client_ip = request.client.host
    check_rate_limit(client_ip)

    if not file.content_type.startswith("image/"):
        raise HTTPException(400, detail="Only image files are allowed")

    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        
        # Preprocessing
        processed_image = preprocess_image(image)

        # সেরা কনফিগারেশন বাংলা + ইংরেজির জন্য
        # PSM 6 = লাইন স্ট্রাকচার ভালোভাবে রাখে
        # ben+eng = বাংলা ও ইংরেজি দুটোই চিনবে
        config = r'--oem 3 --psm 6 -l ben+eng'

        text = pytesseract.image_to_string(processed_image, config=config)

        # ফলব্যাক যদি খুব কম টেক্সট আসে
        if len(text.strip()) < 50:
            config_fallback = r'--oem 3 --psm 3 -l ben+eng'
            text = pytesseract.image_to_string(processed_image, config=config_fallback)

        return {
            "text": text.strip(),
            "filename": file.filename
        }

    except Exception as e:
        raise HTTPException(500, detail=f"Processing error: {str(e)}")

@app.get("/health")
async def health():
    return {"status": "ok"}
