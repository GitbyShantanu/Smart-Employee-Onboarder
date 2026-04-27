from backend.database import Base
from sqlalchemy import Column, Integer, String, Date

class Employee(Base):
    __tablename__ = 'employee'

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    middle_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    gender = Column(String, nullable=False)
    date_of_birth = Column(Date, nullable=False)
    mobile_number = Column(Integer, nullable=False) 
    alternate_mobile_number = Column(Integer, nullable=True)
    email = Column(String, nullable=False, unique=True)
    marrital_status = Column(String, nullable=False)
    blood_group = Column(String, nullable=False)



