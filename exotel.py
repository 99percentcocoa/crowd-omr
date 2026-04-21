import os
import httpx
import json
import logging
from dotenv import load_dotenv

load_dotenv()

EXOTEL_ACCOUNT_SID = os.getenv("EXOTEL_ACCOUNT_SID")
EXOTEL_API_KEY = os.getenv("EXOTEL_API_KEY")
EXOTEL_API_TOKEN = os.getenv("EXOTEL_API_TOKEN")
EXOTEL_SUBDOMAIN = os.getenv("EXOTEL_SUBDOMAIN")
EXOTEL_FROM_NUMBER = os.getenv("EXOTEL_FROM_NUMBER")

logger = logging.getLogger(__name__)

class ExotelClient:
    def __init__(self):
        self.account_sid = EXOTEL_ACCOUNT_SID
        self.api_key = EXOTEL_API_KEY
        self.api_token = EXOTEL_API_TOKEN
        self.base_url = (
            f"https://{self.api_key}:{self.api_token}@{EXOTEL_SUBDOMAIN}"
            f"/v2/accounts/{self.account_sid}/messages"
        )

    @staticmethod
    def _mask_phone(number: str) -> str:
        if not number:
            return "unknown"
        if len(number) <= 4:
            return "*" * len(number)
        return f"{'*' * (len(number) - 4)}{number[-4:]}"

    async def send_whatsapp_message(self, to_number: str, text: str, *, media_url: str = None):
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

        logger.info(
            "Sending WhatsApp message via Exotel to=%s content_type=%s has_media=%s",
            self._mask_phone(to_number),
            "image" if media_url else "text",
            bool(media_url),
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url,
                auth=auth,
                headers={"Content-Type": "application/json"},
                content=payload,
                timeout=20.0,
            )
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                logger.error(
                    "Exotel HTTP error status=%s response=%s",
                    e.response.status_code,
                    e.response.text,
                )
                raise
            except httpx.HTTPError as e:
                logger.exception("Exotel transport error: %s", str(e))
                raise

            logger.info(
                "Exotel message accepted status=%s to=%s",
                response.status_code,
                self._mask_phone(to_number),
            )
            return response.json()

exotel_client = ExotelClient()
