import os
import math
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

BRANCH_LOCATIONS = {
    "Deloitte - Prestige trade tower": (12.986056670745134, 77.58775594422619),
    "Deloitte - Ecospace": (12.925951111015136, 77.6819903307608),
    "Lowes": (13.04448815778972, 77.61869989999472),
    "IBM - FTP": (12.98372007285447, 77.73118068461707),
}
MAX_ALLOWED_DISTANCE_METERS = 100.0


def calculate_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in meters between two coordinates using the Haversine formula."""
    R = 6371000.0  # Earth's mean radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


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

    branch_val = row["branch"] if (row and "branch" in row.keys()) else None
    if not branch_val and row and row["in_lat"] and row["in_lon"]:
        closest_b = None
        closest_d = float("inf")
        for b_name, b_pos in BRANCH_LOCATIONS.items():
            d = calculate_distance_meters(row["in_lat"], row["in_lon"], b_pos[0], b_pos[1])
            if d < closest_d:
                closest_d = d
                closest_b = b_name
        branch_val = closest_b

    return {"state": state,
            "check_in": row["check_in"] if row else None,
            "check_out": row["check_out"] if row else None,
            "branch": branch_val,
            "today": now_ist().strftime("%Y-%m-%d")}


async def save_attendance(request, kind, selfie, lat, lon, branch=None):
    user = need_user(request)
    row = today_row(user["id"])
    if kind == "in" and row:
        raise HTTPException(400, "You have already checked in today.")
    if kind == "out" and (not row or not row["check_in"]):
        raise HTTPException(400, "Check in first.")
    if kind == "out" and row["check_out"]:
        raise HTTPException(400, "You have already checked out today.")

    target_branch = branch.strip() if branch else None
    if kind == "out" and row and "branch" in row.keys() and row["branch"]:
        target_branch = row["branch"]

    if not target_branch:
        raise HTTPException(400, "Branch is mandatory. Please select your branch.")

    if target_branch not in BRANCH_LOCATIONS:
        raise HTTPException(400, f"Unknown branch: '{target_branch}'.")

    if lat is None or lon is None or (lat == 0 and lon == 0):
        raise HTTPException(400, "Location access is required. Please enable GPS permissions on your device.")

    branch_lat, branch_lon = BRANCH_LOCATIONS[target_branch]
    dist = calculate_distance_meters(lat, lon, branch_lat, branch_lon)

    if dist > MAX_ALLOWED_DISTANCE_METERS:
        raise HTTPException(
            400,
            f"Location mismatch: You are {int(round(dist))}m away from '{target_branch}'. "
            f"Attendance can only be marked within 100m of the office."
        )

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
            c.execute("INSERT INTO attendance (employee_id,date,branch,check_in,in_lat,in_lon,in_selfie) "
                      "VALUES (?,?,?,?,?,?,?)", (user["id"], t.strftime("%Y-%m-%d"), target_branch, stamp, lat, lon, path))
        else:
            c.execute("UPDATE attendance SET check_out=?,out_lat=?,out_lon=?,out_selfie=? WHERE id=?",
                      (stamp, lat, lon, path, row["id"]))
    return {"ok": True, "time": stamp, "state": "in" if kind == "in" else "out"}


@app.post("/api/check-in")
async def check_in(request: Request, lat: float = Form(...), lon: float = Form(...),
                   selfie: UploadFile = File(...), branch: str = Form(...)):
    return await save_attendance(request, "in", selfie, lat, lon, branch)


@app.post("/api/check-out")
async def check_out(request: Request, lat: float = Form(...), lon: float = Form(...),
                    selfie: UploadFile = File(...), branch: str | None = Form(None)):
    return await save_attendance(request, "out", selfie, lat, lon, branch)


@app.get("/api/attendance")
def attendance(request: Request, date: str | None = None, branch: str | None = None):
    need_user(request, admin=True)
    date = date or now_ist().strftime("%Y-%m-%d")
    with db() as c:
        query = """
            SELECT e.name, e.emp_code, a.check_in, a.check_out, a.in_lat, a.in_lon,
                   a.out_lat, a.out_lon, a.in_selfie, a.out_selfie, a.branch
            FROM employees e
            LEFT JOIN attendance a ON a.employee_id=e.id AND a.date=?
            WHERE e.role='employee'"""
        params = [date]
        if branch:
            query += " AND a.branch=?"
            params.append(branch)
        query += " ORDER BY e.name"
        rows = c.execute(query, params).fetchall()

    result = []
    for r in rows:
        item = dict(r)
        emp_branch = item.get("branch")

        coords = BRANCH_LOCATIONS.get(emp_branch) if emp_branch else None
        # Auto-detect nearest branch for legacy records or missing branch
        if not coords and item.get("in_lat") and item.get("in_lon"):
            closest_b = None
            closest_d = float("inf")
            for b_name, b_pos in BRANCH_LOCATIONS.items():
                d = calculate_distance_meters(item["in_lat"], item["in_lon"], b_pos[0], b_pos[1])
                if d < closest_d:
                    closest_d = d
                    closest_b = b_name
            if closest_b:
                emp_branch = closest_b
                coords = BRANCH_LOCATIONS[closest_b]
                item["branch"] = emp_branch

        if coords and item.get("in_lat") and item.get("in_lon"):
            dist_in = calculate_distance_meters(item["in_lat"], item["in_lon"], coords[0], coords[1])
            item["in_dist_m"] = round(dist_in, 1)
            item["in_within_range"] = dist_in <= MAX_ALLOWED_DISTANCE_METERS
        else:
            item["in_dist_m"] = None
            item["in_within_range"] = None

        if coords and item.get("out_lat") and item.get("out_lon"):
            dist_out = calculate_distance_meters(item["out_lat"], item["out_lon"], coords[0], coords[1])
            item["out_dist_m"] = round(dist_out, 1)
            item["out_valid"] = dist_out <= MAX_ALLOWED_DISTANCE_METERS
        else:
            item["out_dist_m"] = None
            item["out_valid"] = None

        result.append(item)

    return {"date": date, "rows": result, "max_distance_m": MAX_ALLOWED_DISTANCE_METERS}


@app.post("/api/add-user")
async def api_add_user(request: Request, username: str = Form(...), password: str = Form(...)):
    need_user(request, admin=True)
    try:
        emp_code = f"EMP-{username.strip()}"
        name = username.strip()
        with db() as c:
            c.execute("INSERT INTO employees (emp_code,name,username,password_hash,role) VALUES (?,?,?,?,?)",
                      (emp_code, name, username.strip(), hash_password(password), "employee"))
        return {"ok": True, "message": f"Added employee {username.strip()}"}
    except Exception as e:
        raise HTTPException(400, "Error adding user: Username might already exist.")


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
