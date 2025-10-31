"""
Pytest configuration and fixtures for the test suite
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
import os
import sys

# Add backend to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture(scope="session")
def client():
    """Create a test client for the FastAPI app that persists across the session"""
    # Skip FastAPI tests for now due to import issues
    return None


@pytest.fixture
def agent():
    """Create a fresh conversation agent for each test"""
    import sys
    import os
    # Add current directory to path
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from backend.agent.conversation_agent import ConversationAgent
    return ConversationAgent()


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment variables and configurations"""
    # Set test-specific environment variables if needed
    os.environ.setdefault("DEBUG", "True")
    os.environ.setdefault("DATABASE_NAME", "test_medical_appointments")

    yield

    # Cleanup after test if needed
    pass


@pytest.fixture
def sample_patient_info():
    """Sample patient information for testing"""
    return {
        "name": "John Doe",
        "phone": "555-123-4567",
        "email": "john.doe@example.com"
    }


@pytest.fixture
def sample_appointment_data(sample_patient_info):
    """Sample appointment data for testing"""
    return {
        "appointment_type": "General Consultation",
        "start_time": "2025-11-01T10:00:00Z",
        "patient_info": sample_patient_info
    }


@pytest.fixture
def sample_chat_context():
    """Sample chat context for testing"""
    return {
        "current_context": "understanding_needs",
        "appointment_preferences": {
            "type": "General Consultation",
            "duration": 30
        },
        "user_info": {}
    }