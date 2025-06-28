import os
import json
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
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token_str = auth_header.split(" ")[1]
    try:
        token_data = json.loads(token_str)
        creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        if not creds.valid:
            # Attempt to refresh the token if it's expired and a refresh token is available
            if creds.expired and creds.refresh_token:
                from google.auth.transport.requests import Request as GoogleRequest
                creds.refresh(GoogleRequest())
            else:
                raise HTTPException(
                    status_code=HTTP_401_UNAUTHORIZED,
                    detail="Token is invalid or expired and cannot be refreshed",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        return creds
    except (json.JSONDecodeError, KeyError) as e:
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

    return RedirectResponse(url=redirect_url)
