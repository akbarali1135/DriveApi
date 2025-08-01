from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os, io, json, traceback
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

# CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
async def home():
    try:
        print("Serving index.html...")
        with open("api/index.html", "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print("Error loading homepage:", e)
        return HTMLResponse("<h1>Error loading homepage</h1>", status_code=500)

@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    print("Received file:", file.filename)

    try:
        raw_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_RAW_JSON")
        if not raw_json:
            raise ValueError("Missing GOOGLE_SERVICE_ACCOUNT_RAW_JSON in environment")

        print("Parsing service account credentials...")
        creds_dict = json.loads(raw_json)
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=["https://www.googleapis.com/auth/drive"]
        )

        print("Building Drive API client...")
        drive = build("drive", "v3", credentials=credentials)

        metadata = {"name": file.filename}
        folder_id = os.getenv("DRIVE_FOLDER_ID")
        if folder_id:
            metadata["parents"] = [folder_id]
            print("Uploading to folder:", folder_id)

        print("Reading file into memory...")
        file_stream = io.BytesIO(await file.read())
        media = MediaIoBaseUpload(file_stream, mimetype=file.content_type)

        print("Creating file on Google Drive...")
        uploaded = drive.files().create(
            body=metadata,
            media_body=media,
            fields="id"
        ).execute()

        file_id = uploaded["id"]
        print("File uploaded successfully. File ID:", file_id)

        print("Setting permissions...")
        drive.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader"}
        ).execute()

        shareable_url = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
        print("Shareable URL:", shareable_url)

        return {"url": shareable_url}

    except Exception as e:
        print("❌ Upload failed:", e)
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})
