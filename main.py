from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
import mysql.connector
import bcrypt
import jwt
import datetime
import uuid

# ── Config (hardcoded - no .env needed) ──────────────────────────────────────
DB_HOST    = "localhost"
DB_USER    = "root"
DB_PASSWORD = "tiger"
DB_NAME    = "vendor_management"
SECRET_KEY = "mysecretkey123"

app = FastAPI(title="Vendor Management System", version="1.0.0")


# ── Database ──────────────────────────────────────────────────────────────────
def get_db():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )


# ── JWT ───────────────────────────────────────────────────────────────────────
def create_token(user_id, email, role):
    payload = {
        "id":    user_id,
        "email": email,
        "role":  role,
        "exp":   datetime.datetime.utcnow() + datetime.timedelta(hours=12)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def verify_token(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Token missing. Send: Bearer <token>")
    try:
        token = authorization.replace("Bearer ", "")
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired. Please login again.")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

def only_manager(authorization: str = Header(None)):
    user = verify_token(authorization)
    if user["role"] not in ["Manager", "Procurement Admin"]:
        raise HTTPException(status_code=403, detail="Access denied. Manager role required.")
    return user


# ── Helpers ───────────────────────────────────────────────────────────────────
def add_log(conn, user_id, action):
    cur = conn.cursor()
    cur.execute("INSERT INTO audit_logs(user_id, action) VALUES(%s,%s)", (user_id, action))
    conn.commit()
    cur.close()

def add_notification(conn, user_id, message):
    cur = conn.cursor()
    cur.execute("INSERT INTO notifications(user_id, message) VALUES(%s,%s)", (user_id, message))
    conn.commit()
    cur.close()


# ── Schemas ───────────────────────────────────────────────────────────────────
class RegisterBody(BaseModel):
    name:     str
    email:    str
    password: str
    role:     str

class LoginBody(BaseModel):
    email:    str
    password: str

class VendorBody(BaseModel):
    vendor_name:    str
    contact_person: str
    email:          str
    phone:          str
    gst_number:     str
    address:        str

class RequestBody(BaseModel):
    item_name:      str
    quantity:       int
    estimated_cost: float
    reason:         str

class RejectBody(BaseModel):
    reason: str

class POBody(BaseModel):
    request_id: int
    vendor_id:  int


# ── HOME ──────────────────────────────────────────────────────────────────────
@app.get("/", tags=["Home"])
def home():
    return {"message": "Vendor Management System is Running", "docs": "/docs"}


# ── MODULE 1 - AUTH ───────────────────────────────────────────────────────────
@app.post("/register", tags=["1. Auth"])
def register(body: RegisterBody):
    valid_roles = ["Employee", "Manager", "Procurement Admin"]
    if body.role not in valid_roles:
        raise HTTPException(400, f"Role must be one of: {valid_roles}")
    try:
        conn   = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM users WHERE email=%s", (body.email,))
        if cursor.fetchone():
            conn.close()
            raise HTTPException(400, "Email already registered")
        hashed = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
        cursor.execute(
            "INSERT INTO users(name, email, password, role) VALUES(%s,%s,%s,%s)",
            (body.name, body.email, hashed, body.role)
        )
        conn.commit()
        user_id = cursor.lastrowid
        add_log(conn, user_id, f"User registered: {body.email}")
        cursor.close()
        conn.close()
        return {"message": "Registered successfully", "role": body.role}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)}")


@app.post("/login", tags=["1. Auth"])
def login(body: LoginBody):
    try:
        conn   = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email=%s", (body.email,))
        user = cursor.fetchone()
        if not user:
            conn.close()
            raise HTTPException(404, "User not found")
        if not bcrypt.checkpw(body.password.encode(), user["password"].encode()):
            conn.close()
            raise HTTPException(401, "Wrong password")
        token = create_token(user["id"], user["email"], user["role"])
        add_log(conn, user["id"], f"User logged in: {body.email}")
        cursor.close()
        conn.close()
        return {"message": "Login successful", "token": token, "role": user["role"]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)}")


# ── MODULE 2 - VENDORS ────────────────────────────────────────────────────────
@app.post("/vendors", tags=["2. Vendors"])
def add_vendor(body: VendorBody, authorization: str = Header(None)):
    me   = only_manager(authorization)
    conn = get_db()
    cur  = conn.cursor(dictionary=True)
    cur.execute("SELECT id FROM vendors WHERE vendor_name=%s", (body.vendor_name,))
    if cur.fetchone():
        conn.close()
        raise HTTPException(409, "Vendor name already exists")
    cur.execute("SELECT id FROM vendors WHERE gst_number=%s", (body.gst_number,))
    if cur.fetchone():
        conn.close()
        raise HTTPException(409, "GST number already registered")
    cur.execute(
        "INSERT INTO vendors(vendor_name,contact_person,email,phone,gst_number,address) VALUES(%s,%s,%s,%s,%s,%s)",
        (body.vendor_name, body.contact_person, body.email, body.phone, body.gst_number, body.address)
    )
    conn.commit()
    vendor_id = cur.lastrowid
    add_log(conn, me["id"], f"Vendor created: {body.vendor_name}")
    cur.close(); conn.close()
    return {"message": "Vendor added successfully", "vendor_id": vendor_id}

@app.get("/vendors", tags=["2. Vendors"])
def get_vendors(authorization: str = Header(None)):
    verify_token(authorization)
    conn = get_db()
    cur  = conn.cursor(dictionary=True)
    cur.execute("SELECT id, vendor_name, contact_person, email, phone, gst_number, address FROM vendors")
    vendors = cur.fetchall()
    cur.close(); conn.close()
    return {"total": len(vendors), "vendors": vendors}

@app.put("/vendors/{vendor_id}", tags=["2. Vendors"])
def update_vendor(vendor_id: int, body: VendorBody, authorization: str = Header(None)):
    me   = only_manager(authorization)
    conn = get_db()
    cur  = conn.cursor(dictionary=True)
    cur.execute("SELECT id FROM vendors WHERE id=%s", (vendor_id,))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(404, "Vendor not found")
    cur.execute(
        "UPDATE vendors SET vendor_name=%s, contact_person=%s, email=%s, phone=%s, gst_number=%s, address=%s WHERE id=%s",
        (body.vendor_name, body.contact_person, body.email, body.phone, body.gst_number, body.address, vendor_id)
    )
    conn.commit()
    add_log(conn, me["id"], f"Vendor updated: ID {vendor_id}")
    cur.close(); conn.close()
    return {"message": "Vendor updated successfully"}

@app.delete("/vendors/{vendor_id}", tags=["2. Vendors"])
def delete_vendor(vendor_id: int, authorization: str = Header(None)):
    me   = only_manager(authorization)
    conn = get_db()
    cur  = conn.cursor(dictionary=True)
    cur.execute("SELECT id FROM vendors WHERE id=%s", (vendor_id,))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(404, "Vendor not found")
    cur.execute("DELETE FROM vendors WHERE id=%s", (vendor_id,))
    conn.commit()
    add_log(conn, me["id"], f"Vendor deleted: ID {vendor_id}")
    cur.close(); conn.close()
    return {"message": "Vendor deleted successfully"}


# ── MODULE 3 - PURCHASE REQUESTS ──────────────────────────────────────────────
@app.post("/purchase-requests", tags=["3. Purchase Requests"])
def create_request(body: RequestBody, authorization: str = Header(None)):
    me   = verify_token(authorization)
    conn = get_db()
    cur  = conn.cursor(dictionary=True)
    cur.execute(
        "INSERT INTO purchase_requests(user_id, item_name, quantity, estimated_cost, reason) VALUES(%s,%s,%s,%s,%s)",
        (me["id"], body.item_name, body.quantity, body.estimated_cost, body.reason)
    )
    conn.commit()
    req_id = cur.lastrowid
    add_notification(conn, me["id"], f"Your request #{req_id} for '{body.item_name}' has been submitted.")
    add_log(conn, me["id"], f"Purchase request created: #{req_id} - {body.item_name}")
    cur.close(); conn.close()
    return {"message": "Purchase request submitted", "request_id": req_id, "status": "pending"}

@app.get("/purchase-requests", tags=["3. Purchase Requests"])
def get_requests(authorization: str = Header(None)):
    me   = verify_token(authorization)
    conn = get_db()
    cur  = conn.cursor(dictionary=True)
    if me["role"] == "Employee":
        cur.execute("SELECT * FROM purchase_requests WHERE user_id=%s", (me["id"],))
    else:
        cur.execute("SELECT * FROM purchase_requests")
    requests = cur.fetchall()
    cur.close(); conn.close()
    return {"total": len(requests), "requests": requests}

@app.put("/purchase-requests/{req_id}", tags=["3. Purchase Requests"])
def update_request(req_id: int, body: RequestBody, authorization: str = Header(None)):
    me   = verify_token(authorization)
    conn = get_db()
    cur  = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM purchase_requests WHERE id=%s", (req_id,))
    req = cur.fetchone()
    if not req:
        conn.close()
        raise HTTPException(404, "Request not found")
    if req["status"] != "pending":
        conn.close()
        raise HTTPException(400, f"Cannot edit. Request is already '{req['status']}'")
    if req["user_id"] != me["id"] and me["role"] == "Employee":
        conn.close()
        raise HTTPException(403, "You can only edit your own requests")
    cur.execute(
        "UPDATE purchase_requests SET item_name=%s, quantity=%s, estimated_cost=%s, reason=%s WHERE id=%s",
        (body.item_name, body.quantity, body.estimated_cost, body.reason, req_id)
    )
    conn.commit()
    cur.close(); conn.close()
    return {"message": "Request updated successfully"}


# ── MODULE 4 - APPROVALS ──────────────────────────────────────────────────────
@app.post("/requests/{req_id}/approve", tags=["4. Approvals"])
def approve_request(req_id: int, authorization: str = Header(None)):
    me   = only_manager(authorization)
    conn = get_db()
    cur  = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM purchase_requests WHERE id=%s", (req_id,))
    req = cur.fetchone()
    if not req:
        conn.close()
        raise HTTPException(404, "Request not found")
    if req["status"] != "pending":
        conn.close()
        raise HTTPException(400, f"Request is already '{req['status']}'")
    cur.execute("UPDATE purchase_requests SET status='approved' WHERE id=%s", (req_id,))
    conn.commit()
    add_notification(conn, req["user_id"], f"Your request #{req_id} has been approved.")
    add_log(conn, me["id"], f"Request #{req_id} approved by {me['email']}")
    cur.close(); conn.close()
    return {"message": f"Request #{req_id} approved successfully"}

@app.post("/requests/{req_id}/reject", tags=["4. Approvals"])
def reject_request(req_id: int, body: RejectBody, authorization: str = Header(None)):
    me   = only_manager(authorization)
    conn = get_db()
    cur  = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM purchase_requests WHERE id=%s", (req_id,))
    req = cur.fetchone()
    if not req:
        conn.close()
        raise HTTPException(404, "Request not found")
    if req["status"] != "pending":
        conn.close()
        raise HTTPException(400, f"Request is already '{req['status']}'")
    cur.execute("UPDATE purchase_requests SET status='rejected' WHERE id=%s", (req_id,))
    conn.commit()
    add_notification(conn, req["user_id"], f"Your request #{req_id} was rejected. Reason: {body.reason}")
    add_log(conn, me["id"], f"Request #{req_id} rejected. Reason: {body.reason}")
    cur.close(); conn.close()
    return {"message": f"Request #{req_id} rejected"}


# ── MODULE 5 - PURCHASE ORDERS ────────────────────────────────────────────────
@app.post("/purchase-orders", tags=["5. Purchase Orders"])
def create_po(body: POBody, authorization: str = Header(None)):
    me   = only_manager(authorization)
    conn = get_db()
    cur  = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM purchase_requests WHERE id=%s", (body.request_id,))
    req = cur.fetchone()
    if not req:
        conn.close()
        raise HTTPException(404, "Purchase request not found")
    if req["status"] != "approved":
        conn.close()
        raise HTTPException(400, "Purchase order can only be created for approved requests")
    cur.execute("SELECT id FROM purchase_orders WHERE request_id=%s", (body.request_id,))
    if cur.fetchone():
        conn.close()
        raise HTTPException(409, "Purchase order already exists for this request")
    cur.execute("SELECT id FROM vendors WHERE id=%s", (body.vendor_id,))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(404, "Vendor not found")
    po_number = "PO-" + str(uuid.uuid4())[:8].upper()
    cur.execute(
        "INSERT INTO purchase_orders(request_id, vendor_id, po_number, amount) VALUES(%s,%s,%s,%s)",
        (body.request_id, body.vendor_id, po_number, req["estimated_cost"])
    )
    conn.commit()
    add_notification(conn, req["user_id"], f"Purchase Order {po_number} created for your request #{body.request_id}.")
    add_log(conn, me["id"], f"PO created: {po_number}")
    cur.close(); conn.close()
    return {"message": "Purchase order created", "po_number": po_number, "amount": str(req["estimated_cost"])}

@app.get("/purchase-orders", tags=["5. Purchase Orders"])
def get_pos(authorization: str = Header(None)):
    verify_token(authorization)
    conn = get_db()
    cur  = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM purchase_orders")
    pos = cur.fetchall()
    cur.close(); conn.close()
    return {"total": len(pos), "purchase_orders": pos}


# ── MODULE 6 - NOTIFICATIONS & AUDIT LOGS ────────────────────────────────────
@app.get("/notifications", tags=["6. Notifications"])
def get_notifications(authorization: str = Header(None)):
    me   = verify_token(authorization)
    conn = get_db()
    cur  = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM notifications WHERE user_id=%s ORDER BY created_at DESC", (me["id"],))
    notes = cur.fetchall()
    cur.close(); conn.close()
    return {"total": len(notes), "notifications": notes}

@app.get("/audit-logs", tags=["6. Audit Logs"])
def get_audit_logs(authorization: str = Header(None)):
    only_manager(authorization)
    conn = get_db()
    cur  = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM audit_logs ORDER BY created_at DESC")
    logs = cur.fetchall()
    cur.close(); conn.close()
    return {"total": len(logs), "audit_logs": logs}


# ── MODULE 7 - REPORTS ────────────────────────────────────────────────────────
@app.get("/reports/monthly", tags=["7. Reports"])
def monthly_report(authorization: str = Header(None)):
    only_manager(authorization)
    conn = get_db()
    cur  = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM purchase_orders")
    pos = cur.fetchall()
    cur.execute("SELECT * FROM purchase_requests")
    reqs = cur.fetchall()
    cur.close(); conn.close()
    return {
        "total_purchase_orders": len(pos),
        "total_spend":           sum(float(p["amount"]) for p in pos),
        "total_requests":        len(reqs),
        "approved":              sum(1 for r in reqs if r["status"] == "approved"),
        "pending":               sum(1 for r in reqs if r["status"] == "pending"),
        "rejected":              sum(1 for r in reqs if r["status"] == "rejected"),
    }

@app.get("/reports/vendors", tags=["7. Reports"])
def vendor_report(authorization: str = Header(None)):
    only_manager(authorization)
    conn = get_db()
    cur  = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM vendors")
    vendors = cur.fetchall()
    result = []
    for v in vendors:
        cur.execute("SELECT COUNT(*) as total, SUM(amount) as spend FROM purchase_orders WHERE vendor_id=%s", (v["id"],))
        row = cur.fetchone()
        result.append({
            "vendor_name":  v["vendor_name"],
            "total_orders": row["total"],
            "total_spend":  float(row["spend"]) if row["spend"] else 0
        })
    cur.close(); conn.close()
    return {"vendors": result}

@app.get("/reports/pending", tags=["7. Reports"])
def pending_report(authorization: str = Header(None)):
    only_manager(authorization)
    conn = get_db()
    cur  = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM purchase_requests WHERE status='pending'")
    reqs = cur.fetchall()
    cur.close(); conn.close()
    return {"total_pending": len(reqs), "requests": reqs}

@app.get("/reports/approved", tags=["7. Reports"])
def approved_report(authorization: str = Header(None)):
    only_manager(authorization)
    conn = get_db()
    cur  = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM purchase_requests WHERE status='approved'")
    reqs = cur.fetchall()
    cur.close(); conn.close()
    return {"total_approved": len(reqs), "requests": reqs}

@app.get("/reports/purchase-orders", tags=["7. Reports"])
def po_report(authorization: str = Header(None)):
    only_manager(authorization)
    conn = get_db()
    cur  = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM purchase_orders")
    pos = cur.fetchall()
    cur.close(); conn.close()
    return {
        "total_orders": len(pos),
        "total_spend":  sum(float(p["amount"]) for p in pos),
        "purchase_orders": pos
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080)
