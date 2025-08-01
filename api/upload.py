from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os, io, json, traceback
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from dotenv import load_dotenv

# Load environment variables
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
        print("Serving index.html")
        with open("api/index.html", "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print("Failed to serve index.html:", e)
        return HTMLResponse(content="Error loading index.html", status_code=500)

@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    try:
        print(f"Received file: {file.filename}, content type: {file.content_type}")

        # Load service account credentials
        raw_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_RAW_JSON")
        if not raw_json:
            print("Environment variable 'GOOGLE_SERVICE_ACCOUNT_RAW_JSON' is missing")
            return JSONResponse(status_code=500, content={"error": "Missing credentials"})

        creds = json.loads(raw_json)
        print("Loaded service account JSON successfully")

        credentials = service_account.Credentials.from_service_account_info(
            creds, scopes=["https://www.googleapis.com/auth/drive"]
        )
        print("Service account credentials created")

        drive = build("drive", "v3", credentials=credentials)
        print("Google Drive client built successfully")

        # Build file metadata
        metadata = {"name": file.filename}
        folder_id = os.getenv("DRIVE_FOLDER_ID")
        if folder_id:
            metadata["parents"] = [folder_id]
            print(f"Using folder ID: {folder_id}")
        else:
            print("No folder ID specified. Uploading to root.")

        file_stream = io.BytesIO(await file.read())
        media = MediaIoBaseUpload(file_stream, mimetype=file.content_type)

        print("Starting file upload to Google Drive...")
        uploaded = drive.files().create(
            body=metadata,
            media_body=media,
            fields="id"
        ).execute()

        print(f"File uploaded successfully. File ID: {uploaded['id']}")

        # Set file permission to public
        print("Setting file permissions to 'anyone with link can read'")
        drive.permissions().create(
            fileId=uploaded["id"],
            body={"type": "anyone", "role": "reader"},
        ).execute()

        url = f"https://drive.google.com/file/d/{uploaded['id']}/view?usp=sharing"
        print(f"File available at: {url}")

        return {"url": url}

    except Exception as e:
        print("Upload failed:", str(e))
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})
