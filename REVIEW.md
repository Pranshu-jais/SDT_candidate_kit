# REVIEW.md

List every defect you found in the starter `app/main.py` (helpers and endpoints). For each one:


| # | Where (function / line) | What is wrong | How you'd notice it (test, input, or symptom) | How you fixed it |
|---|---|---|---|---|
| 1 | `list_employees` | **Pagination Offset Bug**: Uses `skip = page * page_size`, skipping the first page entirely on `page=1` (skips 20 items). | Requesting `page=1` omits the first 20 employees. | Changed offset calculation to `skip = (page - 1) * page_size`. |
| 2 | `list_employees` | **Incorrect Total Count**: `db.employees.count_documents({})` ignores the department query filter. | Filtered department requests return a total count representing the entire collection. | Updated count to accept query filters: `db.employees.count_documents(q)`. |
| 3 | `punch_in` | **Missing 404 Handling**: Unknown `emp_code` lookups return `None`, throwing an unhandled `TypeError` (HTTP 500)[cite: 3]. | Passing a non-existent employee code returns a 500 server error instead of a 404[cite: 3]. | Added an explicit check: `if not emp: raise HTTPException(404, "Employee not found")`[cite: 3]. |
| 4 | `punch_in` | **Race Condition Vulnerability**: Uses a non-atomic check-then-insert (`find_one` followed by `insert_one`)[cite: 3]. | Concurrent duplicate punch-ins insert multiple records, violating uniqueness[cite: 3]. | Created a unique compound index on `(emp_code, date)` and caught `DuplicateKeyError` to return a `409 Conflict`[cite: 3]. |
| 5 | `list_attendance` | **Memory Inefficiency**: Loads matching documents into Python memory (`list(...)`), sorting and slicing in-Python[cite: 3]. | Will cause high memory consumption and poor performance on ~100k records[cite: 3]. | Pushed sorting (`.sort()`), skipping (`.skip()`), and limiting (`.limit()`) down to MongoDB[cite: 3]. |
| 6 | API Responses | **Epoch Milliseconds Mismatch**: Returns raw Python `datetime` objects instead of required integer epoch milliseconds[cite: 3]. | API responses output ISO strings/datetimes instead of epoch milliseconds (`EpochMillis`)[cite: 3]. | Implemented a serialization helper `to_epoch_ms()` to convert datetimes at the boundary[cite: 3]. |
| 7 | `compute_work_hours` | **Incorrect Rounding Method**: Uses Python's built-in `round()` (banker's rounding) instead of required half-up rounding[cite: 3]. | Work hours ending in `.xx5` round to the nearest even number instead of half-up per rule R4[cite: 3]. | Used Python's `decimal` module with `ROUND_HALF_UP`[cite: 3]. |

Also note anything you looked at and decided was **not** a defect, and why:
* **`GET /health` endpoint**: Correctly pings the database connection and yields a proper `200 OK` or `503 Service Unavailable` response per the openapi contract[cite: 3].
* **`IST` Timezone Definition**: Properly initialized using `timezone(timedelta(hours=5, minutes=30))` which accurately models Indian Standard Time (UTC+05:30) required by rule R1[cite: 3].
* **`EmployeeIn` Pydantic Model**: Default shift timings (`09:30` to `18:30`) align cleanly with the conventions defined in `DATA_MODEL.md`[cite: 2].
