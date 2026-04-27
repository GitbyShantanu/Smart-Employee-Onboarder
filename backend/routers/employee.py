from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import sessionLocal
from backend.schema import EmployeeCreate, EmployeeResponse, EmployeeUpdate
from backend.models import Employee

router = APIRouter(
    prefix="/employees",
    tags=["Employees"]
)


# DB Session
def get_db():
    db = sessionLocal()
    try:
        yield db
    finally:
        db.close() 


@router.post("", response_model=EmployeeResponse)
def create_employee(
    new_emp : EmployeeCreate,
    db : Session = Depends(get_db)
):
    db_emp = Employee(**new_emp.model_dump())
    db.add(db_emp)
    db.commit()
    db.refresh(db_emp)
    return db_emp 


@router.get("", response_model=list[EmployeeResponse])
def get_all_employees(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    db_all_emp = db.query(Employee).order_by(Employee.id).offset(skip).limit(limit).all()
    return db_all_emp


@router.get("/{eid}", response_model=EmployeeResponse)
def get_employee_by_id(eid : int, db: Session = Depends(get_db)):
    db_emp = db.query(Employee).filter(Employee.id == eid).first() 
    if not db_emp:
        raise HTTPException(status_code=404, detail=f'Employee with id {eid} not found')
    return db_emp


@router.delete("/{eid}", response_model=EmployeeResponse)
def delete_employee_by_id(eid : int, db: Session = Depends(get_db)):
    db_emp = db.query(Employee).filter(Employee.id == eid).first() 
    if not db_emp:
        raise HTTPException(status_code=404, detail=f'Employee with id {eid} not found')
    
    db.delete(db_emp)
    db.commit()
    return db_emp


@router.put("/{eid}", response_model=EmployeeResponse)
def update_employee_by_id(
    eid : int,
    updated_emp : EmployeeUpdate,
    db : Session = Depends(get_db)    
):
    db_emp = db.query(Employee).filter(Employee.id == eid).first() 
    if not db_emp:
        raise HTTPException(status_code=404, detail=f'Employee with id {eid} not found')
    
    update_dict = updated_emp.model_dump(exclude_unset=True)
    for k, v in update_dict.items():
        setattr(db_emp, k, v)

    db.commit()
    return db_emp


@router.patch("/{eid}", response_model=EmployeeResponse)
def partial_update_employee_by_id(
    eid : int,
    updated_emp : EmployeeUpdate,
    db : Session = Depends(get_db)    
):
    db_emp = db.query(Employee).filter(Employee.id == eid).first() 
    if not db_emp:
        raise HTTPException(status_code=404, detail=f'Employee with id {eid} not found')

    update_dict = updated_emp.model_dump(exclude_unset=True)
    for k, v in update_dict.items():
        setattr(db_emp, k, v)

    db.commit()
    return db_emp