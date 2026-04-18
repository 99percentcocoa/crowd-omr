import os
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
# Nginx should be configured to serve files from your local directory at this base URL
BASE_IMAGE_URL = os.getenv("BASE_IMAGE_URL", "http://localhost/images").rstrip('/')

# Default template format (1 question per line)
TEMPLATE = "1: \n2: \n3: \n4: \n5: "

@app.post("/webhook")
async def exotel_webhook(
    request: Request,
    From: str = Form(None),
    Body: str = Form(None),
    db: Session = Depends(get_db)
):
    """
    Webhook endpoint to receive messages from Exotel WhatsApp.
    """
    # Sometimes exotel payload has different keys, fallback to parsing form data directly
    if not From and not Body:
        form_data = await request.form()
        From = form_data.get("From")
        Body = form_data.get("Body")
        
    if not From:
        return Response(content="Missing sender", status_code=400)
    
    sender_number = From.strip()
    
    # Check allowlist
    if sender_number not in ALLOWED_USERS:
        return Response(content="Unauthorized", status_code=403)
        
    text_body = Body.strip() if Body else ""
    
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
            
        worksheet.results = {"raw_text": text_body}
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
    filename = os.path.basename(next_worksheet.image_path)
    media_url = f"{BASE_IMAGE_URL}/{filename}"
    
    await exotel_client.send_whatsapp_message(
        sender_number, 
        f"Please grade this worksheet. Copy the template below, fill it in, and reply:\n\n{TEMPLATE}",
        media_url=media_url
    )
    
    return Response(content="OK")

class AddWorksheetsRequest(BaseModel):
    directory_path: str

@app.post("/admin/worksheets")
def add_worksheets(req: AddWorksheetsRequest, db: Session = Depends(get_db)):
    """
    Scans a directory for images and adds them to the database.
    (Admin MVP tool)
    """
    if not os.path.isdir(req.directory_path):
        raise HTTPException(status_code=400, detail="Invalid directory path")
        
    added = 0
    for filename in os.listdir(req.directory_path):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            full_path = os.path.join(req.directory_path, filename)
            
            # check if exists
            exists = db.query(Worksheet).filter(Worksheet.image_path == full_path).first()
            if not exists:
                worksheet = Worksheet(image_path=full_path, status="pending")
                db.add(worksheet)
                added += 1
                
    db.commit()
    return {"message": f"Added {added} new worksheets"}
