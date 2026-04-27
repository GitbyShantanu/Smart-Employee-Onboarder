import os
import time
import imaplib
import smtplib
import email
from email.message import EmailMessage
from email.utils import parseaddr
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")
API_URL = "http://127.0.0.1:8000/api/ai-onboarding"

# IMAP & SMTP Settings for Gmail
IMAP_SERVER = "imap.gmail.com"
SMTP_SERVER = "smtp.gmail.com"

def clean_email_body(body):
    """Strips out previous email history from replies."""
    lines = body.splitlines()
    cleaned = []
    for line in lines:
        # Stop processing if we hit common markers for previous emails
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
        # Connect to inbox
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_USER, EMAIL_APP_PASSWORD)
        mail.select("inbox")

        # Search for unread emails
        status, messages = mail.search(None, "UNSEEN")
        email_ids = messages[0].split()

        unread_emails = []

        for e_id in email_ids:
            status, msg_data = mail.fetch(e_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    # Extract Sender Address
                    sender = msg.get("From")
                    _, sender_email = parseaddr(sender)
                    
                    # Extract Body Text
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode()
                                break
                    else:
                        body = msg.get_payload(decode=True).decode()
                        
                    # Clean the body to prevent AI confusion from huge email chains
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
        print(f"Error reading emails: {e}")
        return []

def send_reply(to_email, subject, reply_text):
    """Sends a reply via Gmail SMTP."""
    try:
        msg = EmailMessage()
        msg.set_content(reply_text)
        # Add Re: to the subject if it doesn't have it
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"
            
        msg["Subject"] = subject
        msg["From"] = EMAIL_USER
        msg["To"] = to_email

        with smtplib.SMTP_SSL(SMTP_SERVER, 465) as smtp:
            smtp.login(EMAIL_USER, EMAIL_APP_PASSWORD)
            smtp.send_message(msg)
        print(f"  -> Reply sent successfully to {to_email}!")
    except Exception as e:
        print(f"  -> Error sending email reply: {e}")

def process_email_through_ai(sender_email, body_text):
    """Sends the email text to our FastAPI backend."""
    print(f"  -> Sending to Local AI API...")
    payload = {
        "text": body_text,
        # We use their email address as the thread_id so the AI remembers the conversation history with this specific person!
        "thread_id": sender_email  
    }
    
    try:
        res = requests.post(API_URL, json=payload)
        data = res.json()
        return data.get("message") or data.get("conversational_reply", "Sorry, I couldn't process that.")
    except Exception as e:
        print(f"  -> Error connecting to local API: {e}")
        return "System Error: Ensure the FastAPI server is running on port 8000."

def main():
    print("="*50)
    print(f"🚀 Email Listener Service Started")
    print(f"📬 Monitoring Inbox: {EMAIL_USER}")
    print("="*50)
    print("Waiting for new unread emails (checking every 10 seconds)...\n")
    
    while True:
        unread_emails = get_unread_emails()
        
        for em in unread_emails:
            print(f"\n[NEW EMAIL DETECTED]")
            print(f"From: {em['sender']}")
            print(f"Subject: {em['subject']}")
            
            # 1. Send to AI
            ai_reply = process_email_through_ai(em['sender'], em['body'])
            
            # 2. Reply to Sender
            send_reply(em['sender'], em['subject'], ai_reply)
            
        # Wait 10 seconds before checking again
        time.sleep(10)

if __name__ == "__main__":
    main()
