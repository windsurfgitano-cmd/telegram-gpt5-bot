# 🤖 Telegram Bot - VERSIÓN SIMPLIFICADA

## ✅ Esta versión usa AMBAS estructuras:
- `index.py` en la raíz (ruta principal)
- `api/webhook.py` (backup)

## 🚀 Instrucciones:

### 1. Reemplazar archivos
```bash
cd telegram-gpt5-bot
# Copia todos los archivos del ZIP
git add .
git commit -m "Simplified structure with index.py"
git push
```

### 2. Variables en Vercel
Verifica que estén configuradas en:
https://vercel.com/ozymandias1/telegram-gpt5-bot/settings/environment-variables

- TELEGRAM_BOT_TOKEN
- AZURE_ENDPOINT
- AZURE_API_KEY
- DEPLOYMENT_NAME

### 3. Webhook de Telegram

Opción A - Ruta raíz:
```powershell
Invoke-WebRequest -Uri "https://api.telegram.org/bot8384920499:AAGG21trm2kd6AOiZK45li-QtMivadWI1NE/setWebhook?url=https://telegram-gpt5-bot.vercel.app" -Method Post
```

Opción B - Ruta /api/webhook:
```powershell
Invoke-WebRequest -Uri "https://api.telegram.org/bot8384920499:AAGG21trm2kd6AOiZK45li-QtMivadWI1NE/setWebhook?url=https://telegram-gpt5-bot.vercel.app/api/webhook" -Method Post
```

## 🎉 ¡Pruébalo!
Envía un mensaje a @ElReyDeLasPaginasBot
