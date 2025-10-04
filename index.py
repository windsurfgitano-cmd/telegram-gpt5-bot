import os
import json
from http.server import BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# Configuration
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
AZURE_ENDPOINT = os.environ.get("AZURE_ENDPOINT")
AZURE_API_KEY = os.environ.get("AZURE_API_KEY")
DEPLOYMENT_NAME = os.environ.get("DEPLOYMENT_NAME")

# FLUX
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

# Conversation history
conversation_history = {}

SYSTEM_PROMPT = """Eres El Rey de las Páginas Bot, un asistente personal inteligente.

Especializado en:
- Marketing digital y estrategias web
- Organización de tareas, notas, ideas y clientes
- Generación de imágenes profesionales con FLUX
- Consejos prácticos para atraer clientes online

Personalidad: Profesional y amigable. Usa 1-2 emojis por mensaje."""

def send_telegram_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    req = Request(url, data=json.dumps(data).encode(), headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=10) as response:
            return json.loads(response.read())
    except Exception as e:
        print(f"Error: {e}")
        return None

def send_telegram_photo(chat_id, photo_url, caption=""):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    data = {"chat_id": chat_id, "photo": photo_url, "caption": caption}
    req = Request(url, data=json.dumps(data).encode(), headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=15) as response:
            return json.loads(response.read())
    except Exception as e:
        print(f"Error: {e}")
        return None

def call_azure_gpt(messages, user_id):
    url = f"{AZURE_ENDPOINT}/openai/deployments/{DEPLOYMENT_NAME}/chat/completions?api-version=2025-01-01-preview"
    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if user_id in conversation_history:
        full_messages.extend(conversation_history[user_id][-10:])
    full_messages.extend(messages)
    payload = {"messages": full_messages, "max_tokens": 800, "temperature": 0.7}
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
        return f"Error: {str(e)}"

def generate_image_flux(prompt):
    url = f"{FLUX_ENDPOINT}/openai/deployments/{FLUX_DEPLOYMENT}/images/generations?api-version=2025-04-01-preview"
    payload = {
        "prompt": prompt,
        "n": 1,
        "size": "1024x1024",
        "response_format": "url"
    }
    req = Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", "api-key": FLUX_API_KEY})
    try:
        with urlopen(req, timeout=60) as response:
            result = json.loads(response.read())
            if "data" in result and len(result["data"]) > 0:
                return result["data"][0].get("url", None)
            return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def create_notion_page(database_id, properties):
    if not NOTION_API_KEY or not database_id:
        return None
    url = "https://api.notion.com/v1/pages"
    payload = {"parent": {"database_id": database_id}, "properties": properties}
    req = Request(url, data=json.dumps(payload).encode(), headers={"Authorization": f"Bearer {NOTION_API_KEY}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"})
    try:
        with urlopen(req, timeout=10) as response:
            return json.loads(response.read())
    except Exception as e:
        print(f"Error: {e}")
        return None

def save_to_notion(text, message_type):
    db_map = {"task": TASKS_DB_ID, "note": NOTES_DB_ID, "idea": IDEAS_DB_ID, "client": CLIENTS_DB_ID}
    db_id = db_map.get(message_type)
    if not db_id:
        return None
    properties = {"Name": {"title": [{"text": {"content": text[:100]}}]}}
    if message_type == "task":
        properties["Status"] = {"select": {"name": "Por hacer"}}
    return create_notion_page(db_id, properties)

def handle_command(command, chat_id, user_id, args=""):
    if command == "/start":
        return """🎉 ¡Bienvenido a El Rey de las Páginas Bot!

📋 **Comandos:**
/help - Ayuda completa
/task [texto] - Guardar tarea
/note [texto] - Guardar nota
/idea [texto] - Guardar idea
/client [info] - Guardar cliente
/image [descripción] - Generar imagen

💬 O simplemente chatea 🚀"""
    
    elif command == "/help":
        return """📖 **Guía:**

**Comandos:**
• /task - Guardar tarea en Notion
• /note - Guardar nota
• /idea - Guardar idea
• /client - Guardar cliente
• /image - Generar imagen con FLUX

**Ejemplos:**
- "¿Cómo atraer clientes?"
- "Genera logo moderno"

¿En qué te ayudo? 😊"""
    
    elif command == "/task":
        if not args:
            return "❌ Uso: /task [descripción]"
        result = save_to_notion(args, "task")
        if result:
            return f"✅ Tarea guardada:\n📋 {args}"
        return f"⚠️ Tarea registrada:\n📋 {args}"
    
    elif command == "/note":
        if not args:
            return "❌ Uso: /note [tu nota]"
        result = save_to_notion(args, "note")
        if result:
            return f"✅ Nota guardada:\n📝 {args}"
        return f"⚠️ Nota registrada:\n📝 {args}"
    
    elif command == "/idea":
        if not args:
            return "❌ Uso: /idea [tu idea]"
        result = save_to_notion(args, "idea")
        if result:
            return f"✅ Idea guardada:\n💡 {args}"
        return f"⚠️ Idea registrada:\n💡 {args}"
    
    elif command == "/client":
        if not args:
            return "❌ Uso: /client [nombre y contacto]"
        result = save_to_notion(args, "client")
        if result:
            return f"✅ Cliente guardado:\n👤 {args}"
        return f"⚠️ Cliente registrado:\n👤 {args}"
    
    elif command == "/image":
        if not args:
            return "❌ Uso: /image [descripción]"
        send_telegram_message(chat_id, "🎨 Generando imagen con FLUX...\n⏳ 15-30 seg.")
        image_url = generate_image_flux(args)
        if image_url:
            send_telegram_photo(chat_id, image_url, f"🎨 {args[:50]}...")
            return None
        else:
            return "❌ Error. Intenta otra descripción."
    return None

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        html = f"""<html><head><title>Bot Activo</title><meta charset="utf-8"></head>
        <body style="font-family: Arial; padding: 20px;">
            <h1>🤖 Bot Activo! @ElReyDeLasPaginasBot</h1>
            <p>Estado: <strong style="color: green;">✅ Funcionando</strong></p>
            <ul>
                <li>✅ GPT-5 Azure</li>
                <li>✅ Comandos</li>
                <li>✅ Historial</li>
                <li>{"✅" if NOTION_API_KEY else "⚠️"} Notion</li>
                <li>{"✅" if FLUX_ENDPOINT else "⚠️"} FLUX</li>
                <li>{"✅" if GOOGLE_DRIVE_MAIN_FOLDER else "⚠️"} Drive</li>
            </ul>
        </body></html>"""
        self.wfile.write(html.encode('utf-8'))
    
    def do_POST(self):
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
            user_message = [{"role": "user", "content": text}]
            gpt_response = call_azure_gpt(user_message, user_id)
            send_telegram_message(chat_id, gpt_response)
            self.send_response(200)
            self.end_headers()
        except Exception as e:
            print(f"Error: {e}")
            self.send_response(500)
            self.end_headers()
