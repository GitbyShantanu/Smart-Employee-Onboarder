import os
import json
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ValidationError
from typing import Optional, List
from sqlalchemy.orm import Session
from google import genai
from google.genai import types
from dotenv import load_dotenv
import smtplib
from email.message import EmailMessage
import time

# Import database session and schema
from backend.models import Employee
from backend.schema import EmployeeCreate
from backend.routers.employee import get_db

load_dotenv()
client = genai.Client()

router = APIRouter(
    prefix="/api",
    tags=["AI Agent Webhook"]
)

# File-based conversation memory (survives server restarts)
THREAD_MEMORY_FILE = "thread_memory.json"
THREAD_EXPIRY_SECONDS = 86400  # 24 hours


def _load_threads():
    """Load conversation threads from disk. Auto-cleans threads older than 24 hours."""
    if not os.path.exists(THREAD_MEMORY_FILE):
        return {}
    try:
        with open(THREAD_MEMORY_FILE, "r") as f:
            threads = json.load(f)
        # Auto-cleanup stale threads
        now = time.time()
        stale = [tid for tid, data in threads.items() 
                 if isinstance(data, dict) and now - data.get("updated_at", 0) > THREAD_EXPIRY_SECONDS]
        for tid in stale:
            del threads[tid]
        if stale:
            _save_threads(threads)
        return threads
    except (json.JSONDecodeError, IOError):
        return {}


def _save_threads(threads):
    """Save conversation threads to disk."""
    with open(THREAD_MEMORY_FILE, "w") as f:
        json.dump(threads, f, indent=2)


class AgentRequest(BaseModel):
    text: str
    thread_id: Optional[str] = None


class InitiateRequest(BaseModel):
    emails: List[str]


SYSTEM_PROMPT = """You are an intelligent HR Onboarding Assistant for ShanTech.
Your job is to read emails from new hires and extract their onboarding information.

We need exactly these fields from the candidate:
1. name (String: The full name of the candidate)
2. email (String: The email address of the candidate)
3. qualification (String: MUST be strictly mapped to one of: "B.Tech", "M.Tech", "B.E.", "M.E.", "BCA", "MCA", "B.Sc", "M.Sc", "MCS", "Ph.D", "MBA", "BBA", "B.Com", "M.Com", "B.A.", "M.A.", "Diploma", "High School", "Other (Non-Technical)". If they provide anything else, DO NOT extract it.)
4. date_of_birth (String: Date of birth. You MUST strictly normalize and format this as YYYY-MM-DD. The date MUST be in the past. If they provide a future date, DO NOT extract it.)
5. location (String: MUST be one of the allowed Indian cities/districts (e.g. Mumbai, Pune, Nagpur, Nashik, Bangalore, Delhi, Hyderabad, Chennai, Kolkata, Ahmedabad, Jaipur, etc., including all Maharashtra districts). If they provide a city that is valid in India but you are unsure, try to map it to the closest major hub. If it is vague, DO NOT extract it.)

INSTRUCTIONS:
1. Extract the above fields from the conversation. ALWAYS extract any provided fields even if the candidate also asked a question.
2. If ANY field is missing (especially the email address if they use the text parser), set "all_required_present" to false, and in "conversational_reply", politely ask the candidate to provide ONLY the missing fields. If they provided an invalid location or qualification, politely tell them what the allowed options are. You MUST NOT set all_required_present to true unless ALL 5 fields are present.
3. **QUERY HANDLING:** If the candidate asks ANY question (e.g., joining date, salary, documents, timings, etc.), you MUST politely and professionally answer it in the "conversational_reply". In the SAME reply, acknowledge any data they just provided, and then ask for any missing fields. (For example: "Your joining date will be the 1st of next month. I have noted your DOB, but could you please provide your Qualification?"). If you are unsure about their question, say "I will have HR reach out to answer that, but in the meantime..."
4. If ALL required fields are present, set "all_required_present" to true, and in "conversational_reply" say: "Thank you! Your onboarding is complete. Let me know if you have any questions."

RETURN EXACTLY THIS JSON FORMAT:
{
    "all_required_present": true,
    "missing_fields": [],
    "extracted_data": {
        "name": "Jane Doe",
        "email": "jane@example.com",
        "qualification": "B.Tech Computer Science",
        "date_of_birth": "1995-08-15",
        "location": "Pune"
    },
    "conversational_reply": "Polite reply asking for missing details or answering their queries."
}
"""

@router.post("/ai-onboarding")
def process_hr_email(request: AgentRequest, db: Session = Depends(get_db)):
    thread_id = request.thread_id
    if not thread_id:
        thread_id = str(uuid.uuid4())
    
    # Load threads from disk
    threads = _load_threads()
    if thread_id not in threads:
        threads[thread_id] = {"messages": [], "updated_at": time.time(), "onboarded": False}
    
    threads[thread_id]["messages"].append({"role": "user", "content": request.text})
    threads[thread_id]["updated_at"] = time.time()
    
    # Save immediately so even if we crash, user's message is preserved
    _save_threads(threads)
    
    is_onboarded = threads[thread_id].get("onboarded", False)
    history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in threads[thread_id]["messages"]])
    
    if is_onboarded:
        prompt_text = "You are ShanTech HR. This candidate is already successfully onboarded. Answer their questions politely. DO NOT ask for any onboarding details. Return EXACTLY this JSON: {\"conversational_reply\": \"your answer\"}"
        full_prompt = f"{prompt_text}\n\nConversation History:\n{history_text}\n\nRespond in JSON."
    else:
        full_prompt = f"{SYSTEM_PROMPT}\n\nThe candidate's email address is {thread_id}.\n\nConversation History:\n{history_text}\n\nExtract the data based on the instructions."
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=full_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1
            )
        )
        ai_result = json.loads(response.text or "")
        
        threads[thread_id]["messages"].append({"role": "assistant", "content": ai_result.get("conversational_reply", "")})
        _save_threads(threads)
        
        if is_onboarded:
            return {
                "status": "success",
                "message": ai_result.get("conversational_reply", "Thank you for your message."),
                "thread_id": thread_id
            }
        
        if not ai_result.get("all_required_present"):
            return {
                "status": "missing_info",
                "message": ai_result.get("conversational_reply"),
                "missing_fields": ai_result.get("missing_fields", []),
                "thread_id": thread_id
            }
            
        extracted = ai_result.get("extracted_data", {})
        
        # for manual validation because AI can extract wrong format of data which will lead to error in saving it to the database so we validate here
        try:
            new_emp = EmployeeCreate(**extracted)
        except ValidationError as ve:
            missing = [str(error["loc"][0]) for error in ve.errors()]
            return {
                "status": "missing_info",
                "message": f"I still need your {', '.join(missing)}. Could you please provide them?",
                "missing_fields": missing,
                "thread_id": thread_id
            }
        
        db_emp = Employee(**new_emp.model_dump())
        db.add(db_emp)
        db.commit()
        db.refresh(db_emp)
        
        # Mark as onboarded instead of deleting!
        threads[thread_id]["onboarded"] = True
        _save_threads(threads)
        
        return {
            "status": "success",
            "message": "Employee successfully onboarded via AI and saved to database.",
            "employee_id": db_emp.id,
            "thread_id": thread_id,
            "extracted_data": new_emp.model_dump()
        }
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="AI returned invalid JSON structure.")
    except Exception as e:
        print(f"Error processing request: {e}")
        if "429" in str(e) or "quota" in str(e).lower():
            raise HTTPException(status_code=429, detail="AI API Quota Exceeded. Please try again later.")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/initiate")
async def initiate_onboarding(req: InitiateRequest):
    """API Endpoint to send the first welcoming onboarding email to a new hire."""
    EMAIL_USER = os.getenv('EMAIL_USER', '')
    EMAIL_APP_PASSWORD = os.getenv('EMAIL_APP_PASSWORD', '')
    
    body = """Hello!

Welcome to ShanTech! We are excited to have you join the team.
To begin your automated onboarding process, please reply to this email with the following details:

1. Your Full Name
2. Your Qualification (Highest Degree)
3. Your Date of Birth
4. Your Current Location (City)

If you have any questions about joining formalities or required documents, feel free to ask!

Best regards,
ShanTech HR Team"""

    try:
        reminders = {}
        reminders_file = "reminders.json"
        if os.path.exists(reminders_file):
            with open(reminders_file, "r") as f:
                try:
                    reminders = json.load(f)
                except json.JSONDecodeError:
                    reminders = {}

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_USER, EMAIL_APP_PASSWORD)
            
            for target_email in req.emails:
                msg = EmailMessage()
                msg['Subject'] = "Welcome to ShanTech! Complete your onboarding"
                msg['From'] = EMAIL_USER
                msg['To'] = target_email
                msg.set_content(body)
                
                smtp.send_message(msg)
                reminders[target_email] = {"sent_at": time.time(), "reminder_count": 0}
                
        with open(reminders_file, "w") as f:
            json.dump(reminders, f)
            
        return {"status": "success", "message": f"Initial onboarding email sent successfully to {len(req.emails)} candidate(s)!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
