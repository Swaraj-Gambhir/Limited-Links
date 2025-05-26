from fastapi import FastAPI, Depends
from app import auth, config # Use absolute imports if backend is a package, or adjust relative paths

app = FastAPI()
settings = config.settings # Load settings

@app.get("/")
async def root():
    return {"message": "Hello World from Backend"}

@app.get("/api/v1/users/me", response_model=auth.User)
async def read_users_me(current_user: auth.User = Depends(auth.get_current_user)):
    return current_user

@app.get("/api/v1/public")
async def public_route():
    return {"message": "This route is public"}

# Placeholder for tokenUrl if using OAuth2PasswordBearer, not strictly needed for HTTPBearer
# @app.post("/token") 
# async def login_for_access_token():
# return {"access_token": "some_token", "token_type": "bearer"}
