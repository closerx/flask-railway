# app.py
from flask import Flask, render_template
from flask_socketio import SocketIO
import asyncio
import websockets
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'any-secret-key'

# استخدم async_mode="asgi" + uvicorn بدل eventlet
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="asgi")

# مفتاح DeepGram (ضعه في الـ Environment Variables على Railway)
DEEPGRAM_API_KEY = "ضع_مفتاحك_هنا"  # أو من os.getenv

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('start_transcription')
async def handle_transcription():
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
        async with websockets.connect(ws_url, extra_headers=headers) as ws:
            print("متصل بـ DeepGram...")

            async def receive():
                async for message in ws:
                    data = json.loads(message)
                    transcript = data.get("channel", {}) \
                                      .get("alternatives", [{}])[0] \
                                      .get("transcript", "").strip()
                    is_final = data.get("is_final", False)

                    if transcript:
                        await socketio.emit('transcript_update', {
                            'text': transcript,
                            'is_final': is_final
                        })

            async def keep_alive():
                while True:
                    await ws.send(json.dumps({"type": "KeepAlive"}))
                    await asyncio.sleep(5)

            # نشغل الاستقبال + keep alive مع بعض
            await asyncio.gather(receive(), keep_alive())

    except Exception as e:
        await socketio.emit('error', {'message': str(e)})
        print(f"خطأ: {e}")

if __name__ == '__main__':
    # على Railway ومحليًا هيشتغل عادي
    socketio.run(app, host='0.0.0.0', port=5000)
