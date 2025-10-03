from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import os

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Handle incoming Telegram webhooks"""
        try:
            # Read the webhook data
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            update = json.loads(body.decode('utf-8'))

            # Extract message
            if 'message' not in update or 'text' not in update['message']:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"ok":true}')
                return

            chat_id = update['message']['chat']['id']
            user_text = update['message']['text']

            # Get environment variables
            telegram_token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
            azure_endpoint = os.environ.get('AZURE_ENDPOINT', '')
            azure_key = os.environ.get('AZURE_API_KEY', '')
            deployment = os.environ.get('DEPLOYMENT_NAME', 'gpt-5-chat')

            # Call Azure OpenAI
            azure_url = f"{azure_endpoint}/openai/deployments/{deployment}/chat/completions?api-version=2025-01-01-preview"

            azure_payload = {
                "messages": [
                    {"role": "system", "content": "Eres El Rey de las Páginas Bot, experto en marketing digital y diseño web. Ayudas a emprendedores a atraer más clientes. Responde de forma profesional y motivadora."},
                    {"role": "user", "content": user_text}
                ],
                "max_tokens": 800,
                "temperature": 0.7
            }

            azure_req = urllib.request.Request(
                azure_url,
                data=json.dumps(azure_payload).encode('utf-8'),
                headers={
                    'Content-Type': 'application/json',
                    'api-key': azure_key
                },
                method='POST'
            )

            with urllib.request.urlopen(azure_req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                gpt_response = result['choices'][0]['message']['content']

            # Send response back to Telegram
            telegram_url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
            telegram_payload = {
                "chat_id": chat_id,
                "text": gpt_response,
                "parse_mode": "Markdown"
            }

            telegram_req = urllib.request.Request(
                telegram_url,
                data=json.dumps(telegram_payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )

            urllib.request.urlopen(telegram_req, timeout=10)

            # Return success
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"ok":true}')

        except Exception as e:
            # Log error but return 200 to prevent Telegram retries
            print(f"Error: {str(e)}")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode())

    def do_GET(self):
        """Health check endpoint"""
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(b'<h1>Bot Activo!</h1><p>@ElReyDeLasPaginasBot</p>')
