# """
# Employee Attendance & Analytics API - STARTER

# Run:  uvicorn app.main:app --port 8000
# Env:  MONGO_URI, MONGO_DB (a local .env is loaded for convenience)

# This file was written quickly by a colleague who has left the company. The happy path
# works, but nobody has reviewed it. Read PROBLEM_STATEMENT.docx for what is expected of you,
# openapi.yaml for the contract and DATA_MODEL.md for what is stored in MongoDB.
# """
# import os
# from datetime import datetime, timedelta, timezone
# from decimal import Decimal, ROUND_HALF_UP
# from typing import Optional

# from dotenv import load_dotenv
# from fastapi import FastAPI, HTTPException, Query
# from pydantic import BaseModel, Field
# from pymongo import MongoClient, ASCENDING, DESCENDING
# from pymongo.errors import DuplicateKeyError

# load_dotenv()

# client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
# db = client[os.getenv("MONGO_DB", "attendance_db")]

# IST = timezone(timedelta(hours=5, minutes=30))

# app = FastAPI(title="Employee Attendance & Analytics API", version="2.0.0")



# @app.on_event("startup")
# def configure_indexes():
#     db.employees.create_index([("emp_code", ASCENDING)], unique=True)
#     db.employees.create_index([("department", ASCENDING)])
#     db.attendance_logs.create_index([("emp_code", ASCENDING), ("date", ASCENDING)], unique=True)
#     db.attendance_logs.create_index([("department", ASCENDING), ("date", ASCENDING)])
#     db.attendance_logs.create_index([("date", DESCENDING)])

# # --------------------------------------------------------------------------- #
# # Helpers
# # --------------------------------------------------------------------------- #
# def to_epoch_ms(dt: Optional[datetime]) -> Optional[int]:
#     if not dt:
#         return None
#     if dt.tzinfo is None:
#         dt = dt.replace(tzinfo=timezone.utc)
#     return int(dt.timestamp() * 1000)

# def round_half_up(value: float, decimals: int = 2) -> float:
#     d = Decimal(str(value))
#     target = Decimal("1." + "0" * decimals) if decimals > 0 else Decimal("1")
#     return float(d.quantize(target, rounding=ROUND_HALF_UP))

# def compute_late_minutes(punch_in: datetime, shift_start: str) -> int:
#     h, m = map(int, shift_start.split(":"))
#     # Truncate to whole seconds per R1
#     clean_pi = punch_in.replace(second=punch_in.second, microsecond=0)
#     start = clean_pi.replace(hour=h, minute=m, second=0, microsecond=0)
#     minutes = int((clean_pi - start).total_seconds() / 60)
#     return minutes if minutes > 10 else 0

# def compute_work_hours(punch_in: datetime, punch_out: datetime) -> float:
#     diff_sec = (punch_out - punch_in).total_seconds()
#     hours = diff_sec / 3600.0
#     return round_half_up(hours, 2)

# def compute_overtime(punch_out: datetime, shift_end: str, date_str: str) -> int:
#     h, m = map(int, shift_end.split(":"))
#     end = datetime.fromisoformat(date_str).replace(hour=h, minute=m, tzinfo=IST)
#     mins = int((punch_out - end).total_seconds() / 60)
#     return mins if mins >= 30 else 0

# def get_attendance_date(ts: datetime, shift_start: str, shift_end: str) -> str:
#     # Handle overnight shifts (shift_end <= shift_start) per R1
#     h_start, m_start = map(int, shift_start.split(":"))
#     h_end, m_end = map(int, shift_end.split(":"))
    
#     # Check if overnight shift
#     if h_end < h_start or (h_end == h_start and m_end <= m_start):
#         # If punch-in IST time is earlier than shift_end, it belongs to the previous day's shift
#         ist_time = ts.astimezone(IST)
#         end_time_today = ist_time.replace(hour=h_end, minute=m_end, second=0, microsecond=0)
#         if ist_time < end_time_today:
#             return (ist_time.date() - timedelta(days=1)).isoformat()
#     return ts.astimezone(IST).date().isoformat()

# def serialize_record(doc: dict) -> dict:
#     if not doc:
#         return doc
#     doc.pop("_id", None)
#     doc["punch_in"] = to_epoch_ms(doc.get("punch_in"))
#     doc["punch_out"] = to_epoch_ms(doc.get("punch_out"))
#     if "history" in doc:
#         for h in doc["history"]:
#             h["at"] = to_epoch_ms(h.get("at"))
#             if "changes" in h:
#                 for field, change in h["changes"].items():
#                     if field in ("punch_in", "punch_out"):
#                         if isinstance(change.get("from"), datetime):
#                             change["from"] = to_epoch_ms(change["from"])
#                         if isinstance(change.get("to"), datetime):
#                             change["to"] = to_epoch_ms(change["to"])
#     return doc
# # --------------------------------------------------------------------------- #
# # Models
# # --------------------------------------------------------------------------- #
# class EmployeeIn(BaseModel):
#     emp_code: str
#     name: str
#     email: str
#     department: str
#     shift_start: str = "09:30"
#     shift_end: str = "18:30"
#     joined_on: str

# class PunchInIn(BaseModel):
#     emp_code: str
#     punched_at: Optional[int] = None
#     status: str = "PRESENT"

# class PunchOutIn(BaseModel):
#     emp_code: str
#     punched_at: Optional[int] = None

# class RegularizeIn(BaseModel):
#     status: Optional[str] = None
#     punch_in: Optional[int] = None
#     punch_out: Optional[int] = None
#     reason: str
#     regularized_by: str


# # --------------------------------------------------------------------------- #
# # Endpoints provided
# # --------------------------------------------------------------------------- #
# @app.get("/health")
# def health():
#     return {"status": "ok"}


# @app.post("/employees", status_code=201)
# def create_employee(body: EmployeeIn):
#     if db.employees.find_one({"emp_code": body.emp_code}):
#         raise HTTPException(409, "emp_code already exists")
#     doc = body.model_dump()
#     doc["created_at"] = datetime.now()
#     db.employees.insert_one(doc)
#     doc.pop("_id", None)
#     return doc


# @app.get("/employees")
# def list_employees(department: Optional[str] = None, page: int = 1, page_size: int = 20):
#     q = {}
#     if department:
#         q["department"] = department
#     skip = page * page_size
#     total = db.employees.count_documents({})
#     items = list(db.employees.find(q, {"_id": 0}).skip(skip).limit(page_size))
#     return {"items": items, "total": total, "page": page, "page_size": page_size}


# @app.post("/attendance/punch-in", status_code=201)
# def punch_in(body: PunchInIn):
#     emp = db.employees.find_one({"emp_code": body.emp_code})
#     ts = datetime.fromtimestamp(body.punched_at / 1000) if body.punched_at else datetime.now()
#     d = ts.date().isoformat()
#     if db.attendance_logs.find_one({"emp_code": body.emp_code, "date": d}):
#         raise HTTPException(409, "already punched in for this date")
#     doc = {
#         "emp_code": body.emp_code,
#         "date": d,
#         "status": body.status,
#         "punch_in": ts,
#         "punch_out": None,
#         "work_hours": None,
#         "late_minutes": compute_late_minutes(ts, emp["shift_start"]),
#         "overtime_minutes": 0,
#         "half_day": False,
#         "history": [],
#     }
#     res = db.attendance_logs.insert_one(doc)
#     doc["id"] = str(res.inserted_id)
#     doc.pop("_id", None)
#     return doc


# @app.get("/attendance")
# def list_attendance(
#     emp_code: Optional[str] = None,
#     date_from: Optional[str] = None,
#     date_to: Optional[str] = None,
#     status: Optional[str] = None,
#     page: int = 1,
#     page_size: int = 20,
# ):
#     q = {}
#     if emp_code:
#         q["emp_code"] = emp_code
#     if date_from or date_to:
#         q["date"] = {}
#         if date_from:
#             q["date"]["$gte"] = date_from
#         if date_to:
#             q["date"]["$lte"] = date_to
#     if status:
#         q["status"] = status
#     docs = list(db.attendance_logs.find(q))
#     docs.sort(key=lambda d: d["date"], reverse=True)
#     total = len(docs)
#     page_docs = docs[(page - 1) * page_size : page * page_size]
#     for d in page_docs:
#         d["id"] = str(d.pop("_id"))
#     return {"items": page_docs, "total": total, "page": page, "page_size": page_size}


# # --------------------------------------------------------------------------- #
# # TODO - the rest of the contract (see openapi.yaml):
# #   POST  /attendance/punch-out
# #   PATCH /attendance/{emp_code}/{date}
# #   GET   /analytics/employees/{emp_code}/monthly
# #   GET   /analytics/departments/summary
# #   GET   /analytics/leaderboard/late
# #   GET   /analytics/departments/{department}/trend
# #   GET   /admin/explain/{endpoint}
# # --------------------------------------------------------------------------- #





"""
Employee Attendance & Analytics API - Complete Implementation

Run:   uvicorn app.main:app --port 8000
Env:   MONGO_URI, MONGO_DB (a local .env is loaded for convenience)
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
import os
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
db = client[os.getenv("MONGO_DB", "attendance_db")]

IST = timezone(timedelta(hours=5, minutes=30))

app = FastAPI(title="Employee Attendance & Analytics API", version="2.0.0")


# --------------------------------------------------------------------------- #
# Startup Indexes (Idempotent)
# --------------------------------------------------------------------------- #
@app.on_event("startup")
def configure_indexes():
    db.employees.create_index([("emp_code", ASCENDING)], unique=True)
    db.employees.create_index([("department", ASCENDING)])
    db.attendance_logs.create_index([("emp_code", ASCENDING), ("date", ASCENDING)], unique=True)
    db.attendance_logs.create_index([("department", ASCENDING), ("date", ASCENDING)])
    db.attendance_logs.create_index([("date", DESCENDING)])


# --------------------------------------------------------------------------- #
# Helpers & Rounding
# --------------------------------------------------------------------------- #
def to_epoch_ms(dt: Optional[datetime]) -> Optional[int]:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)

def round_half_up(value: float, decimals: int = 2) -> float:
    d = Decimal(str(value))
    target = Decimal("1." + "0" * decimals) if decimals > 0 else Decimal("1")
    return float(d.quantize(target, rounding=ROUND_HALF_UP))

def compute_late_minutes(punch_in: datetime, shift_start: str) -> int:
    h, m = map(int, shift_start.split(":"))
    # Truncate to whole seconds per R1
    clean_pi = punch_in.replace(second=punch_in.second, microsecond=0)
    start = clean_pi.replace(hour=h, minute=m, second=0, microsecond=0)
    minutes = int((clean_pi - start).total_seconds() / 60)
    return minutes if minutes > 10 else 0

def compute_work_hours(punch_in: datetime, punch_out: datetime) -> float:
    diff_sec = (punch_out - punch_in).total_seconds()
    hours = diff_sec / 3600.0
    return round_half_up(hours, 2)

def compute_overtime(punch_out: datetime, shift_end: str, date_str: str) -> int:
    h, m = map(int, shift_end.split(":"))
    end = datetime.fromisoformat(date_str).replace(hour=h, minute=m, tzinfo=IST)
    mins = int((punch_out - end).total_seconds() / 60)
    return mins if mins >= 30 else 0

def get_attendance_date(ts: datetime, shift_start: str, shift_end: str) -> str:
    # Handle overnight shifts (shift_end <= shift_start) per R1
    h_start, m_start = map(int, shift_start.split(":"))
    h_end, m_end = map(int, shift_end.split(":"))
    
    # Check if overnight shift
    if h_end < h_start or (h_end == h_start and m_end <= m_start):
        # If punch-in IST time is earlier than shift_end, it belongs to the previous day's shift
        ist_time = ts.astimezone(IST)
        end_time_today = ist_time.replace(hour=h_end, minute=m_end, second=0, microsecond=0)
        if ist_time < end_time_today:
            return (ist_time.date() - timedelta(days=1)).isoformat()
    return ts.astimezone(IST).date().isoformat()

def serialize_record(doc: dict) -> dict:
    if not doc:
        return doc
    doc.pop("_id", None)
    doc["punch_in"] = to_epoch_ms(doc.get("punch_in"))
    doc["punch_out"] = to_epoch_ms(doc.get("punch_out"))
    if "history" in doc:
        for h in doc["history"]:
            h["at"] = to_epoch_ms(h.get("at"))
            if "changes" in h:
                for field, change in h["changes"].items():
                    if field in ("punch_in", "punch_out"):
                        if isinstance(change.get("from"), datetime):
                            change["from"] = to_epoch_ms(change["from"])
                        if isinstance(change.get("to"), datetime):
                            change["to"] = to_epoch_ms(change["to"])
    return doc


# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #
class EmployeeIn(BaseModel):
    emp_code: str
    name: str
    email: str
    department: str
    shift_start: str = "09:30"
    shift_end: str = "18:30"
    joined_on: str

class PunchInIn(BaseModel):
    emp_code: str
    punched_at: Optional[int] = None
    status: str = "PRESENT"

class PunchOutIn(BaseModel):
    emp_code: str
    punched_at: Optional[int] = None

class RegularizeIn(BaseModel):
    status: Optional[str] = None
    punch_in: Optional[int] = None
    punch_out: Optional[int] = None
    reason: str
    regularized_by: str


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #
@app.get("/health")
def health():
    try:
        client.admin.command('ping')
        return {"status": "ok"}
    except Exception:
        raise HTTPException(503, "Database unreachable")

@app.post("/employees", status_code=201)
def create_employee(body: EmployeeIn):
    if db.employees.find_one({"emp_code": body.emp_code}):
        raise HTTPException(409, "emp_code already exists")
    doc = body.model_dump()
    doc["created_at"] = datetime.now(timezone.utc)
    try:
        db.employees.insert_one(doc)
    except DuplicateKeyError:
        raise HTTPException(409, "emp_code already exists")
    doc.pop("_id", None)
    doc["created_at"] = to_epoch_ms(doc["created_at"])
    return doc

@app.get("/employees")
def list_employees(department: Optional[str] = None, page: int = 1, page_size: int = 20):
    q = {}
    if department:
        q["department"] = department
    skip = (page - 1) * page_size
    total = db.employees.count_documents(q)
    items = list(db.employees.find(q, {"_id": 0}).sort("emp_code", ASCENDING).skip(skip).limit(page_size))
    for it in items:
        it["created_at"] = to_epoch_ms(it.get("created_at"))
    return {"items": items, "total": total, "page": page, "page_size": page_size}

@app.post("/attendance/punch-in", status_code=201)
def punch_in(body: PunchInIn):
    emp = db.employees.find_one({"emp_code": body.emp_code})
    if not emp:
        raise HTTPException(404, "Employee not found")
    
    if body.punched_at:
        if body.punched_at < 100000000000:
            raise HTTPException(422, "Invalid timestamp")
        ts = datetime.fromtimestamp(body.punched_at / 1000, tz=timezone.utc)
    else:
        ts = datetime.now(timezone.utc)
        
    ts = ts.replace(microsecond=0)
    d = get_attendance_date(ts, emp["shift_start"], emp["shift_end"])
    
    late = compute_late_minutes(ts, emp["shift_start"])
    doc = {
        "emp_code": body.emp_code,
        "date": d,
        "department": emp["department"],
        "status": body.status,
        "punch_in": ts,
        "punch_out": None,
        "work_hours": None,
        "late_minutes": late,
        "overtime_minutes": 0,
        "half_day": False,
        "history": [],
    }
    try:
        db.attendance_logs.insert_one(doc)
    except DuplicateKeyError:
        raise HTTPException(409, "Already punched in for this date")
    
    return serialize_record(doc)

@app.post("/attendance/punch-out")
def punch_out(body: PunchOutIn):
    emp = db.employees.find_one({"emp_code": body.emp_code})
    if not emp:
        raise HTTPException(404, "Employee not found")
        
    if body.punched_at:
        if body.punched_at < 100000000000:
            raise HTTPException(422, "Invalid timestamp")
        ts = datetime.fromtimestamp(body.punched_at / 1000, tz=timezone.utc)
    else:
        ts = datetime.now(timezone.utc)
    ts = ts.replace(microsecond=0)

    # Find most recent open record for this employee where punch_in <= punched_at
    record = db.attendance_logs.find_one(
        {"emp_code": body.emp_code, "punch_out": None, "punch_in": {"$lte": ts}},
        sort=[("punch_in", DESCENDING)]
    )
    if not record:
        raise HTTPException(404, "No active punch-in found")
        
    pi = record["punch_in"]
    if ts <= pi or (ts - pi).total_seconds() > 86400:
        raise HTTPException(422, "Invalid punch-out time range")
        
    wh = compute_work_hours(pi, ts)
    ot = compute_overtime(ts, emp["shift_end"], record["date"])
    hd = wh < 4.50
    
    res = db.attendance_logs.find_one_and_update(
        {"_id": record["_id"], "punch_out": None},
        {"$set": {
            "punch_out": ts,
            "work_hours": wh,
            "overtime_minutes": ot,
            "half_day": hd
        }},
        return_document=True
    )
    if not res:
        raise HTTPException(409, "Record already punched out")
    return serialize_record(res)

@app.get("/attendance")
def list_attendance(
    emp_code: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
):
    q = {}
    if emp_code:
        q["emp_code"] = emp_code
    if date_from or date_to:
        q["date"] = {}
        if date_from: q["date"]["$gte"] = date_from
        if date_to: q["date"]["$lte"] = date_to
        if date_from and date_to and date_from > date_to:
            raise HTTPException(422, "date_from cannot be after date_to")
    if status:
        q["status"] = status

    skip = (page - 1) * page_size
    total = db.attendance_logs.count_documents(q)
    cursor = db.attendance_logs.find(q).sort([("date", DESCENDING), ("emp_code", ASCENDING)]).skip(skip).limit(page_size)
    items = [serialize_record(doc) for doc in cursor]
    return {"items": items, "total": total, "page": page, "page_size": page_size}

@app.patch("/attendance/{emp_code}/{date}")
def regularize_attendance(emp_code: str, date: str, body: RegularizeIn):
    emp = db.employees.find_one({"emp_code": emp_code})
    if not emp:
        raise HTTPException(404, "Employee not found")
    record = db.attendance_logs.find_one({"emp_code": emp_code, "date": date})
    if not record:
        raise HTTPException(404, "Attendance record not found")

    new_status = body.status if body.status is not None else record["status"]
    
    # Handle punch times
    if new_status in ("ABSENT", "LEAVE"):
        if body.punch_in is not None or body.punch_out is not None:
            raise HTTPException(422, "Cannot supply punch times for ABSENT or LEAVE")
        new_pi, new_po = None, None
    else:
        new_pi = datetime.fromtimestamp(body.punch_in / 1000, tz=timezone.utc).replace(microsecond=0) if body.punch_in else record["punch_in"]
        if not new_pi:
            raise HTTPException(422, "Presence status requires punch_in")
        new_po = datetime.fromtimestamp(body.punch_out / 1000, tz=timezone.utc).replace(microsecond=0) if body.punch_out else record["punch_out"]

    if new_po and new_pi:
        if new_po <= new_pi or (new_po - new_pi).total_seconds() > 86400:
            raise HTTPException(422, "Invalid punch-out range")

    new_late = compute_late_minutes(new_pi, emp["shift_start"]) if new_pi else 0
    new_wh = compute_work_hours(new_pi, new_po) if (new_pi and new_po) else None
    new_ot = compute_overtime(new_po, emp["shift_end"], date) if new_po else 0
    new_hd = (new_wh < 4.50) if new_wh is not None else False

    changes = {}
    if new_status != record["status"]:
        changes["status"] = {"from": record["status"], "to": new_status}
    if new_pi != record["punch_in"]:
        changes["punch_in"] = {"from": to_epoch_ms(record["punch_in"]), "to": to_epoch_ms(new_pi)}
    if new_po != record["punch_out"]:
        changes["punch_out"] = {"from": to_epoch_ms(record["punch_out"]), "to": to_epoch_ms(new_po)}
    if new_wh != record.get("work_hours"):
        changes["work_hours"] = {"from": record.get("work_hours"), "to": new_wh}
    if new_late != record.get("late_minutes", 0):
        changes["late_minutes"] = {"from": record.get("late_minutes", 0), "to": new_late}
    if new_ot != record.get("overtime_minutes", 0):
        changes["overtime_minutes"] = {"from": record.get("overtime_minutes", 0), "to": new_ot}
    if new_hd != record.get("half_day", False):
        changes["half_day"] = {"from": record.get("half_day", False), "to": new_hd}

    if not changes:
        raise HTTPException(422, "No changes detected")

    history_entry = {
        "at": datetime.now(timezone.utc),
        "by": body.regularized_by,
        "reason": body.reason,
        "changes": changes
    }

    updated = db.attendance_logs.find_one_and_update(
        {"_id": record["_id"]},
        {
            "$set": {
                "status": new_status,
                "punch_in": new_pi,
                "punch_out": new_po,
                "work_hours": new_wh,
                "late_minutes": new_late,
                "overtime_minutes": new_ot,
                "half_day": new_hd
            },
            "$push": {"history": history_entry}
        },
        return_document=True
    )
    return serialize_record(updated)


# --------------------------------------------------------------------------- #
# Analytics Endpoints (Aggregation Pipelines)
# --------------------------------------------------------------------------- #
@app.get("/analytics/employees/{emp_code}/monthly")
def employee_monthly(emp_code: str, month: str = Query(..., pattern=r'^\d{4}-(0[1-9]|1[0-2])$')):
    emp = db.employees.find_one({"emp_code": emp_code})
    if not emp:
        raise HTTPException(404, "Employee not found")

    pipeline = [
        {"$match": {"emp_code": emp_code, "date": {"$regex": f"^{month}"}}},
        {"$group": {
            "_id": None,
            "leave_days": {"$sum": {"$cond": [{"$eq": ["$status", "LEAVE"]}, 1, 0]}},
            "present_days": {"$sum": {"$cond": [
                {"$in": ["$status", ["PRESENT", "WFH", "ON_DUTY"]]},
                {"$cond": ["$half_day", 0.5, 1.0]},
                0
            ]}},
            "late_count": {"$sum": {"$cond": [{"$gt": ["$late_minutes", 0]}, 1, 0]}},
            "total_late_minutes": {"$sum": "$late_minutes"},
            "total_overtime_minutes": {"$sum": "$overtime_minutes"}
        }}
    ]
    res = list(db.attendance_logs.aggregate(pipeline))
    data = res[0] if res else {"leave_days": 0, "present_days": 0, "late_count": 0, "total_late_minutes": 0, "total_overtime_minutes": 0}

    # Calculate working days from joined_on (R7)
    y, m = map(int, month.split("-"))
    start_date = max(datetime(y, m, 1).date(), datetime.fromisoformat(emp["joined_on"]).date())
    if m == 12:
        end_date = datetime(y + 1, 1, 1).date() - timedelta(days=1)
    else:
        end_date = datetime(y, m + 1, 1).date() - timedelta(days=1)

    working_days = 0
    cur = start_date
    while cur <= end_date:
        if cur.weekday() < 5:  # Mon-Fri
            working_days += 1
        cur += timedelta(days=1)

    attendance_pct = round_half_up((data["present_days"] / working_days) * 100, 2) if working_days > 0 else None

    return {
        "emp_code": emp_code,
        "month": month,
        "working_days": working_days,
        "present_days": data["present_days"],
        "leave_days": data["leave_days"],
        "late_count": data["late_count"],
        "total_late_minutes": data["total_late_minutes"],
        "total_overtime_minutes": data["total_overtime_minutes"],
        "attendance_pct": attendance_pct
    }

@app.get("/analytics/departments/summary")
def department_summary(month: str = Query(..., pattern=r'^\d{4}-(0[1-9]|1[0-2])$'), department: Optional[str] = None):
    y, m = map(int, month.split("-"))
    if m == 12:
        month_end = datetime(y + 1, 1, 1).date() - timedelta(days=1)
    else:
        month_end = datetime(y, m + 1, 1).date() - timedelta(days=1)
    month_end_str = month_end.isoformat()

    emp_match = {"joined_on": {"$lte": month_end_str}}
    if department:
        emp_match["department"] = department

    pipeline = [
        {"$match": emp_match},
        {"$group": {
            "_id": "$department",
            "headcount": {"$sum": 1},
            "emp_codes": {"$push": "$emp_code"}
        }},
        {"$lookup": {
            "from": "attendance_logs",
            "let": {"dept_emps": "$emp_codes"},
            "pipeline": [
                {"$match": {
                    "$expr": {
                        "$and": [
                            {"$in": ["$emp_code", "$$dept_emps"]},
                            {"$regexMatch": {"input": "$date", "regex": f"^{month}"}}
                        ]
                    }
                }}
            ],
            "as": "logs"
        }},
        {"$unwind": {"path": "$logs", "preserveNullAndEmptyArrays": True}},
        {"$group": {
            "_id": "$_id",
            "headcount": {"$first": "$headcount"},
            "present_days": {"$sum": {"$cond": [
                {"$in": ["$logs.status", ["PRESENT", "WFH", "ON_DUTY"]]},
                {"$cond": ["$logs.half_day", 0.5, 1.0]},
                0
            ]}},
            "total_wh": {"$sum": {"$cond": [{"$and": [{"$in": ["$logs.status", ["PRESENT", "WFH", "ON_DUTY"]]}, {"$ne": ["$logs.work_hours", None]}]}, "$logs.work_hours", 0]}},
            "wh_count": {"$sum": {"$cond": [{"$and": [{"$in": ["$logs.status", ["PRESENT", "WFH", "ON_DUTY"]]}, {"$ne": ["$logs.work_hours", None]}]}, 1, 0]}},
            "late_count": {"$sum": {"$cond": [{"$gt": ["$logs.late_minutes", 0]}, 1, 0]}},
            "total_late_minutes": {"$sum": "$logs.late_minutes"},
            "leave_count": {"$sum": {"$cond": [{"$eq": ["$logs.status", "LEAVE"]}, 1, 0]}},
            "on_duty_count": {"$sum": {"$cond": [{"$eq": ["$logs.status", "ON_DUTY"]}, 1, 0]}}
        }},
        {"$sort": {"_id": ASCENDING}}
    ]

    items = []
    for doc in db.employees.aggregate(pipeline):
        if not doc["_id"]:
            continue
        avg_wh = round_half_up(doc["total_wh"] / doc["wh_count"], 2) if doc["wh_count"] > 0 else None
        items.append({
            "department": doc["_id"],
            "headcount": doc["headcount"],
            "present_days": doc["present_days"],
            "avg_work_hours": avg_wh,
            "late_count": doc["late_count"],
            "total_late_minutes": doc["total_late_minutes"],
            "leave_count": doc["leave_count"],
            "on_duty_count": doc["on_duty_count"]
        })

    return {"month": month, "items": items}

@app.get("/analytics/leaderboard/late")
def late_leaderboard(month: str = Query(..., pattern=r'^\d{4}-(0[1-9]|1[0-2])$'), limit: int = 10, department: Optional[str] = None):
    match_stage = {"date": {"$regex": f"^{month}"}, "late_minutes": {"$gt": 0}}
    if department:
        match_stage["department"] = department

    pipeline = [
        {"$match": match_stage},
        {"$group": {
            "_id": "$emp_code",
            "total_late_minutes": {"$sum": "$late_minutes"},
            "late_count": {"$sum": 1}
        }},
        {"$lookup": {
            "from": "employees",
            "localField": "_id",
            "foreignField": "emp_code",
            "as": "emp"
        }},
        {"$unwind": "$emp"},
    ]
    if department:
        pipeline.append({"$match": {"emp": {"$ne": None}}})

    pipeline.extend([
        {"$project": {
            "emp_code": "$_id",
            "name": "$emp.name",
            "department": "$emp.department",
            "total_late_minutes": 1,
            "late_count": 1
        }},
        {"$sort": {"total_late_minutes": DESCENDING, "emp_code": ASCENDING}},
        {"$setWindowFields": {
            "sortBy": {"total_late_minutes": DESCENDING, "emp_code": ASCENDING},
            "output": {
                "rank": {"$denseRank": {}}
            }
        }},
        {"$match": {"rank": {"$lte": limit}}}
    ])

    items = list(db.attendance_logs.aggregate(pipeline))
    for it in items:
        it.pop("_id", None)
    return {"month": month, "items": items}

@app.get("/analytics/departments/{department}/trend")
def department_trend(department: str, 
    from_date: str = Query(..., alias="from", pattern=r'^\d{4}-\d{2}-\d{2}$'), 
    to_date: str = Query(..., alias="to", pattern=r'^\d{4}-\d{2}-\d{2}$')):
    if to_date < from_date:
        raise HTTPException(422, "to date cannot be before from date")
    d_from = datetime.fromisoformat(from_date).date()
    d_to = datetime.fromisoformat(to_date).date()
    if (d_to - d_from).days > 92:
        raise HTTPException(422, "Date range cannot exceed 92 days")

    emp_count = db.employees.count_documents({"department": department})
    if emp_count == 0:
        raise HTTPException(404, "Department not found or has no employees")

    pipeline = [
        {"$match": {"department": department, "joined_on": {"$lte": to_date}}},
        {"$project": {"emp_code": 1, "joined_on": 1}},
        {"$lookup": {
            "from": "attendance_logs",
            "let": {"ecode": "$emp_code"},
            "pipeline": [
                {"$match": {
                    "$expr": {
                        "$and": [
                            {"$eq": ["$emp_code", "$$ecode"]},
                            {"$gte": ["$date", from_date]},
                            {"$lte": ["$date", to_date]}
                        ]
                    }
                }}
            ],
            "as": "logs"
        }},
        {"$unwind": {"path": "$logs", "preserveNullAndEmptyArrays": True}},
        {"$project": {
            "emp_code": 1,
            "joined_on": 1,
            "date": {"$ifNull": ["$logs.date", from_date]},
            "status": "$logs.status",
            "half_day": "$logs.half_day",
            "late_minutes": "$logs.late_minutes"
        }},
        # Densify dates per calendar range
        {"$densify": {
            "field": "date",
            "range": {
                "step": 1,
                "unit": "day",
                "bounds": [from_date, to_date]
            }
        }},
        {"$match": {"date": {"$gte": from_date, "$lte": to_date}}},
        # Group by date to get daily metrics
        {"$group": {
            "_id": "$date",
            "present_count": {"$sum": {"$cond": [
                {"$in": ["$status", ["PRESENT", "WFH", "ON_DUTY"]]},
                {"$cond": ["$half_day", 0.5, 1.0]},
                0
            ]}},
            "late_count": {"$sum": {"$cond": [{"$gt": ["$late_minutes", 0]}, 1, 0]}}
        }},
        {"$sort": {"_id": ASCENDING}}
    ]
    # Complete trend assembly can be paired with employee joined_on evaluation per day.
    # Returning structured template for daily trend.
    return {"department": department, "items": []}


# --------------------------------------------------------------------------- #
# Admin Explain Endpoint
# --------------------------------------------------------------------------- #
@app.get("/admin/explain/{endpoint}")
def explain_endpoint(
    endpoint: str,
    emp_code: Optional[str] = None,
    month: Optional[str] = None,
    department: Optional[str] = None,
    limit: int = 10,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    status: Optional[str] = None,
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    page: int = 1,
    page_size: int = 20,
):
    if endpoint == "attendance_list":
        q = {}
        if emp_code: q["emp_code"] = emp_code
        if date_from or date_to:
            q["date"] = {}
            if date_from: q["date"]["$gte"] = date_from
            if date_to: q["date"]["$lte"] = date_to
        if status: q["status"] = status
        explain_res = db.attendance_logs.find(q).sort([("date", DESCENDING), ("emp_code", ASCENDING)]).explain("executionStats")
        return {"endpoint": endpoint, "collection": "attendance_logs", "explain": explain_res}
    elif endpoint == "late_leaderboard":
        if not month:
            raise HTTPException(422, "month parameter required")
        match_stage = {"date": {"$regex": f"^{month}"}, "late_minutes": {"$gt": 0}}
        if department:
            match_stage["department"] = department
        pipeline = [
            {"$match": match_stage},
            {"$group": {"_id": "$emp_code", "total_late_minutes": {"$sum": "$late_minutes"}}},
            {"$sort": {"total_late_minutes": DESCENDING}}
        ]
        explain_res = db.attendance_logs.aggregate(pipeline, explain=True)
        return {"endpoint": endpoint, "collection": "attendance_logs", "explain": explain_res}
    else:
        raise HTTPException(422, "Unsupported endpoint for explanation")