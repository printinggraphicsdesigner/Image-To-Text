from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import io
import time

app = FastAPI(title="Image to Text OCR - Auto Bengali + English")

# Improved CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # WordPress এর জন্য
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Rate limiter
rate_limit = {}

def check_rate_limit(client_ip: str):
    now = time.time()
    window = 6 * 3600
    max_requests = 10

    if client_ip not in rate_limit:
        rate_limit[client_ip] = []
    
    rate_limit[client_ip] = [ts for ts in rate_limit[client_ip] if now - ts < window]
    
    if len(rate_limit[client_ip]) >= max_requests:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. ১০টা ইমেজ প্রতি ৬ ঘণ্টায়।")
    
    rate_limit[client_ip].append(now)

def preprocess_image(image):
    """বাংলা টেক্সটের জন্য ইমেজ পরিষ্কার করা"""
    image = image.convert('L')                    # Grayscale
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2.5)                 # Contrast বাড়ানো
    image = image.filter(ImageFilter.SHARPEN)     # Sharpen
    return image

@app.post("/extract-text")
async def extract_text(request: Request, file: UploadFile = File(...)):
    client_ip = request.client.host
    check_rate_limit(client_ip)

    if not file.content_type.startswith("image/"):
        raise HTTPException(400, detail="শুধু ইমেজ ফাইল অনুমোদিত")

    contents = await file.read()
    image = Image.open(io.BytesIO(contents))
    
    processed_image = preprocess_image(image)

    # Bengali + English ফোর্স করে + লাইন প্রিজার্ভ
    config = r'--oem 3 --psm 6 -l ben+eng'

    text = pytesseract.image_to_string(processed_image, config=config)

    # যদি খুব কম টেক্সট আসে তাহলে fallback
    if len(text.strip()) < 30:
        config2 = r'--oem 3 --psm 3 -l ben+eng'
        text = pytesseract.image_to_string(processed_image, config=config2)

    return {
        "text": text.strip(),
        "filename": file.filename
    }

@app.get("/health")
async def health():
    return {"status": "ok", "message": "Server is running"}
