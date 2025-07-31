import os
import json
import base64
import asyncio
import websockets
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.websockets import WebSocketDisconnect
from twilio.twiml.voice_response import VoiceResponse, Connect, Say, Stream
from dotenv import load_dotenv
import re

load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
PORT = int(os.getenv('PORT', 6060))
raw_domain = os.getenv('PUBLIC_DOMAIN', '')
DOMAIN = re.sub(r'(^\w+:|^)\/\/|\/+$', '', raw_domain)
SYSTEM_MESSAGE = (
    "You are Tarifflo's helpful AI sales call assistant. Your name is Ana. You are female and a sales executive of Tarifflo. " 
    "Your goal is to introduce Tarifflo and politely persuade the user to book a meeting."
    "You MUST follow these rules:"
    "1. Always respond in a friendly, conversational tone."
    "2. If the user says they’re interested but only mentions a vague time (like \"next week\" or \"sometime later\"), politely ask for a **specific day & time**."
    "3. When the user agrees to book a meeting or ends the call, politely say goodbye and end the conversation by saying: 'Thank you for your time. Goodbye.'"
    "Start the conversation by saying: 'Hello, this is Ana from Tarifflo. How are you today?'"
)
VOICE = 'alloy'
SHOW_TIMING_MATH = False

LOG_EVENT_TYPES = [
    'error', 'response.content.done', 'rate_limits.updated', 'response.done',
    'input_audio_buffer.committed', 'input_audio_buffer.speech_stopped',
    'input_audio_buffer.speech_started', 'session.created'
]

app = FastAPI()

@app.get("/", response_class=JSONResponse)
async def index_page():
    return {"message":"Twilio Media Stream Server is running!"}

@app.api_route("/twilio/outbound_call_handler", methods=["GET","POST"])
async def outbound_call_handler(request: Request):
    
    response = VoiceResponse()
    response.pause(length=1)
    host = request.url.hostname
    connect = Connect()
    stream_url = f"wss://{host}/twilio/reply"
    print(f"Connecting call to WebSocket: {stream_url}")
    connect.stream(url=stream_url)
    response.append(connect)

    return HTMLResponse(content=str(response), media_type="application/xml")


@app.websocket("/twilio/reply")
async def handle_media_stream(websocket: WebSocket):
    print("Client connected")

    await websocket.accept()
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Beta": "realtime=v1"
    }
    
    async with websockets.connect(
        'wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2025-06-03',
        extra_headers = headers
    ) as openai_ws:
        await initialize_session(openai_ws)
        stream_sid = None
        mark_queue = []

        async def receive_from_twilio():
            nonlocal stream_sid
            try:
                async for message in websocket.iter_text():
                    data = json.loads(message)
                    if data['event'] == 'media' and openai_ws.open:
                        audio_append = {
                            "type": "input_audio_buffer.append",
                            "audio": data['media']['payload']
                        }
                        await openai_ws.send(json.dumps(audio_append))

                    elif data['event'] == 'start':
                        stream_sid = data['start']['streamSid']
                        print(f"Incoming stream has started {stream_sid}")

                    elif data['event'] == 'mark':
                        if mark_queue:
                            mark_queue.pop(0)

            except WebSocketDisconnect:
                print("Client disconnected.")
                if openai_ws.open:
                    await openai_ws.close()

        async def send_to_twilio():
            nonlocal stream_sid
            try:
                async for openai_message in openai_ws:
                    response = json.loads(openai_message)
                    if response['type'] in LOG_EVENT_TYPES:
                        print(f"Received event: {response['type']}", response)

                    if response.get('type') == 'response.audio.delta' and 'delta' in response:
                        audio_payload = base64.b64encode(base64.b64decode(response['delta'])).decode('utf-8')
                        audio_delta = {
                            "event": "media",
                            "streamSid": stream_sid,
                            "media": {
                                "payload": audio_payload
                            }
                        }
                        await websocket.send_json(audio_delta)

                        await send_mark(websocket, stream_sid)
                
            except Exception as e:
                print(f"Error in send_to_twilio: {e}")

        async def send_mark(connection, stream_sid):
            if stream_sid:
                mark_event = {
                    "event": "mark",
                    "streamSid": stream_sid,
                    "mark": {"name": "responsePart"}
                }
                await connection.send_json(mark_event)
                mark_queue.append('responsePart')

        await asyncio.gather(receive_from_twilio(), send_to_twilio())

async def initialize_session(openai_ws):
    session_update = {
        "type": "session.update",
        "session":{
            "turn_detection":{ "type": "server_vad" },
            "input_audio_format": "g711_ulaw",
            "output_audio_format": "g711_ulaw", #Required for twilio media streams
            "voice": VOICE,
            "instructions": SYSTEM_MESSAGE,
            "modalities":['text','audio'],
            "temperature": 0.8
        }
    }
    print("Sending session update: ", json.dumps(session_update))
    await openai_ws.send(json.dumps(session_update))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)