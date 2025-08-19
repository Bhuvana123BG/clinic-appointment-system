# 🏥 Django Medical Appointment System

A full-stack Django web application where **patients** can register and request appointments with **doctors**, and **doctors** can manage and respond to these requests.

---

## 🚀 Getting Started

This project uses Django for both the backend and the frontend. You can run everything using the `manage.py` script.

### 🔧 Requirements

- Python 3.8+
- Django 4.x
- SQLite (default) or any other supported DB
- Virtualenv (recommended)

### 📦 Installation

1. **Clone the Repository:**

    ```bash
    git clone https://github.com/Bhuvana123BG/clinic-appointment-system.git
    cd clinic-appointment-system
    ```

2. **Set Up Virtual Environment:**

    ```bash
    python -m venv virtual
    source virtual/bin/activate  # Windows: virtual\\Scripts\\activate
    ```

3. **Install Dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4. **Apply Migrations:**

    ```bash
    python manage.py migrate
    ```

5. **Run Development Server:**

    ```bash
    python manage.py runserver
    ```

---

## 👥 User Roles

### 🧑‍⚕️ Doctor

- Login via provided credentials
- View appointment requests from patients
- View upcoming approved appointments
- Approve or reject appointment requests with an optional message

### 🧑 Patient

- Register and login
- View a list of available doctors
- Request appointments with future dates
- Edit pending appointments before approval
- View appointment history with status: Approved / Rejected / Pending
- Automatically reject pending appointments if the scheduled date has passed

---

## 🧩 Features

- ✅ Patient registration and login
- ✅ Doctor login
- ✅ Profile management for both patients and doctors
- ✅ Appointment request system
- ✅ Edit pending appointments (date/time) before approval
- ✅ Doctor response system (approve/reject with message)
- ✅ Automatic rejection of past-due pending appointments
- ✅ Appointment status tracking
- ✅ View appointment history and upcoming appointments
- ✅ Responsive frontend using Django templates

---

## 🗃️ Project Structure

```text
medical_appointment_system/
│
├── manage.py
├── requirements.txt
├── README.md
├── db.sqlite3
│
├── core/               # Main application
│   ├── models.py       # All database models
│   ├── views.py        # App views and business logic
│   ├── urls.py         # URL routing
│   ├── forms.py        # Django forms
│   └── templates/      # HTML templates
│
├── static/             # Static files (CSS, JS)
└── media/              # User uploaded files (profile images, etc.)

```

## 🛠️ Admin Access

```text
To create a superuser (admin):

python manage.py createsuperuser
```

## 📌 Notes

```text
Appointments must be set for future dates only.

If an appointment is still pending after its scheduled time, it will be automatically rejected.

Patients can only edit appointments before they are accepted or rejected.
```
