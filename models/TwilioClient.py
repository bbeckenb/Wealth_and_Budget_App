from twilio.rest import Client
import os

class TwilioClient:
    """Class to represent my connection to Twilio and house methods to call their API for this application"""
    def __init__(self):
        self.twilio_number = os.getenv('TWILIO_NUM')
        self.twilio_client = self.create_Twilio_client()

    def create_Twilio_client(self):
        """Establishes twilio client to enable app to communicate with Twilio server"""
        return Client(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN'))

    def send_text(self, phone_number:str, msg:str):
        """sends text message using Twilio API"""
        phone_number='+1'+phone_number
        self.twilio_client.api.account.messages.create(to=phone_number, from_=self.twilio_number, body=msg)