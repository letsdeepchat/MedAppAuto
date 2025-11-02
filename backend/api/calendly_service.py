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
            self.logger.info("Calendly service initialized with API key")
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
            # First, get the current user's event types
            event_types_url = f"{self.base_url}/event_types"
            event_types_response = await self.client.get(event_types_url, params={"user": "https://api.calendly.com/users/EBHAAFHDCAEQTSEZ"})

            if event_types_response.status_code != 200:
                self.logger.error(f"Failed to get event types: {event_types_response.status_code}")
                return {"error": f"Failed to get event types: {event_types_response.status_code}"}

            event_types_data = event_types_response.json()
            event_types = event_types_data.get("collection", [])

            if not event_types:
                self.logger.warning("No event types found for user")
                return {"error": "No event types configured"}

            # Use the first available event type (in production, this should be configurable)
            event_type_uri = event_types[0]["uri"]

            # Create the event
            event_data = {
                "event": {
                    "start_time": start_time,
                    "event_type": event_type_uri,
                    "name": f"{appointment_type} - {patient_info.get('name', 'Patient')}",
                    "location": {
                        "type": "physical",
                        "location": "MedAppAuto Medical Center"
                    }
                }
            }

            create_url = f"{self.base_url}/scheduling_links"
            response = await self.client.post(create_url, json=event_data)

            if response.status_code == 201:
                event_result = response.json()
                return {
                    "event_id": event_result["resource"]["uri"].split("/")[-1],
                    "status": "created",
                    "start_time": start_time,
                    "appointment_type": appointment_type,
                    "patient_name": patient_info.get("name", "Unknown"),
                    "scheduling_url": event_result["resource"]["scheduling_url"]
                }
            else:
                self.logger.error(f"Failed to create Calendly event: {response.status_code} - {response.text}")
                return {"error": f"Failed to create event: {response.status_code}"}

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
            # Get user info first to find event types
            user_url = "https://api.calendly.com/users/me"
            user_response = await self.client.get(user_url)

            if user_response.status_code != 200:
                self.logger.error(f"Failed to get user info: {user_response.status_code}")
                return {"error": f"Failed to get user info: {user_response.status_code}"}

            user_data = user_response.json()
            user_uri = user_data["resource"]["uri"]

            # Get event types for the user
            event_types_url = f"{self.base_url}/event_types"
            event_types_response = await self.client.get(event_types_url, params={"user": user_uri})

            if event_types_response.status_code != 200:
                self.logger.error(f"Failed to get event types: {event_types_response.status_code}")
                return {"error": f"Failed to get event types: {event_types_response.status_code}"}

            event_types_data = event_types_response.json()
            event_types = event_types_data.get("collection", [])

            if not event_types:
                return {"available_slots": []}

            # Use the first event type or find by ID
            selected_event_type = None
            if event_type_id:
                selected_event_type = next((et for et in event_types if et["id"] == event_type_id), None)

            if not selected_event_type:
                selected_event_type = event_types[0]  # Default to first

            # Get availability for the selected event type
            availability_url = f"{self.base_url}/event_type_available_times"
            params = {
                "event_type": selected_event_type["uri"],
                "start_time": f"{start_date}T00:00:00Z",
                "end_time": f"{end_date}T23:59:59Z"
            }

            availability_response = await self.client.get(availability_url, params=params)

            if availability_response.status_code == 200:
                availability_data = availability_response.json()
                available_slots = []

                for slot in availability_data.get("collection", []):
                    available_slots.append({
                        "start_time": slot["start_time"],
                        "end_time": slot["end_time"]
                    })

                return {"available_slots": available_slots}
            else:
                self.logger.error(f"Failed to get availability: {availability_response.status_code}")
                return {"error": f"Failed to get availability: {availability_response.status_code}"}

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
            # Construct the event URI
            event_uri = f"https://api.calendly.com/scheduled_events/{event_id}"

            # Cancel the event (DELETE request)
            cancel_url = f"{self.base_url}/scheduled_events/{event_id}/cancellation"
            cancel_data = {
                "reason": "Cancelled by MedAppAuto system"
            }

            response = await self.client.post(cancel_url, json=cancel_data)

            if response.status_code == 201:
                return {
                    "event_id": event_id,
                    "status": "cancelled",
                    "cancelled_at": datetime.now(timezone.utc).isoformat()
                }
            else:
                self.logger.error(f"Failed to cancel Calendly event: {response.status_code} - {response.text}")
                return {"error": f"Failed to cancel event: {response.status_code}"}

        except Exception as e:
            self.logger.error(f"Error cancelling Calendly event: {e}")
            return {"error": str(e)}

    async def close(self):
        """Close the HTTP client"""
        if self.client:
            await self.client.aclose()