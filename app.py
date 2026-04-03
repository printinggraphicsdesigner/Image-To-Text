from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Form
from fastapi.middleware.cors import CORSMiddleware
import pytesseract
from PIL import Image
import io
import time

app = FastAPI(title="Image to Text OCR - All Languages")

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
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. ১০টা ইমেজ প্রতি ৬ ঘণ্টায়।"
        )
    
    rate_limit[client_ip].append(now)

@app.post("/extract-text")
async def extract_text(request: Request, file: UploadFile = File(...), lang: str = Form("eng")):
    client_ip = request.client.host
    check_rate_limit(client_ip)

    if not file.content_type.startswith("image/"):
        raise HTTPException(400, detail="শুধু ইমেজ ফাইল অনুমোদিত")

    contents = await file.read()
    image = Image.open(io.BytesIO(contents))

    # মাল্টি-ল্যাঙ্গুয়েজ সাপোর্ট
    text = pytesseract.image_to_string(image, lang=lang)

    return {
        "text": text.strip(),
        "filename": file.filename,
        "languages_used": lang
    }

@app.get("/health")
async def health():
    return {"status": "ok"}
