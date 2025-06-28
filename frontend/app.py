import streamlit as st
import streamlit.components.v1 as components
from streamlit_javascript import st_javascript
import httpx
import json
import os
import base64

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Super Calendar Agent", page_icon="📅")
st.title("Super Calendar Agent")

# --- Final, Corrected Authentication Block ---

# Initialize token_data in session_state if not already defined
if "token_data" not in st.session_state:
    st.session_state.token_data = None

# Get the token string from localStorage.
token_data_str = st_javascript("window.localStorage.getItem('token_data');", key="get_token")

# If a token string exists and we haven't processed it yet, parse it.
if token_data_str and not isinstance(st.session_state.get("token_data"), dict):
    try:
        # The token from localStorage should be a JSON string; parse it into a dict.
        st.session_state.token_data = json.loads(token_data_str)
    except (json.JSONDecodeError, TypeError):
        # If parsing fails, the token is corrupted. Clear it.
        st.session_state.token_data = None
        st_javascript("window.localStorage.removeItem('token_data');", key="remove_bad_token")

# A user is authenticated if the token_data in the session is a dictionary.
authenticated = isinstance(st.session_state.get("token_data"), dict)

# Update the UI based on authentication state
if authenticated:
    st.write("Authenticated! Chat is available.")
else:
    st.info("You must connect your Google Calendar to use this assistant.")


if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Inject JS listener for postMessage to capture token from popup
components.html(
    """
    <script>
    // Listen for messages from the popup (OAuth window)
    window.addEventListener('message', function(event) {
       // The token_data from the backend is already a JSON string.
       if (event.data && event.data.token_data) {
           // Store the token string directly without re-stringifying it.
           window.localStorage.setItem('token_data', event.data.token_data);
           // Reload the page to process the token.
           location.reload();
       }
    }, false);
    </script>
    """,
    height=0
)

if not authenticated:
    st.info("You must connect your Google Calendar to use this assistant.")

    auth_url = f"{BACKEND_URL}/authorize"

    components.html(f'''
        <script>
            function openAuthPopup() {{
                const width = 600, height = 600;
                const left = (window.innerWidth - width) / 2;
                const top = (window.innerHeight - height) / 2;
                window.open('{auth_url}', 'GoogleAuth',
                    `width=${{width}},height=${{height}},top=${{top}},left=${{left}}`);
            }}
            // Always listen for token message, even after page reloads
            window.addEventListener('message', function(event) {{
                // Accept from any origin (cross-origin)
                if (event.data && event.data.token_data) {{
                    // Store in localStorage and reload
                    localStorage.setItem('token_data', event.data.token_data);
                    window.location.reload();
                }}
            }}, false);
        </script>

        <button 
            onclick="openAuthPopup()"
            style="
                background-color: #FF4B4B;
                color: white;
                border: none;
                padding: 10px 20px;
                text-align: center;
                text-decoration: none;
                display: inline-block;
                font-size: 16px;
                margin: 4px 2px;
                cursor: pointer;
                border-radius: 8px;
            "
        >
            Connect Google Calendar
        </button>
    ''', height=100)

else:
    st.success("Google Calendar is connected!")

    # Display chat messages from history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Accept user input
    if user_input := st.chat_input("Ask me to check, book, update or cancel a meeting..."):
        # Add user message to chat history
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        # Display user message
        with st.chat_message("user"):
            st.markdown(user_input)

        # Display assistant response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            try:
                
                # The backend expects the entire token data dictionary as a JSON string.
                token_data_json_string = json.dumps(st.session_state.token_data)
                
                # Encode the string to Base64 to prevent corruption in transit
                token_data_b64 = base64.b64encode(token_data_json_string.encode('utf-8')).decode('utf-8')


                headers = {
                    "Authorization": f"Bearer {token_data_b64}"
                }
                with httpx.stream(
                    "POST",
                    f"{BACKEND_URL}/chat",
                    json={"message": user_input, "history": st.session_state.chat_history},
                    headers=headers,
                    timeout=300
                ) as response:
                    response.raise_for_status()
                    for line in response.iter_lines():
                        if line.startswith('data:'):
                            try:
                                data = json.loads(line[len('data: '):])
                                if "tool" in data:
                                    # Backend is using a tool
                                    tool_name = data["tool"]
                                    message_placeholder.markdown(f"🤖 Using tool: `{tool_name}`...")
                                elif "response" in data:
                                    # Backend sent a response chunk
                                    full_response = data.get("response", "")
                                    message_placeholder.markdown(full_response + "▌")
                            except json.JSONDecodeError:
                                continue
                message_placeholder.markdown(full_response) # Display final response without cursor
            except httpx.ReadTimeout:
                full_response = "Error: The request timed out."
                message_placeholder.markdown(full_response)
            except Exception as e:
                full_response = f"Error: {e}"
                message_placeholder.markdown(full_response)
        
        # Add assistant response to chat history
        st.session_state.chat_history.append({"role": "assistant", "content": full_response})
