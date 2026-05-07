from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, Literal
from datetime import date

ValidLocations = Literal[
    "Mumbai", "Pune", "Nagpur", "Nashik", "Thane", "Aurangabad", "Solapur", "Amravati", "Kolhapur", "Navi Mumbai", 
    "Sangli", "Jalgaon", "Akola", "Latur", "Dhule", "Ahmednagar", "Chandrapur", "Parbhani", "Jalna", "Beed", 
    "Nanded", "Wardha", "Osmanabad", "Nandurbar", "Satara", "Sindhudurg", "Ratnagiri", "Gondia", "Bhandara", 
    "Gadchiroli", "Washim", "Yavatmal", "Hingoli", "Buldhana", "Palghar", "Raigad", "Bangalore", "Delhi", 
    "New Delhi", "Hyderabad", "Chennai", "Kolkata", "Ahmedabad", "Surat", "Jaipur", "Lucknow", "Kanpur", 
    "Indore", "Bhopal", "Patna", "Vadodara", "Ludhiana", "Agra", "Varanasi", "Noida", "Gurgaon", "Kochi", 
    "Trivandrum", "Chandigarh"
]


ValidQualifications = Literal[
    "B.Tech", "M.Tech", "B.E.", "M.E.", "BCA", "MCA", "B.Sc", "M.Sc", "MCS", "Ph.D", 
    "MBA", "BBA", "B.Com", "M.Com", "B.A.", "M.A.", "Diploma", "High School", "Other (Non-Technical)"
]


class EmployeeCreate(BaseModel):
    name : str 
    email : EmailStr
    qualification : ValidQualifications 
    date_of_birth : date
    location : ValidLocations 

    @field_validator("date_of_birth")
    @classmethod
    def dob_must_be_past(cls, v):
        if v >= date.today():
            raise ValueError("Date of birth must be a past date")
        return v


class EmployeeResponse(BaseModel):
    id : int 
    name : str 
    email : EmailStr
    qualification : str 
    date_of_birth : date
    location : str 

    class Config:
        from_attributes = True


class EmployeeUpdate(BaseModel):
    name : Optional[str] = None 
    email : Optional[EmailStr] = None
    qualification : Optional[ValidQualifications] = None 
    date_of_birth : Optional[date] = None
    location : Optional[ValidLocations] = None 
