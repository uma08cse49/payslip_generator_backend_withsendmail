# payslip_generator_backend_withsendmail
# Payslip Generator – Backend Architecture & Deployment Guide

This document explains **how the Payslip Generator system runs in production**, how Flask, Gunicorn, systemd, Apache/Nginx, and React work together, and **why restarting the service is required after Python code changes**.

This README is intended as a **future reference** for maintenance, debugging, and onboarding.

---

## 🏗️ High-Level Architecture

```
User Browser
     │
     ▼
React Frontend (Static Files)
     │
     │  API Requests (/api/*)
     ▼
Apache / Nginx (Reverse Proxy)
     │
     ▼
Gunicorn (WSGI Server)
     │
     ▼
wsgi.py (WSGI Entry Point)
     │
     ▼
Flask Application (service5.py)
     │
     ▼
Payslip Business Logic / PDF Generation
```

---

## 📁 Project Structure (Relevant Parts)

```
/var/www/payslipgenerator/
│
├── payslip_generator_python/
│   ├── service5.py        # Flask app & routes
│   ├── utils.py           # Business logic (example)
│   └── ...
│
├── wsgi.py                # WSGI entry point
└── venv/                  # Python virtual environment
```

---

## 🌐 Frontend (React)

* Built using React (Vite / CRA)
* After `npm run build`, static files are generated
* These files are served directly by **Apache or Nginx**
* React **does not run Python** — it only sends HTTP requests

### Example API Call from React

```js
fetch('/api/generate-payslip', {
  method: 'POST',
  body: JSON.stringify(data)
})
```

---

## 🐍 Backend (Flask)

* Flask contains:

  * API routes
  * Payslip calculations
  * PDF generation logic

⚠️ Flask **cannot run directly** in Apache or Nginx in production.

---

## 🔌 Why WSGI Is Required

* **WSGI (Web Server Gateway Interface)** is a standard
* It defines how a web server communicates with a Python app
* Flask exposes a callable WSGI object

Apache / Nginx → *cannot talk to Flask directly* → **needs a WSGI server**

---

## 🚀 Gunicorn (WSGI Server)

Gunicorn is responsible for:

* Loading Python code
* Running Flask in memory
* Handling concurrent requests

Gunicorn command logic:

```
gunicorn wsgi:application
```

Meaning:

* `wsgi` → wsgi.py
* `application` → Flask app object

---

## 📄 wsgi.py (Entry Point Explained)

```python
import sys
sys.path.insert(0, '/var/www/payslipgenerator')

from payslip_generator_python.service5 import app as application
```

### What This File Does

1. Adds project path to Python import system
2. Imports Flask app from `service5.py`
3. Exposes it as `application` (WSGI standard)

Gunicorn loads this file **once at startup**.

---

## ⚙️ systemd Service (payslip.service)

systemd is used to:

* Start Gunicorn automatically
* Restart it on crash
* Control it using system commands

### Typical Service Flow

```
systemd
  ↓
payslip.service
  ↓
Gunicorn
  ↓
wsgi.py
  ↓
Flask app
```

---

## 🔁 Why Restart Is Required After Python Code Changes

### 🔥 Critical Rule

> Gunicorn loads Python code into memory **only at startup**.

Therefore:

* Editing `.py` files does **not** change running code
* Old code continues to run in memory

### ✅ Correct Command

```bash
sudo systemctl restart payslip.service
```

This:

1. Stops Gunicorn
2. Clears old Python code from memory
3. Reloads `wsgi.py`
4. Loads updated Flask code

---

## 🧪 When Restart Is NOT Needed

| Change Type           | Restart Required       |
| --------------------- | ---------------------- |
| React UI text         | ❌ No                   |
| React build files     | ❌ No                   |
| Apache config         | ❌ (reload Apache only) |
| Python Flask code     | ✅ YES                  |
| Environment variables | ✅ YES                  |
| Gunicorn config       | ✅ YES                  |

---

## 🛠️ Useful Commands

### Restart Backend

```bash
sudo systemctl restart payslip.service
```

### Check Status

```bash
sudo systemctl status payslip.service
```

### View Logs (Live)

```bash
sudo journalctl -u payslip.service -f
```

---

## 🧠 Final Mental Model (Key Takeaway)

```
React UI
   ↓
Apache / Nginx
   ↓
Gunicorn (memory-resident)
   ↓
wsgi.py
   ↓
Flask app (service5.py)
```

> **Any Python code update → restart payslip.service**

---

## ✅ Conclusion

This setup is:

* Production safe
* Scalable
* Industry standard


