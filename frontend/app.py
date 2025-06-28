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

# --- Final, Reliable Auth Flow ---

if "token_data" not in st.session_state:
    st.session_state.token_data = None

# Get token from localStorage
token_data_str = st_javascript(
    "window.localStorage.getItem('token_data');",
    key="get_token"
)

if token_data_str and not isinstance(st.session_state.get("token_data"), dict):
    try:
        st.session_state.token_data = json.loads(token_data_str)
    except (json.JSONDecodeError, TypeError):
        st.session_state.token_data = None
        st_javascript(
            "window.localStorage.removeItem('token_data');",
            key="remove_bad_token"
        )

authenticated = isinstance(st.session_state.get("token_data"), dict)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# JS listener for postMessage from popup
components.html(
    """
    <script>
    window.addEventListener('message', function(event) {
        if (event.data && event.data.token_data) {
            localStorage.setItem('token_data', event.data.token_data);
            setTimeout(() => {
                window.location.href = window.location.href + '?reload=' + new Date().getTime();
            }, 5000);
        }
    }, false);
    </script>
    """,
    height=0
)

if not authenticated:
    st.info("Please connect your Google Calendar to use this assistant. After authenticating, refresh this page. Note: Google verification is in progress and requires CASA certification for sensitive scopes. For testing, use the test account: Email: timeloom34@gmail.com    Password: Timeloomdemo@123")

    auth_url = f"{BACKEND_URL}/authorize"

    components.html(f"""
        <div id="auth-message"></div>
        <script>
            function openAuthPopup() {{
                const width = 600, height = 600;
                const left = (window.innerWidth - width) / 2;
                const top = (window.innerHeight - height) / 2;
                window.open('{auth_url}', 'GoogleAuth',
                    `width=${{width}},height=${{height}},top=${{top}},left=${{left}}`);
            }}

            window.addEventListener('message', function(event) {{
                if (event.data && event.data.token_data) {{
                    localStorage.setItem('token_data', event.data.token_data);
                    // Display message to user
                    const messageDiv = document.getElementById('auth-message');
                    if (messageDiv) {{
                        messageDiv.innerText = 'Authentication successful. Please manually reload the page.';
                        messageDiv.style.color = 'green';
                        messageDiv.style.fontWeight = 'bold';
                        messageDiv.style.marginBottom = '10px';
                    }}
                    // Removed automatic reload: setTimeout(() => {{ window.location.href = window.location.href + '?reload=' + new Date().getTime(); }}, 5000);
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
    """, height=150)

else:
    st.success("✅ Google Calendar is connected!")

    # Display chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    if user_input := st.chat_input("Ask me to check, book, update or cancel a meeting..."):
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            try:
                token_data_json_string = json.dumps(st.session_state.token_data)
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
                                    tool_name = data["tool"]
                                    message_placeholder.markdown(f"🤖 Using tool: `{tool_name}`...")
                                elif "response" in data:
                                    full_response = data.get("response", "")
                                    message_placeholder.markdown(full_response + "▌")
                            except json.JSONDecodeError:
                                continue
                message_placeholder.markdown(full_response)
            except httpx.ReadTimeout:
                full_response = "Error: The request timed out."
                message_placeholder.markdown(full_response)
            except Exception as e:
                full_response = f"Error: {e}"
                message_placeholder.markdown(full_response)

        st.session_state.chat_history.append({"role": "assistant", "content": full_response})
