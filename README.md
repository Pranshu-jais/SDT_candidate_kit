# Employee Attendance & Analytics API

Backend service built with Python, FastAPI, and MongoDB for the HROne Software Engineer Trainee technical assignment.


## Local setup
```bash
1. cd candidate_kit
2. **Initialize Environment**: `python -m venv .venv && .venv\Scripts\activate` (Use `source .venv/bin/activate` on Linux/macOS)
3. **Install Dependencies**: `pip install -r requirements.txt`
4. **Configure Environment**: `copy .env.example .env` and set `MONGO_URI=mongodb://localhost:27017` and `MONGO_DB=attendance_db`
5. **Seed Database**: `python sample_seed.py`
6. **Run Application**: `uvicorn app.main:app --port 8000 --reload`

```
- Use the interactive Swagger documentation at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) to test  endpoints with correct parameters and formats.

MongoDB **6.0 or newer** is required (the grader uses 7.0). MongoDB Atlas free tier (M0) works.
