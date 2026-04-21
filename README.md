# Crowd OMR WhatsApp Bot

## What This Project Is

Crowd OMR is a FastAPI service that distributes worksheet images over WhatsApp (via Exotel for now), collects structured answer replies from reviewers, validates those replies, and stores results in a database.

The system is designed for "human-in-the-loop" checking of OMR-style worksheets where multiple users can collaboratively process pending sheets.

## What It Does

- Receives inbound WhatsApp messages on a webhook.
- Allows only configured phone numbers to participate.
- Assigns pending worksheets to users one at a time.
- Sends worksheet image + fixed answer template.
- Validates replies strictly (header, question order, and A/B/C/D options).
- Saves parsed answers as JSON in the database.
- Supports skipping a worksheet (`skip`, `next`, or `cancel`).
- Provides a `status` command for queue counts.
- Includes an admin endpoint to bulk-load worksheets.

## High-Level Flow

1. Admin loads worksheet references (local filenames/paths or URLs).
2. User sends any message to start.
3. Bot assigns one pending worksheet and sends image + template.
4. User replies with answers in the required format.
5. Bot validates and stores answers, marks worksheet completed.
6. Bot sends the next worksheet until queue is empty.

## Tech Stack

- Python 3
- FastAPI
- SQLAlchemy
- PostgreSQL driver (`psycopg2-binary`)
- Exotel WhatsApp API
- `httpx`
- `python-dotenv`

## Project Structure

- `main.py`: API routes, webhook logic, worksheet assignment workflow.
- `models.py`: `Worksheet` SQLAlchemy model.
- `database.py`: DB engine/session setup.
- `exotel.py`: Exotel WhatsApp client.
- `message_validator.py`: strict template/reply validation parser.
- `logging_config.py`: request-aware rotating file logging.
- `assets/image_files.txt`: sample/default worksheet list.
- `requirements.txt`: Python dependencies.

## Worksheet Data Model

The `worksheets` table stores:

- `id`
- `image_path` (unique)
- `status` (`pending`, `assigned`, `completed`)
- `assigned_to` (phone number)
- `results` (JSON, stores parsed answers)
- timestamps

## Environment Variables

Create a `.env` file in the project root and define:

### Required

- `DATABASE_URL`: SQLAlchemy DB URL.
- `ALLOWED_USERS`: comma-separated WhatsApp numbers allowed to use the bot.
- `BASE_IMAGE_URL`: public base URL used for local image filenames.
- `EXOTEL_ACCOUNT_SID`
- `EXOTEL_API_KEY`
- `EXOTEL_API_TOKEN`
- `EXOTEL_SUBDOMAIN`
- `EXOTEL_FROM_NUMBER`

### Optional Logging Config

- `LOG_LEVEL` (default: `INFO`)
- `LOG_DIR` (default: `logs`)
- `LOG_FILE` (default: `app.log`)
- `LOG_MAX_BYTES` (default: `10485760`)
- `LOG_BACKUP_COUNT` (default: `5`)
- `LOG_CONSOLE` (default: `true`)

Example `.env`:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/crowd_omr
ALLOWED_USERS=+919999999999,+918888888888
BASE_IMAGE_URL=https://your-domain.com/images

EXOTEL_ACCOUNT_SID=your_account_sid
EXOTEL_API_KEY=your_api_key
EXOTEL_API_TOKEN=your_api_token
EXOTEL_SUBDOMAIN=api.exotel.com
EXOTEL_FROM_NUMBER=whatsapp:+91XXXXXXXXXX

LOG_LEVEL=INFO
LOG_DIR=logs
LOG_FILE=app.log
LOG_CONSOLE=true
```

## Setup

1. Create and activate a virtual environment.
2. Install dependencies.
3. Configure `.env`.
4. Ensure your database is reachable.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run The Service

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Tables are created automatically at startup.

## API Endpoints

### 1) Webhook

- `POST /webhook`
- Receives Exotel WhatsApp payloads.
- Expected payload path: `whatsapp.messages[0]`.

Special text commands:

- `status`: returns queue counts.
- `skip`, `next`, `cancel`: release current worksheet and fetch another.

### 2) Admin Worksheet Import

- `POST /admin/worksheets`

Request body:

```json
{
	"directory_path": null,
	"file_list_path": "assets/image_files.txt"
}
```

Behavior:

- If `directory_path` is provided, imports `.png/.jpg/.jpeg` files from that folder.
- Otherwise reads `file_list_path` (one entry per line).
- Avoids duplicates (already existing `image_path` values are skipped).

Example import call:

```bash
curl -X POST http://localhost:8000/admin/worksheets \
	-H "Content-Type: application/json" \
	-d '{"file_list_path":"assets/image_files.txt"}'
```

## How Reviewers Should Reply

The bot sends a template like:

```text
उत्तरे:
1:
2:
...
20:
```

The reviewer must keep structure intact and fill options with only `A`, `B`, `C`, or `D`.

Valid reply example:

```text
उत्तरे:
1: A
2: B
3: C
4: D
5: A
6: B
7: C
8: D
9: A
10: B
11: C
12: D
13: A
14: B
15: C
16: D
17: A
18: B
19: C
20: D
```

If validation fails, the bot sends an error reason and requests resubmission.

## Notes On Images

- If worksheet `image_path` is already an absolute URL (`http`/`https`), it is used directly.
- If it is a local filename/path, the bot generates media URL as:

`BASE_IMAGE_URL/<filename>`

So local files must be publicly accessible from that URL base.

## Logging

- Logs are written to rotating files (default: `logs/app.log`).
- Each request includes a request ID in logs.

## Quick Start Checklist

1. Set `.env` values (DB, Exotel, allowed users, image base URL).
2. Start the app with Uvicorn.
3. Import worksheets using `/admin/worksheets`.
4. Configure Exotel webhook to point to `/webhook`.
5. Send a WhatsApp message from an allowed number to begin reviewing.

## Troubleshooting

- `DATABASE_URL is not configured`: missing DB env var.
- Sender gets no worksheets: ensure they are in `ALLOWED_USERS` and pending data exists.
- Image not delivered: verify `BASE_IMAGE_URL` and public image hosting.
- Invalid template errors: ensure response includes header and exactly 20 numbered lines.

