"""
Embedded Email Listener Service
Runs as a background thread inside FastAPI. Controllable via API endpoints.
"""
import os
import time
import imaplib
import smtplib
import email
import json
import threading
import requests
from email.message import EmailMessage
from email.utils import parseaddr
from dotenv import load_dotenv

load_dotenv()

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")
API_URL = "http://127.0.0.1:8000/api/ai-onboarding"
IMAP_SERVER = "imap.gmail.com"
SMTP_SERVER = "smtp.gmail.com"
REMINDERS_FILE = "reminders.json"

# Reminder schedule (in seconds). Each entry = one reminder level.
# Level 0: 5 min, Level 1: 10 min, Level 2: 20 min (final)
REMINDER_SCHEDULE = [300, 600, 1200]

# ---- Thread State ----
_listener_thread = None
_stop_event = threading.Event()
_is_running = False
_logs = []


def _log(msg):
    """Thread-safe logging."""
    timestamp = time.strftime("%H:%M:%S")
    entry = f"[{timestamp}] {msg}"
    _logs.append(entry)
    # Keep only latest 100 log entries
    if len(_logs) > 100:
        _logs.pop(0)
    print(entry)


def clean_email_body(body):
    """Strips out previous email history from replies."""
    lines = body.splitlines()
    cleaned = []
    for line in lines:
        if line.startswith("On ") and "wrote:" in line:
            break
        if line.startswith("From: ") or line.startswith(">") or line.startswith("-----Original"):
            break
        if line.strip() == "_" * 32:
            break
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def get_unread_emails():
    """Connects to Gmail via IMAP and fetches unread emails."""
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_USER, EMAIL_APP_PASSWORD)
        mail.select("inbox")

        status, messages = mail.search(None, "UNSEEN")
        email_ids = messages[0].split()

        unread_emails = []

        for e_id in email_ids:
            status, msg_data = mail.fetch(e_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    sender = msg.get("From")
                    _, sender_email = parseaddr(sender)

                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode()
                                break
                    else:
                        body = msg.get_payload(decode=True).decode()

                    clean_body = clean_email_body(body)

                    unread_emails.append({
                        "id": e_id,
                        "sender": sender_email,
                        "subject": msg.get("Subject") or "No Subject",
                        "body": clean_body
                    })

        mail.logout()
        return unread_emails

    except Exception as e:
        _log(f"Error reading emails: {e}")
        return []


def send_reply(to_email, subject, reply_text):
    """Sends a reply via Gmail SMTP."""
    try:
        msg = EmailMessage()
        msg.set_content(reply_text)
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"

        msg["Subject"] = subject
        msg["From"] = EMAIL_USER
        msg["To"] = to_email

        with smtplib.SMTP_SSL(SMTP_SERVER, 465) as smtp:
            smtp.login(EMAIL_USER, EMAIL_APP_PASSWORD)
            smtp.send_message(msg)
        _log(f"  -> Reply sent to {to_email}")
    except Exception as e:
        _log(f"  -> Error sending reply: {e}")


def process_email_through_ai(sender_email, body_text):
    """Sends the email text to our FastAPI backend."""
    _log(f"  -> Sending to AI API...")
    payload = {"text": body_text, "thread_id": sender_email}

    try:
        res = requests.post(API_URL, json=payload, timeout=30)
        data = res.json()

        if res.status_code != 200:
            error_detail = data.get('detail', 'Unknown error occurred.')
            error_str = str(error_detail).lower()

            if "503" in str(error_detail) or "unavailable" in error_str:
                # Don't clear reminder - keep tracking them for a retry reminder
                _schedule_retry_reminder(sender_email)
                return "Hello! Our HR Assistant is currently experiencing high traffic. We will follow up with you shortly. No action needed from your side!"
            elif "429" in str(error_detail) or "quota" in error_str:
                _schedule_retry_reminder(sender_email)
                return "Hello! Our HR Assistant is temporarily unavailable due to high demand. We will reach out again soon!"
            else:
                return "Our onboarding service encountered a temporary issue. Please try again later or contact HR directly."

        return data.get("message") or data.get("conversational_reply", "Sorry, I couldn't process that.")
    except Exception as e:
        _log(f"  -> Error connecting to AI API: {e}")
        _schedule_retry_reminder(sender_email)
        return "Our system is temporarily unavailable. We will follow up with you shortly!"


def _schedule_retry_reminder(email_addr):
    """Adds/updates a candidate in reminders for a retry after AI failure."""
    try:
        reminders = _load_reminders()
        reminders[email_addr] = {
            "sent_at": time.time(),
            "reminder_count": 0,
            "type": "retry"
        }
        _save_reminders(reminders)
        _log(f"  -> Scheduled retry reminder for {email_addr}")
    except Exception:
        pass


def _load_reminders():
    """Loads reminders.json safely."""
    if not os.path.exists(REMINDERS_FILE):
        return {}
    try:
        with open(REMINDERS_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _save_reminders(reminders):
    """Saves reminders.json safely."""
    with open(REMINDERS_FILE, "w") as f:
        json.dump(reminders, f, indent=2)


def process_reminders():
    """Multi-stage reminder system. Sends escalating reminders."""
    reminders = _load_reminders()
    if not reminders:
        return

    updated = False
    current_time = time.time()
    completed = []

    for email_addr, data in reminders.items():
        sent_at = data.get("sent_at", current_time)
        reminder_count = data.get("reminder_count", 0)
        elapsed = current_time - sent_at

        # Determine next threshold
        if reminder_count >= len(REMINDER_SCHEDULE):
            # All reminders exhausted - send final notice and remove
            _log(f"[FINAL NOTICE] All reminders exhausted for {email_addr}. Removing from tracker.")
            completed.append(email_addr)
            send_reply(
                email_addr,
                "Final Reminder: Onboarding Pending",
                "Hello,\n\nThis is our final reminder regarding your onboarding at ShanTech. "
                "We still haven't received your details. Please contact HR directly if you "
                "need any assistance.\n\nThank you,\nShanTech HR Team"
            )
            updated = True
            continue

        threshold = REMINDER_SCHEDULE[reminder_count]

        if elapsed >= threshold:
            reminder_num = reminder_count + 1
            total = len(REMINDER_SCHEDULE)

            if data.get("type") == "retry":
                msg = (f"Hello,\n\nWe noticed there was a technical issue earlier when processing your reply. "
                       f"Could you please resend your onboarding details?\n\n"
                       f"We need: Name, Email, Qualification, Date of Birth, and Location.\n\n"
                       f"Thank you,\nShanTech HR Team")
                subject = "Follow-up: Please resend your onboarding details"
            else:
                msg = (f"Hello,\n\nThis is reminder {reminder_num} of {total}. "
                       f"We are still waiting for your onboarding details.\n\n"
                       f"Please reply with: Name, Qualification, Date of Birth, and Location.\n\n"
                       f"Thank you,\nShanTech HR Team")
                subject = f"Reminder {reminder_num}: Action Required for your Onboarding"

            _log(f"[REMINDER {reminder_num}/{total}] Sending to {email_addr}")
            send_reply(email_addr, subject, msg)

            data["reminder_count"] = reminder_num
            # Reset type after first retry reminder
            if data.get("type") == "retry":
                data.pop("type", None)
            updated = True

    for addr in completed:
        del reminders[addr]
        updated = True

    if updated:
        _save_reminders(reminders)


def clear_reminder(email_addr):
    """Removes a candidate from reminders once they successfully onboard."""
    reminders = _load_reminders()
    if email_addr in reminders:
        del reminders[email_addr]
        _save_reminders(reminders)
        _log(f"  -> Cleared reminder for {email_addr}")


def reset_reminder(email_addr):
    """Resets the reminder timer when a candidate replies but still has missing fields.
    This prevents reminders from firing while the candidate is actively conversing."""
    reminders = _load_reminders()
    if email_addr in reminders:
        reminders[email_addr]["sent_at"] = time.time()
        reminders[email_addr]["reminder_count"] = 0
        reminders[email_addr].pop("type", None)
        _save_reminders(reminders)
        _log(f"  -> Reset reminder timer for {email_addr} (candidate replied)")


def _listener_loop():
    """Main loop that runs inside a background thread."""
    global _is_running
    _is_running = True
    _log("Email Listener STARTED")
    _log(f"Monitoring inbox: {EMAIL_USER}")
    _log(f"Checking every 15 seconds")

    while not _stop_event.is_set():
        try:
            process_reminders()
            unread_emails = get_unread_emails()

            for em in unread_emails:
                _log(f"[NEW EMAIL] From: {em['sender']} | Subject: {em['subject']}")

                # Process through AI
                ai_reply = process_email_through_ai(em['sender'], em['body'])

                if "complete" in ai_reply.lower():
                    # Onboarding done - remove from reminders entirely
                    clear_reminder(em['sender'])
                else:
                    # Candidate replied but still has missing fields
                    # Reset the reminder timer so they get another 5 min before next reminder
                    reset_reminder(em['sender'])

                # Reply to sender
                send_reply(em['sender'], em['subject'], ai_reply)

        except Exception as e:
            _log(f"Loop error: {e}")

        # Sleep in small increments so stop_event is responsive
        for _ in range(30):  # 30 * 0.5s = 15 seconds
            if _stop_event.is_set():
                break
            time.sleep(0.5)

    _is_running = False
    _log("Email Listener STOPPED")


def start_listener():
    """Starts the email listener in a background thread."""
    global _listener_thread, _stop_event, _is_running

    if _is_running:
        return {"status": "already_running", "message": "Email listener is already running."}

    _stop_event.clear()
    _listener_thread = threading.Thread(target=_listener_loop, daemon=True)
    _listener_thread.start()
    return {"status": "started", "message": "Email listener started successfully."}


def stop_listener():
    """Gracefully stops the email listener."""
    global _is_running

    if not _is_running:
        return {"status": "already_stopped", "message": "Email listener is not running."}

    _stop_event.set()
    # Wait for thread to finish (max 5 seconds)
    if _listener_thread:
        _listener_thread.join(timeout=5)
    return {"status": "stopped", "message": "Email listener stopped successfully."}


def get_status():
    """Returns the current status and recent logs."""
    return {
        "is_running": _is_running,
        "email_user": EMAIL_USER,
        "logs": _logs[-20:]  # Last 20 log entries
    }
