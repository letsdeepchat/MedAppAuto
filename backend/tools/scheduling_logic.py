"""
Scheduling Logic Service
Handles appointment scheduling, availability checking, and conflict resolution
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from pathlib import Path

try:
    from config import settings
except ImportError:
    # Mock settings for testing
    class MockSettings:
        pass
    settings = MockSettings()


class SchedulingLogic:
    """Service for handling appointment scheduling logic"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.data_dir = Path(__file__).parent.parent.parent / "data"
        self.doctor_schedules = {}
        self.appointments = {}  # In-memory storage, replace with database in production
        self._load_doctor_schedules()

    def _load_doctor_schedules(self):
        """Load doctor schedules from JSON file"""
        try:
            schedule_file = self.data_dir / "doctor_schedule.json"
            if schedule_file.exists():
                with open(schedule_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.doctor_schedules = {doc["id"]: doc for doc in data.get("doctors", [])}
                self.logger.info(f"Loaded schedules for {len(self.doctor_schedules)} doctors")
        except Exception as e:
            self.logger.error(f"Error loading doctor schedules: {e}")

    async def get_available_slots(self, appointment_type: str, preferred_date: Optional[str] = None,
                                duration_minutes: int = 30) -> List[Dict[str, Any]]:
        """
        Get available time slots for a given appointment type

        Args:
            appointment_type: Type of appointment
            preferred_date: Preferred date (YYYY-MM-DD) or None for next available
            duration_minutes: Duration of appointment in minutes

        Returns:
            List of available time slots
        """
        try:
            available_slots = []

            # Parse preferred date or use today
            if preferred_date:
                try:
                    start_date = datetime.fromisoformat(preferred_date).date()
                except ValueError:
                    start_date = datetime.now().date()
            else:
                start_date = datetime.now().date()

            # Check next 7 days
            for day_offset in range(7):
                current_date = start_date + timedelta(days=day_offset)
                day_name = current_date.strftime("%A").lower()

                # Check each doctor's availability
                for doctor_id, doctor in self.doctor_schedules.items():
                    schedule = doctor.get("schedule", {}).get(day_name, [])

                    # Check if doctor offers this appointment type
                    if appointment_type not in doctor.get("appointment_types", []):
                        continue

                    # Process each time slot in doctor's schedule
                    for slot in schedule:
                        if slot.get("type") == "clinic":  # Only clinic hours
                            slot_start = datetime.strptime(slot["start"], "%H:%M").time()
                            slot_end = datetime.strptime(slot["end"], "%H:%M").time()

                            # Create datetime objects
                            slot_start_dt = datetime.combine(current_date, slot_start)
                            slot_end_dt = datetime.combine(current_date, slot_end)

                            # Generate time slots within this schedule block
                            current_time = slot_start_dt
                            while current_time + timedelta(minutes=duration_minutes) <= slot_end_dt:
                                # Check if slot is available (not conflicting with existing appointments)
                                if self._is_slot_available(doctor_id, current_time,
                                                         current_time + timedelta(minutes=duration_minutes)):
                                    available_slots.append({
                                        "doctor_id": doctor_id,
                                        "doctor_name": doctor["name"],
                                        "specialty": doctor["specialty"],
                                        "start_time": current_time.isoformat(),
                                        "end_time": (current_time + timedelta(minutes=duration_minutes)).isoformat(),
                                        "appointment_type": appointment_type,
                                        "duration_minutes": duration_minutes
                                    })

                                current_time += timedelta(minutes=30)  # 30-minute intervals

            # Sort by date and time
            available_slots.sort(key=lambda x: x["start_time"])

            # Return top 10 available slots
            return available_slots[:10]

        except Exception as e:
            self.logger.error(f"Error getting available slots: {e}")
            return []

    def _is_slot_available(self, doctor_id: str, start_time: datetime, end_time: datetime) -> bool:
        """
        Check if a time slot is available for a doctor

        Args:
            doctor_id: Doctor's ID
            start_time: Slot start time
            end_time: Slot end time

        Returns:
            True if slot is available
        """
        # Check against existing appointments
        for appointment in self.appointments.values():
            if (appointment["doctor_id"] == doctor_id and
                appointment["status"] in ["confirmed", "pending"]):

                appt_start = datetime.fromisoformat(appointment["start_time"])
                appt_end = datetime.fromisoformat(appointment["end_time"])

                # Check for overlap
                if not (end_time <= appt_start or start_time >= appt_end):
                    return False

        return True

    async def validate_booking(self, appointment_type: str, start_time: str,
                             patient_info: Dict[str, str]) -> Dict[str, Any]:
        """
        Validate a booking request

        Args:
            appointment_type: Type of appointment
            start_time: Start time in ISO format
            patient_info: Patient information

        Returns:
            Validation result with errors if any
        """
        errors = []

        try:
            # Validate start time
            start_dt = datetime.fromisoformat(start_time)
            now = datetime.now(timezone.utc).replace(tzinfo=None)

            if start_dt < now:
                errors.append("Cannot book appointments in the past")

            # Check if within business hours (basic validation)
            if start_dt.weekday() >= 5:  # Saturday = 5, Sunday = 6
                if not (9 <= start_dt.hour <= 14):  # Weekend hours
                    errors.append("Weekend appointments must be between 9 AM and 2 PM")
            else:  # Weekdays
                if not (8 <= start_dt.hour <= 18):  # Business hours
                    errors.append("Weekday appointments must be between 8 AM and 6 PM")

            # Validate patient info
            required_fields = ["name", "phone", "email"]
            for field in required_fields:
                if not patient_info.get(field):
                    errors.append(f"Patient {field} is required")
                elif field == "email" and "@" not in patient_info[field]:
                    errors.append("Invalid email format")
                elif field == "phone" and len(patient_info[field].replace("-", "").replace(" ", "")) < 10:
                    errors.append("Phone number must be at least 10 digits")

            # Check appointment type exists
            valid_types = set()
            for doctor in self.doctor_schedules.values():
                valid_types.update(doctor.get("appointment_types", []))

            if appointment_type not in valid_types:
                errors.append(f"Appointment type '{appointment_type}' is not available")

        except ValueError as e:
            errors.append(f"Invalid date/time format: {e}")
        except Exception as e:
            errors.append(f"Validation error: {e}")

        return {
            "is_valid": len(errors) == 0,
            "errors": errors
        }

    async def create_booking(self, appointment_type: str, start_time: str,
                           patient_info: Dict[str, str]) -> Dict[str, Any]:
        """
        Create a new appointment booking

        Args:
            appointment_type: Type of appointment
            start_time: Start time in ISO format
            patient_info: Patient information

        Returns:
            Created appointment details
        """
        try:
            # Find available doctor for this time slot
            start_dt = datetime.fromisoformat(start_time)
            duration_minutes = self._get_appointment_duration(appointment_type)

            available_doctor = None
            for doctor_id, doctor in self.doctor_schedules.items():
                if (appointment_type in doctor.get("appointment_types", []) and
                    self._is_slot_available(doctor_id, start_dt, start_dt + timedelta(minutes=duration_minutes))):
                    available_doctor = doctor
                    break

            if not available_doctor:
                raise ValueError("No doctor available for this time slot")

            # Create appointment
            appointment_id = f"APT{datetime.now().strftime('%Y%m%d%H%M%S')}"
            end_time = start_dt + timedelta(minutes=duration_minutes)

            appointment = {
                "id": appointment_id,
                "booking_id": appointment_id,
                "appointment_type": appointment_type,
                "doctor_id": available_doctor["id"],
                "doctor_name": available_doctor["name"],
                "start_time": start_time,
                "end_time": end_time.isoformat(),
                "duration_minutes": duration_minutes,
                "patient_info": patient_info,
                "status": "confirmed",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "notes": None,
                "reason_for_visit": patient_info.get("reason", ""),
                "cancelled_at": None,
                "cancellation_reason": None,
                "rescheduled_from": None,
                "calendly_event_id": None,
                "reminder_sent": False,
                "follow_up_required": False
            }

            # Store appointment
            self.appointments[appointment_id] = appointment

            self.logger.info(f"Created appointment {appointment_id} for {patient_info['name']}")

            return appointment

        except Exception as e:
            self.logger.error(f"Error creating booking: {e}")
            raise

    def _get_appointment_duration(self, appointment_type: str) -> int:
        """Get default duration for appointment type"""
        duration_map = {
            "General Consultation": 30,
            "Follow-up": 15,
            "Physical Exam": 45,
            "Specialist Consultation": 60,
            "Well Child Visit": 30,
            "Sick Visit": 20,
            "Vaccinations": 15,
            "Developmental Screening": 45,
            "ECG": 30,
            "Stress Test": 60,
            "Echocardiogram": 45,
            "Skin Biopsy": 30,
            "Mohs Surgery": 120,
            "Laser Treatment": 60,
            "X-ray": 15,
            "MRI": 60,
            "Physical Therapy": 45,
            "Annual Exam": 30,
            "Pap Smear": 20,
            "Mammogram": 30,
            "Birth Control": 20,
            "Consultation": 30,
            "Eye Exam": 30,
            "Glaucoma Screening": 20,
            "Cataract Surgery": 180,
            "Emergency Care": 60,
            "Urgent Care": 30,
            "Trauma Care": 90,
            "Initial Consultation": 45,
            "Medication Management": 25,
            "Therapy Session": 50,
            "Neurological Exam": 45,
            "PSA Test": 15,
            "Ultrasound": 30,
            "Biopsy": 45,
            "Pre-operative Consultation": 30,
            "Post-operative Follow-up": 20,
            "Surgical Procedure": 120,
            "Pre-operative Evaluation": 45,
            "Anesthesia Consultation": 30,
            "Nephrology Consultation": 30,
            "Endocrinology Consultation": 30,
            "Oncology Consultation": 45,
            "Initial Evaluation": 45,
            "Pain Management": 30,
            "Rehabilitation": 45,
            "Radiology Procedure": 30,
            "Pulmonology Consultation": 30,
            "Rheumatology Consultation": 30,
            "Infectious Diseases Consultation": 30,
            "Sports Medicine Consultation": 30,
            "Allergy & Immunology Consultation": 30,
            "Plastic Surgery Consultation": 30,
            "Pathology Analysis": 30,
            "Blood Test Review": 20,
            "Tissue Analysis": 45
        }

        return duration_map.get(appointment_type, 30)  # Default 30 minutes

    async def reschedule_appointment(self, appointment_id: str, new_start_time: str,
                                   appointment_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Reschedule an existing appointment

        Args:
            appointment_id: ID of appointment to reschedule
            new_start_time: New start time in ISO format
            appointment_type: New appointment type (optional)

        Returns:
            Rescheduling result
        """
        try:
            if appointment_id not in self.appointments:
                return {"success": False, "error": "Appointment not found"}

            appointment = self.appointments[appointment_id]

            if appointment["status"] == "cancelled":
                return {"success": False, "error": "Cannot reschedule cancelled appointment"}

            # Validate new time
            new_start_dt = datetime.fromisoformat(new_start_time)
            duration = self._get_appointment_duration(appointment_type or appointment["appointment_type"])

            # Check availability
            if not self._is_slot_available(appointment["doctor_id"], new_start_dt,
                                        new_start_dt + timedelta(minutes=duration)):
                return {"success": False, "error": "New time slot is not available"}

            # Update appointment
            old_start_time = appointment["start_time"]
            appointment.update({
                "start_time": new_start_time,
                "end_time": (new_start_dt + timedelta(minutes=duration)).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "rescheduled_from": old_start_time
            })

            if appointment_type:
                appointment["appointment_type"] = appointment_type
                appointment["duration_minutes"] = duration

            self.logger.info(f"Rescheduled appointment {appointment_id}")

            return {
                "success": True,
                "appointment": appointment,
                "old_start_time": old_start_time,
                "new_start_time": new_start_time
            }

        except Exception as e:
            self.logger.error(f"Error rescheduling appointment: {e}")
            return {"success": False, "error": str(e)}

    async def cancel_appointment(self, appointment_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """
        Cancel an appointment

        Args:
            appointment_id: ID of appointment to cancel
            reason: Cancellation reason

        Returns:
            Cancellation result with policy information
        """
        try:
            if appointment_id not in self.appointments:
                return {
                    "can_cancel": False,
                    "error": "Appointment not found"
                }

            appointment = self.appointments[appointment_id]

            if appointment["status"] == "cancelled":
                return {
                    "can_cancel": False,
                    "error": "Appointment is already cancelled"
                }

            # Calculate cancellation fee based on policy
            start_dt = datetime.fromisoformat(appointment["start_time"])
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            hours_until_appointment = (start_dt - now).total_seconds() / 3600

            fee = 0
            policy_message = ""

            if hours_until_appointment < 24:
                if hours_until_appointment <= 0:
                    fee = 100  # No-show fee
                    policy_message = "Same-day cancellation: $100 fee applies"
                else:
                    fee = 50  # Within 24 hours
                    policy_message = "Late cancellation (within 24 hours): $50 fee applies"
            else:
                policy_message = "Cancelled more than 24 hours in advance: No fee"

            # Update appointment
            appointment.update({
                "status": "cancelled",
                "cancelled_at": datetime.now(timezone.utc).isoformat(),
                "cancellation_reason": reason,
                "updated_at": datetime.now(timezone.utc).isoformat()
            })

            self.logger.info(f"Cancelled appointment {appointment_id}")

            return {
                "can_cancel": True,
                "fee": fee,
                "policy_message": policy_message,
                "appointment": appointment
            }

        except Exception as e:
            self.logger.error(f"Error cancelling appointment: {e}")
            return {
                "can_cancel": False,
                "error": str(e)
            }

    async def get_appointment(self, appointment_id: str) -> Optional[Dict[str, Any]]:
        """
        Get appointment details

        Args:
            appointment_id: Appointment ID

        Returns:
            Appointment details or None if not found
        """
        return self.appointments.get(appointment_id)

    async def get_doctor_availability(self, doctor_id: str, date: str) -> List[Dict[str, Any]]:
        """
        Get availability for a specific doctor on a specific date

        Args:
            doctor_id: Doctor's ID
            date: Date in YYYY-MM-DD format

        Returns:
            List of available time slots
        """
        try:
            if doctor_id not in self.doctor_schedules:
                return []

            doctor = self.doctor_schedules[doctor_id]
            date_obj = datetime.fromisoformat(date).date()
            day_name = date_obj.strftime("%A").lower()

            schedule = doctor.get("schedule", {}).get(day_name, [])
            available_slots = []

            for slot in schedule:
                if slot.get("type") == "clinic":
                    slot_start = datetime.strptime(slot["start"], "%H:%M").time()
                    slot_end = datetime.strptime(slot["end"], "%H:%M").time()

                    start_dt = datetime.combine(date_obj, slot_start)
                    end_dt = datetime.combine(date_obj, slot_end)

                    # Check 30-minute intervals
                    current_time = start_dt
                    while current_time + timedelta(minutes=30) <= end_dt:
                        if self._is_slot_available(doctor_id, current_time, current_time + timedelta(minutes=30)):
                            available_slots.append({
                                "start_time": current_time.isoformat(),
                                "end_time": (current_time + timedelta(minutes=30)).isoformat()
                            })
                        current_time += timedelta(minutes=30)

            return available_slots

        except Exception as e:
            self.logger.error(f"Error getting doctor availability: {e}")
            return []