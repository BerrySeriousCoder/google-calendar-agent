# Project README

This project contains a backend agent and a frontend application.

## Project Overview

This project features an agent designed to interact with external services, potentially including calendar management, utilizing various tools and capabilities.

## 📽️ Demo

[![Watch the demo](https://img.youtube.com/vi/LTx1TX4Vl1c/0.jpg)](https://youtu.be/LTx1TX4Vl1c?si=osFOMe-c9TXimztS)


## Project Structure

The project is organized into two main directories:

- `backend/`: Contains the core agent logic, tools, memory management, and authentication handling.
- `frontend/`: Contains the user interface application.

Key files include:

- [`backend/agent_graph.py`](backend/agent_graph.py):  defines the agent's workflow or state machine.
- [`backend/calendar_tools.py`](backend/calendar_tools.py): Contains tools for interacting with calendar services.
- [`backend/main.py`](backend/main.py): The main entry point for the backend application.
- [`backend/oauth.py`](backend/oauth.py): Handles OAuth authentication flows.
- [`frontend/app.py`](frontend/app.py): The main entry point for the frontend application.

## Setup and Running Locally

To run this project locally, follow these steps:

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd attempt
    ```

2.  **Set up Environment Variables:**
    Create a file named `.env` in the root directory of the project. This file should contain your `GEMINI_API_KEY`.

    ```env
    GEMINI_API_KEY=YOUR_GEMINI_API_KEY
    ```
    Credentials JSON: A JSON file containing your Google Cloud credentials must be placed inside the `env` folder in the root directory. This is necessary for services requiring GCP authentication.

3.  **Set up Google Cloud Credentials:**
    Download your Google Cloud credentials JSON file from the Google Cloud Platform console. Place this JSON file inside a folder named `.env` in the root directory of the project. The name of the JSON file typically starts with `credentials`.

4.  **Install Dependencies:**
    Navigate to the `backend` and `frontend` directories and install the required dependencies using pip:

    ```bash
    cd backend
    pip install -r requirements.txt
    cd ../frontend
    pip install -r requirements.txt
    cd ..
    ```

5.  **Run the Backend:**
    uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
    ```

6.  **Run the Frontend:**
    streamlit run frontend/app.py --server.address 0.0.0.0 --server.port 8501
    ```

The application should now be running locally. Refer to the specific backend and frontend code for default ports and access details.

## Deployment

To deploy this application, you need to deploy the backend and frontend separately.

### Backend Deployment

Deploy the backend application (files in the `backend/` directory) to a hosting platform like Render, Heroku, or similar services that support Python web applications.

You will need to configure the following environment variables on your backend hosting platform:

*   `GOOGLE_CREDENTIALS_JSON`: The entire JSON content of your Google Cloud credentials file. This is used for Google Calendar OAuth.
*   `GEMINI_API_KEY`: Your Google Gemini API key.
*   `FRONTEND_URL`: The public URL of your deployed Streamlit frontend application. This is used for the redirect after successful Google Calendar authorization.

You also need to add the backend's OAuth2 callback URL to the Authorized Redirect URIs in your Google Cloud Platform project's OAuth 2.0 Client ID settings. The URL is your backend's public URL followed by `/oauth2callback`. For example: `https://your-backend-url.com/oauth2callback`.

### Frontend Deployment

Deploy the frontend application (files in the `frontend/` directory) to Streamlit Cloud.

You need to provide the backend URL to the frontend application. The recommended way to do this on Streamlit Cloud is by creating a `.streamlit/config.toml` file in the root of your frontend repository with the following content:

```toml
[server]
enableCORS = true
enableXsrfProtection = false

[client]
# Set environment variables for the Streamlit app
environment = { BACKEND_URL = "YOUR_BACKEND_URL_HERE" }
```

Replace `"YOUR_BACKEND_URL_HERE"` with the public URL of your deployed backend application.

## Environment Variables and Credentials

This project uses environment variables for configuration, both for local development and deployment.

### Local Development

For local development, environment variables are typically stored in a `.env` file in the root directory.

*   `.env`: Located in the root directory, this file is used to store environment-specific variables like API keys. It must contain `GEMINI_API_KEY`.
*   Credentials JSON: A JSON file containing your Google Cloud credentials must be placed inside the `env` folder in the root directory. This is necessary for services requiring GCP authentication.

### Deployment

For deployment, environment variables should be configured directly on the hosting platform (e.g., Render, Streamlit Cloud) rather than using `.env` files or including sensitive files like `credentials.json` in the repository. Refer to the Deployment section above for the required environment variables for backend and frontend deployments.