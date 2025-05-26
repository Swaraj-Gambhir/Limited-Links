from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware # If not already added, for frontend interaction
from fastapi.responses import StreamingResponse, HTMLResponse # For serving files
import zipfile
import io
import os # For path joining, if saving temp files or creating paths
from typing import List # For response model
from pydantic import BaseModel # For FolderItem model
import mimetypes # To guess MIME types


from app import auth, config # Corrected import path
from app.graph_service import GraphService # Corrected import path
# Assuming create_view_access_token, verify_view_access_token are in auth.py
# from app.auth import create_view_access_token, verify_view_access_token
# No, they are directly available via the auth module: auth.create_view_access_token

app = FastAPI()
settings = config.settings

# Add CORS middleware if not present - adjust origins as needed for your frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], # Adjust to your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get GraphService instance
# This could be enhanced if GraphService needs async initialization for its client
async def get_graph_service():
    service = GraphService()
    # If _initialize_sharepoint_ids needs to be called for every request using the service,
    # or if the service instance can be reused and initialized once.
    # For now, methods within GraphService will call _initialize_sharepoint_ids if needed.
    return service

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

    user_id = current_user.id # Assuming current_user.id is populated (e.g., with 'oid' or 'sub' from token)
    
    try:
        zip_content = await file.read()
        with zipfile.ZipFile(io.BytesIO(zip_content)) as zf:
            # Extract original zip filename without extension to use as base folder name
            folder_name = os.path.splitext(file.filename)[0]

            for member in zf.infolist():
                if member.is_dir():
                    # Optionally create directories explicitly if graph_service doesn't handle nested paths
                    # For now, we assume graph_service.upload_file can handle paths
                    continue 
                
                file_content = zf.read(member.filename)
                # The path in SharePoint should be relative to the user's root upload folder
                # e.g., user_id/original_zip_name/path/to/file/in/zip/file.txt
                # The `member.filename` contains the path within the zip.
                
                # We'll pass folder_name (derived from zip name) and member.filename (path within zip)
                # to graph_service.upload_file. It will need to construct the full SharePoint path.
                # For now, graph_service.upload_file is a placeholder.
                await graph_service.upload_file(
                    user_id=user_id,
                    folder_name=folder_name, # This is the "root" folder for this specific upload
                    file_name=member.filename, # This is the path/name within the zip
                    file_content=file_content
                )
                # print(f"Extracted and (conceptually) queued for upload: {member.filename} to user {user_id}'s folder {folder_name}")

    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid zip file.")
    except Exception as e:
        # Log the exception e
        # print(f"Error during zip processing or conceptual upload: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

    return {"message": f"Folder '{folder_name}' uploaded and processed successfully for user {user_id}."}


# Define a simple response model for a folder item
# You might want to expand this later with more details from SharePoint
class FolderItem(BaseModel):
    name: str
    id: str # Could be SharePoint item ID or path, depending on what graph_service returns
    # path: Optional[str] = None # If you want to return the full path too
    # created_date: Optional[str] = None # Example of other useful info

@app.get("/api/v1/list-folders/", response_model=List[FolderItem])
async def list_folders(
    current_user: auth.User = Depends(auth.get_current_user),
    graph_service: GraphService = Depends(get_graph_service)
):
    if not current_user.id:
        raise HTTPException(status_code=403, detail="User ID not found in token.")

    user_id = current_user.id
    
    try:
        # The graph_service.list_user_folders is currently a placeholder.
        # It's expected to return a list of objects/dictionaries,
        # each representing a folder and having at least 'name' and 'id' keys.
        folders_data = await graph_service.list_user_folders(user_id=user_id)
        
        # Convert the data from graph_service (which might be dicts)
        # into FolderItem Pydantic models.
        # This assumes graph_service.list_user_folders will return a list of dicts like:
        # [{'name': 'folder1', 'id': 'sp_id1'}, {'name': 'folder2', 'id': 'sp_id2'}]
        response_items = [FolderItem(**folder_data) for folder_data in folders_data]
        return response_items

    except Exception as e:
        # Log the exception e
        # print(f"Error listing folders for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred while listing folders: {str(e)}")


@app.get("/api/v1/generate-view-link/{folder_identifier:path}")
async def generate_view_link(
    folder_identifier: str, # This could be a folder name or a SharePoint item ID
    current_user: auth.User = Depends(auth.get_current_user)
):
    if not current_user.id:
        raise HTTPException(status_code=403, detail="User ID not found in token.")
    
    # Here, you might want to verify that folder_identifier actually belongs to current_user
    # by checking against data from graph_service.list_user_folders or a similar method.
    # For now, we'll assume the folder_identifier is valid for the user.

    token_data = {
        "sub": current_user.id, # Subject (user_id)
        "fid": folder_identifier, # Folder Identifier
        # Add any other relevant data, like specific permissions for this view
    }
    view_token = auth.create_view_access_token(data=token_data)
    
    # Construct the serving URL. This needs to match the /serve endpoint.
    # The file_path part will be appended by the client or by how index.html requests assets.
    # We serve index.html by default if no file_path is given to /serve.
    # The folder_identifier might need to be URL-encoded if it contains special characters.
    
    # Link to the "index.html" of that folder by default
    serve_url = f"/serve/{current_user.id}/{folder_identifier}/index.html?token={view_token}"
    # In a real app, this URL should be based on your app's actual domain/host.
    # For local dev, relative is fine if frontend and backend are on same origin or proxied.
    # If not, construct full URL: request.url_for('serve_content_route_name', ...)
    
    return {"view_link": serve_url, "token": view_token}


@app.get("/serve/{user_id}/{folder_identifier:path}/{file_path:path}")
async def serve_content(
    user_id: str,
    folder_identifier: str,
    file_path: str,
    token: str, # Token comes from query parameter
    graph_service: GraphService = Depends(get_graph_service)
):
    payload = auth.verify_view_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired view token.")
    
    token_user_id = payload.get("sub")
    token_folder_id = payload.get("fid")

    # Validate that the token matches the path parameters to prevent misuse
    if token_user_id != user_id or token_folder_id != folder_identifier:
        raise HTTPException(status_code=403, detail="Token does not match requested resource.")

    # Fetch file content using graph_service
    # The file_path here is relative to the folder_identifier in SharePoint
    content_bytes, mime_type = await graph_service.get_file_content(
        user_id=user_id, 
        folder_identifier=folder_identifier, 
        file_path=file_path
    )

    if content_bytes is None:
        raise HTTPException(status_code=404, detail=f"File '{file_path}' not found.")

    actual_mime_type = mime_type
    if not actual_mime_type:
        # Guess MIME type if graph_service didn't provide it
        actual_mime_type, _ = mimetypes.guess_type(file_path)
        if actual_mime_type is None:
            actual_mime_type = "application/octet-stream" # Default if guess fails

    return StreamingResponse(io.BytesIO(content_bytes), media_type=actual_mime_type)
