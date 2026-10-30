# RenewTrack — Subscription Renewal Manager

A responsive full-stack academic project built with Python, Flask, SQLite, HTML, CSS and Jinja2. It works in a laptop browser and on a smartphone browser over the same Wi-Fi network.

## Run on Windows (VS Code is NOT required)

1. Extract `RenewTrack_Laptop_and_Phone.zip` to a normal folder.
2. Make sure Python is installed.
3. Double-click `START_RENEWTRACK.bat`.
4. The first run creates a local virtual environment and installs Flask. An internet connection is needed for this first setup.
5. When the terminal reports that Flask is running, open `http://127.0.0.1:5000` on the laptop.
6. Create an account from the signup page. Your account starts with four sample subscriptions that you can edit or delete.

Keep the black terminal window open while using the app.

## Use on your smartphone

1. Connect the phone and laptop to the same Wi-Fi.
2. On Windows, press Win+R, type `cmd`, press Enter, then run `ipconfig`.
3. Find the active Wi-Fi adapter's IPv4 Address (for example, `192.168.1.5`).
4. On your phone's browser, open `http://192.168.1.5:5000`, replacing the example address with your laptop's actual IPv4 address.
5. If Windows Firewall asks, allow access on Private networks only. Never expose this academic demo to public networks.

If a college/hostel Wi-Fi blocks device-to-device traffic, try connecting both devices to a personal mobile hotspot.

## Features

- New account signup and login/logout
- Passwords stored as one-way hashes (not plain text)
- Separate subscription lists per user account
- Responsive dashboard, subscription manager and analytics
- Create, edit, search, filter, cancel/reactivate and delete subscriptions
- Upcoming renewal tracking for the next 30 days
- Invoice/receipt upload (PDF, PNG, JPG; maximum 8 MB)
- SQLite persistence across app restarts
- Mobile-friendly interface and password visibility toggle

## Technology

Python, Flask, SQLite, HTML5, CSS3, Jinja2 and Werkzeug password hashing.

## Database

- `users`: account name, unique email, password hash and creation time
- `subscriptions`: service name, category, amount, billing cycle, renewal date, status, notes, invoice filename and account owner

The app automatically upgrades the earlier RenewTrack database by adding account ownership to subscription records. On the first account signup, old demo records are assigned to that account. New accounts receive their own demo records.

## Academic demo limitations

This is a local academic demo, not a production financial service. It does not connect to bank accounts, process payments, send email reminders or automatically cancel subscriptions. It has no password-reset or email-verification workflow. Do not upload sensitive invoices or expose the local server to the public internet. For production use, add CSRF protection, HTTPS hosting, secure secret management, email verification, password reset, stronger upload isolation and deployment hardening.
