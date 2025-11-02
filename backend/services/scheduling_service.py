"""
Advanced Scheduling Service with dynamic doctor schedules and availability
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, time, timedelta
from dateutil import parser


class SchedulingService:
    """Advanced scheduling service with dynamic doctor availability"""

    def __init__(self, database_service):
        self.logger = logging.getLogger(__name__)
        self.database_service = database_service

    async def get_doctor_schedule(self, doctor_id: str, date: str) -> Dict[str, Any]:
        """Get doctor's schedule for a specific date"""
        try:
            # Get doctor's working hours from database
            doctor_schedule = await self.database_service.get_doctor_schedule(doctor_id)

            if not doctor_schedule:
                # Return default schedule if none exists
                return self._get_default_schedule(date)

            # Parse the date
            target_date = parser.parse(date).date()
            day_of_week = target_date.weekday()  # 0=Monday, 6=Sunday

            # Find working hours for this day
            working_hours = None
            for wh in doctor_schedule.get('working_hours', []):
                if wh['day_of_week'] == day_of_week and wh.get('is_available', True):
                    working_hours = wh
                    break

            if not working_hours:
                return {
                    "available": False,
                    "reason": "Doctor not available on this day"
                }

            # Get existing appointments for this date
            existing_appointments = await self.database_service.get_appointments_by_doctor_date(
                doctor_id, date
            )

            # Calculate available slots
            available_slots = self._calculate_available_slots(
                working_hours, existing_appointments, doctor_schedule.get('buffer_time_minutes', 15)
            )

            return {
                "available": True,
                "working_hours": working_hours,
                "available_slots": available_slots,
                "existing_appointments": len(existing_appointments)
            }

        except Exception as e:
            self.logger.error(f"Error getting doctor schedule: {e}")
            return self._get_default_schedule(date)

    async def check_availability(self, doctor_id: str, appointment_type_id: str,
                               start_time: str, duration_minutes: int) -> bool:
        """Check if a specific time slot is available"""
        try:
            # Parse start time
            start_dt = parser.parse(start_time)
            date_str = start_dt.date().isoformat()

            # Get doctor's schedule for this date
            schedule = await self.get_doctor_schedule(doctor_id, date_str)

            if not schedule.get('available', False):
                return False

            # Check if the requested time falls within working hours
            working_hours = schedule['working_hours']
            start_time_obj = time.fromisoformat(working_hours['start_time'])
            end_time_obj = time.fromisoformat(working_hours['end_time'])

            requested_start = start_dt.time()
            requested_end = (start_dt + timedelta(minutes=duration_minutes)).time()

            if requested_start < start_time_obj or requested_end > end_time_obj:
                return False

            # Check for conflicts with existing appointments
            existing_appointments = await self.database_service.get_appointments_by_doctor_date(
                doctor_id, date_str
            )

            for appointment in existing_appointments:
                if appointment['status'] in ['confirmed', 'completed']:
                    apt_start = parser.parse(appointment['start_time'])
                    apt_end = parser.parse(appointment['end_time'])

                    # Check for overlap
                    if (start_dt < apt_end and
                        (start_dt + timedelta(minutes=duration_minutes)) > apt_start):
                        return False

            return True

        except Exception as e:
            self.logger.error(f"Error checking availability: {e}")
            return False

    async def find_available_slots(self, doctor_id: str, appointment_type_id: str,
                                 date: str, duration_minutes: int = 30) -> List[Dict[str, str]]:
        """Find all available time slots for a doctor on a specific date"""
        try:
            # Get doctor's schedule
            schedule = await self.get_doctor_schedule(doctor_id, date)

            if not schedule.get('available', False):
                return []

            working_hours = schedule['working_hours']
            buffer_minutes = schedule.get('buffer_time_minutes', 15)

            # Get existing appointments
            existing_appointments = await self.database_service.get_appointments_by_doctor_date(
                doctor_id, date
            )

            # Calculate available slots
            available_slots = self._calculate_available_slots(
                working_hours, existing_appointments, buffer_minutes, duration_minutes
            )

            return available_slots

        except Exception as e:
            self.logger.error(f"Error finding available slots: {e}")
            return []

    def _calculate_available_slots(self, working_hours: Dict[str, Any],
                                 existing_appointments: List[Dict[str, Any]],
                                 buffer_minutes: int = 15,
                                 slot_duration: int = 30) -> List[Dict[str, str]]:
        """Calculate available time slots within working hours"""
        try:
            start_time = time.fromisoformat(working_hours['start_time'])
            end_time = time.fromisoformat(working_hours['end_time'])

            # Create datetime objects for today (we'll replace the date later)
            base_date = datetime.now().date()
            work_start = datetime.combine(base_date, start_time)
            work_end = datetime.combine(base_date, end_time)

            # Sort existing appointments by start time
            sorted_appointments = sorted(
                [apt for apt in existing_appointments if apt['status'] in ['confirmed', 'completed']],
                key=lambda x: parser.parse(x['start_time'])
            )

            available_slots = []
            current_time = work_start

            for appointment in sorted_appointments:
                apt_start = parser.parse(appointment['start_time'])
                apt_end = parser.parse(appointment['end_time'])

                # Add buffer time after appointment
                apt_end_with_buffer = apt_end + timedelta(minutes=buffer_minutes)

                # Find slots between current_time and appointment start
                while current_time + timedelta(minutes=slot_duration) <= apt_start:
                    slot_end = current_time + timedelta(minutes=slot_duration)
                    available_slots.append({
                        "start_time": current_time.isoformat(),
                        "end_time": slot_end.isoformat()
                    })
                    current_time = slot_end

                # Move current_time to after the appointment with buffer
                current_time = max(current_time, apt_end_with_buffer)

            # Add remaining slots until end of working hours
            while current_time + timedelta(minutes=slot_duration) <= work_end:
                slot_end = current_time + timedelta(minutes=slot_duration)
                available_slots.append({
                    "start_time": current_time.isoformat(),
                    "end_time": slot_end.isoformat()
                })
                current_time = slot_end

            return available_slots

        except Exception as e:
            self.logger.error(f"Error calculating available slots: {e}")
            return []

    def _get_default_schedule(self, date: str) -> Dict[str, Any]:
        """Return default schedule when no custom schedule exists"""
        return {
            "available": True,
            "working_hours": {
                "day_of_week": parser.parse(date).date().weekday(),
                "start_time": "09:00",
                "end_time": "17:00",
                "is_available": True
            },
            "available_slots": [
                {"start_time": f"{date}T09:00:00", "end_time": f"{date}T09:30:00"},
                {"start_time": f"{date}T09:30:00", "end_time": f"{date}T10:00:00"},
                {"start_time": f"{date}T10:00:00", "end_time": f"{date}T10:30:00"},
                {"start_time": f"{date}T11:00:00", "end_time": f"{date}T11:30:00"},
                {"start_time": f"{date}T14:00:00", "end_time": f"{date}T14:30:00"},
                {"start_time": f"{date}T15:00:00", "end_time": f"{date}T15:30:00"},
                {"start_time": f"{date}T16:00:00", "end_time": f"{date}T16:30:00"}
            ],
            "existing_appointments": 0
        }

    async def get_doctor_availability_summary(self, doctor_id: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get availability summary for a doctor over a date range"""
        try:
            current_date = parser.parse(start_date).date()
            end_date_obj = parser.parse(end_date).date()

            total_days = 0
            available_days = 0
            total_slots = 0
            booked_slots = 0

            while current_date <= end_date_obj:
                date_str = current_date.isoformat()
                schedule = await self.get_doctor_schedule(doctor_id, date_str)

                total_days += 1
                if schedule.get('available', False):
                    available_days += 1
                    total_slots += len(schedule.get('available_slots', []))
                    booked_slots += schedule.get('existing_appointments', 0)

                current_date += timedelta(days=1)

            return {
                "period": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "total_days": total_days
                },
                "availability": {
                    "available_days": available_days,
                    "availability_rate": (available_days / total_days * 100) if total_days > 0 else 0
                },
                "capacity": {
                    "total_slots": total_slots,
                    "booked_slots": booked_slots,
                    "utilization_rate": (booked_slots / total_slots * 100) if total_slots > 0 else 0
                }
            }

        except Exception as e:
            self.logger.error(f"Error getting availability summary: {e}")
            raise