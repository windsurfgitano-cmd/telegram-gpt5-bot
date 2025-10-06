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

# ============================================================================
# TOOL DETECTION AND ROUTING
# ============================================================================
def detect_required_tools(user_message):
    """
    Usa GPT-5 para determinar qué herramientas se necesitan
    Retorna: {"needs_tools": bool, "tools": [{"app": "gmail", "action": "send_email", "params": {...}}]}
    """
    
    detection_prompt = f"""Analiza esta solicitud del usuario y determina si requiere usar herramientas externas.

HERRAMIENTAS DISPONIBLES:
- Gmail: enviar email, buscar emails, leer emails
- Google Sheets: agregar datos, leer hojas, listar spreadsheets
- Google Calendar: crear eventos, listar eventos
- Slack: enviar mensajes, listar canales
- GitHub: crear issues, listar repositorios
- Google Drive: subir archivos, buscar archivos, listar archivos
- Notion: crear páginas, buscar contenido, listar bases de datos
- Supabase: insertar datos, consultar tablas, actualizar, eliminar
- FLUX: generar imágenes

Solicitud del usuario: "{user_message}"

Responde SOLO en este formato JSON:
{{
  "needs_tools": true/false,
  "reasoning": "breve explicación",
  "tools": [
    {{
      "app": "nombre_app",
      "action": "acción_específica",
      "params": {{"key": "value"}},
      "description": "qué hace este paso"
    }}
  ]
}}

Si NO necesita herramientas externas (ej: solo pregunta información), pon "needs_tools": false.
Si necesita herramientas, lista TODOS los pasos necesarios en orden."""

    url = f"{AZURE_ENDPOINT}/openai/deployments/{DEPLOYMENT_NAME}/chat/completions?api-version=2025-01-01-preview"
    
    payload = {
        "messages": [
            {"role": "system", "content": "Eres un analizador de solicitudes que determina qué herramientas usar."},
            {"role": "user", "content": detection_prompt}
        ],
        "max_tokens": 500,
        "temperature": 0.3,
        "response_format": {"type": "json_object"}
    }
    
    req = Request(url, data=json.dumps(payload).encode(), headers={
        "Content-Type": "application/json",
        "api-key": AZURE_API_KEY
    })
    
    try:
        with urlopen(req, timeout=20) as response:
            result = json.loads(response.read())
            content = result["choices"][0]["message"]["content"]
            return json.loads(content)
    except Exception as e:
        print(f"Error detecting tools: {e}")
        return {"needs_tools": False, "reasoning": "Error en detección"}

# ============================================================================
# TOOL EXECUTION ROUTER - VERSIÓN COMPLETA
# ============================================================================
def execute_detected_tool(tool_info):
    """Ejecuta una herramienta detectada y retorna el resultado"""
    
    app = tool_info.get("app", "").lower()
    action = tool_info.get("action", "").lower()
    params = tool_info.get("params", {})
    
    print(f"🔧 DEBUG: Ejecutando {app}.{action}")
    print(f"📋 DEBUG: Params = {json.dumps(params, indent=2)}")
    
    # ========================================================================
    # GMAIL
    # ========================================================================
    if app == "gmail":
        if "send" in action or action == "send_email":
            return execute_composio_tool("GMAIL_SEND_EMAIL", {
                "to": params.get("to", params.get("destinatario", "")),
                "subject": params.get("subject", params.get("asunto", "")),
                "body": params.get("body", params.get("mensaje", params.get("text", "")))
            })
        
        elif "fetch" in action or "search" in action or "buscar" in action or "read" in action or "list" in action:
            query = params.get("query", params.get("q", ""))
            max_results = params.get("max_results", params.get("limit", 10))
            
            if not query and ("hoy" in str(params).lower() or "today" in str(params).lower()):
                today = datetime.now().strftime("%Y/%m/%d")
                query = f"after:{today}"
            
            elif not query and ("ayer" in str(params).lower() or "yesterday" in str(params).lower()):
                yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y/%m/%d")
                query = f"after:{yesterday}"
            
            return execute_composio_tool("GMAIL_FETCH_EMAILS", {
                "maxResults": max_results,
                "userId": "me",
                "q": query
            })
    
    # ========================================================================
    # GOOGLE SHEETS
    # ========================================================================
    elif app == "sheets" or app == "googlesheets" or app == "google sheets":
        if "add" in action or "write" in action or "update" in action or "agregar" in action:
            return execute_composio_tool("GOOGLESHEETS_BATCH_UPDATE", {
                "spreadsheetId": params.get("spreadsheet_id", params.get("spreadsheetId", "")),
                "range": params.get("range", params.get("range_name", "Sheet1!A1")),
                "values": params.get("values", params.get("data", []))
            })
        
        elif "read" in action or "get" in action or "list" in action or "leer" in action or "listar" in action:
            if "all" in str(params).lower() or "todos" in str(params).lower() or "todas" in str(params).lower() or not params.get("spreadsheet_id"):
                return execute_composio_tool("GOOGLESHEETS_LIST_SPREADSHEETS", {})
            else:
                return execute_composio_tool("GOOGLESHEETS_GET_SPREADSHEET", {
                    "spreadsheetId": params.get("spreadsheet_id", params.get("spreadsheetId", ""))
                })
    
    # ========================================================================
    # GOOGLE CALENDAR
    # ========================================================================
    elif app == "calendar" or app == "googlecalendar" or app == "google calendar":
        if "create" in action or "add" in action or "crear" in action or "agregar" in action:
            event_data = {
                "summary": params.get("summary", params.get("title", params.get("titulo", ""))),
                "description": params.get("description", params.get("descripcion", "")),
                "calendarId": "primary"
            }
            start_time = params.get("start", params.get("start_time", ""))
            if start_time:
                event_data["start"] = {"dateTime": start_time, "timeZone": "America/Santiago"}
            end_time = params.get("end", params.get("end_time", ""))
            if end_time:
                event_data["end"] = {"dateTime": end_time, "timeZone": "America/Santiago"}
            return execute_composio_tool("GOOGLECALENDAR_CREATE_EVENT", event_data)
        
        elif "list" in action or "get" in action or "events" in action or "listar" in action or "eventos" in action:
            time_min = params.get("time_min", params.get("timeMin", ""))
            if "hoy" in str(params).lower() or "today" in str(params).lower():
                time_min = datetime.now().isoformat() + "Z"
            
            event_params = {
                "maxResults": params.get("max_results", params.get("maxResults", 10)),
                "calendarId": "primary",
                "singleEvents": True,
                "orderBy": "startTime"
            }
            if time_min:
                event_params["timeMin"] = time_min
            return execute_composio_tool("GOOGLECALENDAR_LIST_EVENTS", event_params)
    
    # ========================================================================
    # SLACK
    # ========================================================================
    elif app == "slack":
        if "send" in action or "message" in action or "enviar" in action:
            return execute_composio_tool("SLACK_SEND_MESSAGE", {
                "channel": params.get("channel", params.get("canal", "")),
                "text": params.get("text", params.get("mensaje", params.get("message", "")))
            })
        elif "list" in action or "channels" in action or "canales" in action:
            return execute_composio_tool("SLACK_LIST_CHANNELS", {})
    
    # ========================================================================
    # GITHUB
    # ========================================================================
    elif app == "github":
        if "create" in action and "issue" in action:
            return execute_composio_tool("GITHUB_CREATE_ISSUE", {
                "owner": params.get("owner", ""),
                "repo": params.get("repo", ""),
                "title": params.get("title", ""),
                "body": params.get("body", "")
            })
        elif "list" in action and ("repo" in action or "repositories" in action):
            return execute_composio_tool("GITHUB_LIST_REPOS", {})
    
    # ========================================================================
    # GOOGLE DRIVE
    # ========================================================================
    elif app == "drive" or app == "googledrive" or app == "google drive":
        if "search" in action or "find" in action or "buscar" in action:
            return execute_composio_tool("GOOGLEDRIVE_FIND_FILE", {
                "file_name": params.get("query", params.get("file_name", params.get("nombre", "")))
            })
        elif "upload" in action or "subir" in action:
            return execute_composio_tool("GOOGLEDRIVE_UPLOAD_FILE", {
                "file_name": params.get("file_name", ""),
                "file_content_base64": params.get("file_content", params.get("content", "")),
                "parent_folder_id": params.get("folder_id", GOOGLE_DRIVE_IMAGES_FOLDER)
            })
        elif "list" in action or "listar" in action:
            return execute_composio_tool("GOOGLEDRIVE_LIST_FILES", {
                "pageSize": params.get("limit", 10)
            })
    
    # ========================================================================
    # NOTION (vía Composio - más completo)
    # ========================================================================
    elif app == "notion":
        if "create" in action and "page" in action:
            properties = params.get("properties", {})
            if not properties and params.get("text"):
                properties = { "Name": { "title": [{"text": {"content": params.get("text", "")[:100]}}] } }
            return execute_composio_tool("NOTION_CREATE_PAGE", {
                "parent": {"database_id": params.get("database_id", NOTES_DB_ID)},
                "properties": properties
            })
        
        elif "search" in action or "buscar" in action:
            return execute_composio_tool("NOTION_SEARCH", { "query": params.get("query", params.get("q", "")) })
        
        elif "list" in action and "database" in action:
            return execute_composio_tool("NOTION_LIST_DATABASES", {})
        
        else: # Fallback a función directa
            result = save_to_notion(params.get("text", ""), params.get("type", "note"))
            return {"success": True, "result": result}
    
    # ========================================================================
    # SUPABASE
    # ========================================================================
    elif app == "supabase":
        table = params.get("table", params.get("tabla", ""))
        if "insert" in action or "create" in action or "add" in action or "agregar" in action:
            return execute_composio_tool("SUPABASE_INSERT", { "table": table, "data": params.get("data", params.get("datos", {})) })
        elif "select" in action or "read" in action or "get" in action or "consultar" in action or "leer" in action:
            return execute_composio_tool("SUPABASE_SELECT", { "table": table, "filters": params.get("filters", params.get("filtros", {})) })
        elif "update" in action or "actualizar" in action:
            return execute_composio_tool("SUPABASE_UPDATE", { "table": table, "filters": params.get("filters", params.get("filtros", {})), "data": params.get("data", params.get("datos", {})) })
        elif "delete" in action or "remove" in action or "eliminar" in action:
            return execute_composio_tool("SUPABASE_DELETE", { "table": table, "filters": params.get("filters", params.get("filtros", {})) })
    
    # ========================================================================
    # FLUX
    # ========================================================================
    elif app == "flux":
        b64_image = generate_image_flux(params.get("prompt", ""))
        if b64_image:
            return {"success": True, "image_base64": b64_image}
        return {"error": "No se pudo generar la imagen"}
    
    return {"error": f"Herramienta no implementada: {app}.{action}"}

# ============================================================================
# SYSTEM PROMPT
# ============================================================================
SYSTEM_PROMPT = """Eres El Rey de las Páginas Bot, un asistente personal de inteligencia artificial avanzada creado por Kondor Code.

Tu propósito es ser un asistente proactivo y ejecutivo para emprendedores, ayudándolos a organizar, crear y comunicar de manera eficiente.

CAPACIDADES TÉCNICAS:
1.  **INTELIGENCIA (GPT-5):** Conversación natural, memoria contextual, razonamiento y detección automática de herramientas.
2.  **IMÁGENES (FLUX):** Creación de imágenes profesionales (logos, mockups) que se guardan automáticamente en Drive.
3.  **COMUNICACIÓN (Gmail, Slack):** Envío y búsqueda de emails; envío de mensajes a canales de Slack.
4.  **ORGANIZACIÓN (Notion, Google Calendar, Sheets):** Gestión de tareas, notas, ideas; creación y consulta de eventos; lectura y escritura en hojas de cálculo.
5.  **ARCHIVOS (Google Drive):** Almacenamiento y búsqueda de archivos.
6.  **DATOS (Supabase):** Gestión de bases de datos (CRUD).
7.  **DESARROLLO (GitHub):** Creación de issues y listado de repositorios.

COMANDOS:
- `/start`: Bienvenida.
- `/help`: Guía de uso.
- `/task`, `/note`, `/idea`, `/client`: Guardar en Notion.
- `/image [descripción]`: Generar imagen.
- `/search [término]`: Buscar en Drive.
- `/email [dest] [asunto] - [mensaje]`: Enviar email.
- `/slack [canal] [mensaje]`: Enviar a Slack.

PRINCIPIOS DE COMUNICACIÓN:
- **Ejecutivo:** Actúa primero, confirma después. No pidas permiso para acciones obvias.
- **Inteligente:** Usa las herramientas automáticamente sin que el usuario las pida explícitamente.
- **Claro y Conciso:** Usa negritas y emojis para mejorar la legibilidad.
- **Proactivo:** Anticipa necesidades y sugiere los siguientes pasos.

CÓMO RESPONDER:
- **Si te piden enviar un email:** Házlo y confirma "✅ Email enviado a [destinatario]". Si falta info, pregunta solo lo esencial.
- **Si te piden buscar algo:** Ejecuta la búsqueda y presenta los resultados de forma organizada.
- **Si te piden generar una imagen:** Ejecútalo, informa que se guardó en Drive y envía la imagen.
- **Si la solicitud requiere varias herramientas:** Ejecútalas en secuencia, informando de cada paso, y resume el resultado final.
- **Tu objetivo:** Ser el asistente más eficiente, útil y proactivo posible. Sorprende al usuario con tu capacidad de ejecución."""

# ============================================================================
# TELEGRAM, GPT, FLUX, NOTION, DRIVE FUNCTIONS
# ============================================================================
def send_telegram_message(chat_id, text):
    """Send message via Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    req = Request(url, data=json.dumps(data).encode(), headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=10) as response:
            return json.loads(response.read())
    except Exception as e:
        print(f"Error sending message: {e}")
        return None

def send_telegram_photo_base64(chat_id, b64_image, caption=""):
    """Send photo from base64 via Telegram"""
    try:
        image_bytes = base64.b64decode(b64_image)
        boundary = f"----WebKitFormBoundary{uuid.uuid4().hex[:16]}"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="chat_id"\r\n\r\n{chat_id}\r\n'
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="caption"\r\n\r\n{caption}\r\n'
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="photo"; filename="image.png"\r\n'
            f"Content-Type: image/png\r\n\r\n"
        ).encode() + image_bytes + f"\r\n--{boundary}--\r\n".encode()
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        req = Request(url, data=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        
        with urlopen(req, timeout=20) as response:
            return json.loads(response.read())
    except Exception as e:
        print(f"Error sending photo: {e}")
        return None

def call_azure_gpt(messages, user_id, context=""):
    """Call Azure OpenAI GPT-5 with context"""
    url = f"{AZURE_ENDPOINT}/openai/deployments/{DEPLOYMENT_NAME}/chat/completions?api-version=2025-01-01-preview"
    
    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if context:
        full_messages.append({"role": "system", "content": f"CONTEXTO DE EJECUCIÓN DE HERRAMIENTAS:\n{context}"})
    if user_id in conversation_history:
        full_messages.extend(conversation_history[user_id][-10:])
    full_messages.extend(messages)
    
    payload = {"messages": full_messages, "max_tokens": 1000, "temperature": 0.7}
    req = Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", "api-key": AZURE_API_KEY})
    
    try:
        with urlopen(req, timeout=30) as response:
            result = json.loads(response.read())
            assistant_message = result["choices"][0]["message"]["content"]
            
            if user_id not in conversation_history:
                conversation_history[user_id] = []
            conversation_history[user_id].extend(messages)
            conversation_history[user_id].append({"role": "assistant", "content": assistant_message})
            
            return assistant_message
    except Exception as e:
        return f"Error al contactar la IA: {str(e)}"

def generate_image_flux(prompt):
    """Generate image using FLUX (returns base64)"""
    url = f"{FLUX_ENDPOINT}/openai/deployments/{FLUX_DEPLOYMENT}/images/generations?api-version=2025-04-01-preview"
    payload = {"prompt": prompt, "n": 1, "size": "1024x1024", "response_format": "b64_json"}
    req = Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", "api-key": FLUX_API_KEY})
    try:
        with urlopen(req, timeout=60) as response:
            result = json.loads(response.read())
            return result["data"][0]["b64_json"] if "data" in result and result["data"] else None
    except Exception as e:
        print(f"Error generating image: {e}")
        return None

def create_notion_page(database_id, properties):
    """Create page in Notion"""
    if not NOTION_API_KEY or not database_id: return None
    url = "https://api.notion.com/v1/pages"
    payload = {"parent": {"database_id": database_id}, "properties": properties}
    req = Request(url, data=json.dumps(payload).encode(), headers={"Authorization": f"Bearer {NOTION_API_KEY}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"})
    try:
        with urlopen(req, timeout=10) as response:
            return json.loads(response.read())
    except Exception as e:
        print(f"Notion error: {e}")
        return None

def save_to_notion(text, message_type, drive_link=None):
    """Save item to Notion"""
    db_map = {"task": TASKS_DB_ID, "note": NOTES_DB_ID, "idea": IDEAS_DB_ID, "client": CLIENTS_DB_ID}
    db_id = db_map.get(message_type)
    if not db_id: return None
    
    properties = {"Name": {"title": [{"text": {"content": text[:200]}}]}}
    if message_type == "task":
        properties["Status"] = {"select": {"name": "Por hacer"}}
    if drive_link:
        properties["Drive Link"] = {"url": drive_link}
    
    return create_notion_page(db_id, properties)

def save_image_to_drive(b64_image, filename):
    """Save image to Google Drive"""
    if not COMPOSIO_API_KEY:
        print(f"DEV: Simulating save of {filename} to Drive.")
        return f"https://drive.google.com/file/d/simulated_{uuid.uuid4().hex}/view"
    
    result = execute_composio_tool("GOOGLEDRIVE_UPLOAD_FILE", {
        "file_name": filename,
        "file_content_base64": b64_image,
        "parent_folder_id": GOOGLE_DRIVE_IMAGES_FOLDER
    })
    return result.get("data", {}).get("webViewLink", "https://drive.google.com")

def search_drive(query):
    """Search files in Google Drive"""
    if not COMPOSIO_API_KEY:
        print(f"DEV: Simulating search for '{query}'.")
        return [{"name": f"simulated_{query}.pdf", "link": "https://drive.google.com/file/example"}]
    
    result = execute_composio_tool("GOOGLEDRIVE_FIND_FILE", {"file_name": query})
    files = result.get("data", {}).get("files", [])
    return [{"name": f.get("name"), "link": f.get("webViewLink")} for f in files]

# ============================================================================
# COMMAND HANDLERS
# ============================================================================
def handle_command(command, chat_id, user_id, args=""):
    """Handle slash commands"""
    if command == "/start":
        return "🎉 **¡Bienvenido a El Rey de las Páginas Bot!**\n\nSoy tu asistente personal con IA, listo para ayudarte a organizar, crear y comunicar. Simplemente dime qué necesitas o usa `/help` para ver una guía completa."
    
    elif command == "/help":
        return """📖 **Guía de uso:**

🤖 **MODO INTELIGENTE (Recomendado):**
Habla en lenguaje natural. Yo detecto y ejecuto las herramientas necesarias.
*Ej: "Busca mis emails de ayer sobre propuestas y créame una tarea para cada uno."*

📋 **COMANDOS MANUALES:**
- `/task [desc]`: Crea tarea en Notion.
- `/note [texto]`: Guarda nota en Notion.
- `/idea [desc]`: Guarda idea en Notion.
- `/client [info]`: Guarda cliente en Notion.
- `/image [desc]`: Genera imagen con FLUX.
- `/search [término]`: Busca en Google Drive.
- `/email [a] [asunto] - [msg]`: Envía un email.
- `/slack [#canal] [msg]`: Envía a Slack.

¿En qué te puedo ayudar? 😊"""
    
    elif command in ["/task", "/note", "/idea", "/client"]:
        cmd_map = {
            "/task": {"type": "task", "name": "Tarea", "emoji": "📋"},
            "/note": {"type": "note", "name": "Nota", "emoji": "📝"},
            "/idea": {"type": "idea", "name": "Idea", "emoji": "💡"},
            "/client": {"type": "client", "name": "Cliente", "emoji": "👤"}
        }
        info = cmd_map[command]
        if not args: return f"❌ **Uso correcto:** `{command} [descripción]`"
        result = save_to_notion(args, info["type"])
        if result and "url" in result:
             return f"✅ **{info['name']} guardada:** {info['emoji']} {args}\n🔗 [Ver en Notion]({result['url']})"
        return f"✅ **{info['name']} registrada:**\n{info['emoji']} {args}"

    elif command == "/image":
        if not args: return "❌ **Uso correcto:** `/image [descripción detallada]`"
        send_telegram_message(chat_id, "🎨 **Generando tu imagen...** (puede tardar 30s)")
        b64_image = generate_image_flux(args)
        if b64_image:
            filename = f"flux_{uuid.uuid4().hex[:8]}.png"
            drive_link = save_image_to_drive(b64_image, filename)
            caption = f"🎨 {args[:80]}...\n\n📁 [Guardado en Drive]({drive_link})"
            send_telegram_photo_base64(chat_id, b64_image, caption)
            save_to_notion(f"Imagen: {args}", "note", drive_link)
            return None
        else:
            return "❌ **Error al generar la imagen.** Intenta con otra descripción."
    
    elif command == "/search":
        if not args: return "❌ **Uso correcto:** `/search [término]`"
        results = search_drive(args)
        if results:
            response = f"🔍 **Resultados para '{args}':**\n\n" + "\n".join([f"{i+1}. [{f['name']}]({f['link']})" for i, f in enumerate(results[:10])])
            return response
        else:
            return f"❌ **No se encontraron archivos para '{args}'.**"
    
    elif command == "/email":
        parts = args.split(" - ", 1)
        if len(parts) < 2: return "❌ **Formato:** `/email destinatario asunto - mensaje`"
        header = parts[0].split(" ", 1)
        if len(header) < 2: return "❌ **Falta asunto.**"
        to, subject, body = header[0], header[1], parts[1]
        result = execute_composio_tool("GMAIL_SEND_EMAIL", {"to": to, "subject": subject, "body": body})
        if result.get("error"): return f"❌ **Error al enviar:** {result.get('error')}"
        return f"✅ **Email enviado a {to}**"
    
    elif command == "/slack":
        parts = args.split(" ", 1)
        if len(parts) < 2: return "❌ **Formato:** `/slack #canal mensaje`"
        channel, text = parts[0], parts[1]
        result = execute_composio_tool("SLACK_SEND_MESSAGE", {"channel": channel, "text": text})
        if result.get("error"): return f"❌ **Error al enviar:** {result.get('error')}"
        return f"✅ **Mensaje enviado a {channel} en Slack.**"
    
    return None

# ============================================================================
# INTELLIGENT MESSAGE PROCESSOR
# ============================================================================
def process_intelligent_message(text, chat_id, user_id):
    """Process a natural language message, detect and execute tools."""
    detection = detect_required_tools(text)
    
    if not detection.get("needs_tools", False):
        return call_azure_gpt([{"role": "user", "content": text}], user_id)
    
    send_telegram_message(chat_id, "🔄 **Procesando...** Ejecutando acciones.")
    
    execution_results = []
    for tool_info in detection.get("tools", []):
        send_telegram_message(chat_id, f"⚙️ {tool_info.get('description', 'Ejecutando...')}")
        result = execute_detected_tool(tool_info)
        execution_results.append({
            "description": tool_info.get("description"),
            "result": result,
            "success": not result.get("error")
        })
    
    context = "RESULTADOS DE EJECUCIÓN:\n"
    for i, res in enumerate(execution_results, 1):
        status = "✅ ÉXITO" if res["success"] else "❌ ERROR"
        context += f"{i}. {status} - {res['description']}\n"
        result_data = json.dumps(res["result"], indent=2)[:500]
        context += f"   Resultado: {result_data}\n\n"
        
    final_prompt = f"Solicitud original del usuario: '{text}'.\n\nYa he ejecutado las herramientas necesarias. Ahora, genera una respuesta final clara y amigable para el usuario resumiendo lo que se hizo y los resultados obtenidos basándote en el contexto de ejecución."
    return call_azure_gpt([{"role": "user", "content": final_prompt}], user_id, context=context)

# ============================================================================
# MAIN HTTP HANDLER
# ============================================================================

# ================================================================
# AUDIO PROCESSING FUNCTIONS (Added for voice message support)
# ================================================================

def get_telegram_file(file_id):
    """Get file info from Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}"
    try:
        with urlopen(url, timeout=10) as response:
            return json.loads(response.read())["result"]
    except Exception as e:
        print(f"Error getting file: {e}")
        return None

def download_telegram_audio(file_id):
    """Download audio file from Telegram"""
    file_info = get_telegram_file(file_id)
    if not file_info:
        return None

    file_path = file_info["file_path"]
    url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"

    try:
        with urlopen(url, timeout=20) as response:
            return response.read()
    except Exception as e:
        print(f"Error downloading audio: {e}")
        return None

    except Exception as e:
        print(f"❌ Error: {e}")
        return f"Error: {str(e)}"



        # Read converted WAV
        with open(wav_path, "rb") as f:
            wav_bytes = f.read()

        # Cleanup
        os.unlink(ogg_path)
        os.unlink(wav_path)

        return wav_bytes

    except Exception as e:
        print(f"Error converting audio: {e}")
        return None





def transcribe_audio_with_whisper(audio_bytes):
    """Transcribe audio using OpenAI Whisper API (accepts OGG directly)"""
    import io
    try:
        from openai import AzureOpenAI

        # Create client
        client = AzureOpenAI(
            azure_endpoint=AZURE_ENDPOINT,
            api_key=AZURE_API_KEY,
            api_version="2024-02-01"
        )

        # Whisper accepts OGG directly, no conversion needed!
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "audio.ogg"

        # Transcribe
        transcript = client.audio.transcriptions.create(
            model="whisper",  # Your Whisper deployment name
            file=audio_file
        )

        return transcript.text

    except Exception as e:
        print(f"Whisper error: {e}")
        return None

def process_voice_message(message, chat_id, user_id):
    """Process voice message from Telegram using Whisper"""
    try:
        # 1. Download audio from Telegram
        file_id = message["voice"]["file_id"]
        send_telegram_message(chat_id, "🎤 Procesando tu mensaje de voz...")

        audio_bytes = download_telegram_audio(file_id)
        if not audio_bytes:
            return "❌ Error descargando el audio."

        print(f"📥 Downloaded {len(audio_bytes)} bytes of OGG audio")

        # 2. Transcribe with Whisper (accepts OGG directly!)
        transcription = transcribe_audio_with_whisper(audio_bytes)
        if not transcription:
            return "❌ Error transcribiendo el audio."

        print(f"✅ Transcribed: {transcription}")

        # 3. Process as normal text message with GPT-5
        response = process_intelligent_message(transcription, chat_id, user_id)
        return response

    except Exception as e:
        print(f"Error processing voice: {e}")
        import traceback
        traceback.print_exc()
        return f"❌ Error procesando audio: {str(e)}"


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Health check endpoint"""
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(f"""
        <html><head><title>Bot Activo</title></head>
        <body style='font-family: sans-serif; text-align: center; padding-top: 50px;'>
        <h1>🤖 El Rey de las Páginas Bot</h1>
        <p style='color: green; font-weight: bold;'>✅ El bot está funcionando correctamente.</p>
        <p>Entity ID: {COMPOSIO_ENTITY_ID}</p>
        <p>Creado por Kondor Code</p>
        </body></html>
        """.encode('utf-8'))
    
    def do_POST(self):
        """Handle Telegram webhook"""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            update = json.loads(self.rfile.read(content_length).decode('utf-8'))

            message = update.get("message") or update.get("edited_message")
            if not message:
                self.send_response(200)
                self.end_headers()
                return

            # Extract chat_id and user_id FIRST (needed for all message types)
            chat_id = message["chat"]["id"]
            user_id = message["from"]["id"]

            # Handle voice messages
            if message.get("voice"):
                response = process_voice_message(message, chat_id, user_id)
                if response:
                    send_telegram_message(chat_id, response)
                self.send_response(200)
                self.end_headers()
                return

            # Handle text messages
            if message.get("voice"):
                response = process_voice_message(message, chat_id, user_id)
                if response:
                    send_telegram_message(chat_id, response)
                self.send_response(200)
                self.end_headers()
                return

            # Handle text messages
            if "text" not in message:
                self.send_response(200)
                self.end_headers()
                return

            text = message["text"]

            response = None
            if text.startswith("/"):
                parts = text.split(" ", 1)
                command, args = parts[0], parts[1] if len(parts) > 1 else ""
                response = handle_command(command, chat_id, user_id, args)
            else:
                response = process_intelligent_message(text, chat_id, user_id)

            if response:
                send_telegram_message(chat_id, response)

            self.send_response(200)
            self.end_headers()

        except Exception as e:
            print(f"FATAL ERROR processing update: {e}")
            import traceback
            traceback.print_exc()
            self.send_response(500)
            self.end_headers()
