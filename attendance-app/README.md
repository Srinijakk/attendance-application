# Attendance App

## Run
    python -m venv venv
    venv\Scripts\activate          # Windows  (Mac/Linux: source venv/bin/activate)
    pip install -r requirements.txt

    python add_user.py ADM001 "Admin" admin admin123 admin
    python add_user.py EMP001 "Rahul" rahul01 pass1234

    uvicorn main:app --reload
Open http://127.0.0.1:8000

## Notes
- Camera and GPS need `localhost` or HTTPS. Over a LAN IP you must use HTTPS.
- Set a real secret before deploying:  set SECRET_KEY=some-long-random-string
- Selfies are saved in `selfies/`, data in `attendance.db`.
