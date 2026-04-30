# MCPD Portal Handoff

## Project Folder
Copy this entire folder to the new PC:
`C:\Users\rober\OneDrive\Desktop\mcpd-portal`

## Run on New PC
1) Open PowerShell:
```
cd "C:\Users\<YOURUSERNAME>\OneDrive\Desktop\mcpd-portal"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
notepad .env
```

2) Update `.env`:
```
SECRET_KEY=your-secret
ADMIN_USERNAME=robertrichards45
ADMIN_PASSWORD=Stonecold1!
DATABASE_URL=sqlite:///C:/Users/<YOURUSERNAME>/OneDrive/Desktop/mcpd-portal/data/app.db
CAC_AUTH_ENABLED=1
CAC_AUTO_REGISTER=1
```

3) Start server:
```
.venv\Scripts\python.exe app.py
```

4) Open:
`http://localhost:5055`

## Where We Left Off
- CLEO pages embedded as PDFs (fillable if the PDF supports it)
- Narrative page has enclosure rows with per-row upload
- Reports workflow: multi-person, co-authors, submit + admin grading
- Stats, Training, Forms, Annual AI built
- CLEOC clone needs screenshots for exact visual match
- CAC login and `Create Account with CAC` now require a real upstream identity header
- The local `cac.test` fallback was removed
- This PC still fails CAC hardware detection: `certutil -scinfo` reports `SCARD_STATE_EMPTY`
- `ScDeviceEnum` and `SCardSvr` were repaired, but the card is still not detected
- Best real-CAC test path: use another government PC where the CAC is detected correctly
- Quick resume helper added: run `.\resume_session.cmd`

## Troubleshooting
- If login fails: ensure `.env` exists and restart server.
- If CAC login fails: confirm the reverse proxy is forwarding one of the configured `CAC_USERNAME_HEADERS`.
- If DB not created: run `python -c "from app import create_app; create_app()"`

