import os
import io
import json
import uuid
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

# Allow frontend to call this
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Google Drive client
def get_drive_service():
    info = json.loads(os.getenv("GOOGLE_SERVICE_ACCOUNT_RAW_JSON"))
    credentials = service_account.Credentials.from_service_account_info(
        info,
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    return build("drive", "v3", credentials=credentials)

@app.post("/api/upload")
async def upload_to_drive(file: UploadFile = File(...)):
    drive_service = get_drive_service()
    file_metadata = {
        "name": file.filename,
    }
    folder_id = os.getenv("DRIVE_FOLDER_ID")
    if folder_id:
        file_metadata["parents"] = [folder_id]

    file_stream = io.BytesIO(await file.read())

    uploaded = drive_service.files().create(
        body=file_metadata,
        media_body=io.BytesIO(file_stream.getvalue()),
        media_mime_type=file.content_type,
        fields="id"
    ).execute()

    # Make file public
    drive_service.permissions().create(
        fileId=uploaded["id"],
        body={"type": "anyone", "role": "reader"},
    ).execute()

    file_url = f"https://drive.google.com/file/d/{uploaded['id']}/view?usp=sharing"
    return JSONResponse(content={"url": file_url})
