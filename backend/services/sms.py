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
        raise NotImplementedError("PROVIDER_NOT_CONFIGURED: Real Twilio API integration is absent. Set SMS_PROVIDER=demo.")

def get_sms_provider() -> SMSProvider:
    provider = os.getenv("SMS_PROVIDER", "demo").lower()
    if provider == "twilio":
        return TwilioSMSProvider()
    return DemoSMSProvider()
