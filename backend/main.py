from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import zipfile
import io
import os
import mimetypes
from typing import List
from pydantic import BaseModel
import logging

from app import auth, config
from app.graph_service import GraphService

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
settings = config.settings

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def get_graph_service():
    return GraphService()

@app.get("/")
async def root():
    return {"message": "Hello World from Backend"}

@app.get("/api/v1/users/me", response_model=auth.User)
async def read_users_me(current_user: auth.User = Depends(auth.get_current_user)):
    return current_user

@app.get("/api/v1/public")
async def public_route():
    return {"message": "This route is public"}

@app.post("/api/v1/upload-zipped-folder/")
async def upload_zipped_folder(
    file: UploadFile = File(...), 
    current_user: auth.User = Depends(auth.get_current_user),
    graph_service: GraphService = Depends(get_graph_service)
):
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Invalid file type. Only .zip files are allowed.")

    if not current_user.id:
        raise HTTPException(status_code=403, detail="User ID not found in token.")

    user_id = current_user.id

    try:
        zip_content = await file.read()
        with zipfile.ZipFile(io.BytesIO(zip_content)) as zf:
            folder_name = os.path.splitext(file.filename)[0]
            logger.info(f"Processing zip for user '{user_id}' into folder '{folder_name}'")

            for member in zf.infolist():
                if member.is_dir():
                    continue 
                
                file_content = zf.read(member.filename)
                await graph_service.upload_file(
                    user_id=user_id,
                    folder_name=folder_name,
                    file_name=member.filename,
                    file_content=file_content
                )
                logger.info(f"Queued upload: {member.filename} for user {user_id}")

    except zipfile.BadZipFile:
        logger.exception("Uploaded file is not a valid ZIP archive.")
        raise HTTPException(status_code=400, detail="Invalid zip file.")
    except Exception as e:
        logger.exception("Unhandled error during zip upload.")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

    return {"message": f"Folder '{folder_name}' uploaded and processed successfully for user {user_id}."}

class FolderItem(BaseModel):
    name: str
    id: str

@app.get("/api/v1/list-folders/", response_model=List[FolderItem])
async def list_folders(
    current_user: auth.User = Depends(auth.get_current_user),
    graph_service: GraphService = Depends(get_graph_service)
):
    if not current_user.id:
        raise HTTPException(status_code=403, detail="User ID not found in token.")

    user_id = current_user.id
    
    try:
        folders_data = await graph_service.list_user_folders(user_id=user_id)
        logger.info(f"Fetched {len(folders_data)} folders for user {user_id}")
        return [FolderItem(**folder) for folder in folders_data]

    except Exception as e:
        logger.exception(f"Error listing folders for user {user_id}")
        raise HTTPException(status_code=500, detail=f"An error occurred while listing folders: {str(e)}")

@app.get("/api/v1/generate-view-link/{folder_identifier:path}")
async def generate_view_link(
    folder_identifier: str,
    current_user: auth.User = Depends(auth.get_current_user)
):
    if not current_user.id:
        raise HTTPException(status_code=403, detail="User ID not found in token.")

    token_data = {
        "sub": current_user.id,
        "fid": folder_identifier,
    }
    view_token = auth.create_view_access_token(data=token_data)
    serve_url = f"/serve/{current_user.id}/{folder_identifier}/index.html?token={view_token}"

    logger.info(f"Generated view link for user {current_user.id} -> {serve_url}")
    return {"view_link": serve_url, "token": view_token}

@app.get("/serve/{user_id}/{folder_identifier:path}/{file_path:path}")
async def serve_content(
    user_id: str,
    folder_identifier: str,
    file_path: str,
    token: str,
    graph_service: GraphService = Depends(get_graph_service)
):
    payload = auth.verify_view_access_token(token)
    if not payload:
        logger.warning("Invalid or expired view token used.")
        raise HTTPException(status_code=401, detail="Invalid or expired view token.")

    token_user_id = payload.get("sub")
    token_folder_id = payload.get("fid")

    if token_user_id != user_id or token_folder_id != folder_identifier:
        logger.warning(f"Token mismatch. Expected: {token_user_id}/{token_folder_id}, Got: {user_id}/{folder_identifier}")
        raise HTTPException(status_code=403, detail="Token does not match requested resource.")

    content_bytes, mime_type = await graph_service.get_file_content(
        user_id=user_id, 
        folder_identifier=folder_identifier, 
        file_path=file_path
    )

    if content_bytes is None:
        logger.warning(f"File not found: {file_path} for user {user_id}")
        raise HTTPException(status_code=404, detail=f"File '{file_path}' not found.")

    if not mime_type:
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = "application/octet-stream"

    logger.info(f"Serving file: {file_path} for user {user_id} with MIME type: {mime_type}")
    return StreamingResponse(io.BytesIO(content_bytes), media_type=mime_type)
