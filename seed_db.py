from backend.database import engine, sessionLocal
from backend.models import Employee
from sqlalchemy import text
from datetime import date

# 1. Verify connection
with engine.connect() as conn:
    r = conn.execute(text("SELECT COUNT(*) FROM employee"))
    print("Current rows in Neon before seeding:", r.scalar())

# 2. Add more seed records
db = sessionLocal()
seed_data = [
    # Original 5 (to ensure they are present)
    Employee(name="Shantanu Deshmukh", email="shantanu@shantech.dev", qualification="B.Tech", date_of_birth=date(2002, 5, 5), location="Nagpur"),
    Employee(name="Priya Sharma", email="priya.sharma@example.com", qualification="MCA", date_of_birth=date(1998, 3, 14), location="Mumbai"),
    Employee(name="Rahul Verma", email="rahul.verma@example.com", qualification="M.Tech", date_of_birth=date(1996, 11, 22), location="Pune"),
    Employee(name="Anjali Patil", email="anjali.patil@example.com", qualification="MBA", date_of_birth=date(1999, 7, 8), location="Bangalore"),
    Employee(name="Vikram Singh", email="vikram.singh@example.com", qualification="B.E.", date_of_birth=date(1997, 1, 30), location="Delhi"),
    
    # 15 New high-quality corporate profiles
    Employee(name="Karan Malhotra", email="karan.malhotra@example.com", qualification="B.E. Computer Science", date_of_birth=date(1997, 8, 12), location="Delhi"),
    Employee(name="Neha Joshi", email="neha.joshi@example.com", qualification="B.Tech IT", date_of_birth=date(1999, 12, 4), location="Nagpur"),
    Employee(name="Rohan Saxena", email="rohan.saxena@example.com", qualification="MCA Software", date_of_birth=date(1998, 4, 18), location="Bangalore"),
    Employee(name="Simran Kaur", email="simran.kaur@example.com", qualification="MBA Finance", date_of_birth=date(1996, 10, 29), location="Mumbai"),
    Employee(name="Aditya Sen", email="aditya.sen@example.com", qualification="M.Tech AI", date_of_birth=date(1995, 3, 23), location="Pune"),
    Employee(name="Tanvi Hegde", email="tanvi.hegde@example.com", qualification="MS Data Science", date_of_birth=date(1997, 6, 15), location="Hyderabad"),
    Employee(name="Devendra Dixit", email="devendra.dixit@example.com", qualification="B.Sc Software Eng", date_of_birth=date(1998, 9, 21), location="Noida"),
    Employee(name="Ishaan Roy", email="ishaan.roy@example.com", qualification="MCA Software Systems", date_of_birth=date(1996, 7, 9), location="Gurgaon"),
    Employee(name="Meera Nair", email="meera.nair@example.com", qualification="B.Tech Electrical", date_of_birth=date(1999, 11, 14), location="Chennai"),
    Employee(name="Kabir Mehta", email="kabir.mehta@example.com", qualification="MBA Marketing", date_of_birth=date(1995, 2, 8), location="Ahmedabad"),
    Employee(name="Riya Kapoor", email="riya.kapoor@example.com", qualification="B.E. Electronics", date_of_birth=date(1998, 5, 27), location="Nagpur"),
    Employee(name="Kunal Shah", email="kunal.shah@example.com", qualification="MS Computer Engineering", date_of_birth=date(1996, 1, 11), location="Mumbai"),
    Employee(name="Divya Teja", email="divya.teja@example.com", qualification="MCA Systems", date_of_birth=date(1997, 10, 3), location="Hyderabad"),
    Employee(name="Aakash Mishra", email="aakash.mishra@example.com", qualification="B.Tech CS", date_of_birth=date(1999, 1, 28), location="Delhi"),
    Employee(name="Shreya Ghoshal", email="shreya.ghoshal@example.com", qualification="MBA HR", date_of_birth=date(1996, 5, 12), location="Kolkata"),
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
db.close()
