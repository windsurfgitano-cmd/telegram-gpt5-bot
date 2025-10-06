# 🎤 Telegram GPT-5 Bot con Audio Nativo

## ✅ ¿Qué hay en este ZIP?

- **index.py** → Bot completo con soporte de audio nativo
- **requirements.txt** → Dependencias actualizadas
- **vercel.json** → Configuración con FFmpeg  
- **README_AUDIO.md** → Este archivo

---

## 🚀 IMPLEMENTACIÓN (3 pasos)

### 1️⃣ Reemplazar archivos en tu repo local

```bash
cd telegram-gpt5-bot

# Copia estos archivos (reemplaza los existentes):
cp index.py .
cp requirements.txt .
cp vercel.json .
```

### 2️⃣ Verificar variables de entorno en Vercel

Asegúrate de tener configuradas en tu proyecto de Vercel:

```
TELEGRAM_BOT_TOKEN = 7xxxxxx:AAHxxxxxxxxxxxxxx
AZURE_ENDPOINT = https://kondorcode-resource.cognitiveservices.azure.com  
AZURE_API_KEY = tu_api_key
DEPLOYMENT_NAME = gpt-audio
COMPOSIO_API_KEY = tu_api_key
COMPOSIO_ENTITY_ID = urJQejDZeeeD
FLUX_API_KEY = tu_api_key (opcional)
NOTION_API_KEY = tu_api_key (opcional)
```

### 3️⃣ Commit y push

```bash
git add .
git commit -m "feat: add complete audio support with Azure GPT-Audio and modalities"
git push
```

**Vercel hará deploy automáticamente** (2-3 minutos).

---

## ✨ NUEVAS FUNCIONALIDADES

✅ **Procesamiento de mensajes de voz nativamente**  
✅ **Azure GPT-Audio con parámetro `modalities`** (requerido)  
✅ **Sin necesidad de Whisper** (más económico)  
✅ **Conserva tono y contexto emocional del audio**  

---

## 🧪 CÓMO PROBAR

1. Abre tu bot en Telegram
2. Graba un mensaje de voz:

   🗣️ **"Hola, ¿cómo estás?"**

   o mejor aún:

   🗣️ **"Envía un email a juan@example.com con el asunto Prueba de audio"**

3. El bot debería responder:

   ```
   🎤 Procesando tu mensaje de voz...
   [respuesta del bot]
   ```

---

## 🔧 CAMBIOS TÉCNICOS

### Funciones agregadas:

1. `get_telegram_file(file_id)` → Obtiene metadata del audio
2. `download_telegram_audio(file_id)` → Descarga el archivo
3. `call_azure_gpt_with_audio(audio_b64, user_id)` → **Incluye `modalities: ["text"]`**
4. `process_voice_message(message, chat_id, user_id)` → Handler completo

### Modificación en `do_POST()`:

```python
# Después de extraer chat_id y user_id:
if message.get("voice"):
    response = process_voice_message(message, chat_id, user_id)
    if response:
        send_telegram_message(chat_id, response)
    self.send_response(200)
    self.end_headers()
    return
```

---

## 🐛 TROUBLESHOOTING

### Error: "Missing variable handler"
→ El archivo `index.py` está corrupto. Vuelve a copiar el del ZIP.

### Error: "400 Bad Request" en Azure
→ Falta el parámetro `modalities` (ya está incluido en este código).

### Error: "Error downloading audio"
→ Verifica que `TELEGRAM_BOT_TOKEN` sea correcto.

### Error: FFmpeg not found
→ Vercel instalará FFmpeg automáticamente con el `buildCommand` en `vercel.json`.

---

## 📊 LOGS ESPERADOS

Si todo funciona bien, verás en Vercel:

```
✅ Processing voice message from user_12345
📥 Downloaded 45230 bytes of audio  
🎤 Sending to Azure GPT-Audio...
✅ Azure response received
💬 Sending response to user
```

---

## 📚 DOCUMENTACIÓN COMPLETA

Ver documentación detallada en Google Drive:
- Arquitectura del sistema
- Comparación de tecnologías (Whisper vs GPT-Audio)
- Casos de uso
- Costos y pricing

---

## 🎯 PRÓXIMOS PASOS (Mejoras futuras)

Una vez que funcione el audio básico, puedes agregar:

- 🎤 **Respuestas en audio (TTS)** - El bot también responde con voz
- 🌍 **Multi-idioma** - Detecta el idioma del audio automáticamente  
- 🎯 **Detección de urgencia** - Entiende si el tono es urgente o calmado
- 📊 **Dashboard de métricas** - Estadísticas de uso

---

## 💡 AYUDA

Si tienes problemas:

1. Revisa los logs en **Vercel Dashboard**
2. Verifica que todas las **variables de entorno** estén configuradas
3. Prueba primero con un mensaje de **texto** para verificar que el bot funciona
4. Luego prueba con **audio**

---

🎉 **¡Disfruta tu control remoto por voz!** 🎤🚀

Creado por: Kondor Code
Implementación con: Rube.app + Composio
