import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel
from starlette import status

from .config import settings

# --- Constants ---
CACHE_TTL_SECONDS = 3600  # 1 hour cache for JWKS and OIDC
ALGORITHM_VIEW_TOKEN = "HS256"

# --- Caches ---
_jwks_cache = None
_jwks_cache_expiry = 0
_oidc_config_cache = None
_oidc_config_cache_expiry = 0

# --- Security scheme ---
oauth2_scheme = HTTPBearer()


# --- Models ---
class User(BaseModel):
    id: str
    email: Optional[str] = None
    name: Optional[str] = None


# --- OIDC Configuration ---
async def get_oidc_config():
    global _oidc_config_cache, _oidc_config_cache_expiry

    if _oidc_config_cache and time.time() < _oidc_config_cache_expiry:
        return _oidc_config_cache

    authority = f"https://login.microsoftonline.com/{settings.AZURE_AD_TENANT_ID}/v2.0"
    oidc_discovery_url = f"{authority}/.well-known/openid-configuration"

 

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(oidc_discovery_url)
            response.raise_for_status()

        _oidc_config_cache = response.json()
        _oidc_config_cache_expiry = time.time() + CACHE_TTL_SECONDS
        
        return _oidc_config_cache

    except httpx.HTTPError as e:
        print(f"DEBUG: OIDC config fetch error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch OIDC config")


# --- JWKS Fetching ---
async def get_jwks():
    global _jwks_cache, _jwks_cache_expiry

    if _jwks_cache and time.time() < _jwks_cache_expiry:
        return _jwks_cache

    oidc_config = await get_oidc_config()
    jwks_uri = oidc_config.get("jwks_uri")

    if not jwks_uri:
        raise HTTPException(status_code=500, detail="JWKS URI not found in OIDC config")

    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_uri)
            response.raise_for_status()

        _jwks_cache = response.json()
        _jwks_cache_expiry = time.time() + CACHE_TTL_SECONDS
        
        return _jwks_cache

    except httpx.HTTPError as e:
        print(f"DEBUG: JWKS fetch error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch JWKS")


# --- Azure AD Token Validation ---
async def get_current_user(token: HTTPAuthorizationCredentials = Security(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token_value = token.credentials
   

    try:
        jwks = await get_jwks()
        unverified_header = jwt.get_unverified_header(token_value)
        
        kid = unverified_header.get("kid")
        if not kid:
            print("DEBUG: 'kid' not found in token header, token might be encrypted or opaque")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Encrypted or opaque token received. Please provide a signed JWT."
            )
        rsa_key = next(
            (
                {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"],
                }
                for key in jwks["keys"]
                if key["kid"] == unverified_header["kid"]
            ),
            None,
        )
        
        if not rsa_key:
            print("DEBUG: RSA key not found")
            raise credentials_exception

        oidc_config = await get_oidc_config()
        expected_issuer = oidc_config.get("issuer")
       
        if not expected_issuer:
            raise HTTPException(status_code=500, detail="Issuer not found in OIDC config")
        
        payload = jwt.decode(
            token_value,
            rsa_key,
            algorithms=["RS256"],
            audience=settings.AZURE_AD_CLIENT_ID,
            issuer=expected_issuer,
        )
        user_id = payload.get("oid") or payload.get("sub")
        if not user_id:
            raise credentials_exception

        return User(
            id=user_id,
            email=payload.get("email") or payload.get("upn"),
            name=payload.get("name"),
        )

    except JWTError as e:
        print(f"DEBUG: JWTError - {e}")
        raise credentials_exception
    except Exception as e:
        print(f"DEBUG: Unexpected error - {type(e).__name__}: {str(e)}")
        raise credentials_exception


# --- View Token Utilities (HS256) ---
def create_view_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.VIEW_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.VIEW_TOKEN_SECRET_KEY, algorithm=ALGORITHM_VIEW_TOKEN)


def verify_view_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.VIEW_TOKEN_SECRET_KEY, algorithms=[ALGORITHM_VIEW_TOKEN])
    except JWTError:
        return None

