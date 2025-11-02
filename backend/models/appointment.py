"""
Pydantic models for appointment scheduling system
"""

from pydantic import BaseModel, Field, field_validator, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class AppointmentStatus(str, Enum):
    CONFIRMED = "confirmed"
    PENDING = "pending"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class AppointmentType(BaseModel):
    """Dynamic appointment type model"""
    id: str = Field(..., description="Unique identifier for appointment type")
    name: str = Field(..., description="Display name of appointment type")
    duration_minutes: int = Field(..., description="Duration in minutes")
    description: Optional[str] = Field(None, description="Description of the appointment type")
    price: Optional[float] = Field(None, description="Price for the appointment")
    is_active: bool = Field(default=True, description="Whether this type is currently available")
    color: Optional[str] = Field(None, description="Color code for UI display")


class Doctor(BaseModel):
    """Doctor model for dynamic scheduling"""
    id: str = Field(..., description="Unique doctor identifier")
    name: str = Field(..., description="Doctor's full name")
    specialty: str = Field(..., description="Medical specialty")
    email: EmailStr = Field(..., description="Doctor's email")
    phone: Optional[str] = Field(None, description="Doctor's phone number")
    appointment_types: List[str] = Field(default_factory=list, description="List of appointment type IDs this doctor handles")
    languages: List[str] = Field(default_factory=list, description="Languages spoken by doctor")
    is_active: bool = Field(default=True, description="Whether doctor is currently active")
    bio: Optional[str] = Field(None, description="Doctor's biography")
    qualifications: List[str] = Field(default_factory=list, description="Doctor's qualifications")


class WorkingHours(BaseModel):
    """Working hours for doctors"""
    day_of_week: int = Field(..., ge=0, le=6, description="Day of week (0=Monday, 6=Sunday)")
    start_time: str = Field(..., pattern=r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', description="Start time in HH:MM format")
    end_time: str = Field(..., pattern=r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', description="End time in HH:MM format")
    is_available: bool = Field(default=True, description="Whether doctor is available on this day")


class DoctorSchedule(BaseModel):
    """Doctor's complete schedule"""
    doctor_id: str = Field(..., description="Doctor ID this schedule belongs to")
    working_hours: List[WorkingHours] = Field(default_factory=list, description="Working hours for each day")
    time_off: List[Dict[str, Any]] = Field(default_factory=list, description="Time off periods")
    buffer_time_minutes: int = Field(default=15, description="Buffer time between appointments")


class ClinicInfo(BaseModel):
    """Dynamic clinic information"""
    name: str = Field(..., description="Clinic name")
    address: str = Field(..., description="Clinic address")
    phone: str = Field(..., description="Clinic phone number")
    email: EmailStr = Field(..., description="Clinic email")
    website: Optional[str] = Field(None, description="Clinic website")
    timezone: str = Field(default="America/New_York", description="Clinic timezone")
    policies: Dict[str, str] = Field(default_factory=dict, description="Clinic policies")
    services: List[str] = Field(default_factory=list, description="Available services")
    insurance_accepted: List[str] = Field(default_factory=list, description="Accepted insurance providers")
    languages_spoken: List[str] = Field(default_factory=list, description="Languages spoken at clinic")


class PatientInfo(BaseModel):
    """Patient information model"""
    name: str = Field(..., min_length=1, description="Patient's full name")
    email: EmailStr = Field(..., description="Patient's email address")
    phone: str = Field(..., pattern=r'^\+?1?[-.\s]?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})$', description="Patient's phone number")
    date_of_birth: Optional[str] = Field(None, pattern=r'^\d{4}-\d{2}-\d{2}$', description="Patient's date of birth (YYYY-MM-DD)")
    insurance_provider: Optional[str] = Field(None, description="Patient's insurance provider")
    insurance_id: Optional[str] = Field(None, description="Patient's insurance ID")
    emergency_contact: Optional[Dict[str, str]] = Field(None, description="Emergency contact information")
    medical_notes: Optional[str] = Field(None, description="Medical notes or special requirements")

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        """Basic phone validation"""
        if v:
            # Remove all non-digit characters
            digits = ''.join(filter(str.isdigit, v))
            if len(digits) < 10:
                raise ValueError('Phone number must have at least 10 digits')
        return v


class AppointmentCreate(BaseModel):
    """Model for creating new appointments"""
    appointment_type_id: str = Field(..., description="Appointment type ID")
    doctor_id: str = Field(..., description="Doctor ID")
    start_time: str = Field(..., description="Start time in ISO format")
    patient_info: PatientInfo = Field(..., description="Patient information")
    notes: Optional[str] = Field(None, description="Additional appointment notes")


class AppointmentUpdate(BaseModel):
    """Model for updating appointments"""
    appointment_type_id: Optional[str] = Field(None, description="Appointment type ID")
    doctor_id: Optional[str] = Field(None, description="Doctor ID")
    start_time: Optional[str] = Field(None, description="Start time in ISO format")
    patient_info: Optional[PatientInfo] = Field(None, description="Patient information")
    notes: Optional[str] = Field(None, description="Additional appointment notes")
    status: Optional[AppointmentStatus] = Field(None, description="Appointment status")


class Appointment(BaseModel):
    """Complete appointment model"""
    id: str = Field(..., description="Unique appointment identifier")
    booking_id: str = Field(..., description="Human-readable booking ID")
    appointment_type: AppointmentType = Field(..., description="Appointment type details")
    doctor: Doctor = Field(..., description="Doctor details")
    start_time: str = Field(..., description="Start time in ISO format")
    end_time: str = Field(..., description="End time in ISO format")
    patient_info: PatientInfo = Field(..., description="Patient information")
    status: AppointmentStatus = Field(default=AppointmentStatus.CONFIRMED, description="Appointment status")
    notes: Optional[str] = Field(None, description="Additional appointment notes")
    calendly_event_id: Optional[str] = Field(None, description="Calendly event ID")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    cancelled_at: Optional[str] = Field(None, description="Cancellation timestamp")


class NotificationSettings(BaseModel):
    """Notification preferences"""
    email_reminders: bool = Field(default=True, description="Send email reminders")
    sms_reminders: bool = Field(default=False, description="Send SMS reminders")
    reminder_hours_before: List[int] = Field(default=[24, 2], description="Hours before appointment to send reminders")


class User(BaseModel):
    """User model for authentication"""
    id: str = Field(..., description="Unique user identifier")
    email: EmailStr = Field(..., description="User email")
    role: str = Field(..., description="User role (admin, doctor, patient)")
    name: str = Field(..., description="User full name")
    is_active: bool = Field(default=True, description="Whether user is active")
    notification_settings: NotificationSettings = Field(default_factory=NotificationSettings, description="Notification preferences")
    created_at: str = Field(..., description="Account creation timestamp")