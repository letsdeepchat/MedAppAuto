"""
Database Service for MongoDB integration
Handles appointment persistence and data management
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection

try:
    from config import settings
except ImportError:
    # Mock settings for testing
    class MockSettings:
        mongodb_url = "mongodb://localhost:27017"
        database_name = "medical_appointments"
    settings = MockSettings()


class DatabaseService:
    """Service for MongoDB database operations"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.client: Optional[AsyncIOMotorClient] = None
        self.database: Optional[AsyncIOMotorDatabase] = None
        self.appointments_collection: Optional[AsyncIOMotorCollection] = None

    async def initialize(self):
        """Initialize the database connection"""
        try:
            self.client = AsyncIOMotorClient(settings.mongodb_url)
            self.database = self.client[settings.database_name]
            self.appointments_collection = self.database.appointments

            # Test the connection
            await self.client.admin.command('ping')
            self.logger.info("Database connection established successfully")

            # Create indexes for better performance
            await self._create_indexes()

        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise

    async def _create_indexes(self):
        """Create database indexes for optimal performance"""
        try:
            # Index on booking_id for fast lookups
            await self.appointments_collection.create_index("booking_id", unique=True)

            # Index on patient email for patient-specific queries
            await self.appointments_collection.create_index("patient_info.email")

            # Index on appointment date/time for scheduling queries
            await self.appointments_collection.create_index("start_time")

            # Compound index for availability queries
            await self.appointments_collection.create_index([
                ("start_time", 1),
                ("appointment_type", 1)
            ])

            self.logger.info("Database indexes created successfully")

        except Exception as e:
            self.logger.error(f"Error creating indexes: {e}")

    async def create_appointment(self, appointment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new appointment in the database

        Args:
            appointment_data: Appointment data dictionary

        Returns:
            Dict containing created appointment data
        """
        try:
            # Add timestamps
            appointment_data["created_at"] = datetime.now(timezone.utc)
            appointment_data["updated_at"] = datetime.now(timezone.utc)
            appointment_data["status"] = appointment_data.get("status", "confirmed")

            # Insert the appointment
            result = await self.appointments_collection.insert_one(appointment_data)

            # Retrieve the created appointment
            created_appointment = await self.appointments_collection.find_one(
                {"_id": result.inserted_id}
            )

            # Convert ObjectId to string for JSON serialization
            created_appointment["_id"] = str(created_appointment["_id"])

            self.logger.info(f"Appointment created: {appointment_data.get('booking_id')}")
            return created_appointment

        except Exception as e:
            self.logger.error(f"Error creating appointment: {e}")
            raise

    async def get_appointment(self, booking_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve an appointment by booking ID

        Args:
            booking_id: Unique booking identifier

        Returns:
            Appointment data or None if not found
        """
        try:
            appointment = await self.appointments_collection.find_one({"booking_id": booking_id})

            if appointment:
                # Convert ObjectId to string
                appointment["_id"] = str(appointment["_id"])
                return appointment

            return None

        except Exception as e:
            self.logger.error(f"Error retrieving appointment {booking_id}: {e}")
            raise

    async def update_appointment(self, booking_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update an existing appointment

        Args:
            booking_id: Unique booking identifier
            update_data: Data to update

        Returns:
            Updated appointment data or None if not found
        """
        try:
            # Add update timestamp
            update_data["updated_at"] = datetime.now(timezone.utc)

            result = await self.appointments_collection.update_one(
                {"booking_id": booking_id},
                {"$set": update_data}
            )

            if result.modified_count > 0:
                # Return the updated appointment
                return await self.get_appointment(booking_id)

            return None

        except Exception as e:
            self.logger.error(f"Error updating appointment {booking_id}: {e}")
            raise

    async def cancel_appointment(self, booking_id: str) -> bool:
        """
        Cancel an appointment

        Args:
            booking_id: Unique booking identifier

        Returns:
            True if cancelled successfully, False otherwise
        """
        try:
            result = await self.appointments_collection.update_one(
                {"booking_id": booking_id},
                {
                    "$set": {
                        "status": "cancelled",
                        "cancelled_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )

            success = result.modified_count > 0
            if success:
                self.logger.info(f"Appointment cancelled: {booking_id}")

            return success

        except Exception as e:
            self.logger.error(f"Error cancelling appointment {booking_id}: {e}")
            raise

    async def get_appointments_by_patient(self, email: str) -> List[Dict[str, Any]]:
        """
        Get all appointments for a specific patient

        Args:
            email: Patient email address

        Returns:
            List of appointment data
        """
        try:
            cursor = self.appointments_collection.find(
                {"patient_info.email": email}
            ).sort("start_time", 1)

            appointments = []
            async for appointment in cursor:
                appointment["_id"] = str(appointment["_id"])
                appointments.append(appointment)

            return appointments

        except Exception as e:
            self.logger.error(f"Error retrieving appointments for {email}: {e}")
            raise

    async def check_availability(self, appointment_type: str, start_time: str, duration_minutes: int = 30) -> bool:
        """
        Check if a time slot is available for booking

        Args:
            appointment_type: Type of appointment
            start_time: Start time in ISO format
            duration_minutes: Duration in minutes

        Returns:
            True if available, False if conflict exists
        """
        try:
            from dateutil import parser

            # Parse the start time
            start_dt = parser.parse(start_time)
            end_dt = start_dt + timedelta(minutes=duration_minutes)

            # Check for conflicting appointments
            conflict_count = await self.appointments_collection.count_documents({
                "appointment_type": appointment_type,
                "status": {"$ne": "cancelled"},  # Exclude cancelled appointments
                "$or": [
                    # New appointment starts during existing appointment
                    {
                        "start_time": {"$lte": start_dt.isoformat()},
                        "end_time": {"$gt": start_dt.isoformat()}
                    },
                    # New appointment ends during existing appointment
                    {
                        "start_time": {"$lt": end_dt.isoformat()},
                        "end_time": {"$gte": end_dt.isoformat()}
                    },
                    # New appointment completely contains existing appointment
                    {
                        "start_time": {"$gte": start_dt.isoformat()},
                        "end_time": {"$lte": end_dt.isoformat()}
                    }
                ]
            })

            return conflict_count == 0

        except Exception as e:
            self.logger.error(f"Error checking availability: {e}")
            raise

    async def get_available_slots(self, appointment_type: str, date: str, doctor_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get available time slots for a specific date and appointment type

        Args:
            appointment_type: Type of appointment
            date: Date in YYYY-MM-DD format
            doctor_id: Optional doctor ID for filtering

        Returns:
            List of available time slots
        """
        try:
            pass

            # Get appointment duration from type
            duration_map = {
                "General Consultation": 30,
                "Follow-up": 15,
                "Physical Exam": 45,
                "Specialist Consultation": 60
            }
            duration = duration_map.get(appointment_type, 30)

            # Generate time slots for the day (9 AM to 5 PM)
            slots = []
            start_hour = 9
            end_hour = 17

            for hour in range(start_hour, end_hour):
                for minute in [0, 30]:  # 30-minute intervals
                    slot_start = datetime.strptime(f"{date} {hour:02d}:{minute:02d}", "%Y-%m-%d %H:%M")
                    slot_end = slot_start + timedelta(minutes=duration)

                    # Check if this slot is available
                    if await self.check_availability(appointment_type, slot_start.isoformat()):
                        slots.append({
                            "start_time": slot_start.isoformat(),
                            "end_time": slot_end.isoformat(),
                            "duration": duration
                        })

            return slots

        except Exception as e:
            self.logger.error(f"Error getting available slots: {e}")
            raise

    async def get_appointments_by_date_range(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        Get all appointments within a date range

        Args:
            start_date: Start date in ISO format
            end_date: End date in ISO format

        Returns:
            List of appointments
        """
        try:
            cursor = self.appointments_collection.find({
                "start_time": {
                    "$gte": start_date,
                    "$lte": end_date
                },
                "status": {"$ne": "cancelled"}
            }).sort("start_time", 1)

            appointments = []
            async for appointment in cursor:
                appointment["_id"] = str(appointment["_id"])
                appointments.append(appointment)

            return appointments

        except Exception as e:
            self.logger.error(f"Error retrieving appointments by date range: {e}")
            raise

    async def close(self):
        """Close the database connection"""
        if self.client:
            self.client.close()
            self.logger.info("Database connection closed")