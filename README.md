# Automatic Teacher Timetable Generator

A working school timetable system for classes 5–11, with section support (5A, 5B, etc.). Directors enter subjects, teachers, weekly hour limits, class requirements and teacher unavailability. OR-Tools CP-SAT assigns qualified teachers and school time slots automatically. The frontend supports Tajik, Russian and English.

## Stack and structure

- `backend/`: Django 5.2, Django REST Framework, PostgreSQL, token authentication, migrations, seed command, validation and CP-SAT service.
- `frontend/`: React 19, TypeScript and Vite 7. Responsive director and teacher screens.
- `backend/scheduler/services/`: preflight proofs, CP-SAT model, solution validation and atomic activation.

## Windows PowerShell setup

Install Python 3.13, Node.js 24 or newer, and PostgreSQL. From the project root:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\pip.exe install -r backend\requirements.txt
Copy-Item .env.example .env
cd frontend
npm.cmd install
cd ..
```

Create a PostgreSQL database and account, then edit `.env`: set `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`, and a long random `DJANGO_SECRET_KEY`. The default example assumes a local PostgreSQL server on port 5432. Keep `.env` private. For a local PostgreSQL installation, the SQL is:

```sql
CREATE USER timetable WITH PASSWORD 'choose-a-strong-password';
CREATE DATABASE timetable OWNER timetable;
```

If using the project's isolated local PostgreSQL cluster from this workspace, start it with:

```powershell
& 'C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe' -D .runtime\postgres -o '-p 55432 -h 127.0.0.1' -l .runtime\postgres.log start
```

Set `POSTGRES_PORT=55432` in `.env` for that cluster. It uses local trust authentication for development only; use a password-protected PostgreSQL account for deployment.

Apply migrations and optionally load example data:

```powershell
.\.venv\Scripts\python.exe backend\manage.py migrate
.\.venv\Scripts\python.exe backend\manage.py seed_demo --scenario feasible
```

`seed_demo` reads `DEMO_DIRECTOR_PASSWORD` and `DEMO_TEACHER_PASSWORD` from `.env`, or accepts `--director-password` and `--teacher-password`. It creates director login `director`, teacher logins `ali`, `farida`, `said`, `farzona`, and `madina`. The feasible example has 72 required lessons; Али has at most 18 English hours, Саид at most 20 Mathematics hours and Мадина at most 16 Physics hours. `seed_demo --scenario infeasible` deactivates the extra English teacher, making the 21 English hours exceed the remaining 18-hour capacity. Run `--scenario feasible` to restore it.

Open two PowerShell windows:

```powershell
.\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000
```

```powershell
cd frontend
npm.cmd run dev
```

Open **http://127.0.0.1:5173/**. If no director exists, the first visit offers director registration; registration closes after the first director account is created. With seed data, sign in as `director` using the password configured in `.env`. Teacher accounts can only open their own timetable. The Django admin is at `http://127.0.0.1:8000/admin/` for the director account.

## Generation behavior

Teacher weekly hours are **maximums**, not exact targets. The server checks class slot counts, qualified teacher capacity and availability before solving. CP-SAT enforces every required lesson, subject qualification, class and teacher collision avoidance, weekly limits, unavailable slots and school days/periods. Day balance, subject distribution and teacher free periods are soft optimization goals.

The result distinguishes `completed`, proven `infeasible`, `timeout` (feasibility unknown) and `error`. A successful result is validated again on the server, then written and activated inside a database transaction. Unsuccessful attempts are saved with diagnostics and leave the previous active version in place. Changing input data while a solve is running prevents that stale result from becoming active.

## API

All endpoints are under `/api/`. `/auth/bootstrap/`, `/auth/register/`, `/auth/login/`, `/auth/me/`, `/auth/logout/` manage users. Director-only endpoints cover `/subjects/`, `/classes/`, `/teachers/`, `/requirements/`, `/unavailable/`, `/availability/teachers/<id>/`, `/settings/`, `/generations/` and `/timetable/`. A teacher can use `/my-timetable/` and read school settings. Authenticated requests use `Authorization: Token <token>`.

## Verification

```powershell
.\.venv\Scripts\python.exe backend\manage.py check
.\.venv\Scripts\python.exe backend\manage.py test scheduler --settings=config.test_settings --noinput
.\.venv\Scripts\python.exe backend\manage.py makemigrations --check --dry-run
cd frontend
npm.cmd run build
```

The test settings use an in-memory SQLite database for fast isolated unit tests; the application itself uses PostgreSQL. With both development servers and seed data running, `node scripts\smoke.mjs` verifies HTTP login, the 72-lesson active timetable, the teacher view and API permissions against PostgreSQL.
# DRF
# DRF_
