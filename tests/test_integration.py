"""
Integration tests for the complete MedAppAuto system
Tests end-to-end workflows and component interactions
"""

import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient
from backend.main import app
from backend.agent.conversation_agent import ConversationAgent
import asyncio
import time


class TestIntegration:
    """Integration test suite for the complete system"""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app"""
        return TestClient(app)

    @pytest.fixture
    async def async_client(self):
        """Create an async test client"""
        async with AsyncClient(app=app, base_url="http://testserver") as client:
            yield client

    def test_complete_booking_workflow(self, client):
        """Test complete booking workflow from start to finish"""
        # Step 1: Initial greeting
        response = client.post("/api/chat", json={"message": "Hello"})
        assert response.status_code == 200
        data = response.json()
        assert "scheduling assistant" in data["response"].lower()

        # Step 2: Request booking
        response = client.post("/api/chat", json={"message": "I want to book an appointment"})
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "booking_request"
        assert data["context"]["current_context"] == "understanding_needs"

        # Step 3: Specify appointment type
        response = client.post("/api/chat", json={
            "message": "General consultation",
            "context": data["context"]
        })
        assert response.status_code == 200
        data = response.json()
        assert "General Consultation" in data["response"]

        # Step 4: Request available slots
        response = client.post("/api/chat", json={
            "message": "tomorrow morning",
            "context": data["context"]
        })
        assert response.status_code == 200
        data = response.json()
        assert "available slots" in data["response"].lower()

        # Step 5: Select a slot (simulate selecting option 1)
        response = client.post("/api/chat", json={
            "message": "1",
            "context": data["context"]
        })
        assert response.status_code == 200
        data = response.json()
        # Should move to booking confirmation

        # Step 6: Provide patient information
        response = client.post("/api/chat", json={
            "message": "John Smith, 555-123-4567, john@email.com",
            "context": data["context"]
        })
        assert response.status_code == 200
        data = response.json()
        assert "successfully booked" in data["response"].lower()
        assert "APT" in data["response"]  # Should contain booking ID

    def test_faq_during_booking_workflow(self, client):
        """Test FAQ interruption during booking workflow"""
        # Start booking process
        response = client.post("/api/chat", json={"message": "I want to book an appointment"})
        assert response.status_code == 200
        booking_context = response.json()["context"]

        # Ask FAQ during booking
        response = client.post("/api/chat", json={
            "message": "What are your hours?",
            "context": booking_context
        })
        assert response.status_code == 200
        data = response.json()
        assert "hours" in data["response"].lower()
        assert data["intent"] == "faq_question"

        # Should return to booking context
        response = client.post("/api/chat", json={
            "message": "Thanks, now about my appointment",
            "context": data["context"]
        })
        assert response.status_code == 200
        data = response.json()
        # Should resume booking flow

    def test_reschedule_workflow(self, client):
        """Test appointment reschedule workflow"""
        # First create a booking
        booking_response = client.post("/api/book", json={
            "appointment_type": "General Consultation",
            "start_time": "2025-11-01T10:00:00Z",
            "patient_info": {
                "name": "Jane Doe",
                "phone": "555-987-6543",
                "email": "jane@email.com"
            }
        })
        assert booking_response.status_code == 200
        booking_data = booking_response.json()
        booking_id = booking_data["booking_id"]

        # Now test reschedule via chat
        response = client.post("/api/chat", json={"message": "I need to reschedule my appointment"})
        assert response.status_code == 200
        data = response.json()
        assert "reschedule" in data["response"].lower()

        # Test direct reschedule API
        reschedule_response = client.put(f"/api/appointments/{booking_id}", json={
            "appointment_type": "General Consultation",
            "start_time": "2025-11-02T14:00:00Z",
            "patient_info": {
                "name": "Jane Doe",
                "phone": "555-987-6543",
                "email": "jane@email.com"
            }
        })
        assert reschedule_response.status_code == 200

    def test_cancel_workflow(self, client):
        """Test appointment cancellation workflow"""
        # Create a booking first
        booking_response = client.post("/api/book", json={
            "appointment_type": "Follow-up",
            "start_time": "2025-11-01T15:00:00Z",
            "patient_info": {
                "name": "Bob Wilson",
                "phone": "555-456-7890",
                "email": "bob@email.com"
            }
        })
        assert booking_response.status_code == 200
        booking_data = booking_response.json()
        booking_id = booking_data["booking_id"]

        # Test cancel via chat
        response = client.post("/api/chat", json={"message": "I want to cancel my appointment"})
        assert response.status_code == 200
        data = response.json()
        assert "cancel" in data["response"].lower()

        # Test direct cancel API
        cancel_response = client.delete(f"/api/appointments/{booking_id}")
        assert cancel_response.status_code == 200
        cancel_data = cancel_response.json()
        assert "cancelled successfully" in cancel_data["message"].lower()

    def test_multiple_appointment_types(self, client):
        """Test booking different appointment types"""
        appointment_types = [
            ("General Consultation", 30),
            ("Follow-up", 15),
            ("Physical Exam", 45),
            ("Specialist Consultation", 60)
        ]

        for apt_type, expected_duration in appointment_types:
            # Test via chat
            response = client.post("/api/chat", json={"message": f"I need a {apt_type.lower()}"})
            assert response.status_code == 200
            data = response.json()
            assert apt_type in data["response"]

            # Test direct booking
            booking_response = client.post("/api/book", json={
                "appointment_type": apt_type,
                "start_time": "2025-11-01T10:00:00Z",
                "patient_info": {
                    "name": "Test Patient",
                    "phone": "555-000-0000",
                    "email": "test@email.com"
                }
            })
            assert booking_response.status_code == 200

    def test_availability_integration(self, client):
        """Test availability endpoint integration"""
        # Get availability
        avail_response = client.get("/api/availability", params={
            "appointment_type": "General Consultation",
            "preferred_date": "2025-11-01"
        })
        assert avail_response.status_code == 200
        avail_data = avail_response.json()
        assert "slots" in avail_data
        assert isinstance(avail_data["slots"], list)

        # Use availability in booking
        if avail_data["slots"]:
            slot = avail_data["slots"][0]  # Take first available slot
            # Assuming slot has time information
            booking_response = client.post("/api/book", json={
                "appointment_type": "General Consultation",
                "start_time": "2025-11-01T10:00:00Z",  # Mock time
                "patient_info": {
                    "name": "Avail Test",
                    "phone": "555-111-1111",
                    "email": "avail@test.com"
                }
            })
            assert booking_response.status_code == 200

    def test_faq_integration(self, client):
        """Test FAQ system integration"""
        faq_queries = [
            "What are your hours?",
            "Where are you located?",
            "Do you accept insurance?",
            "What's your cancellation policy?",
            "What should I bring to my appointment?"
        ]

        for query in faq_queries:
            response = client.post("/api/faq", json={"query": query})
            assert response.status_code == 200
            data = response.json()
            assert "answer" in data
            assert isinstance(data["answer"], str)
            assert len(data["answer"]) > 0

    def test_error_recovery(self, client):
        """Test error recovery and edge cases"""
        # Test with invalid appointment type
        response = client.get("/api/availability?appointment_type=Invalid+Type")
        # Should handle gracefully
        assert response.status_code in [200, 400, 422]

        # Test booking with invalid time
        response = client.post("/api/book", json={
            "appointment_type": "General Consultation",
            "start_time": "invalid-time",
            "patient_info": {
                "name": "Test",
                "phone": "123",
                "email": "test@test.com"
            }
        })
        # Should handle validation error
        assert response.status_code in [200, 400, 422]

        # Test chat with empty message
        response = client.post("/api/chat", json={"message": ""})
        assert response.status_code == 200  # Should handle gracefully

    def test_concurrent_bookings(self, client):
        """Test handling multiple concurrent bookings"""
        import threading

        results = []
        errors = []

        def make_booking(booking_id):
            try:
                response = client.post("/api/book", json={
                    "appointment_type": "General Consultation",
                    "start_time": f"2025-11-01T{10+booking_id}:00:00Z",
                    "patient_info": {
                        "name": f"Concurrent User {booking_id}",
                        "phone": f"555-000-{booking_id}",
                        "email": f"user{booking_id}@test.com"
                    }
                })
                results.append(response.status_code)
            except Exception as e:
                errors.append(str(e))

        # Create multiple concurrent bookings
        threads = []
        for i in range(3):
            thread = threading.Thread(target=make_booking, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Check results
        assert len(results) == 3
        assert all(status in [200, 409] for status in results)  # 409 for conflicts
        assert len(errors) == 0

    def test_context_persistence(self, client):
        """Test that conversation context persists correctly"""
        # Start a conversation
        response1 = client.post("/api/chat", json={"message": "Hello"})
        context1 = response1.json()["context"]

        # Continue with context
        response2 = client.post("/api/chat", json={
            "message": "I want to book",
            "context": context1
        })
        context2 = response2.json()["context"]

        # Context should evolve
        assert context1["current_context"] == "slot_recommendation"
        assert context2["current_context"] == "understanding_needs"

        # Continue booking
        response3 = client.post("/api/chat", json={
            "message": "General consultation",
            "context": context2
        })
        context3 = response3.json()["context"]

        assert "appointment_preferences" in context3
        assert context3["appointment_preferences"]["type"] == "General Consultation"

    def test_system_resilience(self, client):
        """Test system resilience under various conditions"""
        # Test rapid successive requests
        for i in range(10):
            response = client.post("/api/chat", json={"message": f"Message {i}"})
            assert response.status_code == 200

        # Test large payloads
        large_message = "Hello! " * 100
        response = client.post("/api/chat", json={"message": large_message})
        assert response.status_code == 200

        # Test special characters
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?/~`"
        response = client.post("/api/chat", json={"message": special_chars})
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_async_endpoints(self, async_client):
        """Test async endpoint performance"""
        import time

        start_time = time.time()

        # Make multiple async requests
        tasks = []
        for i in range(5):
            task = async_client.post("/api/chat", json={"message": f"Async test {i}"})
            tasks.append(task)

        responses = await asyncio.gather(*tasks)

        end_time = time.time()

        # All should succeed
        assert all(response.status_code == 200 for response in responses)

        # Should complete within reasonable time
        assert (end_time - start_time) < 5.0  # Less than 5 seconds for 5 requests

    def test_end_to_end_user_journey(self, client):
        """Test complete end-to-end user journey"""
        # 1. User greets the system
        response = client.post("/api/chat", json={"message": "Hi there"})
        assert response.status_code == 200
        assert "scheduling assistant" in response.json()["response"].lower()

        # 2. User asks about hours (FAQ)
        response = client.post("/api/chat", json={"message": "What time do you open?"})
        assert response.status_code == 200
        assert "hours" in response.json()["response"].lower()

        # 3. User decides to book
        response = client.post("/api/chat", json={"message": "I'd like to schedule an appointment"})
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "booking_request"

        # 4. User specifies type
        response = client.post("/api/chat", json={
            "message": "I need a physical exam",
            "context": data["context"]
        })
        assert response.status_code == 200
        assert "Physical Exam" in response.json()["response"]

        # 5. User asks for availability
        response = client.post("/api/chat", json={
            "message": "What times are available next week?",
            "context": response.json()["context"]
        })
        assert response.status_code == 200
        assert "available slots" in response.json()["response"].lower()

        # 6. User selects a time and provides info
        response = client.post("/api/chat", json={
            "message": "I'll take the first one. My name is Alice Johnson, phone 555-222-3333, email alice@email.com",
            "context": response.json()["context"]
        })
        assert response.status_code == 200
        final_response = response.json()["response"]
        assert "successfully booked" in final_response.lower()
        assert "APT" in final_response  # Booking ID

        # 7. User checks status later
        response = client.post("/api/chat", json={"message": "Check my appointment status"})
        assert response.status_code == 200
        assert "confirmation number" in response.json()["response"].lower()

        # Journey complete - user has successfully booked and can check status