from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os, io, json, requests, traceback
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.auth.transport.requests import Request

# Load env variables
load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_access_token():
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")

    token_url = "https://oauth2.googleapis.com/token"
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }

    response = requests.post(token_url, data=payload)
    if response.status_code != 200:
        raise Exception(f"Failed to refresh token: {response.text}")
    return response.json()["access_token"]

@app.get("/", response_class=HTMLResponse)
async def home():
    try:
        with open("api/index.html", "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return HTMLResponse(content="Error loading index.html", status_code=500)

@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    try:
        print(f"Received file: {file.filename}")

        # Step 1: Get access token using refresh token
        access_token = get_access_token()
        print("Access token obtained")

        # Step 2: Build authorized Drive client
        drive = build("drive", "v3", credentials=None, developerKey=None,
                      requestBuilder=lambda *a, **k: Request(headers={"Authorization": f"Bearer {access_token}"}))

        # Step 3: File metadata and upload
        metadata = {"name": file.filename}
        folder_id = os.getenv("DRIVE_FOLDER_ID")
        if folder_id:
            metadata["parents"] = [folder_id]

        file_stream = io.BytesIO(await file.read())
        media = MediaIoBaseUpload(file_stream, mimetype=file.content_type)

        uploaded = drive.files().create(
            body=metadata,
            media_body=media,
            fields="id"
        ).execute()

        print(f"File uploaded with ID: {uploaded['id']}")

        # Step 4: Make file public
        drive.permissions().create(
            fileId=uploaded["id"],
            body={"type": "anyone", "role": "reader"},
        ).execute()

        url = f"https://drive.google.com/file/d/{uploaded['id']}/view?usp=sharing"
        return {"url": url}

    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})
