
# BusinessFlow — Business Management System

BusinessFlow is a Django-based business management and point-of-sale (POS) application designed to help businesses manage inventory, customers, sales, invoices, expenses, and reports from one place.

## Features

- Dashboard for business overview
- Product and category management
- Inventory tracking and low-stock alerts
- Customer management
- Sales transactions and invoice management
- Invoice editing, printing, and PDF downloads
- Expense tracking
- Sales and inventory reports
- Monthly profit and loss reporting
- User authentication
- MySQL database integration

## Technology Stack

- Python
- Django
- MySQL
- HTML
- CSS
- JavaScript
- Bootstrap
- Bootstrap Icons

## Project Structure

```text
BusinessFlow/
├── accounts/
├── config/
├── customers/
├── expenses/
├── products/
├── reports/
├── sales/
├── static/
├── templates/
├── .env.example
├── .gitignore
├── manage.py
├── requirements.txt
└── README.md
```

## Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/Parth-dotcom/Business-Flow.git
cd Business-Flow
```

### 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Configure environment variables

Copy `.env.example` to `.env` and update the values for your local environment.

Never commit your actual `.env` file or real credentials.

### 5. Prepare the MySQL database

Create a MySQL database named `businessflow`. Update the database settings in `.env` to match your local MySQL configuration.

### 6. Apply migrations

```bash
python manage.py migrate
```

### 7. Create an administrator

```bash
python manage.py createsuperuser
```

### 8. Start the development server

```bash
python manage.py runserver
```

Open http://127.0.0.1:8000/ in your browser.

## Security Notes

- Keep `.env` private.
- Use a unique Django secret key.
- Never publish database passwords.
- Set `DJANGO_DEBUG=False` and configure appropriate allowed hosts before deployment.

## Project Status

This project is under active development. Features and setup instructions may evolve.

## Author

Parth Kurani
