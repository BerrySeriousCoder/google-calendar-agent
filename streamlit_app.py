import streamlit as st
import uuid
import json
import time
from streamlit_javascript import st_javascript

# --- Placeholder for your actual Google Auth functions ---
# You should replace these with your logic using a library like google-auth-oauthlib

def get_google_auth_url(state_id):
    """Generates the Google Auth URL."""
    base_url = "https://accounts.google.com/o/oauth2/v2/auth"
    # IMPORTANT: Update with your details. The redirect_uri must match Google Cloud Console.
    params = {
        "client_id": "YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com",
        "redirect_uri": st.secrets.get("REDIRECT_URI", "http://localhost:8501?page=callback"),
        "scope": "openid email profile",
        "response_type": "code",
        "state": state_id,
        "access_type": "offline"
    }
    import urllib.parse
    return f"{base_url}?{urllib.parse.urlencode(params)}"

def get_token_from_code(code):
    """Exchanges the authorization code for an access token."""
    # This is a placeholder. Replace with your actual implementation.
    return {"access_token": f"fake_token_for_{code}", "expires_in": 3600}

# --- Streamlit App Logic ---

st.set_page_config(page_title="Google Auth Pop-up Demo", layout="centered")

# Part 1: Handle the authentication callback in the pop-up
if st.query_params.get("page") == "callback":
    st.title("Authenticating...")
    code = st.query_params.get("code")
    token = get_token_from_code(code)

    if token:
        # JavaScript to send the token to the parent window and close the pop-up
        st.html(f"""
        <script>
            window.opener.postMessage({{ "type": "auth_token", "token": {json.dumps(token)} }}, "*");
            window.close();
        </script>
        """)
        st.success("Authentication successful! Closing window...")
    else:
        st.error("Authentication failed.")
    st.stop()

# Part 2: Main application logic
if 'token' in st.session_state:
    st.title("🎉 You are logged in!")
    st.write("Your Token:")
    st.json(st.session_state.token)
    if st.button("Logout"):
        del st.session_state['token']
        st.rerun()
    st.stop()

# Part 3: Show the login button and handle the login flow
st.title("Welcome!")
st.write("Please log in to continue.")

if st.button("Login with Google", type="primary"):
    auth_url = get_google_auth_url(str(uuid.uuid4()))

    # JavaScript to open the pop-up, listen for the message, and store the token
    st.html(f"""
        <script>
            const popup = window.open("{auth_url}", "google-auth", "width=500,height=600");
            window.addEventListener('message', (event) => {{
                if (event.data.type === 'auth_token') {{
                    // When the token is received, store it in localStorage
                    window.localStorage.setItem('auth_token', JSON.stringify(event.data.token));
                    popup.close();
                    // Force a Streamlit rerun by setting a dummy query parameter
                    window.location.search = "r=" + Math.random();
                }}
            }}, false);
        </script>
    """)

    # Poll localStorage for the token
    with st.spinner("Waiting for authentication in pop-up window..."):
        token_str = None
        for _ in range(60): # Poll for 60 seconds
            # Use st_javascript to get the token from localStorage
            token_str = st_javascript("window.localStorage.getItem('auth_token')")
            if token_str:
                break
            time.sleep(1)

    if token_str:
        # If token is found, clear it from localStorage and update session state
        st_javascript("window.localStorage.removeItem('auth_token')")
        st.session_state.token = json.loads(token_str)
        st.success("Login Successful!")
        time.sleep(1)
        st.rerun()
    else:
        st.error("Login failed or timed out. Please try again.")
