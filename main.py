# app.py
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import eventlet

eventlet.monkey_patch()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# ضع مفتاح DeepGram هنا
DEEPGRAM_API_KEY = "ضع_مفتاح_DeepGram_هنا"   # مثال: 407e4e5d8c9f...

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('start_transcription')
def handle_transcription():
    import asyncio
    import websockets
    import json

    async def deepgram_ws():
        url = "wss://api.deepgram.com/v1/listen"
        params = {
            "model": "nova-3",
            "language": "ar",
            "smart_format": "true",
            "filler_words": "true",
            "interim_results": "true",
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        ws_url = f"{url}?{query}"

        extra_headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}"}

        try:
            async with websockets.connect(ws_url, additional_headers=extra_headers) as ws:
                print("DeepGram متصل - ابدأ الكلام...")

                async def receive():
                    async for message in ws:
                        data = json.loads(message)
                        transcript = data.get("channel", {}).get("alternatives", [{}])[0].get("transcript", "")
                        is_final = data.get("is_final", False)
                        if transcript.strip():
                            socketio.emit('transcript_update', {
                                'text': transcript,
                                'is_final': is_final
                            })

                async def keep_alive():
                    while True:
                        await ws.send(json.dumps({"type": "KeepAlive"}))
                        await asyncio.sleep(5)

                await asyncio.gather(receive(), keep_alive())

        except Exception as e:
            socketio.emit('error', {'message': str(e)})

    # نشغل الـ WebSocket في thread منفصل
    socketio.start_background_task(lambda: asyncio.run(deepgram_ws()))

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
