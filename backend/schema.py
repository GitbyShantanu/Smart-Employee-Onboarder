from pydantic import BaseModel, EmailStr, Field
from datetime import date
from typing import Optional

class EmployeeCreate(BaseModel):
    first_name : str 
    middle_name : str 
    last_name : str 
    gender : str 
    date_of_birth : date
    mobile_number : int
    alternate_mobile_number : Optional[int] = None
    email : EmailStr
    marrital_status : str 
    blood_group : str 


class EmployeeResponse(BaseModel):
    id : int 
    first_name : str 
    middle_name : Optional[str] = None
    last_name : str 
    gender : str 
    date_of_birth : date
    mobile_number : int
    alternate_mobile_number : Optional[int] = None
    email : EmailStr
    marrital_status : str 
    blood_group : str 

    class config :
        from_attributes : True


class EmployeeUpdate(BaseModel):
    first_name : Optional[str] = None 
    middle_name : Optional[str] = None 
    last_name : Optional[str] = None
    gender : Optional[str] = None
    date_of_birth : Optional[date] = None
    mobile_number : Optional[int] = None 
    alternate_mobile_number : Optional[int] = None
    email : Optional[EmailStr] = None
    marrital_status : Optional[str] = None 
    blood_group : Optional[str] = None

