import os
import json
import asyncio
from google import genai
from dotenv import load_dotenv
from fastapi.responses import HTMLResponse
from fastapi import FastAPI, WebSocket, Request
from fastapi.websockets import WebSocketDisconnect
from twilio.twiml.voice_response import VoiceResponse, Connect
from utils import convert_audio_to_mulaw, convert_mulaw_to_pcm_16k

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = 'gemini-2.5-flash-preview-native-audio-dialog'
PORT = int(os.getenv('PORT', 6060))
ASSISTANT_NAME = "Emily"

SYSTEM_MESSAGE = [
    f"You are Tarifflo's helpful AI sales call assistant. Your name is {ASSISTANT_NAME}. You are female and a sales executive of Tarifflo.",
    "Your goal is to introduce Tarifflo and politely persuade the user to book a meeting.",
    "You MUST follow these Rules:",
    "-  Always respond in a friendly, conversational tone.",
    "-  If the user says they’re interested but only mentions a vague time (like \"next week\" or \"sometime later\"), politely ask for a **specific day & time**.",
    "-  When the user agrees to book a meeting or ends the call, politely say goodbye and end the conversation by saying: 'Thank you for your time. Goodbye.'"
]
    
CONFIG = {
    "response_modalities": ["AUDIO"],
    "system_instruction": " ".join(SYSTEM_MESSAGE),
    "speech_config":{
        "voice_config":{
            "prebuilt_voice_config":{
                "voice_name":"Achernar"
            }
        },
        "language_code":"en-US"
    },
    "output_audio_transcription":{},
    "input_audio_transcription":{},
}

client = genai.Client(api_key=GEMINI_API_KEY)

app = FastAPI()

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
async def handle_media_stream(twilio_ws: WebSocket):
    
    await twilio_ws.accept()
    print(f"WebSocket client connected")
    async with client.aio.live.connect(model=MODEL, config=CONFIG) as gemini_ws:

        stream_sid = None
        await gemini_ws.send_client_content(turns={
            "parts": [
                {"text": f"Start the conversation by saying: 'Hello, this is {ASSISTANT_NAME} from Tarifflo. How are you today?'"}
                ]
            })

        async def receive_from_twilio():
            nonlocal stream_sid
            try:
                async for message in twilio_ws.iter_text():
                
                    data = json.loads(message)
                    if data['event'] == 'start':
                        stream_sid = data['start']['streamSid']

                    if data['event'] == 'media':
                        audio_data = convert_mulaw_to_pcm_16k(data['media']['payload'])
                        await gemini_ws.send_realtime_input(
                            audio = {
                                "data":audio_data, 
                                "mime_type":"audio/pcm"
                            }
                        )

                    if data['event'] == 'stop':
                        print("stream stopped")

            except WebSocketDisconnect:
                    print("Client disconnected.")
                    if gemini_ws.open:
                        await gemini_ws.close()

        full_transcript = []
        async def send_to_twilio():
            nonlocal stream_sid
            try:
                while True:
                    human_transcript = ""
                    ai_transcript = ""
                    async for response in gemini_ws.receive():

                        if response.server_content.input_transcription:
                            text = response.server_content.input_transcription.text
                            human_transcript += text + " "

                        if response.server_content.output_transcription:
                            text = response.server_content.output_transcription.text
                            ai_transcript += text + " "
                        
                        if response.server_content.model_turn:
                            data = response.server_content.model_turn.parts[0].inline_data.data
                            if data:
                                audio_data = convert_audio_to_mulaw(data)
                                payload = {
                                    'event': "media",
                                    "streamSid": stream_sid,
                                    "media":{
                                        "payload": audio_data
                                    }
                                }
                                
                                await twilio_ws.send_json(payload)

                                if "goodbye" in (" ".join(full_transcript)).lower():
                                    print(f"Full Transcript: {" ".join(full_transcript)}")
                                    await twilio_ws.close()
                                    await gemini_ws.close()

                    full_transcript.append(f"AI: {ai_transcript}\nHuman: {human_transcript}\n")    


            except Exception as e:
                print(f"Unexpected error in gemini websocket: {e}")

        await asyncio.gather(receive_from_twilio(), send_to_twilio())

if __name__ == "__main__":
    import uvicorn
    print("Starting Uvicorn server...")
    uvicorn.run(app, host="0.0.0.0", port=PORT)