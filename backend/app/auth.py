import httpx
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel, Field # Added Field for alias
from starlette import status
import time # For cache expiry

from .config import settings # Your existing settings

# --- JWKS Handling ---
# Global cache for JWKS keys and OIDC config
_jwks_cache = None
_jwks_cache_expiry = 0
_oidc_config_cache = None
_oidc_config_cache_expiry = 0
CACHE_TTL_SECONDS = 3600  # Cache JWKS and OIDC config for 1 hour

async def get_oidc_config():
    global _oidc_config_cache, _oidc_config_cache_expiry
    if _oidc_config_cache and time.time() < _oidc_config_cache_expiry:
        return _oidc_config_cache

    # Construct the OpenID Connect configuration endpoint URL
    # Example: https://login.microsoftonline.com/{tenant_id}/v2.0/.well-known/openid-configuration
    # For multi-tenant apps or if using 'common' or 'organizations' authority:
    # authority = f"https://login.microsoftonline.com/{settings.AZURE_AD_TENANT_ID}/v2.0" 
    # If your app registration allows "Accounts in any organizational directory (Any Azure AD directory - Multitenant)"
    # or "Accounts in any organizational directory ... and personal Microsoft accounts",
    # you might use 'common' or 'organizations' in place of tenant_id for discovery.
    # However, for validating tokens issued to *your* app, the authority used by NextAuth
    # (which includes your tenant_id) is often the most direct one to use here.
    
    # Using the tenant ID from settings for constructing the authority.
    # This assumes tokens are issued from your specific tenant.
    authority = f"https://login.microsoftonline.com/{settings.AZURE_AD_TENANT_ID}/v2.0"
    # If NextAuth uses a different authority (e.g. "common" for multi-tenant apps), adjust this.
    # The issuer claim in the token ("iss") should match this authority.
    
    oidc_discovery_url = f"{authority}/.well-known/openid-configuration"
    
    print(f"DEBUG: auth.py - Fetching OIDC config from: {oidc_discovery_url}")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(oidc_discovery_url)
            response.raise_for_status()
            _oidc_config_cache = response.json()
            _oidc_config_cache_expiry = time.time() + CACHE_TTL_SECONDS
            print("DEBUG: auth.py - Successfully fetched and cached OIDC config.")
            return _oidc_config_cache
        except httpx.HTTPStatusError as e:
            print(f"DEBUG: auth.py - HTTP error fetching OIDC config: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=500, detail="Could not fetch OIDC server configuration from Azure AD.")
        except Exception as e:
            print(f"DEBUG: auth.py - Error fetching OIDC config: {str(e)}")
            raise HTTPException(status_code=500, detail="Could not fetch OIDC server configuration.")


async def get_jwks():
    global _jwks_cache, _jwks_cache_expiry
    if _jwks_cache and time.time() < _jwks_cache_expiry:
        return _jwks_cache

    oidc_config = await get_oidc_config()
    jwks_uri = oidc_config.get("jwks_uri")
    if not jwks_uri:
        print("DEBUG: auth.py - jwks_uri not found in OIDC config.")
        raise HTTPException(status_code=500, detail="jwks_uri not found in OIDC configuration.")

    print(f"DEBUG: auth.py - Fetching JWKS from: {jwks_uri}")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(jwks_uri)
            response.raise_for_status()
            _jwks_cache = response.json()
            _jwks_cache_expiry = time.time() + CACHE_TTL_SECONDS
            print("DEBUG: auth.py - Successfully fetched and cached JWKS.")
            return _jwks_cache
        except httpx.HTTPStatusError as e:
            print(f"DEBUG: auth.py - HTTP error fetching JWKS: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=500, detail="Could not fetch JWKS from Azure AD.")
        except Exception as e:
            print(f"DEBUG: auth.py - Error fetching JWKS: {str(e)}")
            raise HTTPException(status_code=500, detail="Could not fetch JWKS.")
# --- End JWKS Handling ---

oauth2_scheme = HTTPBearer()

class User(BaseModel):
    id: str # Will be populated with 'oid' (Object ID) or 'sub' (Subject)
    email: str | None = None # Will be populated with 'email' or 'upn'
    name: str | None = None # Will be populated with 'name'
    # Add other fields as needed, ensure they exist in the token or can be None.
    # Using alias for 'oid' if that's the claim name in your token for user ID
    # oid: str | None = Field(None, alias="oid") 

async def get_current_user(token: HTTPAuthorizationCredentials = Security(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token_value = token.credentials
    print(f"DEBUG: auth.py - Received token for validation: {token_value[:20]}...") # Log part of token

    try:
        jwks = await get_jwks()
        unverified_header = jwt.get_unverified_header(token_value)
        rsa_key = {}
        for key in jwks["keys"]:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }
                break
        
        if not rsa_key:
            print("DEBUG: auth.py - RSA key not found for token KID.")
            raise credentials_exception # Or a more specific error

        # Construct the expected issuer. This must match the 'iss' claim in the token.
        # For Azure AD, it's typically https://login.microsoftonline.com/{tenant_id}/v2.0
        # Or for personal accounts + Entra ID, it might be different (e.g. involving sts.windows.net)
        # Check your token's "iss" claim if unsure.
        # The OIDC config (issuer field) should also confirm this.
        oidc_config = await get_oidc_config() # Get OIDC config again (cached)
        expected_issuer = oidc_config.get("issuer")
        if not expected_issuer:
             print("DEBUG: auth.py - Expected issuer not found in OIDC config.")
             raise HTTPException(status_code=500, detail="Issuer not found in OIDC configuration.")

        print(f"DEBUG: auth.py - Decoding JWT. Expected Audience: '{settings.AZURE_AD_CLIENT_ID}', Expected Issuer: '{expected_issuer}'")

        payload = jwt.decode(
            token_value,
            rsa_key,
            algorithms=["RS256"],
            audience=settings.AZURE_AD_CLIENT_ID, # Your App's Client ID
            issuer=expected_issuer 
        )
        
        # Extract claims. Common claims from Azure AD:
        # oid: Object ID of the user (good for a stable user ID)
        # sub: Subject (can also be used as user ID, often same as oid for users)
        # email: User's email
        # upn: User Principal Name (often same as email for work accounts)
        # name: User's display name
        # tid: Tenant ID
        
        user_id = payload.get("oid") or payload.get("sub")
        if user_id is None:
            print("DEBUG: auth.py - 'oid' or 'sub' claim missing in token.")
            raise credentials_exception

        user_email = payload.get("email") or payload.get("upn")
        user_name = payload.get("name")
        
        print(f"DEBUG: auth.py - Token validated successfully. User ID (oid/sub): {user_id}, Email: {user_email}")
        return User(id=user_id, email=user_email, name=user_name)

    except JWTError as e:
        print(f"DEBUG: auth.py - JWTError during token validation: {str(e)}")
        raise credentials_exception
    except Exception as e:
        print(f"DEBUG: auth.py - Unexpected error during token validation: {type(e).__name__} - {str(e)}")
        raise credentials_exception

# Note: The 'VIEW_TOKEN_SECRET_KEY', 'create_view_access_token', 'verify_view_access_token'
# for the temporary view links should remain if they are separate and use HS256.
# This new logic is for validating the main Azure AD Bearer token for API authentication.
# Ensure ALGORITHM = "HS256" and settings.VIEW_TOKEN_SECRET_KEY are still present for those functions
# if they were in this file. For clarity, view token utils could be moved to a separate file.
# For now, assuming they are still here and distinct.

# --- View token functions ---
from datetime import datetime, timedelta, timezone
# from .config import settings # Already imported above

ALGORITHM_VIEW_TOKEN = "HS256" 

def create_view_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.VIEW_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.VIEW_TOKEN_SECRET_KEY, algorithm=ALGORITHM_VIEW_TOKEN)
    return encoded_jwt

def verify_view_access_token(token: str):
    try:
        payload = jwt.decode(token, settings.VIEW_TOKEN_SECRET_KEY, algorithms=[ALGORITHM_VIEW_TOKEN])
        return payload
    except JWTError:
        return None
