"""Add an employee or admin.
Usage:
  python add_user.py EMP001 "Rahul" rahul01 password123
  python add_user.py ADM001 "Admin" admin admin123 admin
"""
import sys
from database import db, init_db
from auth import hash_password

if len(sys.argv) < 5:
    sys.exit(__doc__)
init_db()
code, name, username, pw = sys.argv[1:5]
role = sys.argv[5] if len(sys.argv) > 5 else "employee"
with db() as c:
    c.execute(
        "INSERT INTO employees (emp_code,name,username,password_hash,role) VALUES (?,?,?,?,?)",
        (code, name, username, hash_password(pw), role),
    )
print(f"Added {role}: {name} ({username})")
