from datetime import datetime
from database import db


class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    external_id = db.Column(db.String(50), unique=True, index=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    email = db.Column(db.String(180), unique=True, index=True)
    gender = db.Column(db.String(30), default="Not specified")
    attendance_rate = db.Column(db.Float, default=0)
    study_hours_per_week = db.Column(db.Float, default=0)
    previous_grade = db.Column(db.Float, default=0)
    extracurricular_activities = db.Column(db.Float, default=0)
    parental_support = db.Column(db.String(20), default="Medium")
    final_grade = db.Column(db.Float, default=0)
    daily_study_hours = db.Column(db.Float, default=0)
    secondary_attendance = db.Column(db.Float, default=0)
    online_classes_taken = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "external_id": self.external_id, "name": self.name,
            "email": self.email, "gender": self.gender,
            "attendance_rate": round(self.attendance_rate or 0, 1),
            "study_hours_per_week": round(self.study_hours_per_week or 0, 1),
            "previous_grade": round(self.previous_grade or 0, 1),
            "extracurricular_activities": round(self.extracurricular_activities or 0, 1),
            "parental_support": self.parental_support,
            "final_grade": round(self.final_grade or 0, 1),
            "daily_study_hours": round(self.daily_study_hours or 0, 1),
            "secondary_attendance": round(self.secondary_attendance or 0, 1),
            "online_classes_taken": bool(self.online_classes_taken),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
