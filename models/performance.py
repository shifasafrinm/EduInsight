from database import db


class Performance(db.Model):
    __tablename__ = "performances"

    id = db.Column(db.Integer, primary_key=True)

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("students.id"),
        nullable=False
    )

    subject_id = db.Column(
        db.Integer,
        db.ForeignKey("subjects.id"),
        nullable=False
    )

    exam = db.Column(db.String(50), nullable=False)

    marks = db.Column(db.Float, nullable=False)

    attendance = db.Column(db.Float, nullable=False)

    student = db.relationship("Student", backref="performances")
    subject = db.relationship("Subject", backref="performances")

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "subject_id": self.subject_id,
            "exam": self.exam,
            "marks": self.marks,
            "attendance": self.attendance
        }