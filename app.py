import os
import smtplib
from email.message import EmailMessage
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

from config import Config
from database import db
from models.student import Student
from models.user import User
from routes.student_routes import import_csv_stream, student_bp
from services.auth_service import admin_required, login_required
from services.performance_service import dashboard_summary, predict_grade


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config: app.config.update(test_config)
    db.init_app(app)
    CORS(app, supports_credentials=True)
    app.register_blueprint(student_bp, url_prefix="/api/students")

    @app.get("/")
    def dashboard_page():
        if not session.get("user_id") and not session.get("student_id"):
            return redirect(url_for("login_page"))
        return render_template("dashboard.html")

    @app.get("/login")
    def login_page():
        if session.get("user_id") or session.get("student_id"):
            return redirect(url_for("dashboard_page"))
        return render_template("login.html")

    @app.post("/api/auth/login")
    def login():
        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").lower().strip()
        password = (data.get("password") or "").strip()
        mode = data.get("mode", "admin")
        session.clear()
        session.permanent = bool(data.get("remember"))
        if mode == "student":
            student = Student.query.filter(db.func.lower(Student.email) == email).first()
            if not student or password.lower() != (student.external_id or "").lower():
                return jsonify({"error": "Student email or student ID is incorrect."}), 401
            session["student_id"] = student.id
            return jsonify({"user": {"name": student.name, "email": student.email, "role": "student", "student_id": student.id}})
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            return jsonify({"error": "Email or password is incorrect."}), 401
        session["user_id"] = user.id
        return jsonify({"user": {**user.to_dict(), "role": "admin"}})

    @app.post("/api/auth/logout")
    def logout():
        session.clear(); return jsonify({"message": "Signed out."})

    @app.get("/api/auth/me")
    @login_required
    def me():
        if session.get("student_id"):
            student = db.session.get(Student, session["student_id"])
            return jsonify({"user": {"name": student.name, "email": student.email, "role": "student", "student_id": student.id}})
        user = db.session.get(User, session["user_id"])
        return jsonify({"user": {**user.to_dict(), "role": "admin"}})

    @app.get("/api/dashboard")
    @login_required
    def dashboard_data():
        students = [db.session.get(Student, session["student_id"])] if session.get("student_id") else Student.query.all()
        return jsonify(dashboard_summary(students))

    @app.post("/api/predict")
    @login_required
    def predict():
        data = request.get_json(silent=True) or {}
        requested_id = int(data.get("student_id") or 0)
        if session.get("student_id") and requested_id != session["student_id"]:
            return jsonify({"error": "You can only run scenarios for your own profile."}), 403
        student = Student.query.get_or_404(requested_id)
        prediction = predict_grade(student, data.get("attendance"), data.get("study_hours"))
        return jsonify({"prediction": prediction, "baseline": predict_grade(student), "current": student.final_grade, "student": student.name})

    @app.get("/api/email/status")
    @admin_required
    def email_status():
        return jsonify({"configured": bool(app.config["GMAIL_ADDRESS"] and app.config["GMAIL_APP_PASSWORD"]), "sender": app.config["GMAIL_ADDRESS"] or "Not connected"})

    @app.post("/api/email/send")
    @admin_required
    def send_email():
        data = request.get_json(silent=True) or {}
        student = Student.query.get_or_404(data.get("student_id"))
        if not app.config["GMAIL_ADDRESS"] or not app.config["GMAIL_APP_PASSWORD"]:
            return jsonify({"error": "Gmail is not connected yet. Add GMAIL_ADDRESS and GMAIL_APP_PASSWORD to your .env file."}), 503
        message = EmailMessage()
        message["From"] = f'{app.config["GMAIL_FROM_NAME"]} <{app.config["GMAIL_ADDRESS"]}>'
        message["To"] = data.get("to") or student.email
        message["Subject"] = data.get("subject") or "Your EduInsight performance update"
        message.set_content(data.get("message") or "Your latest performance update is ready.")
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as smtp:
                smtp.login(app.config["GMAIL_ADDRESS"], app.config["GMAIL_APP_PASSWORD"])
                smtp.send_message(message)
        except (smtplib.SMTPException, OSError):
            return jsonify({"error": "Gmail could not send the message. Check the address and app password."}), 502
        return jsonify({"message": f"Email sent to {message['To']}."})

    @app.errorhandler(404)
    def not_found(_): return jsonify({"error": "Not found."}), 404

    with app.app_context():
        os.makedirs(os.path.join(app.root_path, "database"), exist_ok=True)
        db.create_all()
        if not User.query.first():
            admin = User(name="EduInsight Admin", email=os.getenv("ADMIN_EMAIL", "admin@eduinsight.app").lower(), role="admin")
            admin_password = os.getenv("ADMIN_PASSWORD")
            if not admin_password: raise RuntimeError("Set ADMIN_PASSWORD before first launch.")
            admin.set_password(admin_password)
            db.session.add(admin); db.session.commit()
        seed_path = os.path.join(app.root_path, "data", "student_performance_updated_1000.csv")
        if Student.query.count() == 0 and os.path.exists(seed_path):
            with open(seed_path, "rb") as seed_file: import_csv_stream(seed_file)
    return app


app = create_app()
if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "false").lower() == "true", port=int(os.getenv("PORT", 5000)))
