import os
import httpx
from dotenv import load_dotenv

load_dotenv()

class ExotelClient:
    def __init__(self):
        self.account_sid = os.getenv("EXOTEL_ACCOUNT_SID")
        self.api_key = os.getenv("EXOTEL_API_KEY")
        self.api_token = os.getenv("EXOTEL_API_TOKEN")
        self.sender_id = os.getenv("EXOTEL_SENDER_ID")
        self.base_url = f"https://api.exotel.com/v1/Accounts/{self.account_sid}/Sms/send.json"

    async def send_whatsapp_message(self, to_number: str, text: str, media_url: str = None):
        """
        Sends a WhatsApp message via Exotel.
        Using Exotel Campaign API / SMS API with WhatsApp channel.
        """
        auth = (self.api_key, self.api_token)
        payload = {
            "From": self.sender_id,
            "To": to_number,
            "Body": text,
        }
        
        # Exotel might use different parameter for WhatsApp or media based on specific API version
        # We will include basic payload for MVP
        if media_url:
            payload["MediaUrl"] = media_url

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url,
                auth=auth,
                data=payload
            )
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                print(f"Error sending Exotel message: {e.response.text}")
                raise
            return response.json()

exotel_client = ExotelClient()
