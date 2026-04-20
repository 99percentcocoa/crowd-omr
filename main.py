import os
import re
from typing import Optional

from fastapi import FastAPI, Form, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import Base, engine, get_db
from models import Worksheet
from exotel import exotel_client
from dotenv import load_dotenv

load_dotenv()

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="WhatsApp OMR Bot")

ALLOWED_USERS = set(os.getenv("ALLOWED_USERS", "").split(","))

BASE_IMAGE_URL = os.getenv("BASE_IMAGE_URL", "").strip().rstrip("/")

# Default template format (1 question per line)
TEMPLATE = "Answers:\n1: \n2: \n3: \n4: \n5: \n6: \n7: \n8: \n9: \n10: \n11: \n12: \n13: \n14: \n15: \n16: \n17: \n18: \n19: \n20: "
QUESTION_COUNT = 20


def build_media_url(image_ref: str) -> str:
    """Build a public image URL from a stored worksheet reference."""
    if image_ref.startswith("http://") or image_ref.startswith("https://"):
        return image_ref

    filename = os.path.basename(image_ref)
    if not BASE_IMAGE_URL:
        raise HTTPException(status_code=500, detail="BASE_URL/BASE_IMAGE_URL is not configured")

    return f"{BASE_IMAGE_URL}/{filename}"


def parse_answers(text_body: str, question_count: int = QUESTION_COUNT) -> dict[str, str]:
    """Parse user response text into {"1": "A", ..., "N": ""} format."""
    answers = {str(i): "" for i in range(1, question_count + 1)}

    # Accept formats like: "1: A", "2) b", "3 - C", "4.D".
    pattern = re.compile(r"^\s*(\d+)\s*[:)\-.]\s*([ABCDabcd]?)\s*$")

    for raw_line in text_body.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        match = pattern.match(line)
        if not match:
            continue

        q_num, option = match.groups()
        if q_num in answers:
            answers[q_num] = option.upper() if option else ""

    return answers

@app.post("/webhook")
async def exotel_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Webhook endpoint to receive messages from Exotel WhatsApp.
    """
    try:
        data = await request.json()
    except Exception:
        return Response(content="Invalid JSON", status_code=400)
        
    messages = data.get("whatsapp", {}).get("messages", [])
    if not messages:
        return Response(content="No messages found", status_code=400)
        
    msg = messages[0]
    sender_number = msg.get("from", "").strip()
    
    if not sender_number:
        return Response(content="Missing sender", status_code=400)
    
    # Check allowlist
    if sender_number not in ALLOWED_USERS:
        return Response(content="OK")
        
    content = msg.get("content", {})
    text_body = ""
    if content.get("type") == "text":
        text_body = content.get("text", {}).get("body", "").strip()
    
    # Check if user has an assigned worksheet
    worksheet = db.query(Worksheet).filter(
        Worksheet.assigned_to == sender_number,
        Worksheet.status == "assigned"
    ).first()
    
    if worksheet:
        # We assume the user replied with the answers
        if text_body.lower() in ['cancel', 'skip']:
            worksheet.status = "pending"
            worksheet.assigned_to = None
            db.commit()
            await exotel_client.send_whatsapp_message(sender_number, "Worksheet skipped. Send any message to get a new one.")
            return Response(content="Skipped")
            
        worksheet.results = {
            "answers": parse_answers(text_body),
        }
        worksheet.status = "completed"
        db.commit()
        
        await exotel_client.send_whatsapp_message(sender_number, "Results saved! Sending next worksheet...")
    
    # Send next worksheet
    next_worksheet = db.query(Worksheet).filter(Worksheet.status == "pending").first()
    
    if not next_worksheet:
        await exotel_client.send_whatsapp_message(sender_number, "No pending worksheets available.")
        return Response(content="Done")
        
    next_worksheet.status = "assigned"
    next_worksheet.assigned_to = sender_number
    db.commit()
    
    # Construct media URL
    media_url = build_media_url(next_worksheet.image_path)
    
    await exotel_client.send_whatsapp_message(
        sender_number,
        "Please grade this worksheet. Use the answer template in the next message."
        " Fill it in and reply.",
        media_url=media_url
    )

    await exotel_client.send_whatsapp_message(
        sender_number,
        TEMPLATE
    )
    
    return Response(content="OK")

class AddWorksheetsRequest(BaseModel):
    directory_path: Optional[str] = None
    file_list_path: str = "assets/image_files.txt"

@app.post("/admin/worksheets")
def add_worksheets(req: AddWorksheetsRequest, db: Session = Depends(get_db)):
    """
    Adds worksheets either from a local image directory or from a text file
    containing one image filename/URL per line.
    """
    added = 0
    seen_refs = set()
    if req.directory_path:
        if not os.path.isdir(req.directory_path):
            raise HTTPException(status_code=400, detail="Invalid directory path")

        for filename in os.listdir(req.directory_path):
            if filename.lower().endswith((".png", ".jpg", ".jpeg")):
                full_path = os.path.join(req.directory_path, filename)

                if full_path in seen_refs:
                    continue
                seen_refs.add(full_path)

                exists = db.query(Worksheet).filter(Worksheet.image_path == full_path).first()
                if not exists:
                    worksheet = Worksheet(image_path=full_path, status="pending")
                    db.add(worksheet)
                    added += 1
    else:
        if not os.path.isfile(req.file_list_path):
            raise HTTPException(status_code=400, detail="Invalid file list path")

        with open(req.file_list_path, "r", encoding="utf-8") as file:
            for line in file:
                image_ref = line.strip()
                if not image_ref:
                    continue

                if image_ref in seen_refs:
                    continue
                seen_refs.add(image_ref)

                # Skip unsupported extensions when entries are plain filenames.
                if not (
                    image_ref.lower().endswith((".png", ".jpg", ".jpeg"))
                    or image_ref.startswith("http://")
                    or image_ref.startswith("https://")
                ):
                    continue

                exists = db.query(Worksheet).filter(Worksheet.image_path == image_ref).first()
                if not exists:
                    worksheet = Worksheet(image_path=image_ref, status="pending")
                    db.add(worksheet)
                    added += 1
                
    db.commit()
    return {"message": f"Added {added} new worksheets"}
