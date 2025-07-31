from twilio.rest import Client
import os
from dotenv import load_dotenv

load_dotenv()

account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
base_url = os.getenv("PUBLIC_DOMAIN")
number = os.getenv("TWILIO_PHONE_NUMBER")
client = Client(account_sid, auth_token)

def make_outbound_call(to_phone):
    url = f"{base_url}/twilio/outbound_call_handler"
    call = client.calls.create(
        to=to_phone,
        from_=number,
        url= url
    )
    print(f"Call initiated: {call.sid}")

make_outbound_call(to_phone="+15854068142")