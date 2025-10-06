import os
import json
import base64
import uuid
from http.server import BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from datetime import datetime, timedelta

# ============================================================================
# CONFIGURATION
# ============================================================================
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
AZURE_ENDPOINT = os.environ.get("AZURE_ENDPOINT")
AZURE_API_KEY = os.environ.get("AZURE_API_KEY")
DEPLOYMENT_NAME = os.environ.get("DEPLOYMENT_NAME")

# FLUX Kontext Pro
FLUX_ENDPOINT = os.environ.get("FLUX_ENDPOINT")
FLUX_API_KEY = os.environ.get("FLUX_API_KEY")
FLUX_DEPLOYMENT = os.environ.get("FLUX_DEPLOYMENT")

# Notion
NOTION_API_KEY = os.environ.get("NOTION_API_KEY", "")
TASKS_DB_ID = os.environ.get("TASKS_DB_ID", "")
NOTES_DB_ID = os.environ.get("NOTES_DB_ID", "")
IDEAS_DB_ID = os.environ.get("IDEAS_DB_ID", "")
CLIENTS_DB_ID = os.environ.get("CLIENTS_DB_ID", "")

# Google Drive
GOOGLE_DRIVE_MAIN_FOLDER = os.environ.get("GOOGLE_DRIVE_MAIN_FOLDER", "")
GOOGLE_DRIVE_IMAGES_FOLDER = "1KeE0v8YOHbYL1n0e7f4Xy1JaP1-B76KI"

# Composio/Rube Integration
COMPOSIO_API_KEY = os.environ.get("COMPOSIO_API_KEY", "")
COMPOSIO_ENTITY_ID = os.environ.get("COMPOSIO_ENTITY_ID", "urJQejDZeeeD")

# Conversation history
conversation_history = {}

# ============================================================================
# COMPOSIO/RUBE TOOL EXECUTOR
# ============================================================================
def execute_composio_tool(tool_slug, arguments):
    """Execute a Composio tool via API"""
    if not COMPOSIO_API_KEY:
        return {"error": "Composio API key no configurado"}
    
    url = "https://backend.composio.dev/api/v1/actions/execute"
    
    payload = {
        "actionName": tool_slug,
        "params": arguments,
        "entityId": COMPOSIO_ENTITY_ID
    }
    
    req = Request(url, data=json.dumps(payload).encode(), headers={
        "Content-Type": "application/json",
        "X-API-Key": COMPOSIO_API_KEY
    })
    
    try:
        with urlopen(req, timeout=30) as response:
            result = json.loads(response.read())
            return result
    except Exception as e:
        print(f"Composio error: {e}")
        return {"error": str(e)}

# [... Rest del código se mantiene igual ...]
# (Tool detection, execution, message handlers, etc.)