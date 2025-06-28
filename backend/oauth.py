import os
import json
import logging
import base64
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from starlette.responses import Response
from starlette.status import HTTP_401_UNAUTHORIZED

SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/calendar.readonly'
]
BASE_DIR = os.path.join(os.path.dirname(__file__), '..')
CREDENTIALS_PATH = os.path.join(BASE_DIR, 'env', 'credentials.json')
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/oauth2callback")

router = APIRouter()

async def get_current_user(request: Request) -> Credentials:
    logging.info("--- Attempting to authenticate user ---")
    auth_header = request.headers.get("Authorization")
    logging.info(f"Received Authorization header: {auth_header}")

    if not auth_header or not auth_header.startswith("Bearer "):
        logging.warning("Authentication failed: Missing or malformed 'Bearer' token.")
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token_str_b64 = auth_header.split(" ")[1]
    logging.info(f"Extracted Base64 token string: {token_str_b64}")

    try:
        token_str = base64.b64decode(token_str_b64).decode('utf-8')
        logging.info(f"Decoded token string: {token_str}")
        token_data = json.loads(token_str)
        logging.info("Successfully parsed token string into JSON.")
        creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        
        if not creds.valid:
            logging.warning("Token is not valid. Checking if it can be refreshed.")
            if creds.expired and creds.refresh_token:
                logging.info("Token is expired, attempting to refresh.")
                from google.auth.transport.requests import Request as GoogleRequest
                creds.refresh(GoogleRequest())
                logging.info("Token refreshed successfully.")
            else:
                logging.error("Token is invalid or expired and cannot be refreshed.")
                raise HTTPException(
                    status_code=HTTP_401_UNAUTHORIZED,
                    detail="Token is invalid or expired and cannot be refreshed",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        logging.info("Authentication successful, returning credentials.")
        return creds
    except (json.JSONDecodeError, KeyError) as e:
        logging.error(f"Authentication failed: Invalid token format. Error: {e}")
        logging.error(f"Problematic token string: {token_str}")
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token format: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_google_calendar_service(creds: Credentials = Depends(get_current_user)):
    if not creds or not creds.valid:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        service = build('calendar', 'v3', credentials=creds)
        return service
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail=f"Failed to build calendar service: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )

@router.get("/authorize")
def authorize():
    credentials_info = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if credentials_info:
        client_config = json.loads(credentials_info)
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
    else:
        flow = Flow.from_client_secrets_file(
            CREDENTIALS_PATH,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline', include_granted_scopes='true')
    return RedirectResponse(auth_url)

@router.get("/oauth2callback")
def oauth2callback(request: Request):
    code = request.query_params.get('code')
    if not code:
        return HTMLResponse("<h3>No code found in callback.</h3>")
    credentials_info = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if credentials_info:
        client_config = json.loads(credentials_info)
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
    else:
        flow = Flow.from_client_secrets_file(
            CREDENTIALS_PATH,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
    flow.fetch_token(code=code)
    creds = flow.credentials
    token_data = json.loads(creds.to_json())
    token_data_str = json.dumps(token_data)
    
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:8501")
    redirect_url = f"{frontend_url}?token_data={token_data_str}"
    # backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
    # redirect_url = f"{backend_url}/static/auth_redirect.html?token_data={token_data_str}"

    return RedirectResponse(url=redirect_url)
