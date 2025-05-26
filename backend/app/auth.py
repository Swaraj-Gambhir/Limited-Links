from fastapi import HTTPException, Security
from fastapi.security import OAuth2PasswordBearer, HTTPBearer # Or HTTPBearer depending on NextAuth token type
from jose import JWTError, jwt
from pydantic import BaseModel
from starlette import status

from .config import settings # Assuming your config.py is in the same directory

# This will depend on how NextAuth.js issues tokens. 
# If it's a simple Bearer token, HTTPBearer might be more appropriate.
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token") # Placeholder
oauth2_scheme = HTTPBearer() 

class User(BaseModel):
    id: str | None = None
    email: str | None = None
    # Add other fields that you expect in the token

async def get_current_user(token: str = Security(oauth2_scheme)):
    # In a real scenario, you'd get the public key from Azure AD (JWKS URI)
    # to verify the token signature.
    # For now, this is a placeholder and might need significant adjustment
    # once NextAuth.js token structure and signing are known.
    
    # This is a very basic placeholder.
    # You will need to implement proper JWT validation using Azure AD's public keys.
    # Consider using a library like `msal` for robust validation if needed.
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # This is a simplified example.
        # You'll need to know the structure of the token from NextAuth/Azure AD
        # and what claims to expect (e.g., 'sub', 'email', 'tid').
        # Also, the key for decoding will be Azure AD's public signing key.
        # For now, we'll assume the token itself contains user info or we mock it.
        # payload = jwt.decode(token.credentials, "YOUR_SECRET_KEY_OR_PUBLIC_KEY", algorithms=["RS256"], audience=settings.AZURE_AD_CLIENT_ID)
        # username: str = payload.get("sub")
        # if username is None:
        #     raise credentials_exception
        
        # Mocking user data based on token presence for now
        # In a real app, decode and verify token, then extract user info
        if not token.credentials:
            raise credentials_exception
        
        # Placeholder: Extract claims. The actual claims will depend on your Azure AD token configuration.
        # Common claims: sub, name, email, oid (object id), tid (tenant id)
        # This is NOT secure and is for demonstration ONLY.
        # You MUST validate the token signature against Azure AD's public keys.
        # Example (very simplified, assumes token is unverified JWT string):
        # decoded_token = jwt.decode(token.credentials, options={"verify_signature": False}) # DO NOT DO THIS IN PRODUCTION
        # user_email = decoded_token.get("email") or decoded_token.get("upn")
        # user_id = decoded_token.get("oid") or decoded_token.get("sub")

        # For now, let's return a mock user if a token is present.
        # Replace this with actual token parsing and validation.
        return User(id="mockuser", email="mock@example.com")

    except JWTError:
        raise credentials_exception
    except Exception: # Catch any other error during placeholder logic
        raise credentials_exception

# For View Tokens
from datetime import datetime, timedelta, timezone
# settings is already imported

ALGORITHM = "HS256" # For view tokens

def create_view_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.VIEW_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.VIEW_TOKEN_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_view_access_token(token: str):
    try:
        payload = jwt.decode(token, settings.VIEW_TOKEN_SECRET_KEY, algorithms=[ALGORITHM])
        # You could add more checks here, like if the required data (e.g., user_id, folder_id) is in payload
        return payload
    except JWTError:
        return None
