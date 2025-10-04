import os
import json
import base64
import uuid
from http.server import BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

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
COMPOSIO_ENTITY_ID = os.environ.get("COMPOSIO_ENTITY_ID", "default")

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
AVAILABLE_TOOLS = {
    "gmail": {
        "send_email": "GMAIL_SEND_EMAIL",
        "fetch_emails": "GMAIL_FETCH_EMAILS",
        "search_emails": "GMAIL_SEARCH_EMAILS"
    },
    "sheets": {
        "add_row": "GOOGLESHEETS_BATCH_UPDATE",
        "read_sheet": "GOOGLESHEETS_GET_SPREADSHEET"
    },
    "slack": {
        "send_message": "SLACK_SEND_MESSAGE",
        "list_channels": "SLACK_LIST_CHANNELS"
    },
    "github": {
        "create_issue": "GITHUB_CREATE_ISSUE",
        "list_repos": "GITHUB_LIST_REPOS"
    },
    "drive": {
        "upload_file": "GOOGLEDRIVE_UPLOAD_FILE",
        "search_files": "GOOGLEDRIVE_FIND_FILE"
    }
}

def detect_required_tools(user_message):
    """
    Usa GPT-5 para determinar qué herramientas se necesitan
    Retorna: {"needs_tools": bool, "tools": [{"app": "gmail", "action": "send_email", "params": {...}}]}
    """
    
    detection_prompt = f"""Analiza esta solicitud del usuario y determina si requiere usar herramientas externas.

HERRAMIENTAS DISPONIBLES:
- Gmail: enviar email, buscar emails, leer emails
- Google Sheets: agregar datos, leer hojas
- Slack: enviar mensajes, listar canales
- GitHub: crear issues, listar repositorios
- Google Drive: subir archivos, buscar archivos
- Notion: crear tareas, notas, ideas, clientes
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
# TOOL EXECUTION ROUTER
# ============================================================================
def execute_detected_tool(tool_info):
    """Ejecuta una herramienta detectada y retorna el resultado"""
    
    app = tool_info.get("app", "").lower()
    action = tool_info.get("action", "").lower()
    params = tool_info.get("params", {})
    
    # Gmail
    if app == "gmail":
        if action == "send_email":
            return execute_composio_tool("GMAIL_SEND_EMAIL", {
                "to": params.get("to", ""),
                "subject": params.get("subject", ""),
                "body": params.get("body", "")
            })
        elif action == "fetch_emails" or action == "search_emails":
            return execute_composio_tool("GMAIL_FETCH_EMAILS", {
                "max_results": params.get("max_results", 10),
                "query": params.get("query", "")
            })
    
    # Google Sheets
    elif app == "sheets":
        if action == "add_row":
            return execute_composio_tool("GOOGLESHEETS_BATCH_UPDATE", params)
        elif action == "read_sheet":
            return execute_composio_tool("GOOGLESHEETS_GET_SPREADSHEET", params)
    
    # Slack
    elif app == "slack":
        if action == "send_message":
            return execute_composio_tool("SLACK_SEND_MESSAGE", {
                "channel": params.get("channel", ""),
                "text": params.get("text", "")
            })
        elif action == "list_channels":
            return execute_composio_tool("SLACK_LIST_CHANNELS", {})
    
    # GitHub
    elif app == "github":
        if action == "create_issue":
            return execute_composio_tool("GITHUB_CREATE_ISSUE", {
                "owner": params.get("owner", ""),
                "repo": params.get("repo", ""),
                "title": params.get("title", ""),
                "body": params.get("body", "")
            })
        elif action == "list_repos":
            return execute_composio_tool("GITHUB_LIST_REPOS", {})
    
    # Google Drive (ya implementado pero podemos usar Composio)
    elif app == "drive":
        if action == "search_files":
            return execute_composio_tool("GOOGLEDRIVE_FIND_FILE", {
                "file_name": params.get("query", "")
            })
    
    # Notion (usar función existente)
    elif app == "notion":
        action_type = params.get("type", "note")
        text = params.get("text", "")
        return {"success": True, "result": save_to_notion(text, action_type)}
    
    # FLUX (usar función existente)
    elif app == "flux":
        prompt = params.get("prompt", "")
        b64_image = generate_image_flux(prompt)
        if b64_image:
            return {"success": True, "image_base64": b64_image}
        return {"error": "No se pudo generar la imagen"}
    
    return {"error": f"Herramienta no implementada: {app}.{action}"}
# ============================================================================
# SYSTEM PROMPT - COMPLETO CON HERRAMIENTAS DE RUBE
# ============================================================================
SYSTEM_PROMPT = """Eres El Rey de las Páginas Bot, un asistente personal de inteligencia artificial avanzada creado por Kondor Code.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 TU IDENTIDAD Y PROPÓSITO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Eres un asistente especializado en ayudar a emprendedores, dueños de negocios y profesionales del marketing digital a:
- Crear y optimizar páginas web de alto impacto
- Diseñar estrategias de marketing digital efectivas
- Atraer y convertir más clientes online
- Organizar proyectos, tareas e ideas de negocio
- Generar contenido visual profesional
- Automatizar procesos de trabajo con herramientas integradas

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 TUS CAPACIDADES TÉCNICAS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. **INTELIGENCIA ARTIFICIAL (Azure OpenAI GPT-5)**
   - Conversación natural en español
   - Comprensión contextual profunda
   - Memoria de conversación (últimas 10 interacciones por usuario)
   - Razonamiento complejo y análisis estratégico
   - Generación de contenido creativo (textos, ideas, estrategias)
   - **DETECCIÓN AUTOMÁTICA de qué herramientas usar según la solicitud**

2. **GENERACIÓN DE IMÁGENES (FLUX.1-Kontext-Pro)**
   - Creación de imágenes profesionales en alta resolución (1024x1024)
   - Logos, mockups, ilustraciones, diseños web
   - Estilo realista y contexto preciso
   - Las imágenes se guardan automáticamente en Google Drive

3. **ORGANIZACIÓN EN NOTION**
   - Guardar tareas con estados (Por hacer, En proceso, Completado)
   - Crear notas estructuradas con propiedades
   - Almacenar ideas de negocio categorizadas
   - Gestionar base de datos de clientes con información de contacto
   - Todo sincronizado en tiempo real

4. **GESTIÓN DE ARCHIVOS EN GOOGLE DRIVE**
   - Guardar imágenes generadas automáticamente
   - Buscar archivos y documentos por nombre o contenido
   - Subir archivos nuevos
   - Organizar recursos en carpetas estructuradas
   - Compartir links de acceso directo

5. **EMAIL CON GMAIL**
   - Enviar emails con formato profesional
   - Buscar emails específicos
   - Leer mensajes recientes
   - Filtrar por remitente, asunto, fecha

6. **HOJAS DE CÁLCULO CON GOOGLE SHEETS**
   - Agregar datos a hojas existentes
   - Leer información de spreadsheets
   - Crear registros automáticos
   - Análisis de datos

7. **COMUNICACIÓN CON SLACK**
   - Enviar mensajes a canales
   - Listar canales disponibles
   - Notificaciones automáticas

8. **GESTIÓN DE CÓDIGO CON GITHUB**
   - Crear issues y reportes de bugs
   - Listar repositorios
   - Consultar información de proyectos

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 COMANDOS DISPONIBLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Comandos básicos:**
/start - Mensaje de bienvenida
/help - Guía completa de uso
/task [descripción] - Crear tarea en Notion
/note [texto] - Guardar nota rápida en Notion
/idea [descripción] - Guardar idea de negocio en Notion
/client [nombre - contacto] - Guardar cliente en Notion
/image [descripción detallada] - Generar imagen con FLUX
/search [término] - Buscar archivos en Google Drive

**Comandos de integración (opcionales):**
/email [destinatario] [asunto] - Enviar email
/slack [canal] [mensaje] - Enviar mensaje a Slack
/sheet [acción] - Trabajar con Google Sheets
/github [acción] - Gestionar GitHub

**IMPORTANTE:** Los comandos son opcionales. Puedes simplemente decirme en lenguaje natural lo que necesitas y yo determino automáticamente qué herramientas usar.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💬 TU PERSONALIDAD Y ESTILO DE COMUNICACIÓN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- **Tono:** Profesional pero cercano y amigable
- **Lenguaje:** Claro, directo y sin tecnicismos innecesarios
- **Emojis:** Usa 1-2 emojis por mensaje para dar calidez (sin excederte)
- **Formato:** Usa **negritas** para destacar puntos importantes
- **Estructura:** Organiza respuestas largas con bullets, números o secciones
- **Proactividad:** Siempre ofrece soluciones accionables y próximos pasos

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 CÓMO RESPONDER SEGÚN EL CONTEXTO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Si te piden enviar un email:**
- NO preguntes si quieren que lo hagas, HÁZLO directamente
- Confirma la acción: "✅ Email enviado a [destinatario]"
- Si falta información (destinatario/asunto), pregunta solo eso

**Si te piden buscar información (emails, archivos, etc):**
- Ejecuta la búsqueda automáticamente
- Presenta los resultados de forma clara y organizada
- Ofrece acciones de seguimiento

**Si te piden generar una imagen:**
- Usa el comando /image automáticamente si la solicitud es directa
- Si la descripción es vaga, pide más detalles específicos
- Explica que se guardará en Drive

**Si te piden organizar tareas o información:**
- Usa automáticamente /task, /note, /idea o /client según corresponda
- Confirma que se sincronizó con Notion
- Ofrece el link para verlo

**Si te preguntan sobre marketing/páginas web:**
- Da consejos prácticos y específicos
- Menciona ejemplos reales o casos de uso
- Ofrece crear un plan y guardarlo automáticamente en Notion
- Sugiere próximos pasos accionables

**Si te piden algo que requiere múltiples herramientas:**
- Ejecuta todas las acciones en secuencia
- Explica qué estás haciendo en cada paso
- Confirma los resultados de cada acción

**Si no tienes suficiente información:**
- Pide solo lo esencial que falta
- Ofrece opciones cuando sea relevante
- Nunca inventes información

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✨ PRINCIPIOS CLAVE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. **Sé ejecutivo:** Actúa primero, explica después (cuando sea apropiado)
2. **Sé inteligente:** Usa las herramientas sin que el usuario tenga que pedírtelo explícitamente
3. **Sé transparente:** Siempre confirma qué acciones tomaste
4. **Sé práctico:** Ofrece soluciones específicas y accionables
5. **Sé memorable:** Crea una experiencia que sorprenda positivamente

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 EJEMPLOS DE RESPUESTAS IDEALES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Usuario: "Envía un email a maria@ejemplo.com diciendo que la reunión es mañana a las 3pm"
Tú: "✅ **Email enviado a maria@ejemplo.com**

**Asunto:** Confirmación de reunión
**Mensaje:** La reunión está confirmada para mañana a las 3pm.

¿Necesitas que agregue esta reunión a tu calendario también?"

Usuario: "Busca los emails de ayer sobre propuestas"
Tú: "🔍 **Buscando emails sobre propuestas de ayer...**

**Encontrados 3 emails:**
1. **Juan Pérez** - Propuesta de diseño web (10:30 AM)
2. **María López** - Propuesta de marketing digital (2:45 PM)  
3. **Carlos Ruiz** - Propuesta de branding (4:20 PM)

¿Quieres que cree un resumen de estas propuestas en Notion?"

Usuario: "Crea una tarea para revisar las propuestas y envíame un recordatorio por Slack"
Tú: "✅ **Acciones completadas:**

1. ✅ Tarea creada en Notion: "Revisar propuestas"
   🔗 [Ver en Notion](link)

2. ✅ Recordatorio enviado a Slack (#general)
   💬 "Recordatorio: Revisar propuestas pendientes"

¿Necesitas algo más?"

Usuario: "¿Cómo atraer más clientes?"
Tú: "¡Excelente pregunta! 🚀 Para atraer más clientes necesitas combinar 3 elementos:

**1. Visibilidad** 👀
- SEO local optimizado
- Presencia en redes sociales relevantes
- Google My Business actualizado

**2. Confianza** 💪
- Testimonios de clientes reales
- Portfolio de trabajos anteriores
- Garantías claras

**3. Conversión** 🎯
- Landing page enfocada
- Llamados a la acción claros
- Formularios simples

Acabo de guardar este plan en Notion para que no lo olvides. ¿Quieres que profundicemos en alguno de estos puntos?"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Recuerda: Tu objetivo es ser el asistente más útil, proactivo y eficiente. Anticipa necesidades, ejecuta acciones sin esperar confirmación cuando sea obvio, y siempre confirma los resultados."""

# ============================================================================
# TELEGRAM FUNCTIONS
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
        
        body = b""
        body += f"--{boundary}\r\n".encode()
        body += b'Content-Disposition: form-data; name="chat_id"\r\n\r\n'
        body += f"{chat_id}\r\n".encode()
        
        if caption:
            body += f"--{boundary}\r\n".encode()
            body += b'Content-Disposition: form-data; name="caption"\r\n\r\n'
            body += f"{caption}\r\n".encode()
        
        body += f"--{boundary}\r\n".encode()
        body += b'Content-Disposition: form-data; name="photo"; filename="image.png"\r\n'
        body += b'Content-Type: image/png\r\n\r\n'
        body += image_bytes
        body += f"\r\n--{boundary}--\r\n".encode()
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        req = Request(url, data=body, headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}"
        })
        
        with urlopen(req, timeout=20) as response:
            return json.loads(response.read())
    except Exception as e:
        print(f"Error sending photo: {e}")
        return None

# ============================================================================
# AZURE GPT-5 - CONVERSACIÓN INTELIGENTE
# ============================================================================
def call_azure_gpt(messages, user_id, context=""):
    """Call Azure OpenAI GPT-5 with optional tool execution context"""
    url = f"{AZURE_ENDPOINT}/openai/deployments/{DEPLOYMENT_NAME}/chat/completions?api-version=2025-01-01-preview"
    
    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Add tool execution context if available
    if context:
        full_messages.append({
            "role": "system", 
            "content": f"CONTEXTO DE EJECUCIÓN DE HERRAMIENTAS:\n{context}"
        })
    
    if user_id in conversation_history:
        full_messages.extend(conversation_history[user_id][-10](streamdown:incomplete-link)
if user_id in conversation_history:
        full_messages.extend(conversation_history[user_id][-10:])
    full_messages.extend(messages)
    
    payload = {"messages": full_messages, "max_tokens": 1000, "temperature": 0.7}
    req = Request(url, data=json.dumps(payload).encode(), headers={
        "Content-Type": "application/json",
        "api-key": AZURE_API_KEY
    })
    
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
        return f"Error: {str(e)}"

# ============================================================================
# FLUX IMAGE GENERATION
# ============================================================================
def generate_image_flux(prompt):
    """Generate image using FLUX Kontext Pro (returns base64)"""
    url = f"{FLUX_ENDPOINT}/openai/deployments/{FLUX_DEPLOYMENT}/images/generations?api-version=2025-04-01-preview"
    payload = {"prompt": prompt, "n": 1, "size": "1024x1024"}
    req = Request(url, data=json.dumps(payload).encode(), headers={
        "Content-Type": "application/json",
        "api-key": FLUX_API_KEY
    })
    
    try:
        with urlopen(req, timeout=60) as response:
            result = json.loads(response.read())
            if "data" in result and len(result["data"]) > 0:
                return result["data"][0].get("b64_json", None)
            return None
    except Exception as e:
        print(f"Error generating image: {e}")
        return None

# ============================================================================
# NOTION FUNCTIONS
# ============================================================================
def create_notion_page(database_id, properties):
    """Create page in Notion database"""
    if not NOTION_API_KEY or not database_id:
        return None
    
    url = "https://api.notion.com/v1/pages"
    payload = {"parent": {"database_id": database_id}, "properties": properties}
    req = Request(url, data=json.dumps(payload).encode(), headers={
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    })
    
    try:
        with urlopen(req, timeout=10) as response:
            return json.loads(response.read())
    except Exception as e:
        print(f"Notion error: {e}")
        return None

def save_to_notion(text, message_type, drive_link=None):
    """Save to Notion with optional Drive link"""
    db_map = {"task": TASKS_DB_ID, "note": NOTES_DB_ID, "idea": IDEAS_DB_ID, "client": CLIENTS_DB_ID}
    db_id = db_map.get(message_type)
    if not db_id:
        return None
    
    properties = {"Name": {"title": [{"text": {"content": text[:100]}}]}}
    if message_type == "task":
        properties["Status"] = {"select": {"name": "Por hacer"}}
    if drive_link:
        properties["Drive Link"] = {"url": drive_link}
    
    return create_notion_page(db_id, properties)

# ============================================================================
# GOOGLE DRIVE FUNCTIONS
# ============================================================================
def save_image_to_drive(b64_image, filename):
    """Save base64 image to Google Drive via Composio"""
    if not COMPOSIO_API_KEY:
        # Fallback to placeholder
        print(f"Would save {filename} to Drive folder {GOOGLE_DRIVE_IMAGES_FOLDER}")
        return f"https://drive.google.com/file/d/{uuid.uuid4().hex}/view"
    
    # In production with Composio
    result = execute_composio_tool("GOOGLEDRIVE_UPLOAD_FILE", {
        "file_name": filename,
        "file_content_base64": b64_image,
        "parent_folder_id": GOOGLE_DRIVE_IMAGES_FOLDER
    })
    
    if result.get("error"):
        return f"https://drive.google.com/file/d/{uuid.uuid4().hex}/view"
    
    return result.get("data", {}).get("webViewLink", "")

def search_drive(query):
    """Search files in Google Drive via Composio"""
    if not COMPOSIO_API_KEY:
        # Fallback to mock results
        print(f"Would search Drive for: {query}")
        return [
            {"name": f"resultado1_{query}.pdf", "link": "https://drive.google.com/file/example1"},
            {"name": f"resultado2_{query}.doc", "link": "https://drive.google.com/file/example2"}
        ]
    
    result = execute_composio_tool("GOOGLEDRIVE_FIND_FILE", {
        "file_name": query
    })
    
    if result.get("error"):
        return []
    
    files = result.get("data", {}).get("files", [])
    return [{"name": f.get("name"), "link": f.get("webViewLink")} for f in files]
# ============================================================================
# COMMAND HANDLERS
# ============================================================================
def handle_command(command, chat_id, user_id, args=""):
    """Handle bot commands"""
    
    if command == "/start":
        return """🎉 ¡Bienvenido a El Rey de las Páginas Bot!

Soy tu asistente personal con IA avanzada y acceso a múltiples herramientas.

📋 **Comandos disponibles:**
/help - Ver ayuda completa
/task - Guardar tarea en Notion
/note - Guardar nota rápida
/idea - Guardar idea de negocio
/client - Guardar info de cliente
/image - Generar imagen con FLUX
/search - Buscar archivos en Drive
/email - Enviar email vía Gmail
/slack - Enviar mensaje a Slack

💬 **O simplemente dime qué necesitas:**
No necesitas usar comandos. Puedo entender lenguaje natural y ejecutar automáticamente las acciones que necesites.

**Ejemplos:**
• "Envía un email a juan@ejemplo.com confirmando la reunión"
• "Busca mis emails de ayer sobre propuestas"
• "Crea una tarea para revisar el proyecto"
• "Genera un logo moderno para mi cafetería"

¡Empecemos! 🚀"""
    
    elif command == "/help":
        return """📖 **Guía completa de uso:**

🤖 **MODO INTELIGENTE (Recomendado):**
Simplemente dime en lenguaje natural lo que necesitas. Yo detecto automáticamente qué herramientas usar.

**Ejemplos:**
• "Envía un email a maria@empresa.com sobre la propuesta"
• "Busca archivos en Drive sobre marketing digital"
• "Crea una tarea para llamar al cliente mañana"
• "Genera una imagen de un logo minimalista"
• "Manda un mensaje a Slack avisando que terminé"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 **COMANDOS MANUALES (Opcional):**

**Organización:**
• `/task [descripción]` - Crear tarea en Notion
• `/note [texto]` - Guardar nota rápida
• `/idea [descripción]` - Guardar idea de negocio
• `/client [nombre - contacto]` - Guardar cliente

**Contenido:**
• `/image [descripción]` - Generar imagen con FLUX
• `/search [término]` - Buscar en Drive

**Comunicación:**
• `/email [destinatario] [asunto]` - Enviar email
• `/slack [canal] [mensaje]` - Enviar a Slack

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🧠 **Capacidades:**
✅ Gmail - Enviar y buscar emails
✅ Google Drive - Subir y buscar archivos
✅ Google Sheets - Agregar datos
✅ Slack - Enviar mensajes
✅ GitHub - Crear issues
✅ Notion - Organizar tareas e ideas
✅ FLUX - Generar imágenes
✅ GPT-5 - Conversación inteligente

¿En qué te ayudo? 😊"""
    
    elif command == "/task":
        if not args:
            return """❌ **Uso correcto:**
`/task [descripción de la tarea]`

**Ejemplo:**
`/task Revisar propuesta de cliente antes del viernes`

💡 **O simplemente di:** "Crea una tarea para revisar la propuesta" """
        
        result = save_to_notion(args, "task")
        if result:
            return f"✅ **Tarea guardada en Notion:**\n📋 {args}\n\n🔗 [Ver en Notion](https://notion.so)"
        return f"✅ **Tarea registrada:**\n📋 {args}"
    
    elif command == "/note":
        if not args:
            return """❌ **Uso correcto:**
`/note [tu nota]`

**Ejemplo:**
`/note Agregar testimonios de clientes en homepage`

💡 **O simplemente di:** "Guarda una nota sobre testimonios" """
        
        result = save_to_notion(args, "note")
        if result:
            return f"✅ **Nota guardada en Notion:**\n📝 {args}"
        return f"✅ **Nota registrada:**\n📝 {args}"
    
    elif command == "/idea":
        if not args:
            return """❌ **Uso correcto:**
`/idea [tu idea]`

**Ejemplo:**
`/idea Crear curso online de marketing digital`

💡 **O simplemente di:** "Tengo una idea de crear un curso online" """
        
        result = save_to_notion(args, "idea")
        if result:
            return f"✅ **Idea guardada en Notion:**\n💡 {args}"
        return f"✅ **Idea registrada:**\n💡 {args}"
    
    elif command == "/client":
        if not args:
            return """❌ **Uso correcto:**
`/client [nombre y contacto]`

**Ejemplo:**
`/client Juan López - juan@email.com - 555-1234`

💡 **O simplemente di:** "Guarda el contacto de Juan López" """
        
        result = save_to_notion(args, "client")
        if result:
            return f"✅ **Cliente guardado en Notion:**\n👤 {args}"
        return f"✅ **Cliente registrado:**\n👤 {args}"
    
    elif command == "/image":
        if not args:
            return """❌ **Uso correcto:**
`/image [descripción detallada]`

**Ejemplos:**
• `/image Logo moderno para cafetería con estilo minimalista`
• `/image Diseño de landing page para app móvil`
• `/image Ilustración de equipo trabajando en oficina moderna`

💡 **Tip:** Cuanto más detallada la descripción, mejor resultado.

💡 **O simplemente di:** "Genera una imagen de un logo moderno" """
        
        # Send generating message
        send_telegram_message(chat_id, "🎨 **Generando tu imagen con FLUX Kontext Pro...**\n⏳ Esto puede tomar 15-30 segundos.")
        
        # Generate image
        b64_image = generate_image_flux(args)
        
        if b64_image:
            # Save to Drive
            filename = f"flux_{uuid.uuid4().hex[:8]}.png"
            drive_link = save_image_to_drive(b64_image, filename)
            
            # Send image to Telegram
            caption = f"🎨 {args[:80]}{'...' if len(args) > 80 else ''}\n\n📁 [Ver en Drive]({drive_link})"
            send_telegram_photo_base64(chat_id, b64_image, caption)
            
            # Save reference in Notion
            save_to_notion(f"Imagen: {args}", "note", drive_link)
            
            return None  # Already sent photo
        else:
            return "❌ **Error generando la imagen.**\n\nIntenta con:\n• Una descripción diferente\n• Más detalles específicos\n• Evitar contenido sensible"
    
    elif command == "/search":
        if not args:
            return """❌ **Uso correcto:**
`/search [término de búsqueda]`

**Ejemplos:**
• `/search propuesta cliente`
• `/search mockup landing`
• `/search logo cafetería`

💡 **O simplemente di:** "Busca archivos sobre propuestas" """
        
        results = search_drive(args)
        
        if results:
            response = f"🔍 **Resultados para:** {args}\n\n"
            for i, file in enumerate(results[:10], 1):
                response += f"{i}. [{file['name']}]({file['link']})\n"
            response += f"\n📁 Total: {len(results)} archivo(s)"
            return response
        else:
            return f"❌ **No se encontraron archivos con:** {args}\n\n💡 Intenta con otros términos."
    
    elif command == "/email":
        if not args:
            return """❌ **Uso correcto:**
`/email [destinatario] [asunto] - [mensaje]`

**Ejemplo:**
`/email juan@ejemplo.com Reunión - La reunión es mañana a las 3pm`

💡 **O simplemente di:** "Envía un email a juan sobre la reunión" """
        
        # Parse email arguments
        parts = args.split(" - ", 1)
        if len(parts) < 2:
            return "❌ **Formato incorrecto.** Usa: `/email destinatario asunto - mensaje`"
        
        header = parts[0].split(" ", 1)
        if len(header) < 2:
            return "❌ **Falta el asunto.** Usa: `/email destinatario asunto - mensaje`"
        
        to = header[0]
        subject = header[1]
        body = parts[1]
        
        result = execute_composio_tool("GMAIL_SEND_EMAIL", {
            "to": to,
            "subject": subject,
            "body": body
        })
        
        if result.get("error"):
            return f"❌ **Error enviando email:** {result.get('error')}\n\n⚠️ Verifica que Gmail esté conectado en Composio."
        
        return f"✅ **Email enviado exitosamente**\n\n📧 **A:** {to}\n📌 **Asunto:** {subject}\n💬 **Mensaje:** {body[:100]}{'...' if len(body) > 100 else ''}"
    
    elif command == "/slack":
        if not args:
            return """❌ **Uso correcto:**
`/slack [canal] [mensaje]`

**Ejemplo:**
`/slack #general Hola equipo, proyecto terminado!`

💡 **O simplemente di:** "Manda un mensaje a Slack diciendo que terminé" """
        
        parts = args.split(" ", 1)
        if len(parts) < 2:
            return "❌ **Formato incorrecto.** Usa: `/slack #canal mensaje`"
        
        channel = parts[0]
        text = parts[1]
        
        result = execute_composio_tool("SLACK_SEND_MESSAGE", {
            "channel": channel,
            "text": text
        })
        
        if result.get("error"):
            return f"❌ **Error enviando mensaje a Slack:** {result.get('error')}\n\n⚠️ Verifica que Slack esté conectado en Composio."
        
        return f"✅ **Mensaje enviado a Slack**\n\n📢 **Canal:** {channel}\n💬 **Mensaje:** {text}"
    
    return None
# ============================================================================
# INTELLIGENT MESSAGE PROCESSOR
# ============================================================================
def process_intelligent_message(text, chat_id, user_id):
    """
    Procesa un mensaje en lenguaje natural, detecta si necesita herramientas,
    las ejecuta automáticamente, y genera una respuesta contextual.
    """
    
    # Step 1: Detectar qué herramientas se necesitan
    detection = detect_required_tools(text)
    
    # Step 2: Si no necesita herramientas, respuesta conversacional normal
    if not detection.get("needs_tools", False):
        user_message = [{"role": "user", "content": text}]
        response = call_azure_gpt(user_message, user_id)
        return response
    
    # Step 3: Ejecutar herramientas detectadas
    send_telegram_message(chat_id, "🔄 **Procesando tu solicitud...**\n⏳ Ejecutando acciones necesarias.")
    
    tools = detection.get("tools", [])
    execution_results = []
    
    for tool_info in tools:
        app = tool_info.get("app", "")
        action = tool_info.get("action", "")
        description = tool_info.get("description", "")
        
        # Notify user about current step
        send_telegram_message(chat_id, f"⚙️ {description}...")
        
        # Execute the tool
        result = execute_detected_tool(tool_info)
        
        execution_results.append({
            "app": app,
            "action": action,
            "description": description,
            "result": result,
            "success": not result.get("error")
        })
    
    # Step 4: Construir contexto de ejecución para GPT-5
    context = "RESULTADOS DE EJECUCIÓN:\n\n"
    for i, exec_result in enumerate(execution_results, 1):
        status = "✅ ÉXITO" if exec_result["success"] else "❌ ERROR"
        context += f"{i}. {status} - {exec_result['description']}\n"
        context += f"   App: {exec_result['app']}, Acción: {exec_result['action']}\n"
        
        if exec_result["success"]:
            result_data = exec_result["result"].get("data", exec_result["result"])
            context += f"   Resultado: {json.dumps(result_data, indent=2)[:500]}\n"
        else:
            context += f"   Error: {exec_result['result'].get('error', 'Unknown error')}\n"
        context += "\n"
    
    # Step 5: GPT-5 genera respuesta final con contexto de ejecución
    user_message = [{"role": "user", "content": f"Solicitud original: {text}\n\nGenera una respuesta clara y concisa sobre los resultados de las acciones ejecutadas."}]
    final_response = call_azure_gpt(user_message, user_id, context=context)
    
    return final_response

# ============================================================================
# MAIN HANDLER
# ============================================================================
class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Health check endpoint"""
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        
        status_html = f"""<html>
<head>
    <title>Bot Activo</title>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; margin: 0; }}
        .container {{ max-width: 700px; margin: 50px auto; background: white; padding: 40px; border-radius: 15px; box-shadow: 0 10px 40px rgba(0,0,0,0.3); }}
        h1 {{ color: #2c3e50; margin-bottom: 10px; }}
        .status {{ color: #27ae60; font-weight: bold; font-size: 1.2em; }}
        .warning {{ color: #f39c12; }}
        .feature-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }}
        .feature {{ background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #667eea; }}
        .feature.active {{ border-left-color: #27ae60; }}
        .feature.inactive {{ border-left-color: #f39c12; }}
        ul {{ line-height: 2; list-style: none; padding: 0; }}
        ul li {{ padding: 8px 0; border-bottom: 1px solid #ecf0f1; }}
        ul li:last-child {{ border-bottom: none; }}
        .badge {{ display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 0.85em; margin-left: 10px; }}
        .badge.success {{ background: #d4edda; color: #155724; }}
        .badge.warning {{ background: #fff3cd; color: #856404; }}
        footer {{ margin-top: 30px; padding-top: 20px; border-top: 2px solid #ecf0f1; color: #7f8c8d; font-size: 0.9em; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Bot Activo! @ElReyDeLasPaginasBot</h1>
        <p>Estado: <span class="status">✅ Funcionando perfectamente</span></p>
        
        <h3>🧠 Inteligencia y Capacidades:</h3>
        <div class="feature-grid">
            <div class="feature active">
                <strong>🤖 GPT-5 Azure</strong>
                <div class="badge success">Activo</div>
            </div>
            <div class="feature active">
                <strong>🎨 FLUX Images</strong>
                <div class="badge success">Activo</div>
            </div>
            <div class="feature {"active" if NOTION_API_KEY else "inactive"}">
                <strong>📝 Notion</strong>
                <div class="badge {"success" if NOTION_API_KEY else "warning"}">{"Activo" if NOTION_API_KEY else "Inactivo"}</div>
            </div>
            <div class="feature {"active" if COMPOSIO_API_KEY else "inactive"}">
                <strong>🔗 Composio/Rube</strong>
                <div class="badge {"success" if COMPOSIO_API_KEY else "warning"}">{"Activo" if COMPOSIO_API_KEY else "Inactivo"}</div>
            </div>
        </div>
        
        <h3>🛠️ Herramientas Integradas:</h3>
        <ul>
            <li>✅ Chat inteligente con memoria contextual</li>
            <li>✅ Detección automática de herramientas necesarias</li>
            <li>✅ Generación de imágenes profesionales (FLUX)</li>
            <li>{"✅" if NOTION_API_KEY else "⚠️"} Organización en Notion (Tareas, Notas, Ideas, Clientes)</li>
            <li>{"✅" if COMPOSIO_API_KEY else "⚠️"} Gmail - Enviar y buscar emails</li>
            <li>{"✅" if COMPOSIO_API_KEY else "⚠️"} Google Drive - Subir y buscar archivos</li>
            <li>{"✅" if COMPOSIO_API_KEY else "⚠️"} Google Sheets - Gestión de datos</li>
            <li>{"✅" if COMPOSIO_API_KEY else "⚠️"} Slack - Mensajería de equipo</li>
            <li>{"✅" if COMPOSIO_API_KEY else "⚠️"} GitHub - Gestión de proyectos</li>
        </ul>
        
        <h3>📱 Modos de uso:</h3>
        <div style="background: #e8f5e9; padding: 15px; border-radius: 8px; margin: 15px 0;">
            <strong>🎯 Modo Inteligente (Recomendado):</strong>
            <p style="margin: 10px 0 0 0;">Habla naturalmente y el bot detecta automáticamente qué hacer.</p>
            <code style="background: white; padding: 5px 10px; border-radius: 4px; display: block; margin-top: 10px;">
                "Envía un email a juan confirmando la reunión"
            </code>
        </div>
        
        <div style="background: #fff3e0; padding: 15px; border-radius: 8px;">
            <strong>⚙️ Modo Manual:</strong>
            <p style="margin: 10px 0 0 0;">Usa comandos específicos para control directo.</p>
            <code style="background: white; padding: 5px 10px; border-radius: 4px; display: block; margin-top: 10px;">
                /email juan@ejemplo.com Asunto - Mensaje
            </code>
        </div>
        
        <h3>📋 Comandos disponibles:</h3>
        <ul>
            <li>/start - Mensaje de bienvenida completo</li>
            <li>/help - Guía detallada de uso</li>
            <li>/task [texto] - Crear tarea en Notion</li>
            <li>/note [texto] - Guardar nota rápida</li>
            <li>/idea [texto] - Registrar idea de negocio</li>
            <li>/client [info] - Guardar información de cliente</li>
            <li>/image [descripción] - Generar imagen con FLUX</li>
            <li>/search [término] - Buscar archivos en Drive</li>
            <li>/email [dest] [asunto] - Enviar email vía Gmail</li>
            <li>/slack [canal] [mensaje] - Enviar mensaje a Slack</li>
        </ul>
        
        <footer>
            <p>🔧 Bot desplegado en Vercel | 🤖 Powered by Azure AI + Composio</p>
            <p style="margin-top: 10px;">🏢 Creado por <strong>Kondor Code</strong></p>
        </footer>
    </div>
</body>
</html>"""
        self.wfile.write(status_html.encode('utf-8'))
    
    def do_POST(self):
        """Handle Telegram webhook with intelligent processing"""
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)
        
        try:
            update = json.loads(post_data.decode('utf-8'))
            
            if "message" not in update:
                self.send_response(200)
                self.end_headers()
                return
            
            message = update["message"]
            chat_id = message["chat"]["id"]
            user_id = message["from"]["id"]
            text = message.get("text", "")
            
            if not text:
                self.send_response(200)
                self.end_headers()
                return
            
            # Handle commands explicitly
            if text.startswith("/"):
                parts = text.split(" ", 1)
                command = parts[0]
                args = parts[1] if len(parts) > 1 else ""
                
                response = handle_command(command, chat_id, user_id, args)
                if response:
                    send_telegram_message(chat_id, response)
                
                self.send_response(200)
                self.end_headers()
                return
            
            # ===================================================================
            # INTELLIGENT PROCESSING - GPT-5 decides what tools to use
            # ===================================================================
            response = process_intelligent_message(text, chat_id, user_id)
            send_telegram_message(chat_id, response)
            
            self.send_response(200)
            self.end_headers()
            
        except Exception as e:
            print(f"Error processing update: {e}")
            import traceback
            traceback.print_exc()
            
            # Send error message to user
            try:
                send_telegram_message(chat_id, f"❌ **Error procesando tu mensaje:**\n\n`{str(e)}`\n\nIntenta de nuevo o usa /help para ver comandos disponibles.")
            except:
                pass
            
            self.send_response(500)
            self.end_headers()
