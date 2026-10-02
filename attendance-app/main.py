import os
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from database import db, init_db
from auth import verify_password, get_user, hash_password

IST = timezone(timedelta(hours=5, minutes=30))
DATA_DIR = os.environ.get("DATA_DIR", ".")
SELFIE_DIR = os.path.join(DATA_DIR, "selfies")

app = FastAPI()
app.add_middleware(SessionMiddleware,
                   secret_key=os.environ.get("SECRET_KEY", "change-me-before-deploying"),
                   max_age=60 * 60 * 12)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
init_db()

with db() as c:
    if not c.execute("SELECT 1 FROM employees WHERE username='surya'").fetchone():
        c.execute("INSERT INTO employees (emp_code,name,username,password_hash,role) VALUES (?,?,?,?,?)",
                  ("EMP004", "Surya", "surya", hash_password("pass"), "employee"))
    if not c.execute("SELECT 1 FROM employees WHERE username='admin'").fetchone():
        c.execute("INSERT INTO employees (emp_code,name,username,password_hash,role) VALUES (?,?,?,?,?)",
                  ("ADM001", "Admin", "admin", hash_password("admin123"), "admin"))


def now_ist():
    return datetime.now(IST)


def need_user(request, admin=False):
    user = get_user(request)
    if not user:
        raise HTTPException(401, "Please log in")
    if admin and user["role"] != "admin":
        raise HTTPException(403, "Admins only")
    return user


# ---------- pages ----------
@app.get("/")
def home(request: Request):
    user = get_user(request)
    if not user:
        return RedirectResponse("/login")
    return RedirectResponse("/admin" if user["role"] == "admin" else "/employee")


@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"error": None})


@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    with db() as c:
        user = c.execute("SELECT * FROM employees WHERE username=?", (username.strip(),)).fetchone()
    if not user or not verify_password(password, user["password_hash"]):
        return templates.TemplateResponse(request, "login.html",
                                          {"error": "Wrong username or password."}, status_code=401)
    request.session.clear()
    request.session["user_id"] = user["id"]
    return RedirectResponse("/", status_code=303)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login")


@app.get("/employee")
def employee_page(request: Request):
    user = get_user(request)
    if not user:
        return RedirectResponse("/login")
    if user["role"] == "admin":
        return RedirectResponse("/admin")
    return templates.TemplateResponse(request, "employee.html", {"user": user})


@app.get("/admin")
def admin_page(request: Request):
    user = get_user(request)
    if not user:
        return RedirectResponse("/login")
    if user["role"] != "admin":
        return RedirectResponse("/employee")
    return templates.TemplateResponse(request, "admin.html", {"user": user})


# ---------- attendance API ----------
def today_row(emp_id):
    with db() as c:
        return c.execute("SELECT * FROM attendance WHERE employee_id=? AND date=?",
                         (emp_id, now_ist().strftime("%Y-%m-%d"))).fetchone()


@app.get("/api/status")
def status(request: Request):
    user = need_user(request)
    row = today_row(user["id"])
    state = "not_in"
    if row and row["check_out"]:
        state = "out"
    elif row and row["check_in"]:
        state = "in"
    return {"state": state,
            "check_in": row["check_in"] if row else None,
            "check_out": row["check_out"] if row else None,
            "today": now_ist().strftime("%Y-%m-%d")}


async def save_attendance(request, kind, selfie, lat, lon):
    user = need_user(request)
    row = today_row(user["id"])
    if kind == "in" and row:
        raise HTTPException(400, "You have already checked in today.")
    if kind == "out" and (not row or not row["check_in"]):
        raise HTTPException(400, "Check in first.")
    if kind == "out" and row["check_out"]:
        raise HTTPException(400, "You have already checked out today.")

    data = await selfie.read()
    if not data or len(data) > 5_000_000:
        raise HTTPException(400, "Selfie missing or too large.")

    t = now_ist()  # server time, never from the browser
    folder = os.path.join(SELFIE_DIR, user["emp_code"])
    os.makedirs(folder, exist_ok=True)
    fname = f"{t:%Y-%m-%d}-{kind}.jpg"
    with open(os.path.join(folder, fname), "wb") as f:
        f.write(data)
    path = f"{user['emp_code']}/{fname}"
    stamp = t.strftime("%H:%M:%S")

    with db() as c:
        if kind == "in":
            c.execute("INSERT INTO attendance (employee_id,date,check_in,in_lat,in_lon,in_selfie) "
                      "VALUES (?,?,?,?,?,?)", (user["id"], t.strftime("%Y-%m-%d"), stamp, lat, lon, path))
        else:
            c.execute("UPDATE attendance SET check_out=?,out_lat=?,out_lon=?,out_selfie=? WHERE id=?",
                      (stamp, lat, lon, path, row["id"]))
    return {"ok": True, "time": stamp, "state": "in" if kind == "in" else "out"}


@app.post("/api/check-in")
async def check_in(request: Request, lat: float = Form(...), lon: float = Form(...),
                   selfie: UploadFile = File(...)):
    return await save_attendance(request, "in", selfie, lat, lon)


@app.post("/api/check-out")
async def check_out(request: Request, lat: float = Form(...), lon: float = Form(...),
                    selfie: UploadFile = File(...)):
    return await save_attendance(request, "out", selfie, lat, lon)


@app.get("/api/attendance")
def attendance(request: Request, date: str | None = None):
    need_user(request, admin=True)
    date = date or now_ist().strftime("%Y-%m-%d")
    with db() as c:
        rows = c.execute("""
            SELECT e.name, e.emp_code, a.check_in, a.check_out, a.in_lat, a.in_lon,
                   a.out_lat, a.out_lon, a.in_selfie, a.out_selfie
            FROM employees e
            LEFT JOIN attendance a ON a.employee_id=e.id AND a.date=?
            WHERE e.role='employee' ORDER BY e.name""", (date,)).fetchall()
    return {"date": date, "rows": [dict(r) for r in rows]}


@app.get("/selfie/{emp_code}/{filename}")
def get_selfie(request: Request, emp_code: str, filename: str):
    user = need_user(request)
    if user["role"] != "admin" and user["emp_code"] != emp_code:
        raise HTTPException(403, "Not allowed")
    if os.path.basename(emp_code) != emp_code or os.path.basename(filename) != filename:
        raise HTTPException(400, "Bad path")
    path = os.path.join(SELFIE_DIR, emp_code, filename)
    if not os.path.isfile(path):
        raise HTTPException(404)
    return FileResponse(path, media_type="image/jpeg")
