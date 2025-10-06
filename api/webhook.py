from http.server import BaseHTTPRequestHandler
import json
import os
import requests

# Configuración
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
AZURE_API_KEY = os.getenv("AZURE_API_KEY")
KONDOR_BASE = "https://kondorcode-resource.cognitiveservices.azure.com/openai/deployments"

# Endpoints
GPT5_ENDPOINT = f"{KONDOR_BASE}/gpt-5-chat/chat/completions?api-version=2025-01-01-preview"
WHISPER_ENDPOINT = f"{KONDOR_BASE}/whisper/audio/transcriptions?api-version=2024-06-01"
GPT_AUDIO_ENDPOINT = f"{KONDOR_BASE}/gpt-audio/audio/speech?api-version=2025-01-01-preview"

SYSTEM_PROMPT = "Eres el Dr. Oscar Zambrano, veterinario experto del Pittsburgh Trauma Center. Respondes con lenguaje técnico profesional a colegas veterinarios. Evita temas no veterinarios."

def transcribe_audio(audio_file_url):
    try:
        audio_response = requests.get(audio_file_url)
        headers = {"api-key": AZURE_API_KEY}
        files = {"file": ("audio.ogg", audio_response.content, "audio/ogg")}
        response = requests.post(WHISPER_ENDPOINT, headers=headers, files=files, data={"model": "whisper"}, timeout=30)
        response.raise_for_status()
        return response.json().get("text", "No pude entender")
    except Exception as e:
        return f"Error: {str(e)[:100]}"

def analyze_image_with_gpt5(image_url, user_question):
    headers = {"Content-Type": "application/json", "api-key": AZURE_API_KEY}
    payload = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": [
                {"type": "text", "text": user_question},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]}
        ],
        "temperature": 0.7,
        "max_tokens": 1500
    }
    try:
        response = requests.post(GPT5_ENDPOINT, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"Error: {str(e)[:100]}"

def get_gpt5_response(user_message):
    headers = {"Content-Type": "application/json", "api-key": AZURE_API_KEY}
    payload = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.7,
        "max_tokens": 1500
    }
    try:
        response = requests.post(GPT5_ENDPOINT, headers=headers, json=payload, timeout=25)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return "Error de sistema. Reintenta."

def generate_voice_response(text):
    headers = {"Content-Type": "application/json", "api-key": AZURE_API_KEY}
    payload = {"model": "gpt-audio", "input": text, "voice": "echo", "response_format": "mp3", "speed": 1.0}
    try:
        response = requests.post(GPT_AUDIO_ENDPOINT, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.content
    except:
        return None

def get_telegram_file_url(file_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}"
    response = requests.get(url)
    result = response.json()
    if result.get("ok"):
        return f"https://api.telegram.org/file/bot{BOT_TOKEN}/{result['result']['file_path']}"
    return None

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})

def send_voice(chat_id, audio_content):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice"
    files = {"voice": ("response.mp3", audio_content, "audio/mpeg")}
    requests.post(url, files=files, data={"chat_id": chat_id})

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Dr. Oscar Zambrano - ONLINE')
        return

    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            if 'message' not in data:
                self.send_response(200)
                self.end_headers()
                return
            
            message = data['message']
            chat_id = message['chat']['id']
            
            if 'voice' in message or 'audio' in message:
                file_id = message.get('voice', {}).get('file_id') or message.get('audio', {}).get('file_id')
                audio_url = get_telegram_file_url(file_id)
                if audio_url:
                    transcription = transcribe_audio(audio_url)
                    ai_response = get_gpt5_response(f"El colega dice: {transcription}")
                    audio_response = generate_voice_response(ai_response)
                    if audio_response:
                        send_voice(chat_id, audio_response)
                    else:
                        send_message(chat_id, f"🎤 '{transcription}'\n\n{ai_response}")
            
            elif 'photo' in message:
                photo = message['photo'][-1]
                image_url = get_telegram_file_url(photo['file_id'])
                user_text = message.get('caption', '¿Qué observas? DDx?')
                if image_url:
                    ai_response = analyze_image_with_gpt5(image_url, user_text)
                    send_message(chat_id, f"📸 {ai_response}")
            
            elif 'text' in message:
                user_message = message['text']
                respond_with_voice = "/voz" in user_message.lower()
                user_message = user_message.replace("/voz", "").replace("/VOZ", "").strip()
                ai_response = get_gpt5_response(user_message)
                
                if respond_with_voice:
                    audio_response = generate_voice_response(ai_response)
                    if audio_response:
                        send_voice(chat_id, audio_response)
                    else:
                        send_message(chat_id, ai_response)
                else:
                    send_message(chat_id, ai_response)
            
            self.send_response(200)
            self.end_headers()
        
        except Exception as e:
            print(f"Error: {e}")
            self.send_response(500)
            self.end_headers()
