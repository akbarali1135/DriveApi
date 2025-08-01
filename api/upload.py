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

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load credentials and build Drive client
def get_drive_client():
    try:
        raw_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_RAW_JSON")
        print("🔐 Loading service account credentials...")
        creds = json.loads(raw_json)
        credentials = service_account.Credentials.from_service_account_info(
            creds, scopes=["https://www.googleapis.com/auth/drive"]
        )
        print("✅ Credentials loaded successfully.")
        return build("drive", "v3", credentials=credentials)
    except Exception as e:
        print("❌ Error loading credentials:", e)
        traceback.print_exc()
        raise

# Root endpoint to serve index.html (optional frontend)
@app.get("/", response_class=HTMLResponse)
async def home():
    try:
        with open("api/index.html", "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return HTMLResponse(content=f"<h2>Error loading page: {e}</h2>", status_code=500)

# File upload endpoint
@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    try:
        drive = get_drive_client()

        # Check folder access
        folder_id = os.getenv("DRIVE_FOLDER_ID")
        print(f"📁 Checking access to folder ID: {folder_id}")
        folder_check = drive.files().get(fileId=folder_id, fields="id, name").execute()
        print(f"✅ Access confirmed for folder: {folder_check['name']}")

        # Prepare file metadata
        metadata = {"name": file.filename}
        if folder_id:
            metadata["parents"] = [folder_id]
        print(f"📤 Preparing to upload: {file.filename}")

        # Read and upload file
        file_stream = io.BytesIO(await file.read())
        media = MediaIoBaseUpload(file_stream, mimetype=file.content_type)
        uploaded = drive.files().create(
            body=metadata, media_body=media, fields="id"
        ).execute()
        print(f"✅ File uploaded with ID: {uploaded['id']}")

        # Make file public
        drive.permissions().create(
            fileId=uploaded["id"],
            body={"type": "anyone", "role": "reader"},
        ).execute()
        print(f"🔗 Public permission granted.")

        # Return shareable URL
        file_url = f"https://drive.google.com/file/d/{uploaded['id']}/view?usp=sharing"
        print(f"📎 Shareable link: {file_url}")
        return {"url": file_url}

    except Exception as e:
        print("❌ Upload failed:", e)
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})
