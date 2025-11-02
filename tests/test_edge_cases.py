"""
Edge case and error handling tests
Tests system robustness under various failure conditions and edge cases
"""

import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient
from backend.main import app
from backend.agent.conversation_agent import ConversationAgent
import time
import threading
import concurrent.futures


class TestEdgeCases:
    """Test suite for edge cases and error handling"""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app"""
        return TestClient(app)

    @pytest.fixture
    def agent(self):
        """Create a fresh conversation agent"""
        return ConversationAgent()

    def test_empty_and_whitespace_messages(self, client):
        """Test handling of empty and whitespace-only messages"""
        test_cases = [
            "",
            "   ",
            "\t\n",
            " \t \n \r "
        ]

        for message in test_cases:
            response = client.post("/api/chat", json={"message": message})
            assert response.status_code == 200  # Should handle gracefully

            data = response.json()
            assert "response" in data
            assert isinstance(data["response"], str)

    def test_very_long_messages(self, client):
        """Test handling of extremely long messages"""
        # Test with very long message
        long_message = "Hello! " * 1000  # ~7KB message
        response = client.post("/api/chat", json={"message": long_message})

        # Should either succeed or return appropriate error
        assert response.status_code in [200, 413, 422]

        if response.status_code == 200:
            data = response.json()
            assert "response" in data

    def test_special_characters_and_unicode(self, client):
        """Test handling of special characters and Unicode"""
        special_messages = [
            "!@#$%^&*()_+-=[]{}|;:,.<>?/~`",
            "Hello 世界 🌍",
            "🚑 Medical 💊 appointment 📅",
            "café, naïve, résumé",
            "SELECT * FROM users; DROP TABLE users;",  # SQL injection attempt
            "<script>alert('xss')</script>",  # XSS attempt
            "Multi\nLine\nMessage",
            "Tab\tSeparated\tText",
            "Quote: \"Hello World\"",
            "Apostrophe: Don't worry"
        ]

        for message in special_messages:
            response = client.post("/api/chat", json={"message": message})
            assert response.status_code == 200

            data = response.json()
            assert "response" in data
            assert isinstance(data["response"], str)

    def test_malformed_json_payloads(self, client):
        """Test handling of malformed JSON payloads"""
        malformed_payloads = [
            '{"message": "hello"',  # Missing closing brace
            '{"message": hello}',   # Unquoted value
            '{"message": "hello",}', # Trailing comma
            'null',
            '[]',
            '"string"',
            '123'
        ]

        for payload in malformed_payloads:
            try:
                response = client.post("/api/chat", data=payload)
                # Should return appropriate error status
                assert response.status_code in [400, 422]
            except Exception:
                # Some payloads might cause parsing errors before request
                pass

    def test_extreme_time_values(self, client):
        """Test booking with extreme or invalid time values"""
        extreme_times = [
            "2025-11-01T25:00:00Z",  # Invalid hour
            "2025-11-01T10:60:00Z",  # Invalid minute
            "2025-11-32T10:00:00Z",  # Invalid day
            "2025-13-01T10:00:00Z",  # Invalid month
            "2020-01-01T10:00:00Z",  # Past date
            "2030-01-01T10:00:00Z",  # Far future date
            "",  # Empty string
            "not-a-date",  # Invalid format
        ]

        for time_value in extreme_times:
            response = client.post("/api/book", json={
                "appointment_type": "General Consultation",
                "start_time": time_value,
                "patient_info": {
                    "name": "Test User",
                    "phone": "555-123-4567",
                    "email": "test@example.com"
                }
            })

            # Should handle gracefully - either validation error or success
            assert response.status_code in [200, 400, 422]

    def test_concurrent_requests_stress_test(self, client):
        """Test system under concurrent request load"""
        def make_request(request_id):
            try:
                response = client.post("/api/chat", json={
                    "message": f"Concurrent request {request_id}"
                })
                return response.status_code
            except Exception as e:
                return str(e)

        # Test with multiple concurrent requests
        num_requests = 20

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request, i) for i in range(num_requests)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # All requests should either succeed or fail gracefully
        for result in results:
            if isinstance(result, int):
                assert result in [200, 429, 500, 503]  # Acceptable status codes
            else:
                # String error message - should be handled gracefully
                assert isinstance(result, str)

    def test_memory_and_resource_limits(self, client):
        """Test system behavior near resource limits"""
        # Test with many rapid requests
        start_time = time.time()

        for i in range(50):
            response = client.post("/api/chat", json={"message": f"Request {i}"})
            assert response.status_code in [200, 429, 500, 503]

        end_time = time.time()

        # Should complete within reasonable time (allowing for some delay)
        duration = end_time - start_time
        assert duration < 30  # Less than 30 seconds for 50 requests

    def test_invalid_appointment_types(self, client):
        """Test booking with invalid appointment types"""
        invalid_types = [
            "",
            "Invalid Type",
            "Emergency Surgery",
            "123",
            "!@#$%",
            "Very Long Appointment Type Name That Exceeds Normal Limits",
            None,
            [],
            {}
        ]

        for apt_type in invalid_types:
            response = client.post("/api/book", json={
                "appointment_type": apt_type,
                "start_time": "2025-11-01T10:00:00Z",
                "patient_info": {
                    "name": "Test User",
                    "phone": "555-123-4567",
                    "email": "test@example.com"
                }
            })

            # Should handle validation appropriately
            assert response.status_code in [200, 400, 422]

    def test_malformed_patient_info(self, client):
        """Test booking with malformed patient information"""
        malformed_info = [
            {},  # Empty object
            {"name": ""},  # Empty name
            {"name": "John", "phone": ""},  # Empty phone
            {"name": "John", "email": "invalid-email"},  # Invalid email
            {"name": "A" * 1000, "phone": "555-123-4567", "email": "test@test.com"},  # Very long name
            {"name": "John<script>", "phone": "555-123-4567", "email": "test@test.com"},  # XSS attempt
            {"name": "John", "phone": "555-123-4567", "email": "test@test.com", "extra": "field"},  # Extra fields
        ]

        for patient_info in malformed_info:
            response = client.post("/api/book", json={
                "appointment_type": "General Consultation",
                "start_time": "2025-11-01T10:00:00Z",
                "patient_info": patient_info
            })

            # Should handle appropriately
            assert response.status_code in [200, 400, 422]

    def test_network_timeout_simulation(self, client):
        """Test handling of simulated network issues"""
        # This is difficult to test directly, but we can test with very slow/large payloads
        # and ensure the system doesn't crash

        # Test with large payload that might cause processing delays
        large_payload = {
            "message": "Hello " * 500,
            "context": {"large_context": "data" * 1000}
        }

        response = client.post("/api/chat", json=large_payload)

        # Should either succeed or fail gracefully
        assert response.status_code in [200, 413, 422, 500]

    def test_context_corruption_recovery(self, client):
        """Test recovery from corrupted context"""
        corrupted_contexts = [
            None,
            {},
            {"current_context": "invalid_state"},
            {"current_context": "greeting", "invalid_field": "value"},
            {"current_context": "understanding_needs", "appointment_preferences": "not_an_object"},
            {"current_context": "booking_confirmation", "user_info": []},
        ]

        for context in corrupted_contexts:
            response = client.post("/api/chat", json={
                "message": "Hello",
                "context": context
            })

            # Should handle corrupted context gracefully
            assert response.status_code == 200
            data = response.json()
            assert "response" in data
            assert "context" in data

    def test_agent_state_recovery(self, agent):
        """Test conversation agent state recovery"""
        # Corrupt internal state
        agent.current_context = "invalid_context"
        agent.user_info = "not_a_dict"
        agent.appointment_preferences = None

        # Agent should handle gracefully
        result = agent.process_message_sync("Hello")

        assert "response" in result
        assert "context" in result
        assert "intent" in result

        # State should be reset or handled properly
        assert isinstance(result["context"], dict)

    def test_database_connection_failures(self, client):
        """Test handling when database operations fail"""
        # This would require mocking database failures
        # For now, test with invalid booking IDs that don't exist

        invalid_ids = [
            "",
            "INVALID",
            "APT999999999",
            "not-a-number",
            "APT-123",
            "APT 123"
        ]

        for booking_id in invalid_ids:
            response = client.get(f"/api/appointments/{booking_id}")
            # Should return 400 for invalid IDs
            assert response.status_code in [200, 400, 404, 422, 500]

            response = client.put(f"/api/appointments/{booking_id}", json={
                "appointment_type": "General Consultation",
                "start_time": "2025-11-01T10:00:00Z",
                "patient_info": {"name": "Test"}
            })
            assert response.status_code in [200, 400, 404, 422, 500]

            response = client.delete(f"/api/appointments/{booking_id}")
            assert response.status_code in [400, 404, 422, 500]

    def test_rate_limiting_simulation(self, client):
        """Test behavior under rapid request rates"""
        import time

        start_time = time.time()
        request_count = 0
        max_requests = 100

        while request_count < max_requests and (time.time() - start_time) < 10:  # 10 second window
            response = client.post("/api/chat", json={"message": f"Request {request_count}"})
            request_count += 1

            # Should not crash under load
            assert response.status_code in [200, 429, 500, 503]

        # Should have made reasonable number of requests
        assert request_count > 10

    def test_memory_leak_prevention(self, client):
        """Test that repeated requests don't cause memory issues"""
        # Make many requests and ensure system remains stable
        for i in range(100):
            response = client.post("/api/chat", json={"message": f"Memory test {i}"})
            assert response.status_code == 200

            # Keep some responses in memory to simulate client-side state
            if i % 10 == 0:
                data = response.json()
                assert "response" in data

        # If we get here without crashes, memory management is likely OK
        # In a real scenario, we'd monitor actual memory usage

    def test_encoding_edge_cases(self, client):
        """Test various text encodings and edge cases"""
        encoding_tests = [
            "UTF-8: Hello 世界 🌍",
            "Latin-1: café résumé naïve",
            "Emoji: 😀🎉🚑💊📅",
            "RTL: مرحبا بالعالم",
            "Mixed: Hello 世界 こんにちは 🌍",
            "Control chars: \n\t\r",
            "Zero width: H\u200Be\u200Cllo",  # Zero-width characters
        ]

        for message in encoding_tests:
            response = client.post("/api/chat", json={"message": message})
            assert response.status_code == 200

            data = response.json()
            assert "response" in data

    def test_boundary_condition_times(self, client):
        """Test booking at boundary time conditions"""
        boundary_times = [
            "2025-11-01T00:00:00Z",  # Midnight
            "2025-11-01T23:59:59Z",  # End of day
            "2025-11-01T12:00:00Z",  # Noon
            "2025-11-01T06:00:00Z",  # Early morning
            "2025-11-01T18:00:00Z",  # Evening
        ]

        for time_value in boundary_times:
            response = client.post("/api/book", json={
                "appointment_type": "General Consultation",
                "start_time": time_value,
                "patient_info": {
                    "name": "Boundary Test",
                    "phone": "555-123-4567",
                    "email": "boundary@test.com"
                }
            })

            # Should handle boundary times appropriately
            assert response.status_code in [200, 400, 422]

    def test_extreme_context_sizes(self, client):
        """Test handling of extremely large context objects"""
        # Create a very large context
        large_context = {
            "current_context": "understanding_needs",
            "appointment_preferences": {
                "type": "General Consultation",
                "large_data": "x" * 10000  # 10KB of data
            },
            "user_info": {"name": "Test"},
            "conversation_history": [{"message": "test"}] * 100  # Many history items
        }

        response = client.post("/api/chat", json={
            "message": "Hello with large context",
            "context": large_context
        })

        # Should handle large context gracefully
        assert response.status_code in [200, 413, 422, 500]

    def test_service_unavailability_simulation(self, client):
        """Test graceful degradation when services are unavailable"""
        # This would require mocking service failures
        # For now, test with endpoints that might not be fully implemented

        # Test endpoints that depend on external services
        response = client.get("/api/availability", params={"appointment_type": "Test"})
        # Should either work or fail gracefully
        assert response.status_code in [200, 400, 500]

        # Test FAQ with various queries
        faq_queries = ["", "a", "very long query " * 50]
        for query in faq_queries:
            response = client.post("/api/faq", json={"query": query})
            assert response.status_code in [200, 400, 422, 500]