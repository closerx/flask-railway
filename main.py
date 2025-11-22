# app.py
import os
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import asyncio
import websockets
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = "qwertyuiopasdfghjklzxcvbnm"

# مفتاح DeepGram من Environment Variable (أمان أكتر)
DEEPGRAM_API_KEY = "3c87d0d29e1ed5b1cabf7ab61fd326b9e04f5a75" 

# الحل: async_mode=None (افتراضي threading) - مش 'asgi'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode=None)  # <-- هنا التغيير الرئيسي

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('start_transcription')
def handle_transcription():  # مش async هنا، عشان threading
    # نشغل الـ DeepGram WS في background task (متوافق مع threading)
    socketio.start_background_task(run_deepgram_ws)

def run_deepgram_ws():
    """دالة الـ WebSocket لـ DeepGram - تشغيل في thread منفصل"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(deepgram_ws())

async def deepgram_ws():
    """الـ WebSocket الفعلي"""
    url = "wss://api.deepgram.com/v1/listen"
    params = {
        "model": "nova-3",
        "language": "ar",
        "smart_format": "true",
        "filler_words": "true",
        "interim_results": "true",
        "utterance_end_ms": "3000",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    ws_url = f"{url}?{query}"

    headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}"}

    try:
        async with websockets.connect(ws_url, additional_headers=headers) as ws:
            print("✅ متصل بـ DeepGram! ابدأ الكلام...")

            async def receive():
                async for message in ws:
                    data = json.loads(message)
                    transcript = data.get("channel", {}) \
                                      .get("alternatives", [{}])[0] \
                                      .get("transcript", "").strip()
                    is_final = data.get("is_final", False)

                    if transcript:
                        # emit في thread آمن
                        emit('transcript_update', {
                            'text': transcript,
                            'is_final': is_final
                        }, broadcast=False)  # للعميل اللي طلب

            async def keep_alive():
                while True:
                    try:
                        await ws.send(json.dumps({"type": "KeepAlive"}))
                        await asyncio.sleep(5)
                    except:
                        break

            await asyncio.gather(receive(), keep_alive())

    except Exception as e:
        print(f"❌ خطأ: {e}")
        emit('error', {'message': str(e)})

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
