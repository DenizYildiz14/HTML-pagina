# Health Tracker (Flask)

Simple Python web app for tracking health habits.

## Features
- Dashboard with progress summary (`X days busy`).
- Weight progress chart.
- Supplements status summary with separate page to mark taken/not taken.
- Water intake tracker with +/- controls and a 2.5L target.

## Run on Windows (Python) in `C:\diet`

1. Open **Command Prompt**.
2. Go to the project folder:
   ```bat
   cd /d C:\diet
   ```
3. Create a virtual environment:
   ```bat
   py -m venv .venv
   ```
4. Activate the virtual environment:
   ```bat
   .venv\Scripts\activate
   ```
5. Install dependencies:
   ```bat
   pip install -r requirements.txt
   ```
6. Start the app:
   ```bat
   py app.py
   ```
7. Open in browser:
   ```
   http://127.0.0.1:5000
   ```

## Notes
- If `py` is not available, use `python` instead.
- Keep running commands from `C:\diet` so files (including SQLite DB) stay in the project folder.
