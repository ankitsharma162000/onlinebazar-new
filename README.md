# 🛒 E-Commerce Web Application
### MCA Academic Project — Django + PostgreSQL + Machine Learning

---

## 👨‍💻 Developed By

| Name          | Roll Number | Programme |
|---------------|-------------|-----------|
| Ankit Sharma  | 34          | MCA       |
| Niraj Kumar   | 8           | MCA       |

---

## 🚀 Features

### 3 Role System
- **User (Buyer)** — Register, browse, cart, checkout, track orders, reviews
- **Seller** — Register, list products with images, manage stock, view analytics
- **SuperAdmin** — Blacklist/whitelist sellers, create discounts, view all analytics

### 💳 Payments
- Cash on Delivery, UPI, ATM/Debit Card, Net Banking (via Razorpay)

### 📦 Smart Stock Management
- Auto stock deduction on every purchase (atomic transaction)
- ML-powered low stock alerts to sellers

### 🤖 Machine Learning (4 Modules)
1. **Seasonal Sales Prediction** — Random Forest Classifier
2. **Regional Demand Analysis** — Pandas GroupBy aggregation
3. **Low Stock Warning** — Linear extrapolation of daily sales rate
4. **Product Recommendations** — TF-IDF + Cosine Similarity

### 📊 Dashboards
- User Dashboard: orders, wishlist, recommendations
- Seller Dashboard: revenue chart, category pie, ML alerts, regional map
- SuperAdmin Dashboard: full platform analytics, ML insights

---

## ⚙️ Setup Instructions

### 1. Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Redis (optional, for Celery)

### 2. Clone / Extract Project
```bash
cd ecommerce_project
```

### 3. Create Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Create PostgreSQL Database
```sql
CREATE DATABASE ecommerce_db;
CREATE USER postgres WITH PASSWORD 'postgres';
GRANT ALL PRIVILEGES ON DATABASE ecommerce_db TO postgres;
```

### 6. Configure Environment
Edit the `.env` file with your actual credentials:
```
DB_NAME=ecommerce_db
DB_USER=postgres
DB_PASSWORD=yourpassword
DB_HOST=localhost
DB_PORT=5432
```

### 7. Run Migrations
```bash
python manage.py makemigrations users
python manage.py makemigrations seller
python manage.py makemigrations store
python manage.py migrate
```

### 8. Create Django Superuser (for /admin panel)
```bash
python manage.py createsuperuser
```

### 9. Run Development Server
```bash
python manage.py runserver
```

### 10. Open in Browser
- **Home Page:** http://127.0.0.1:8000/
- **User Login:** http://127.0.0.1:8000/user/login/
- **Seller Login:** http://127.0.0.1:8000/seller/login/
- **SuperAdmin Login:** http://127.0.0.1:8000/superadmin/login/
- **Django Admin:** http://127.0.0.1:8000/admin/

---

## 🔑 Default SuperAdmin Credentials
```
Email:    admin@ecommerce.com
Password: Admin@123
```

---

## 🛠️ Tech Stack

| Layer      | Technology                    |
|------------|-------------------------------|
| Backend    | Django 5.0 (Python)           |
| Database   | PostgreSQL 15                 |
| Frontend   | Bootstrap 5 + Chart.js        |
| ML         | scikit-learn, pandas, numpy   |
| Payments   | Razorpay API                  |
| Images     | Pillow (Django ImageField)    |
| Auth       | Custom session-based auth     |

---

## 📁 Project Structure

```
ecommerce_project/
├── manage.py
├── requirements.txt
├── .env
├── ecommerce/          ← settings, urls, wsgi
├── users/              ← buyer registration, login, dashboard
├── seller/             ← seller portal, product management
├── store/              ← products, cart, orders, reviews
├── superadmin/         ← admin portal, blacklist, discounts
├── payments/           ← Razorpay integration
├── ml/                 ← 4 ML modules
├── templates/          ← all HTML templates
├── static/             ← CSS, JS, images
└── media/              ← uploaded product images
```

---

## 📄 License
Academic use only — MCA Project Submission 2024–2025
