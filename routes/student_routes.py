import csv
import io
import re
from flask import Blueprint, jsonify, request, session
from database import db
from models.student import Student
from services.auth_service import admin_required, login_required
from services.performance_service import student_insights

student_bp = Blueprint("student_bp", __name__)


def _number(value, default=0):
    try:
        return float(value) if value not in (None, "") else default
    except (TypeError, ValueError):
        return default


def _boolean(value):
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _email_for(name, external_id):
    slug = re.sub(r"[^a-z0-9]+", ".", (name or "student").lower()).strip(".")
    return f"{slug}.{external_id or 'new'}@student.edu"


def student_from_csv(row, fallback_id):
    raw_id = row.get("StudentID")
    external_id = str(raw_id).replace(".0", "") if raw_id not in (None, "") else f"CSV-{fallback_id}"
    name = (row.get("Name") or f"Student {external_id}").strip()
    return {
        "external_id": external_id, "name": name, "email": _email_for(name, external_id),
        "gender": (row.get("Gender") or "Not specified").strip(),
        "attendance_rate": _number(row.get("AttendanceRate")),
        "study_hours_per_week": _number(row.get("StudyHoursPerWeek")),
        "previous_grade": _number(row.get("PreviousGrade")),
        "extracurricular_activities": _number(row.get("ExtracurricularActivities")),
        "parental_support": (row.get("ParentalSupport") or "Medium").strip(),
        "final_grade": _number(row.get("FinalGrade")),
        "daily_study_hours": _number(row.get("Study Hours")),
        "secondary_attendance": _number(row.get("Attendance (%)")),
        "online_classes_taken": _boolean(row.get("Online Classes Taken")),
    }


def import_csv_stream(stream):
    text = io.TextIOWrapper(stream, encoding="utf-8-sig") if hasattr(stream, "read") else stream
    reader = csv.DictReader(text)
    if not reader.fieldnames or "Name" not in reader.fieldnames:
        raise ValueError("CSV must include at least a Name column.")
    created = updated = 0
    seen_ids = set()
    for index, row in enumerate(reader, start=1):
        values = student_from_csv(row, index)
        if values["external_id"] in seen_ids:
            values["external_id"] = f"{values['external_id']}-{index}"
            values["email"] = _email_for(values["name"], values["external_id"])
        seen_ids.add(values["external_id"])
        student = Student.query.filter_by(external_id=values["external_id"]).first()
        if student:
            for key, value in values.items():
                if key != "email" or not student.email:
                    setattr(student, key, value)
            updated += 1
        else:
            email = values["email"]
            while Student.query.filter_by(email=email).first():
                email = f"{values['external_id']}.{email}"
            values["email"] = email
            db.session.add(Student(**values))
            created += 1
    db.session.commit()
    return created, updated


@student_bp.get("/")
@login_required
def list_students():
    query = Student.query.filter_by(id=session["student_id"]) if session.get("student_id") else Student.query
    search = request.args.get("q", "").strip()
    risk = request.args.get("risk", "all")
    sort = request.args.get("sort", "name")
    page = max(int(request.args.get("page", 1)), 1)
    per_page = min(max(int(request.args.get("per_page", 12)), 1), 100)
    if search:
        query = query.filter(db.or_(Student.name.ilike(f"%{search}%"), Student.email.ilike(f"%{search}%")))
    if risk == "high": query = query.filter(db.or_(Student.final_grade < 60, Student.attendance_rate < 70))
    elif risk == "watch": query = query.filter(Student.final_grade >= 60, Student.final_grade < 75)
    elif risk == "strong": query = query.filter(Student.final_grade >= 75)
    ordering = {"grade_desc": Student.final_grade.desc(), "grade_asc": Student.final_grade.asc(), "attendance": Student.attendance_rate.desc(), "name": Student.name.asc()}.get(sort, Student.name.asc())
    pagination = query.order_by(ordering).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({"items": [student_insights(s) for s in pagination.items], "total": pagination.total, "pages": pagination.pages, "page": pagination.page})


@student_bp.get("/<int:student_id>")
@login_required
def get_student(student_id):
    if session.get("student_id") and student_id != session["student_id"]:
        return jsonify({"error": "You can only view your own profile."}), 403
    return jsonify(student_insights(Student.query.get_or_404(student_id), detailed=True))


@student_bp.post("/")
@admin_required
def add_student():
    data = request.get_json(silent=True) or {}
    if not data.get("name"): return jsonify({"error": "Student name is required."}), 400
    external_id = str(data.get("external_id") or f"NEW-{Student.query.count() + 1}")
    if Student.query.filter_by(external_id=external_id).first(): return jsonify({"error": "That student ID already exists."}), 409
    student = Student(external_id=external_id, name=data["name"].strip(), email=(data.get("email") or _email_for(data["name"], external_id)).lower(), gender=data.get("gender", "Not specified"), attendance_rate=_number(data.get("attendance_rate")), study_hours_per_week=_number(data.get("study_hours_per_week")), previous_grade=_number(data.get("previous_grade")), extracurricular_activities=_number(data.get("extracurricular_activities")), parental_support=data.get("parental_support", "Medium"), final_grade=_number(data.get("final_grade")), daily_study_hours=_number(data.get("daily_study_hours")), secondary_attendance=_number(data.get("secondary_attendance")), online_classes_taken=_boolean(data.get("online_classes_taken")))
    db.session.add(student); db.session.commit()
    return jsonify(student_insights(student)), 201


@student_bp.put("/<int:student_id>")
@admin_required
def update_student(student_id):
    student = Student.query.get_or_404(student_id); data = request.get_json(silent=True) or {}
    numeric = {"attendance_rate", "study_hours_per_week", "previous_grade", "extracurricular_activities", "final_grade", "daily_study_hours", "secondary_attendance"}
    allowed = numeric | {"name", "email", "gender", "parental_support", "online_classes_taken"}
    for key in allowed:
        if key in data:
            value = _number(data[key]) if key in numeric else data[key]
            if key == "online_classes_taken": value = _boolean(value)
            setattr(student, key, value)
    db.session.commit(); return jsonify(student_insights(student))


@student_bp.post("/import")
@admin_required
def import_students():
    upload = request.files.get("file")
    if not upload or not upload.filename.lower().endswith(".csv"): return jsonify({"error": "Choose a CSV file to import."}), 400
    try: created, updated = import_csv_stream(upload.stream)
    except (ValueError, UnicodeDecodeError) as exc: return jsonify({"error": str(exc)}), 400
    return jsonify({"message": f"Import complete: {created} added, {updated} updated.", "created": created, "updated": updated})





