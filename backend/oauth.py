import os
import json
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from starlette.responses import Response

SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/calendar.readonly'
]
BASE_DIR = os.path.join(os.path.dirname(__file__), '..')
CREDENTIALS_PATH = os.path.join(BASE_DIR, 'env', 'credentials.json')
TOKEN_PATH = os.path.join(BASE_DIR, 'env', 'token.json')
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/oauth2callback")

router = APIRouter()

def save_token(token):
    with open(TOKEN_PATH, 'w') as f:
        json.dump(token, f)

def load_token():
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'r') as f:
            token = json.load(f)
        return token
    return None

def get_google_calendar_service():
    token = load_token()
    if not token:
        return None
    creds = Credentials.from_authorized_user_info(token, SCOPES)
    service = build('calendar', 'v3', credentials=creds)
    return service

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
    save_token(json.loads(creds.to_json()))
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:8501") # Default to localhost for local development
    html_content = f"""
        <h3>Google Calendar connected! Redirecting to the app...</h3>
        <script>
            setTimeout(function() {{
                window.location.href = '{frontend_url}';
            }}, 1500);
        </script>
    """
    return HTMLResponse(content=html_content)

def is_authenticated():
    token = load_token()
    if not token:
        return False
    creds = Credentials.from_authorized_user_info(token, SCOPES)
    return creds and creds.valid
