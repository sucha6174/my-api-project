import unittest
from unittest.mock import MagicMock
import uuid
from fastapi.testclient import TestClient

from src.app import app, get_db


class TestAPIUnitLogic(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.mock_db = MagicMock()
        # Mock database session to isolate unit tests from external dependencies
        app.dependency_overrides[get_db] = lambda: self.mock_db

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "healthy"})

    def test_greet_endpoint(self):
        response = self.client.get("/greet/Alice")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Hello, Alice!"})

    def test_create_message_success(self):
        test_uuid = uuid.UUID("a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d")

        def mock_refresh(instance):
            instance.id = test_uuid

        self.mock_db.add = MagicMock()
        self.mock_db.commit = MagicMock()
        self.mock_db.refresh = MagicMock(side_effect=mock_refresh)

        payload = {"text": "Hello, Unit Testing World!"}
        response = self.client.post("/message", json=payload)

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["text"], "Hello, Unit Testing World!")
        self.assertEqual(data["id"], str(test_uuid))

        self.mock_db.add.assert_called_once()
        self.mock_db.commit.assert_called_once()
        self.mock_db.refresh.assert_called_once()

    def test_create_message_invalid_empty(self):
        payload = {"text": ""}
        response = self.client.post("/message", json=payload)
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["error"], "Bad Request")
        self.assertEqual(data["message"], "Invalid input data provided.")
        self.assertIn("details", data)

    def test_create_message_invalid_too_long(self):
        payload = {"text": "x" * 256}
        response = self.client.post("/message", json=payload)
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["error"], "Bad Request")
        self.assertEqual(data["message"], "Invalid input data provided.")

    def test_create_message_missing_text(self):
        payload = {}
        response = self.client.post("/message", json=payload)
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["error"], "Bad Request")
        self.assertEqual(data["message"], "Invalid input data provided.")

    def test_create_message_invalid_type(self):
        payload = {"text": 12345}
        response = self.client.post("/message", json=payload)
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["error"], "Bad Request")


if __name__ == "__main__":
    unittest.main()
