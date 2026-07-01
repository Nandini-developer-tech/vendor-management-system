# Vendor Management & Purchase Request System

A backend REST API project built with **FastAPI** and **MySQL**.

---

## Tech Stack     

- Python
- FastAPI
- MySQL
- JWT Authentication
- Bcrypt Password Hashing
- Swagger UI (auto-generated)

---

## Project Structure

```
vendor_management/
│
├── main.py          # Complete backend code
├── requirements.txt # Required packages
├── database.sql     # Database and table creation
├── .env             # Environment variables
└── README.md        # Project documentation
```

---

## Database Tables

| Table | Description |
|---|---|
| users | Stores registered users |
| vendors | Stores vendor information |
| purchase_requests | Stores purchase requests by employees |
| purchase_orders | Stores generated purchase orders |
| notifications | Stores notifications for users |
| audit_logs | Stores all system activity logs |

---

## Setup Instructions

### Step 1 — Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/vendor-management-system.git
cd vendor-management-system
```

### Step 2 — Install Required Packages

```bash
pip install -r requirements.txt
```

### Step 3 — Setup MySQL Database

Open MySQL and run:

```bash
source database.sql
```

Or paste the contents of `database.sql` directly in MySQL Workbench and run it.

### Step 4 — Configure Database Password

Open `main.py` and update your MySQL password at the top:

```python
DB_PASSWORD = "your_mysql_password"
```

### Step 5 — Run the Project

```bash
python main.py
```

Or:

```bash
uvicorn main:app --port 8080
```

### Step 6 — Open Swagger UI

```
http://127.0.0.1:8080/docs
```

---

## User Roles

| Role | Permissions |
|---|---|
| Employee | Register, Login, Create & View own Purchase Requests |
| Manager | All Employee permissions + Approve/Reject Requests, Manage Vendors, Create Purchase Orders, View Reports |
| Procurement Admin | All Manager permissions + Delete Vendors, View Audit Logs |

---

## API Endpoints

### Module 1 — Authentication

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| POST | /register | Register a new user | No |
| POST | /login | Login and get JWT token | No |

### Module 2 — Vendor Management

| Method | Endpoint | Description | Role Required |
|---|---|---|---|
| POST | /vendors | Add new vendor | Manager |
| GET | /vendors | Get all vendors | Any |
| PUT | /vendors/{id} | Update vendor | Manager |
| DELETE | /vendors/{id} | Delete vendor | Manager |

### Module 3 — Purchase Requests

| Method | Endpoint | Description | Role Required |
|---|---|---|---|
| POST | /purchase-requests | Create purchase request | Any |
| GET | /purchase-requests | Get purchase requests | Any |
| PUT | /purchase-requests/{id} | Update purchase request | Owner only |

### Module 4 — Approval Workflow

| Method | Endpoint | Description | Role Required |
|---|---|---|---|
| POST | /requests/{id}/approve | Approve a request | Manager |
| POST | /requests/{id}/reject | Reject a request | Manager |

### Module 5 — Purchase Orders

| Method | Endpoint | Description | Role Required |
|---|---|---|---|
| POST | /purchase-orders | Create purchase order | Manager |
| GET | /purchase-orders | Get all purchase orders | Any |

### Module 6 — Notifications

| Method | Endpoint | Description | Role Required |
|---|---|---|---|
| GET | /notifications | Get my notifications | Any |

### Module 6 — Audit Logs

| Method | Endpoint | Description | Role Required |
|---|---|---|---|
| GET | /audit-logs | Get all audit logs | Manager |

### Module 7 — Reports

| Method | Endpoint | Description | Role Required |
|---|---|---|---|
| GET | /reports/monthly | Monthly procurement report | Manager |
| GET | /reports/vendors | Vendor summary report | Manager |
| GET | /reports/pending | Pending requests report | Manager |
| GET | /reports/approved | Approved requests report | Manager |
| GET | /reports/purchase-orders | Purchase orders report | Manager |

---

## How to Test in Swagger

### 1. Register Users
```json
POST /register
{
  "name": "Nandini",
  "email": "nandini@gmail.com",
  "password": "12345",
  "role": "Employee"
}
```

### 2. Login
```json
POST /login
{
  "email": "nandini@gmail.com",
  "password": "12345"
}
```

### 3. Authorize
- Copy the token from login response
- Click **Authorize 🔒** button in Swagger
- Type: `Bearer your_token_here`
- Click Authorize → Close

### 4. Test APIs
Now you can test all protected APIs.

---

## Sample API Responses

### Register
```json
{
  "message": "Registered successfully",
  "role": "Employee"
}
```

### Login
```json
{
  "message": "Login successful",
  "token": "eyJhbGciOiJIUzI1NiIs......",
  "role": "Manager"
}
```

### Add Vendor
```json
{
  "message": "Vendor added successfully",
  "vendor_id": 1
}
```

### Create Purchase Request
```json
{
  "message": "Purchase request submitted",
  "request_id": 1,
  "status": "pending"
}
```

### Approve Request
```json
{
  "message": "Request #1 approved successfully"
}
```

### Create Purchase Order
```json
{
  "message": "Purchase order created",
  "po_number": "PO-A1B2C3D4",
  "amount": "250000.00"
}
```

### Monthly Report
```json
{
  "total_purchase_orders": 1,
  "total_spend": 250000.0,
  "total_requests": 2,
  "approved": 1,
  "pending": 0,
  "rejected": 1
}
```

---

## Validation & Error Handling

| Scenario | Response |
|---|---|
| Duplicate email registration | 400 - Email already registered |
| Wrong password | 401 - Wrong password |
| Missing token | 401 - Token missing |
| Employee tries to approve | 403 - Access denied |
| Edit approved request | 400 - Cannot edit |
| Duplicate vendor name | 409 - Vendor name already exists |
| PO for unapproved request | 400 - Only approved requests allowed |

---

## GitHub Commit History

```
git commit -m "Initial project setup"
git commit -m "Added database schema"
git commit -m "Implemented user authentication with JWT"
git commit -m "Added vendor management APIs"
git commit -m "Implemented purchase request module"
git commit -m "Added approval workflow"
git commit -m "Implemented purchase order generation"
git commit -m "Added notifications and audit logs"
git commit -m "Added reporting APIs"
git commit -m "Fixed validation and error handling"
```

---

## Requirements

```
fastapi==0.111.0
uvicorn==0.29.0
mysql-connector-python==8.3.0
python-dotenv==1.0.1
PyJWT==2.8.0
bcrypt==4.0.1
python-multipart==0.0.9
```

---

## Author

**Nandini**
Vendor Management System — Backend Project
