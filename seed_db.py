from backend.database import engine, sessionLocal
from backend.models import Employee, Base
from sqlalchemy import text
from datetime import date

# 1. Verify table exists
with engine.connect() as conn:
    r = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
    print("Tables in Neon:", [row[0] for row in r])
    r2 = conn.execute(text("SELECT COUNT(*) FROM employee"))
    print("Current rows:", r2.scalar())

# 2. Seed data
db = sessionLocal()
seed_data = [
    Employee(name="Shantanu Deshmukh", email="shantanu@shantech.dev", qualification="B.Tech", date_of_birth=date(2002, 5, 5), location="Nagpur"),
    Employee(name="Priya Sharma", email="priya.sharma@example.com", qualification="MCA", date_of_birth=date(1998, 3, 14), location="Mumbai"),
    Employee(name="Rahul Verma", email="rahul.verma@example.com", qualification="M.Tech", date_of_birth=date(1996, 11, 22), location="Pune"),
    Employee(name="Anjali Patil", email="anjali.patil@example.com", qualification="MBA", date_of_birth=date(1999, 7, 8), location="Bangalore"),
    Employee(name="Vikram Singh", email="vikram.singh@example.com", qualification="B.E.", date_of_birth=date(1997, 1, 30), location="Delhi"),
]

for emp in seed_data:
    existing = db.query(Employee).filter(Employee.email == emp.email).first()
    if not existing:
        db.add(emp)
        print(f"  Added: {emp.name}")
    else:
        print(f"  Skipped (exists): {emp.name}")

db.commit()

# 3. Verify
count = db.query(Employee).count()
print(f"\nTotal employees in Neon: {count}")
all_emps = db.query(Employee).all()
for e in all_emps:
    print(f"  [{e.id}] {e.name} | {e.email} | {e.qualification} | {e.location}")
db.close()
