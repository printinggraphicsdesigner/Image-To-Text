from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import io
import time

app = FastAPI(title="Image to Text OCR - Improved Auto Language Detection")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    """ইমেজকে আরও পরিষ্কার করা — বাংলা টেক্সটের জন্য সাহায্য করে"""
    # Convert to grayscale
    image = image.convert('L')
    # Enhance contrast
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2.0)
    # Sharpen
    image = image.filter(ImageFilter.SHARPEN)
    return image

@app.post("/extract-text")
async def extract_text(request: Request, file: UploadFile = File(...)):
    client_ip = request.client.host
    check_rate_limit(client_ip)

    if not file.content_type.startswith("image/"):
        raise HTTPException(400, detail="শুধু ইমেজ ফাইল অনুমোদিত")

    contents = await file.read()
    image = Image.open(io.BytesIO(contents))
    
    # Preprocessing
    processed_image = preprocess_image(image)

    # সেরা অটো কনফিগারেশন (OSD + PSM 6)
    # OSD দিয়ে স্ক্রিপ্ট ডিটেক্ট করে, তারপর PSM 6 দিয়ে লাইন প্রিজার্ভ করে
    config = r'--oem 3 --psm 6 -c tessedit_char_whitelist= --tessdata-dir /usr/share/tesseract-ocr/4.00/tessdata'

    text = pytesseract.image_to_string(processed_image, config=config)

    # যদি টেক্সট খুব কম আসে, তাহলে PSM 3 চেষ্টা করা
    if len(text.strip()) < 20:
        config_fallback = r'--oem 3 --psm 3'
        text = pytesseract.image_to_string(processed_image, config=config_fallback)

    return {
        "text": text.strip(),
        "filename": file.filename
    }

@app.get("/health")
async def health():
    return {"status": "ok"}
