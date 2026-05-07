from backend.database import Base
from sqlalchemy import Column, Integer, String, Date

class Employee(Base):
    __tablename__ = 'employee'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    qualification = Column(String, nullable=False)
    date_of_birth = Column(Date, nullable=False) 
    location = Column(String, nullable=False)
