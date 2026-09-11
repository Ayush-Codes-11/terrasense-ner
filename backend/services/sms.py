import os
from abc import ABC, abstractmethod

class SMSProvider(ABC):
    @abstractmethod
    def send_sms(self, to_number: str, message: str) -> str:
        pass

class DemoSMSProvider(SMSProvider):
    def send_sms(self, to_number: str, message: str) -> str:
        print(f"\n[DEMO SMS to {to_number}]\n{message}\n[DEMO — not delivered to telecom network]\n")
        return "DEMO_PREVIEW"

class TwilioSMSProvider(SMSProvider):
    def send_sms(self, to_number: str, message: str) -> str:
        try:
            from twilio.rest import Client
        except ImportError as exc:
            raise RuntimeError(
                "SMS_PROVIDER=twilio requires `pip install -r backend/requirements-local.txt`."
            ) from exc
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        from_number = os.getenv("TWILIO_FROM_NUMBER")
        if not account_sid or not auth_token or not from_number:
            raise RuntimeError(
                "Twilio is not configured. Set TWILIO_ACCOUNT_SID, "
                "TWILIO_AUTH_TOKEN, and TWILIO_FROM_NUMBER."
            )
        Client(account_sid, auth_token).messages.create(
            body=message,
            from_=from_number,
            to=to_number,
        )
        return "SENT_TWILIO"

def get_sms_provider() -> SMSProvider:
    provider = os.getenv("SMS_PROVIDER", "demo").lower()
    if provider == "twilio":
        return TwilioSMSProvider()
    return DemoSMSProvider()
