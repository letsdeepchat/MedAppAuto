"""
Calendly API Integration Service
Handles calendar integration for appointment scheduling
"""

import httpx
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

try:
    from config import settings
except ImportError:
    # Mock settings for testing
    class MockSettings:
        CALENDLY_API_KEY = None
        CALENDLY_BASE_URL = "https://api.calendly.com/v2"
    settings = MockSettings()


class CalendlyService:
    """Service for integrating with Calendly API"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.api_key = settings.CALENDLY_API_KEY
        self.base_url = settings.CALENDLY_BASE_URL
        self.client = None

    async def initialize(self):
        """Initialize the Calendly service"""
        if self.api_key:
            self.client = httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                timeout=30.0
            )
            self.logger.info("Calendly service initialized")
        else:
            self.logger.warning("Calendly API key not configured")

    async def create_event(self, booking_id: str, appointment_type: str,
                          start_time: str, patient_info: Dict[str, str]) -> Dict[str, Any]:
        """
        Create a Calendly event for the appointment

        Args:
            booking_id: Unique booking identifier
            appointment_type: Type of appointment
            start_time: Start time in ISO format
            patient_info: Patient information

        Returns:
            Dict containing event details or error information
        """
        if not self.client:
            return {"error": "Calendly service not initialized"}

        try:
            # Get user's event type (this would need to be configured)
            event_type_url = f"{self.base_url}/event_types"

            # For now, return mock response since we don't have actual Calendly setup
            return {
                "event_id": f"calendly_{booking_id}",
                "status": "created",
                "start_time": start_time,
                "appointment_type": appointment_type,
                "patient_name": patient_info.get("name", "Unknown")
            }

        except Exception as e:
            self.logger.error(f"Error creating Calendly event: {e}")
            return {"error": str(e)}

    async def get_availability(self, event_type_id: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Get available time slots from Calendly

        Args:
            event_type_id: Calendly event type ID
            start_date: Start date for availability check
            end_date: End date for availability check

        Returns:
            Dict containing available slots
        """
        if not self.client:
            return {"error": "Calendly service not initialized"}

        try:
            # Mock availability response
            return {
                "available_slots": [
                    {"start_time": "2024-01-15T09:00:00Z", "end_time": "2024-01-15T10:00:00Z"},
                    {"start_time": "2024-01-15T10:00:00Z", "end_time": "2024-01-15T11:00:00Z"},
                    {"start_time": "2024-01-16T09:00:00Z", "end_time": "2024-01-16T10:00:00Z"}
                ]
            }

        except Exception as e:
            self.logger.error(f"Error getting Calendly availability: {e}")
            return {"error": str(e)}

    async def cancel_event(self, event_id: str) -> Dict[str, Any]:
        """
        Cancel a Calendly event

        Args:
            event_id: Calendly event ID to cancel

        Returns:
            Dict containing cancellation result
        """
        if not self.client:
            return {"error": "Calendly service not initialized"}

        try:
            # Mock cancellation response
            return {
                "event_id": event_id,
                "status": "cancelled",
                "cancelled_at": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error cancelling Calendly event: {e}")
            return {"error": str(e)}

    async def close(self):
        """Close the HTTP client"""
        if self.client:
            await self.client.aclose()