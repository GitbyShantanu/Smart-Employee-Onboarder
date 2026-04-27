import os
import json
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy.orm import Session
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Import database session and schema
from backend.models import Employee
from backend.schema import EmployeeCreate
from backend.routers.employee import get_db

# Load environment variables from .env file
load_dotenv()

# Configure Gemini Client
# It automatically picks up GEMINI_API_KEY from environment variables
client = genai.Client()

router = APIRouter(
    prefix="/api",
    tags=["AI Agent Webhook"]
)

# ---------------------------------------------------------
# In-memory memory dictionary to store conversation threads
# For production, replace this with Redis or a database table!
# ---------------------------------------------------------
thread_memory = {}

# Pydantic schema for the incoming POST request
class AgentRequest(BaseModel):
    text: str
    thread_id: Optional[str] = None


# The System Prompt guiding the AI
SYSTEM_PROMPT = """
You are an HR Onboarding Assistant. Your job is to extract employee information from HR emails.
The following fields are STRICTLY REQUIRED:
- first_name (str)
- middle_name (str)
- last_name (str)
- gender (str)
- date_of_birth (format: YYYY-MM-DD)
- mobile_number (int)
- email (str)
- marrital_status (str)
- blood_group (str)

The following field is OPTIONAL:
- alternate_mobile_number (int)

If ANY required fields are missing from the conversation history, you must:
1. Set 'all_required_present' to false.
2. List the missing fields in 'missing_fields'.
3. Provide a 'conversational_reply' asking the user for those specific missing fields in a friendly tone.
4. Set 'extracted_data' to an empty dictionary {}.

If ALL required fields are present, you must:
1. Set 'all_required_present' to true.
2. Set 'missing_fields' to an empty list [].
3. Provide a 'conversational_reply' confirming all information is collected.
4. Set 'extracted_data' containing all the required fields (and the optional field if provided).

Respond strictly with valid JSON. Do NOT include markdown blocks like ```json. Your response must be parseable by json.loads().
Schema Structure:
{
  "all_required_present": boolean,
  "missing_fields": ["field1", "field2"],
  "conversational_reply": "string",
  "extracted_data": {
     "first_name": "string",
     ...
  }
}
"""

@router.post("/ai-onboarding")
def process_hr_email(request: AgentRequest, db: Session = Depends(get_db)):
    # 1. Manage the Thread ID
    thread_id = request.thread_id
    if not thread_id:
        # Generate a new unique ID if this is a new conversation
        thread_id = str(uuid.uuid4())
        thread_memory[thread_id] = []
    
    # 2. Ensure thread exists in memory
    if thread_id not in thread_memory:
        thread_memory[thread_id] = []
    
    # 3. Add the incoming email/message to the conversation history
    thread_memory[thread_id].append({"role": "user", "content": request.text})
    
    # 4. Prepare the full prompt for the AI
    history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in thread_memory[thread_id]])
    full_prompt = f"{SYSTEM_PROMPT}\n\nConversation History:\n{history_text}\n\nExtract the data based on the instructions."
    
    try:
        # 5. Call the real Gemini API
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=full_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1
            )
        )
        response_text = response.text
            
        # 6. Parse the JSON response
        ai_result = json.loads(response_text)
        
        # Add AI's reply to memory so it remembers what it asked
        thread_memory[thread_id].append({"role": "assistant", "content": ai_result.get("conversational_reply", "")})
        
        # 7. Logic Branch: If Information is Missing
        if not ai_result.get("all_required_present"):
            return {
                "status": "missing_info",
                "message": ai_result.get("conversational_reply"),
                "missing_fields": ai_result.get("missing_fields", []),
                "thread_id": thread_id
            }
            
        # 8. Logic Branch: All Information is Present
        extracted = ai_result.get("extracted_data", {})
        
        # Handle the optional field before validation
        if "alternate_mobile_number" not in extracted or not extracted["alternate_mobile_number"]:
             extracted["alternate_mobile_number"] = None
             
        # Validate data with our Pydantic schema
        new_emp = EmployeeCreate(**extracted)
        
        # Save to Database using SQLAlchemy
        db_emp = Employee(**new_emp.model_dump())
        db.add(db_emp)
        db.commit()
        db.refresh(db_emp)
        
        # Clear the memory since the onboarding is complete
        del thread_memory[thread_id]
        
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
        # If it's a quota error from Google, return a clean message for the frontend
        if "429" in str(e) or "quota" in str(e).lower():
            raise HTTPException(status_code=429, detail="AI API Quota Exceeded. Please try again later.")
        raise HTTPException(status_code=500, detail=str(e))
