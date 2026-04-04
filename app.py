from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import io

app = FastAPI(title="Image to Text Converter - High Accuracy")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rate_limit = {}

def check_rate_limit(client_ip: str):
    now = time.time()
    if client_ip not in rate_limit:
        rate_limit[client_ip] = []
    rate_limit[client_ip] = [ts for ts in rate_limit[client_ip] if now - ts < 6*3600]
    if len(rate_limit[client_ip]) >= 10:
        raise HTTPException(429, detail="১০টা ইমেজ প্রতি ৬ ঘণ্টা।")
    rate_limit[client_ip].append(now)

def preprocess_image(image):
    image = image.convert('L')
    image = ImageEnhance.Contrast(image).enhance(2.8)
    image = image.filter(ImageFilter.SHARPEN)
    image = image.filter(ImageFilter.MedianFilter(3))
    # উচ্চ রেজোলিউশনের জন্য স্কেল আপ
    image = image.resize((int(image.width * 1.8), int(image.height * 1.8)), Image.LANCZOS)
    return image

@app.post("/extract-text")
async def extract_text(request: Request, file: UploadFile = File(...)):
    client_ip = request.client.host
    check_rate_limit(client_ip)

    if not file.content_type.startswith("image/"):
        raise HTTPException(400, detail="শুধু ইমেজ ফাইল অনুমোদিত")

    contents = await file.read()
    image = Image.open(io.BytesIO(contents))
    processed = preprocess_image(image)

    # High accuracy config (বাংলা + ইংরেজি + চাইনিজ)
    config = r'--oem 3 --psm 6 -l ben+eng+chi_sim'

    text = pytesseract.image_to_string(processed, config=config)

    # ফলব্যাক (যদি খুব কম টেক্সট আসে)
    if len(text.strip()) < 30:
        config2 = r'--oem 3 --psm 3 -l ben+eng+chi_sim'
        text = pytesseract.image_to_string(processed, config=config2)

    return {"text": text.strip(), "filename": file.filename}

@app.get("/health")
async def health():
    return {"status": "ok"}
