import os
import httpx
import json
from dotenv import load_dotenv

load_dotenv()

EXOTEL_ACCOUNT_SID = os.getenv("EXOTEL_ACCOUNT_SID")
EXOTEL_API_KEY = os.getenv("EXOTEL_API_KEY")
EXOTEL_API_TOKEN = os.getenv("EXOTEL_API_TOKEN")
EXOTEL_SUBDOMAIN = os.getenv("EXOTEL_SUBDOMAIN")
EXOTEL_FROM_NUMBER = os.getenv("EXOTEL_FROM_NUMBER")

class ExotelClient:
    def __init__(self):
        self.account_sid = EXOTEL_ACCOUNT_SID
        self.api_key = EXOTEL_API_KEY
        self.api_token = EXOTEL_API_TOKEN
        self.base_url = (
            f"https://{self.api_key}:{self.api_token}@{EXOTEL_SUBDOMAIN}"
            f"/v2/accounts/{self.account_sid}/messages"
        )

    async def send_whatsapp_message(self, to_number: str, text: str, media_url: str = None):
        """
        Sends a WhatsApp message via Exotel.
        Using Exotel Campaign API / SMS API with WhatsApp channel.
        """
        auth = (self.api_key, self.api_token)
        
        if media_url:
            content = {
                "type": "image",
                "image": {
                    "link": media_url,
                    "caption": text
                }
            }
        else:
            content = {
                "type": "text",
                "text": {
                    "body": text
                }
            }

        payload = json.dumps({
            "whatsapp": {
                "messages": [
                    {
                        "from": EXOTEL_FROM_NUMBER,
                        "to": to_number,
                        "content": content
                    }
                ]
            }
        })

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url,
                auth=auth,
                headers={"Content-Type": "application/json"},
                content=payload
            )
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                print(f"Error sending Exotel message: {e.response.text}")
                raise
            return response.json()

exotel_client = ExotelClient()
