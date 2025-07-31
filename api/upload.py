from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os, io, json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv
import traceback

load_dotenv()
app = FastAPI()

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the frontend
@app.get("/", response_class=HTMLResponse)
async def home():
    with open("api/index.html", "r", encoding="utf-8") as f:
        return f.read()

# Upload endpoint
@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    try:
        creds = json.loads(os.getenv("GOOGLE_SERVICE_ACCOUNT_RAW_JSON"))
        credentials = service_account.Credentials.from_service_account_info(
            creds,
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        drive = build("drive", "v3", credentials=credentials)

        metadata = {"name": file.filename}
        if os.getenv("DRIVE_FOLDER_ID"):
            metadata["parents"] = [os.getenv("DRIVE_FOLDER_ID")]

        file_stream = io.BytesIO(await file.read())
        uploaded = drive.files().create(
            body=metadata,
            media_body=io.BytesIO(file_stream.getvalue()),
            media_mime_type=file.content_type,
            fields="id"
        ).execute()

        drive.permissions().create(
            fileId=uploaded["id"],
            body={"type": "anyone", "role": "reader"}
        ).execute()

        return {"url": f"https://drive.google.com/file/d/{uploaded['id']}/view?usp=sharing"}
    except Exception as e:
        print("Upload failed:", e)
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})