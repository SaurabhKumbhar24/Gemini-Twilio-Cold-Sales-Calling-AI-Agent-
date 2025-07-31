from dotenv import load_dotenv
from twilio.rest import Client
import requests
import os
from datetime import datetime

load_dotenv()

account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
base_url = os.getenv("PUBLIC_DOMAIN")
number = os.getenv("TWILIO_PHONE_NUMBER")
sheet_url = os.getenv("SHEET_URL")
gapp_url = os.getenv("GAPP_URL")
my_phone = os.getenv("MY_PHONE")

client = Client(account_sid, auth_token)

def store_data(call_sid, to_phone):
    data = {
        "call_sid": call_sid,
        "to_number": to_phone,
        "timestamp": datetime.now()
    }
    try:
        response = requests.post(gapp_url, json=data)
        print("Google Sheet response:", response.text)
    except Exception as e:
        print("Failed to send to Google Sheet:", e)

def make_outbound_call(to_phone):
    url = f"{base_url}/twilio/outbound_call_handler"
    call = client.calls.create(
        to=to_phone,
        from_=number,
        url= url
    )
    print(f"Call initiated: {call.sid}")
    store_data(call.sid, to_phone)


make_outbound_call(to_phone=my_phone)