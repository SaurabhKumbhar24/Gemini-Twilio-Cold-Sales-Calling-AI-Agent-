import base64
import audioop
import numpy as np
import requests
import os
from dotenv import load_dotenv
from scipy.signal import resample

def convert_audio_to_mulaw(audio_data: bytes) -> str:
    pcm_np = np.frombuffer(audio_data, dtype=np.int16)
    target_length = int(len(pcm_np) * (8000 / 24000))
    pcm_8k_np = resample(pcm_np, target_length)
    pcm_8k_bytes = pcm_8k_np.astype(np.int16).tobytes()
    mulaw_bytes = audioop.lin2ulaw(pcm_8k_bytes, 2)

    return base64.b64encode(mulaw_bytes).decode('utf-8')

def convert_mulaw_to_pcm_16k(mulaw_base64: str) -> bytes:
    mulaw_data = base64.b64decode(mulaw_base64)
    pcm_8k = audioop.ulaw2lin(mulaw_data, 2)
    pcm_np = np.frombuffer(pcm_8k, dtype=np.int16)
    num_samples_16k = int(len(pcm_np) * 16000 / 8000)
    pcm_16k_np = resample(pcm_np, num_samples_16k)
    pcm_16k = pcm_16k_np.astype(np.int16).tobytes()

    return pcm_16k

load_dotenv()
gapp_url = os.getenv("GAPP_TRANSCRIPT_URL")
def save_details(transcript, call_sid):
    data = {
        "call_sid": call_sid,
        "transcript": transcript
    }
    try:
        response = requests.post(gapp_url, json=data)
        print("Google Sheet response:", response.text)
    except Exception as e:
        print("Failed to send to Google Sheet:", e)