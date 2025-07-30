import os
import json
import uuid
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware

load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

SERVICE_ACCOUNT_FILE = "service_account.json"

def create_service_account_file():
    raw_json_str = os.getenv("GOOGLE_SERVICE_ACCOUNT_RAW_JSON")
    if not raw_json_str:
        raise Exception("Service account JSON not found in environment")
    raw_json = json.loads(raw_json_str)
    raw_json["private_key"] = raw_json["private_key"].replace("\\n", "\n")
    with open(SERVICE_ACCOUNT_FILE, "w") as f:
        json.dump(raw_json, f)

def get_drive_service():
    create_service_account_file()
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    return build("drive", "v3", credentials=credentials)

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    drive_service = get_drive_service()
    folder_id = os.getenv("DRIVE_FOLDER_ID")
    metadata = {
        "name": file.filename,
        "parents": [folder_id]
    }
    uploaded_file = drive_service.files().create(
        body=metadata,
        media_body=file.file,
        fields="id"
    ).execute()
    drive_service.permissions().create(
        fileId=uploaded_file["id"],
        body={"role": "reader", "type": "anyone"},
    ).execute()
    file_url = f"https://drive.google.com/file/d/{uploaded_file['id']}/view?usp=sharing"
    return JSONResponse({"url": file_url})