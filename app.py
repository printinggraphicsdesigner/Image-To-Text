from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import io

app = FastAPI(title="Image to Text Converter")

# Strong CORS Configuration (Failed to fetch এর মূল কারণ)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # WordPress এর জন্য সব অনুমোদন (পরে নির্দিষ্ট করতে পারবেন)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

rate_limit = {}

def check_rate_limit(client_ip: str):
    now = time.time()
    window = 6 * 3600
    if client_ip not in rate_limit:
        rate_limit[client_ip] = []
    rate_limit[client_ip] = [ts for ts in rate_limit[client_ip] if now - ts < window]
    if len(rate_limit[client_ip]) >= 10:
        raise HTTPException(429, detail="Rate limit exceeded. ১০টা ইমেজ প্রতি ৬ ঘণ্টায়।")
    rate_limit[client_ip].append(now)

def preprocess_image(image):
    image = image.convert('L')
    image = ImageEnhance.Contrast(image).enhance(3.0)   # Contrast বেশি
    image = image.filter(ImageFilter.SHARPEN)
    image = image.filter(ImageFilter.MedianFilter(3))
    # Resize for better OCR accuracy
    image = image.resize((int(image.width * 2), int(image.height * 2)), Image.LANCZOS)
    return image

@app.post("/extract-text")
async def extract_text(request: Request, file: UploadFile = File(...)):
    client_ip = request.client.host
    check_rate_limit(client_ip)

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, detail="Only image files allowed")

    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        processed = preprocess_image(image)

        # Mixed language support (Chinese + English + Bengali)
        config = r'--oem 3 --psm 6 -l chi_sim+eng+ben'

        text = pytesseract.image_to_string(processed, config=config)

        # Fallback if text is too short
        if len(text.strip()) < 40:
            text = pytesseract.image_to_string(processed, config=r'--oem 3 --psm 3 -l chi_sim+eng+ben')

        return {"text": text.strip()}

    except Exception as e:
        raise HTTPException(500, detail=f"Processing failed: {str(e)}")

@app.get("/health")
async def health():
    return {"status": "ok", "message": "Server running"}
