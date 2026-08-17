import argparse
import getpass
import os
from app import app
from database import db
from models.user import User


def reset_password(email):
    with app.app_context():
        user = User.query.filter_by(email=email.lower()).first()
        if not user:
            raise SystemExit(f"No user found for {email}")
        password = getpass.getpass("New password: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            raise SystemExit("Passwords do not match.")
        if len(password) < 12:
            raise SystemExit("Use at least 12 characters.")
        user.set_password(password)
        db.session.commit()
        print("Admin password updated.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EduInsight administration")
    parser.add_argument("command", choices=["reset-password"])
    parser.add_argument("--email", default=os.getenv("ADMIN_EMAIL", "admin@eduinsight.app"))
    args = parser.parse_args()
    if args.command == "reset-password":
        reset_password(args.email)
