"""
Appointment Models for MedAppAuto
Pydantic models for appointment data validation and serialization
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class AppointmentType(str, Enum):
    """Enumeration of appointment types"""
    GENERAL_CONSULTATION = "General Consultation"
    FOLLOW_UP = "Follow-up"
    PHYSICAL_EXAM = "Physical Exam"
    SPECIALIST_CONSULTATION = "Specialist Consultation"
    WELL_CHILD_VISIT = "Well Child Visit"
    SICK_VISIT = "Sick Visit"
    VACCINATIONS = "Vaccinations"
    DEVELOPMENTAL_SCREENING = "Developmental Screening"
    ECG = "ECG"
    STRESS_TEST = "Stress Test"
    ECHOCARDIOGRAM = "Echocardiogram"
    SKIN_BIOPSY = "Skin Biopsy"
    MOHS_SURGERY = "Mohs Surgery"
    LASER_TREATMENT = "Laser Treatment"
    X_RAY = "X-ray"
    MRI = "MRI"
    PHYSICAL_THERAPY = "Physical Therapy"
    ANNUAL_EXAM = "Annual Exam"
    PAP_SMEAR = "Pap Smear"
    MAMMOGRAM = "Mammogram"
    BIRTH_CONTROL = "Birth Control"
    CONSULTATION = "Consultation"
    EYE_EXAM = "Eye Exam"
    GLAUCOMA_SCREENING = "Glaucoma Screening"
    CATARACT_SURGERY = "Cataract Surgery"
    EMERGENCY_CARE = "Emergency Care"
    URGENT_CARE = "Urgent Care"
    TRAUMA_CARE = "Trauma Care"
    INITIAL_CONSULTATION = "Initial Consultation"
    MEDICATION_MANAGEMENT = "Medication Management"
    THERAPY_SESSION = "Therapy Session"
    NEUROLOGICAL_EXAM = "Neurological Exam"
    PSA_TEST = "PSA Test"
    ULTRASOUND = "Ultrasound"
    BIOPSY = "Biopsy"
    KIDNEY_DISEASE_CONSULTATION = "Kidney Disease Consultation"
    DIALYSIS_MANAGEMENT = "Dialysis Management"
    TRANSPLANT_EVALUATION = "Transplant Evaluation"
    DIABETES_CONSULTATION = "Diabetes Consultation"
    THYROID_EVALUATION = "Thyroid Evaluation"
    HORMONE_THERAPY = "Hormone Therapy"
    BLOOD_TESTS = "Blood Tests"
    INITIAL_CONSULTATION_ONCOLOGY = "Initial Consultation"
    RADIATION_THERAPY = "Radiation Therapy"
    ARTHRITIS_CONSULTATION = "Arthritis Consultation"
    AUTOIMMUNE_DISEASE_MANAGEMENT = "Autoimmune Disease Management"
    JOINT_INJECTION = "Joint Injection"
    LUNG_FUNCTION_TEST = "Lung Function Test"
    ASTHMA_MANAGEMENT = "Asthma Management"
    COPD_TREATMENT = "COPD Treatment"
    SLEEP_STUDY = "Sleep Study"
    INFECTION_CONSULTATION = "Infection Consultation"
    TRAVEL_MEDICINE = "Travel Medicine"
    HIV_CARE = "HIV Care"
    HEPATITIS_MANAGEMENT = "Hepatitis Management"
    SPORTS_INJURY_EVALUATION = "Sports Injury Evaluation"
    PERFORMANCE_ENHANCEMENT = "Performance Enhancement"
    CONCUSSION_MANAGEMENT = "Concussion Management"
    ALLERGY_TESTING = "Allergy Testing"
    IMMUNOTHERAPY = "Immunotherapy"
    FOOD_ALLERGY_CONSULTATION = "Food Allergy Consultation"
    COSMETIC_CONSULTATION = "Cosmetic Consultation"
    RECONSTRUCTIVE_SURGERY = "Reconstructive Surgery"
    SKIN_CANCER_TREATMENT = "Skin Cancer Treatment"
    HAND_SURGERY = "Hand Surgery"
    CT_SCAN = "CT Scan"
    COLONOSCOPY = "Colonoscopy"
    ENDOSCOPY = "Endoscopy"
    LIVER_DISEASE_MANAGEMENT = "Liver Disease Management"
    PULMONOLOGY_CONSULTATION = "Pulmonology Consultation"
    RHEUMATOLOGY_CONSULTATION = "Rheumatology Consultation"
    INFECTIOUS_DISEASES_CONSULTATION = "Infectious Diseases Consultation"
    SPORTS_MEDICINE_CONSULTATION = "Sports Medicine Consultation"
    ALLERGY_AND_IMMUNOLOGY_CONSULTATION = "Allergy & Immunology Consultation"
    PLASTIC_SURGERY_CONSULTATION = "Plastic Surgery Consultation"
    PATHOLOGY_ANALYSIS = "Biopsy Analysis"
    BLOOD_TEST_REVIEW = "Blood Test Review"
    TISSUE_ANALYSIS = "Tissue Analysis"
    GENERAL_SURGERY_CONSULTATION = "Pre-operative Consultation"
    POST_OPERATIVE_FOLLOW_UP = "Post-operative Follow-up"
    SURGICAL_PROCEDURE = "Surgical Procedure"
    ANESTHESIOLOGY_EVALUATION = "Pre-operative Evaluation"
    ANESTHESIOLOGY_CONSULTATION = "Anesthesia Consultation"
    NEPHROLOGY_CONSULTATION = "Nephrology Consultation"
    ENDOCRINOLOGY_CONSULTATION = "Endocrinology Consultation"
    ONCOLOGY_CONSULTATION = "Oncology Consultation"
    PHYSICAL_MEDICINE_EVALUATION = "Initial Evaluation"
    PAIN_MANAGEMENT = "Pain Management"
    REHABILITATION = "Rehabilitation"
    RADIOLOGY_PROCEDURE = "Radiology Procedure"


class AppointmentStatus(str, Enum):
    """Enumeration of appointment statuses"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"


class PatientInfo(BaseModel):
    """Patient information model"""
    name: str = Field(..., description="Patient's full name", min_length=1, max_length=100)
    phone: str = Field(..., description="Patient's phone number", min_length=10, max_length=15)
    email: str = Field(..., description="Patient's email address", min_length=5, max_length=100)
    date_of_birth: Optional[str] = Field(None, description="Patient's date of birth (YYYY-MM-DD)")
    insurance_provider: Optional[str] = Field(None, description="Insurance provider name")
    insurance_id: Optional[str] = Field(None, description="Insurance ID number")
    emergency_contact_name: Optional[str] = Field(None, description="Emergency contact name")
    emergency_contact_phone: Optional[str] = Field(None, description="Emergency contact phone")
    medical_history: Optional[str] = Field(None, description="Brief medical history")
    allergies: Optional[str] = Field(None, description="Known allergies")
    current_medications: Optional[str] = Field(None, description="Current medications")

    @validator('email')
    def validate_email(cls, v):
        if v and '@' not in v:
            raise ValueError('Invalid email format')
        return v

    @validator('phone')
    def validate_phone(cls, v):
        if v:
            # Remove all non-digit characters
            digits = ''.join(filter(str.isdigit, v))
            if len(digits) < 10:
                raise ValueError('Phone number must have at least 10 digits')
        return v


class AppointmentBase(BaseModel):
    """Base appointment model"""
    appointment_type: AppointmentType = Field(..., description="Type of appointment")
    doctor_id: str = Field(..., description="ID of the assigned doctor")
    doctor_name: str = Field(..., description="Name of the assigned doctor")
    start_time: datetime = Field(..., description="Appointment start time")
    end_time: datetime = Field(..., description="Appointment end time")
    duration_minutes: int = Field(..., description="Appointment duration in minutes", gt=0)
    patient_info: PatientInfo = Field(..., description="Patient information")
    notes: Optional[str] = Field(None, description="Additional appointment notes")
    reason_for_visit: Optional[str] = Field(None, description="Reason for the visit")


class AppointmentCreate(AppointmentBase):
    """Model for creating new appointments"""
    pass


class AppointmentUpdate(BaseModel):
    """Model for updating existing appointments"""
    appointment_type: Optional[AppointmentType] = None
    doctor_id: Optional[str] = None
    doctor_name: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(None, gt=0)
    patient_info: Optional[PatientInfo] = None
    notes: Optional[str] = None
    reason_for_visit: Optional[str] = None
    status: Optional[AppointmentStatus] = None


class Appointment(AppointmentBase):
    """Complete appointment model with system fields"""
    id: str = Field(..., description="Unique appointment identifier")
    booking_id: str = Field(..., description="Booking confirmation ID")
    status: AppointmentStatus = Field(default=AppointmentStatus.PENDING, description="Appointment status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    cancelled_at: Optional[datetime] = Field(None, description="Cancellation timestamp")
    cancellation_reason: Optional[str] = Field(None, description="Reason for cancellation")
    rescheduled_from: Optional[str] = Field(None, description="Original appointment ID if rescheduled")
    calendly_event_id: Optional[str] = Field(None, description="Calendly event ID if synced")
    reminder_sent: bool = Field(default=False, description="Whether reminder was sent")
    follow_up_required: bool = Field(default=False, description="Whether follow-up is required")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AppointmentSummary(BaseModel):
    """Summary model for appointment listings"""
    id: str
    booking_id: str
    appointment_type: AppointmentType
    doctor_name: str
    start_time: datetime
    status: AppointmentStatus
    patient_name: str

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TimeSlot(BaseModel):
    """Model for available time slots"""
    start_time: datetime = Field(..., description="Slot start time")
    end_time: datetime = Field(..., description="Slot end time")
    doctor_id: str = Field(..., description="Available doctor ID")
    doctor_name: str = Field(..., description="Available doctor name")
    appointment_type: AppointmentType = Field(..., description="Supported appointment type")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class BookingRequest(BaseModel):
    """Model for booking requests"""
    appointment_type: AppointmentType = Field(..., description="Type of appointment")
    start_time: datetime = Field(..., description="Requested start time")
    patient_info: PatientInfo = Field(..., description="Patient information")
    preferred_doctor_id: Optional[str] = Field(None, description="Preferred doctor ID")
    notes: Optional[str] = Field(None, description="Additional notes")


class BookingResponse(BaseModel):
    """Model for booking responses"""
    booking_id: str = Field(..., description="Booking confirmation ID")
    appointment_id: str = Field(..., description="Appointment ID")
    status: str = Field(..., description="Booking status")
    appointment_details: Appointment = Field(..., description="Complete appointment details")
    confirmation_message: str = Field(..., description="Confirmation message for patient")


class CancellationRequest(BaseModel):
    """Model for cancellation requests"""
    reason: Optional[str] = Field(None, description="Reason for cancellation")
    notify_patient: bool = Field(default=True, description="Whether to notify patient")


class CancellationResponse(BaseModel):
    """Model for cancellation responses"""
    appointment_id: str = Field(..., description="Cancelled appointment ID")
    status: str = Field(..., description="Cancellation status")
    refund_amount: Optional[float] = Field(None, description="Refund amount if applicable")
    cancellation_fee: Optional[float] = Field(None, description="Cancellation fee if applicable")
    policy_message: str = Field(..., description="Cancellation policy message")


class RescheduleRequest(BaseModel):
    """Model for reschedule requests"""
    new_start_time: datetime = Field(..., description="New appointment start time")
    reason: Optional[str] = Field(None, description="Reason for rescheduling")
    preferred_doctor_id: Optional[str] = Field(None, description="Preferred doctor for rescheduled appointment")


class RescheduleResponse(BaseModel):
    """Model for reschedule responses"""
    appointment_id: str = Field(..., description="Rescheduled appointment ID")
    old_start_time: datetime = Field(..., description="Original start time")
    new_start_time: datetime = Field(..., description="New start time")
    status: str = Field(..., description="Reschedule status")
    confirmation_message: str = Field(..., description="Confirmation message")