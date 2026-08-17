import unittest
from app import app
from models.student import Student
from services.performance_service import student_insights


class EduInsightTests(unittest.TestCase):
    def test_protected_api_requires_login(self):
        client = app.test_client()
        self.assertEqual(client.get("/api/dashboard").status_code, 401)

    def test_dataset_is_loaded(self):
        with app.app_context():
            self.assertEqual(Student.query.count(), 1000)
            self.assertTrue(all(student_insights(s)["recommendations"] for s in Student.query.limit(50)))


if __name__ == "__main__":
    unittest.main()
