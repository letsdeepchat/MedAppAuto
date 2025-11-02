"""
Test cases for API endpoints
Tests FastAPI endpoints for chat, booking, authentication, and FAQ
"""

import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient
from backend.main import app
import json


class TestAPIEndpoints:
    """Test suite for API endpoints"""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app"""
        return TestClient(app)

    @pytest.fixture
    async def async_client(self):
        """Create an async test client"""
        async with AsyncClient(app=app, base_url="http://testserver") as client:
            yield client

    def test_root_endpoint(self, client):
        """Test the root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "Medical Appointment Scheduling Agent API" in data["message"]
        assert data["status"] == "healthy"

    def test_chat_endpoint_success(self, client):
        """Test successful chat endpoint"""
        payload = {
            "message": "Hello",
            "context": {"current_context": "greeting"}
        }

        response = client.post("/api/chat", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert "response" in data
        assert "context" in data
        assert "intent" in data
        assert isinstance(data["response"], str)
        assert len(data["response"]) > 0

    def test_chat_endpoint_with_context(self, client):
        """Test chat endpoint with context preservation"""
        payload = {
            "message": "I want to book an appointment",
            "context": {"current_context": "greeting"}
        }

        response = client.post("/api/chat", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["intent"] == "booking_request"
        assert data["context"]["current_context"] == "understanding_needs"

    def test_chat_endpoint_empty_message(self, client):
        """Test chat endpoint with empty message"""
        payload = {"message": ""}

        response = client.post("/api/chat", json=payload)
        assert response.status_code == 200  # Should handle gracefully

        data = response.json()
        assert "response" in data

    def test_chat_endpoint_invalid_json(self, client):
        """Test chat endpoint with invalid JSON"""
        response = client.post("/api/chat", data="invalid json")
        assert response.status_code == 422  # Validation error

    def test_faq_endpoint_success(self, client):
        """Test successful FAQ endpoint"""
        payload = {"query": "What are your hours?"}

        response = client.post("/api/faq", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "hours" in data["answer"].lower()

    def test_faq_endpoint_different_queries(self, client):
        """Test FAQ endpoint with different types of queries"""
        queries = [
            "Where are you located?",
            "Do you accept insurance?",
            "What's your cancellation policy?"
        ]

        for query in queries:
            payload = {"query": query}
            response = client.post("/api/faq", json=payload)
            assert response.status_code == 200

            data = response.json()
            assert "answer" in data
            assert isinstance(data["answer"], str)
            assert len(data["answer"]) > 0

    def test_availability_endpoint_success(self, client):
        """Test availability endpoint"""
        params = {
            "appointment_type": "General Consultation",
            "preferred_date": "2025-11-01"
        }

        response = client.get("/api/availability", params=params)
        assert response.status_code == 200

        data = response.json()
        assert "slots" in data
        assert isinstance(data["slots"], list)

    def test_availability_endpoint_no_date(self, client):
        """Test availability endpoint without preferred date"""
        params = {"appointment_type": "Follow-up"}

        response = client.get("/api/availability", params=params)
        assert response.status_code == 200

        data = response.json()
        assert "slots" in data

    def test_booking_endpoint_success(self, client):
        """Test successful booking endpoint"""
        payload = {
            "appointment_type": "General Consultation",
            "start_time": "2025-11-01T10:00:00Z",
            "patient_info": {
                "name": "John Doe",
                "phone": "555-123-4567",
                "email": "john@example.com"
            }
        }

        response = client.post("/api/book", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert "booking_id" in data
        assert "status" in data
        assert "details" in data
        assert data["status"] == "confirmed"

    def test_booking_endpoint_missing_fields(self, client):
        """Test booking endpoint with missing required fields"""
        payload = {
            "appointment_type": "General Consultation"
            # Missing start_time and patient_info
        }

        response = client.post("/api/book", json=payload)
        assert response.status_code == 422  # Validation error

    def test_booking_endpoint_invalid_time(self, client):
        """Test booking endpoint with invalid time"""
        payload = {
            "appointment_type": "General Consultation",
            "start_time": "invalid-time",
            "patient_info": {
                "name": "John Doe",
                "phone": "555-123-4567",
                "email": "john@example.com"
            }
        }

        response = client.post("/api/book", json=payload)
        assert response.status_code == 200  # Currently accepts any input

    def test_reschedule_endpoint_success(self, client):
        """Test successful reschedule endpoint"""
        booking_id = "APT123456"
        payload = {
            "appointment_type": "General Consultation",
            "start_time": "2025-11-02T14:00:00Z",
            "patient_info": {
                "name": "John Doe",
                "phone": "555-123-4567",
                "email": "john@example.com"
            }
        }

        response = client.put(f"/api/appointments/{booking_id}", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert "booking_id" in data
        assert "status" in data

    def test_reschedule_endpoint_not_found(self, client):
        """Test reschedule endpoint with non-existent booking"""
        booking_id = "NONEXISTENT"
        payload = {
            "appointment_type": "General Consultation",
            "start_time": "2025-11-02T14:00:00Z",
            "patient_info": {
                "name": "John Doe",
                "phone": "555-123-4567",
                "email": "john@example.com"
            }
        }

        response = client.put(f"/api/appointments/{booking_id}", json=payload)
        # Should handle gracefully - either 404 or appropriate error

    def test_cancel_endpoint_success(self, client):
        """Test successful cancel endpoint"""
        booking_id = "APT123456"

        response = client.delete(f"/api/appointments/{booking_id}")
        assert response.status_code == 200

        data = response.json()
        assert "message" in data

    def test_cancel_endpoint_not_found(self, client):
        """Test cancel endpoint with non-existent booking"""
        booking_id = "NONEXISTENT"

        response = client.delete(f"/api/appointments/{booking_id}")
        # Should handle gracefully

    def test_get_appointment_endpoint_success(self, client):
        """Test get appointment endpoint"""
        booking_id = "APT123456"

        response = client.get(f"/api/appointments/{booking_id}")
        # This might return 404 for test data, but should handle gracefully

    def test_auth_endpoints_mock(self, client):
        """Test authentication endpoints (mock implementation)"""
        # Test login
        login_payload = {
            "username": "testuser",
            "password": "testpass"
        }

        response = client.post("/api/auth/login", json=login_payload)
        # Mock implementation - may or may not succeed

        # Test register
        register_payload = {
            "username": "newuser",
            "password": "newpass",
            "fullName": "New User"
        }

        response = client.post("/api/auth/register", json=register_payload)
        # Mock implementation

    def test_mock_data_endpoint(self, client):
        """Test mock data endpoint"""
        response = client.get("/api/mock-data")
        assert response.status_code == 200

        data = response.json()
        assert "username" in data
        assert "password" in data
        assert "date" in data
        assert "time" in data

    def test_swagger_docs_endpoint(self, client):
        """Test Swagger documentation endpoint"""
        response = client.get("/api-docs")
        assert response.status_code == 200
        # Should serve Swagger UI

    def test_cors_headers(self, client):
        """Test CORS headers are present"""
        response = client.options("/api/chat", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type"
        })

        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers

    def test_error_handling_invalid_endpoint(self, client):
        """Test error handling for invalid endpoints"""
        response = client.get("/api/invalid-endpoint")
        assert response.status_code == 404

    def test_error_handling_method_not_allowed(self, client):
        """Test error handling for wrong HTTP method"""
        response = client.get("/api/book")  # Should be POST
        assert response.status_code == 405

    @pytest.mark.parametrize("endpoint,payload", [
        ("/api/chat", {"message": "Hello"}),
        ("/api/faq", {"query": "What are your hours?"}),
        ("/api/book", {
            "appointment_type": "General Consultation",
            "start_time": "2025-11-01T10:00:00Z",
            "patient_info": {"name": "Test", "phone": "123", "email": "test@test.com"}
        }),
    ])
    def test_endpoints_accept_valid_json(self, client, endpoint, payload):
        """Test that endpoints accept valid JSON payloads"""
        response = client.post(endpoint, json=payload)
        # Should not return 422 for valid payloads
        assert response.status_code != 422

    def test_large_message_handling(self, client):
        """Test handling of large messages"""
        large_message = "Hello " * 1000  # Very long message
        payload = {"message": large_message}

        response = client.post("/api/chat", json=payload)
        # Should handle gracefully without crashing
        assert response.status_code in [200, 413]  # 200 OK or 413 Payload Too Large

    def test_special_characters_in_message(self, client):
        """Test handling of special characters in messages"""
        special_message = "Hello! @#$%^&*()_+{}|:<>?[]\\;',./"
        payload = {"message": special_message}

        response = client.post("/api/chat", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert "response" in data

    def test_concurrent_requests_simulation(self, client):
        """Test handling multiple concurrent requests"""
        import threading
        import time

        results = []
        errors = []

        def make_request():
            try:
                response = client.post("/api/chat", json={"message": "Hello"})
                results.append(response.status_code)
            except Exception as e:
                errors.append(str(e))

        # Simulate concurrent requests
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # All requests should succeed
        assert len(results) == 5
        assert all(status == 200 for status in results)
        assert len(errors) == 0