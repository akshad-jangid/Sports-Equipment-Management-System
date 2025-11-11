# Sports Equipment Database Management System

A Flask + MySQL-based web app for managing sports equipment issue/return with an 8-hour reminder scheduler.

## Features
- Add, view, and manage students and equipment.
- Issue/return logic with auto quantity update.
- Background task checks overdue issues and prints simulated SMS reminders.
- Simple Bootstrap web UI.

## Tech Stack
- Python (Flask)
- MySQL
- APScheduler (for background reminders)
- Bootstrap (frontend)

## Run Instructions
1. Install dependencies: `pip install -r requirements.txt`
2. Create database tables (SQL provided in app.py comments)
3. Run the app: `python app.py`
4. Visit: http://127.0.0.1:5000/
