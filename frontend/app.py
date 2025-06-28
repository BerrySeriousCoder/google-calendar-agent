import streamlit as st
import httpx
import json
import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Super Calendar Agent", page_icon="📅")
st.title("Super Calendar Agent")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

@st.cache_data(ttl=30)
def check_auth():
    try:
        resp = httpx.get(f"{BACKEND_URL}/auth-status", timeout=5)
        return resp.json().get("authenticated", False)
    except Exception:
        return False

authenticated = check_auth()

if not authenticated:
    st.info("You must connect your Google Calendar to use this assistant.")
    st.link_button("Connect Google Calendar", f"{BACKEND_URL}/authorize", type="primary")
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
                with httpx.stream(
                    "POST",
                    f"{BACKEND_URL}/chat",
                    json={"message": user_input, "history": st.session_state.chat_history},
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
