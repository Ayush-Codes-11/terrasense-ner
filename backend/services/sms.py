import os
from abc import ABC, abstractmethod

class SMSProvider(ABC):
    @abstractmethod
    def send_sms(self, to_number: str, message: str) -> bool:
        pass

class DemoSMSProvider(SMSProvider):
    def send_sms(self, to_number: str, message: str) -> bool:
        print(f"\n[DEMO SMS to {to_number}]\n{message}\n[DEMO — not delivered to telecom network]\n")
        return True

class TwilioSMSProvider(SMSProvider):
    def send_sms(self, to_number: str, message: str) -> bool:
        # In a real implementation, this would use twilio python client
        print(f"Twilio SMS sent to {to_number}: {message}")
        return True

def get_sms_provider() -> SMSProvider:
    provider = os.getenv("SMS_PROVIDER", "demo").lower()
    if provider == "twilio":
        return TwilioSMSProvider()
    return DemoSMSProvider()
