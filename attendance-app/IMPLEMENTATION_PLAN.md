# Attendance App: Phase-wise Implementation Plan

**Stack:** FastAPI + SQLite + HTML/CSS/JS (served by FastAPI) + selfies on local disk
**Users:** Admin (dashboard) and Employees (check-in/out with live selfie + GPS, IST timestamps)

## Status at a glance

| Phase | Name | Status |
|---|---|---|
| 0 | Project setup | Done |
| 1 | Database and authentication | Code written, not yet tested end to end |
| 2 | Attendance backend (check-in/out API) | Code written, not yet tested end to end |
| 3 | Employee UI (camera, GPS, calendar, status dot) | **Not complete.** Templates and JS still need to be written |
| 4 | Admin dashboard | **Not complete.** Same as above |
| 5 | Testing and security checks | Pending |
| 6 | Deployment (HTTPS, backups) | Pending |
| 7 | Optional improvements | Later |

---

## Phase 0: Project setup

**Goal:** A runnable empty project in VS Code.

- Create the folder structure: `main.py`, `database.py`, `auth.py`, `add_user.py`, `static/`, `templates/`, `selfies/`
- Create and activate a virtual environment
- Install `fastapi`, `uvicorn`, `jinja2`, `python-multipart`, `itsdangerous`, `bcrypt`

**Done when:** `uvicorn main:app --reload` starts without errors.

---

## Phase 1: Database and authentication

**Goal:** Users can log in; roles are enforced on the server.

- SQLite tables: `employees` (id, emp_code, name, username, password_hash, role) and `attendance` (one row per employee per day)
- Passwords stored as bcrypt hashes, never plain text
- Signed session cookie holds only the user id; role is always read from the database
- `add_user.py` script to create the admin and each employee from your list
- Routes: `GET/POST /login`, `GET /logout`, `/` redirects by role

**Done when:**
- Admin login lands on `/admin`; employee login lands on `/employee`
- Wrong password shows an error
- An employee opening `/admin` is redirected away

---

## Phase 2: Attendance backend

**Goal:** Check-in and check-out are saved correctly and safely.

- `POST /api/check-in` and `POST /api/check-out` accept selfie image, latitude, longitude
- **Server** generates the IST timestamp and takes the employee from the session; nothing is trusted from the browser
- Selfie saved to `selfies/<EMP_CODE>/<date>-in.jpg` (or `-out.jpg`); only the path is stored in SQLite
- Rules: one check-in per day; check-out only after check-in; no double check-out
- `GET /api/status` returns not-in / in / out for the status dot
- `GET /api/attendance` (admin only) returns the table data
- `GET /selfie/...` serves images to admin or to the owning employee only

**Done when:** Calls made with a test client create the right row and file, and duplicate or out-of-order calls are rejected.

---

## Phase 3: Employee UI

**Goal:** The employee page from the requirements.

- `login.html` with username, password, and a sign-in button
- `employee.html` with a profile status dot, **Check in** and **Check out** buttons, and an IST calendar and live clock
- `employee.js` flow: button click, then camera opens (`getUserMedia`), then **Take selfie**, then GPS is read, then the form is posted
- No file input anywhere, so there is no upload option
- Status dot: grey = not checked in, green = checked in, red = checked out
- Clear messages when camera or location permission is denied

**Done when:** On a phone and a laptop, an employee can check in, the dot turns green, and the times shown are in IST.

---

## Phase 4: Admin dashboard

**Goal:** Admin sees who came in, with proof.

- `admin.html` titled **Attendance dashboard**, table titled **Employee attendance records**
- Columns: Employee name, Employee picture, Location, Check-in time, Check-out time
- Location shown as coordinates linking to a map
- Date picker to view past days; auto-refresh every 30 seconds
- Employees who have not checked in show as "—"

**Done when:** Records created in Phase 3 appear on the dashboard with working selfie thumbnails.

---

## Phase 5: Testing and security checks

- Employee cannot open `/admin`, `/api/attendance`, or another employee's selfie
- Logged-out user cannot call any API
- Double check-in and check-out-before-check-in are rejected
- Oversized or empty selfie is rejected
- Selfie path cannot escape the `selfies/` folder
- Change the default `SECRET_KEY` before real use
- Test on at least one Android phone and one iPhone browser

**Known limit:** A browser cannot be made to *prove* an image came from the live camera; a determined person could send a fake request. The camera-only UI stops normal users from uploading. If stronger proof is needed later, add a server-side check (for example, comparing against a reference photo).

---

## Phase 6: Deployment

- Host on a small server (Linux VM or similar)
- **HTTPS is required**: browsers block camera and GPS on plain `http://` except on localhost
- Run uvicorn behind a reverse proxy (Caddy or Nginx handles HTTPS certificates)
- Set `SECRET_KEY` as an environment variable
- Daily backup of `attendance.db` and the `selfies/` folder
- Decide how long selfies are kept and delete older ones if needed

**Done when:** Employees can open the public URL on their phones and complete a check-in.

---

## Phase 7: Optional improvements (only if asked)

- Convert coordinates to a place name such as "Bangalore, Karnataka" (needs a geocoding service)
- Export attendance to CSV or Excel
- Month view and per-employee history
- Admin screen to add, disable, or reset employees (instead of `add_user.py`)
- Geofence: flag check-ins made far from the office
- Allow multiple check-in/out sessions per day
