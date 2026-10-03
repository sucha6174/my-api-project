import os
import unittest
import uuid
import httpx


class TestAPIIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base_url = os.environ.get("API_BASE_URL", "http://localhost:8000").rstrip("/")

    def test_health_endpoint(self):
        url = f"{self.base_url}/health"
        response = httpx.get(url, timeout=10.0)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "healthy"})

    def test_greet_endpoint(self):
        url = f"{self.base_url}/greet/World"
        response = httpx.get(url, timeout=10.0)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Hello, World!"})

    def test_create_message_success(self):
        url = f"{self.base_url}/message"
        payload = {"text": "Integration test live message payload"}
        response = httpx.post(url, json=payload, timeout=10.0)

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["text"], "Integration test live message payload")
        self.assertIn("id", data)

        # Validate that the returned ID is a valid UUID
        try:
            parsed_uuid = uuid.UUID(data["id"])
            self.assertEqual(str(parsed_uuid), data["id"])
        except ValueError:
            self.fail(f"Returned ID '{data['id']}' is not a valid UUID string.")

    def test_create_message_validation_failure(self):
        url = f"{self.base_url}/message"

        # Case 1: Empty string (violates min_length=1)
        res_empty = httpx.post(url, json={"text": ""}, timeout=10.0)
        self.assertEqual(res_empty.status_code, 400)
        self.assertEqual(res_empty.json()["error"], "Bad Request")

        # Case 2: String exceeding 255 characters
        res_long = httpx.post(url, json={"text": "A" * 256}, timeout=10.0)
        self.assertEqual(res_long.status_code, 400)
        self.assertEqual(res_long.json()["error"], "Bad Request")

        # Case 3: Missing text key
        res_missing = httpx.post(url, json={}, timeout=10.0)
        self.assertEqual(res_missing.status_code, 400)
        self.assertEqual(res_missing.json()["error"], "Bad Request")


if __name__ == "__main__":
    unittest.main()
