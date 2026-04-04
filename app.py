from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import io
import time

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rate_limit = {}

def check_rate_limit(ip):
    now = time.time()
    window = 6 * 3600

    if ip not in rate_limit:
        rate_limit[ip] = []

    rate_limit[ip] = [t for t in rate_limit[ip] if now - t < window]

    if len(rate_limit[ip]) >= 10:
        raise HTTPException(429, "Limit exceeded")

    rate_limit[ip].append(now)

def preprocess(image):
    image = image.convert("L")
    image = ImageEnhance.Contrast(image).enhance(2.5)
    image = image.filter(ImageFilter.SHARPEN)
    return image

@app.post("/extract-text")
async def extract_text(request: Request, file: UploadFile = File(...)):
    check_rate_limit(request.client.host)

    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        image = preprocess(image)

        text = pytesseract.image_to_string(image, config="--oem 3 --psm 6 -l eng")

        return {"text": text}

    except Exception as e:
        print("ERROR:", e)  # Render log এ দেখবা
        raise HTTPException(500, detail=str(e))

@app.get("/")
def root():
    return {"status": "running"}
