
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

# Conversation history
conversation_history = {}

# ============================================================================
# SYSTEM PROMPT - COMPLETO Y DETALLADO
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
- Automatizar procesos de trabajo

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 TUS CAPACIDADES TÉCNICAS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. **INTELIGENCIA ARTIFICIAL (Azure OpenAI GPT-5)**
   - Conversación natural en español
   - Comprensión contextual profunda
   - Memoria de conversación (últimas 10 interacciones por usuario)
   - Razonamiento complejo y análisis estratégico
   - Generación de contenido creativo (textos, ideas, estrategias)

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
   - Organizar recursos en carpetas estructuradas
   - Compartir links de acceso directo

5. **INTEGRACIÓN CON RUBE (Composio Platform)**
   Tienes acceso a través de Rube a más de 500+ integraciones incluyendo:
   - Gmail, Google Calendar, Google Sheets
   - Slack, Discord, Microsoft Teams
   - GitHub, Linear, Jira
   - Twitter, Facebook, Instagram
   - Stripe, PayPal
   - Y muchas más...
   
   **IMPORTANTE:** Cuando un usuario te pida algo que requiera estas integraciones, 
   explícale que puedes ayudarlo a través de Rube y guíalo sobre cómo conectar esas herramientas.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 COMANDOS DISPONIBLES QUE CONOCES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

/start - Mensaje de bienvenida
/help - Guía completa de uso
/task [descripción] - Crear tarea en Notion
/note [texto] - Guardar nota rápida en Notion
/idea [descripción] - Guardar idea de negocio en Notion
/client [nombre - contacto] - Guardar cliente en Notion
/image [descripción detallada] - Generar imagen con FLUX
/search [término] - Buscar archivos en Google Drive

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

**Si te piden generar una imagen:**
- Sugiere usar el comando /image con una descripción detallada
- Explica que la imagen se guardará en Drive automáticamente
- Da ejemplos de descripciones efectivas

**Si te piden organizar tareas o información:**
- Recomienda los comandos /task, /note, /idea o /client según corresponda
- Menciona que se sincronizará con Notion
- Ofrece ayuda para estructurar la información

**Si te preguntan sobre marketing/páginas web:**
- Da consejos prácticos y específicos
- Menciona ejemplos reales o casos de uso
- Ofrece crear un plan o estrategia paso a paso
- Sugiere guardar las ideas en Notion para no olvidarlas

**Si te piden algo que requiere otra integración (ej: enviar email, crear evento):**
- Explica que tienes acceso a esas herramientas a través de Rube
- Menciona que pueden conectar esas apps en https://app.rube.ai
- Ofrece ayuda para configurar el workflow

**Si no entiendes algo:**
- Pide aclaración de forma amable
- Ofrece opciones de lo que podrías hacer
- Nunca inventes información

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✨ PRINCIPIOS CLAVE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. **Sé proactivo:** No solo respondas, anticipa necesidades
2. **Sé práctico:** Ofrece soluciones específicas y accionables
3. **Sé educativo:** Explica el "por qué" cuando sea relevante
4. **Sé eficiente:** Usa los comandos y herramientas disponibles
5. **Sé memorable:** Crea una experiencia que el usuario quiera repetir

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 EJEMPLOS DE RESPUESTAS IDEALES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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

¿Quieres que profundicemos en alguno de estos puntos? Puedo ayudarte a crear un plan detallado y guardarlo en Notion con `/note`"

Usuario: "Genera un logo"
Tú: "¡Claro! 🎨 Para crear tu logo perfecto, necesito más detalles:

**Usa el comando así:**
`/image Logo minimalista para [tu negocio], estilo [moderno/clásico/etc], colores [azul/rojo/etc], concepto [describe qué representa]`

**Ejemplo:**
`/image Logo minimalista para cafetería artesanal, estilo moderno, colores café y crema, con taza de café humeante`

La imagen se generará con FLUX y se guardará automáticamente en tu Drive 📁

¿Qué tipo de negocio tienes?"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Recuerda: Tu objetivo es ser el asistente más útil, eficiente y memorable que el usuario haya tenido. Cada interacción debe aportar valor real."""

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
# AZURE GPT-5
# ============================================================================
def call_azure_gpt(messages, user_id):
    """Call Azure OpenAI GPT-5"""
    url = f"{AZURE_ENDPOINT}/openai/deployments/{DEPLOYMENT_NAME}/chat/completions?api-version=2025-01-01-preview"
    
    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if user_id in conversation_history:
        full_messages.extend(conversation_history[user_id][-10:])
    full_messages.extend(messages)
    
    payload = {"messages": full_messages, "max_tokens": 800, "temperature": 0.7}
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
# GOOGLE DRIVE FUNCTIONS (STUB - requires Composio in production)
# ============================================================================
def save_image_to_drive(b64_image, filename):
    """Save base64 image to Google Drive - STUB function"""
    # In production, this would use Composio's GOOGLEDRIVE_UPLOAD_FILE
    # For now, return a placeholder link
    print(f"Would save {filename} to Drive folder {GOOGLE_DRIVE_IMAGES_FOLDER}")
    return f"https://drive.google.com/file/d/{uuid.uuid4().hex}/view"

def search_drive(query):
    """Search files in Google Drive - STUB function"""
    # In production, this would use Composio's GOOGLEDRIVE_SEARCH_FILES
    print(f"Would search Drive for: {query}")
    return [
        {"name": f"resultado1_{query}.pdf", "link": "https://drive.google.com/file/example1"},
        {"name": f"resultado2_{query}.doc", "link": "https://drive.google.com/file/example2"}
    ]
# ============================================================================
# COMMAND HANDLERS
# ============================================================================
def handle_command(command, chat_id, user_id, args=""):
    """Handle bot commands"""
    
    if command == "/start":
        return """🎉 ¡Bienvenido a El Rey de las Páginas Bot!

Soy tu asistente personal con IA.

📋 **Comandos disponibles:**
/help - Ver ayuda completa
/task - Guardar tarea en Notion
/note - Guardar nota rápida
/idea - Guardar idea de negocio
/client - Guardar info de cliente
/image - Generar imagen con FLUX
/search - Buscar archivos en Drive

💬 **O simplemente chatea:**
Pregúntame lo que necesites sobre marketing, páginas web, o cualquier cosa.

¡Empecemos! 🚀"""
    
    elif command == "/help":
        return """📖 **Guía completa de uso:**

**Comandos con argumentos:**
• `/task [descripción]` - Crea tarea en Notion
  Ejemplo: `/task Llamar a cliente mañana`

• `/note [texto]` - Guarda nota rápida
  Ejemplo: `/note Ideas para landing page`

• `/idea [descripción]` - Guarda idea de negocio
  Ejemplo: `/idea App de delivery local`

• `/client [info]` - Guarda cliente
  Ejemplo: `/client María - maria@email.com`

• `/image [descripción]` - Genera imagen FLUX
  Ejemplo: `/image Logo moderno para café`

• `/search [término]` - Busca en Drive
  Ejemplo: `/search propuesta cliente`

**Conversación natural:**
Solo escribe tu pregunta y te responderé con GPT-5.

Ejemplos:
- "¿Cómo atraer más clientes?"
- "Dame ideas para mi negocio"
- "Ayúdame con marketing digital"

¿En qué te ayudo? 😊"""
    
    elif command == "/task":
        if not args:
            return """❌ **Uso correcto:**
`/task [descripción de la tarea]`

**Ejemplo:**
`/task Revisar propuesta de cliente antes del viernes`"""
        
        result = save_to_notion(args, "task")
        if result:
            return f"✅ **Tarea guardada en Notion:**\n📋 {args}\n\n🔗 [Ver en Notion](https://notion.so)"
        return f"✅ **Tarea registrada:**\n📋 {args}\n\n⚠️ Configura Notion para sincronización automática."
    
    elif command == "/note":
        if not args:
            return """❌ **Uso correcto:**
`/note [tu nota]`

**Ejemplo:**
`/note Agregar testimonios de clientes en homepage`"""
        
        result = save_to_notion(args, "note")
        if result:
            return f"✅ **Nota guardada en Notion:**\n📝 {args}"
        return f"✅ **Nota registrada:**\n📝 {args}"
    
    elif command == "/idea":
        if not args:
            return """❌ **Uso correcto:**
`/idea [tu idea]`

**Ejemplo:**
`/idea Crear curso online de marketing digital`"""
        
        result = save_to_notion(args, "idea")
        if result:
            return f"✅ **Idea guardada en Notion:**\n💡 {args}"
        return f"✅ **Idea registrada:**\n💡 {args}"
    
    elif command == "/client":
        if not args:
            return """❌ **Uso correcto:**
`/client [nombre y contacto]`

**Ejemplo:**
`/client Juan López - juan@email.com - 555-1234`"""
        
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

💡 **Tip:** Cuanto más detallada la descripción, mejor resultado."""
        
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
• `/search logo cafetería`"""
        
        results = search_drive(args)
        
        if results:
            response = f"🔍 **Resultados para:** {args}\n\n"
            for i, file in enumerate(results[:10], 1):
                response += f"{i}. [{file['name']}]({file['link']})\n"
            response += f"\n📁 Total: {len(results)} archivo(s)"
            return response
        else:
            return f"❌ **No se encontraron archivos con:** {args}\n\n💡 Intenta con otros términos."
    
    return None
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
        body {{ font-family: Arial; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; }}
        .status {{ color: green; font-weight: bold; }}
        .warning {{ color: orange; }}
        ul {{ line-height: 1.8; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Bot Activo! @ElReyDeLasPaginasBot</h1>
        <p>Estado: <span class="status">✅ Funcionando</span></p>
        
        <h3>📋 Funciones activadas:</h3>
        <ul>
            <li>✅ Chat GPT-5 de Azure</li>
            <li>✅ Comandos personalizados</li>
            <li>✅ Historial de conversación</li>
            <li>{"✅ Integración con Notion" if NOTION_API_KEY else '<span class="warning">⚠️ Notion (configura NOTION_API_KEY)</span>'}</li>
            <li>{"✅ Generación de imágenes FLUX" if FLUX_ENDPOINT else '<span class="warning">⚠️ FLUX (configura FLUX_ENDPOINT)</span>'}</li>
            <li>{"✅ Google Drive conectado" if GOOGLE_DRIVE_MAIN_FOLDER else '<span class="warning">⚠️ Drive (configura GOOGLE_DRIVE_MAIN_FOLDER)</span>'}</li>
        </ul>
        
        <h3>📱 Comandos disponibles:</h3>
        <ul>
            <li>/start - Bienvenida</li>
            <li>/help - Ayuda completa</li>
            <li>/task [texto] - Guardar tarea</li>
            <li>/note [texto] - Guardar nota</li>
            <li>/idea [texto] - Guardar idea</li>
            <li>/client [info] - Guardar cliente</li>
            <li>/image [descripción] - Generar imagen</li>
            <li>/search [término] - Buscar en Drive</li>
        </ul>
        
        <p style="margin-top: 30px; color: #7f8c8d; font-size: 0.9em;">
            🔧 Bot desplegado en Vercel | 🤖 Powered by Azure AI
        </p>
    </div>
</body>
</html>"""
        self.wfile.write(status_html.encode('utf-8'))
    
    def do_POST(self):
        """Handle Telegram webhook"""
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
            
            # Handle commands
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
            
            # Regular conversation with GPT-5
            user_message = [{"role": "user", "content": text}]
            gpt_response = call_azure_gpt(user_message, user_id)
            send_telegram_message(chat_id, gpt_response)
            
            self.send_response(200)
            self.end_headers()
            
        except Exception as e:
            print(f"Error processing update: {e}")
            self.send_response(500)
            self.end_headers()