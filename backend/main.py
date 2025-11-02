"""
Medical Appointment Scheduling Agent - FastAPI Backend
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uvicorn
import logging
from datetime import datetime, timezone
import os

from agent.conversation_agent import ConversationAgent
from services.rag_service import RAGService
from services.calendly_service import CalendlyService
from services.database_service import DatabaseService
from services.notification_service import NotificationService
from services.analytics_service import AnalyticsService
from services.scheduling_service import SchedulingService
from tools.scheduling_logic import SchedulingLogic
from models.appointment import Appointment, AppointmentCreate, AppointmentUpdate
from config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Medical Appointment Scheduling Agent",
    description="Intelligent conversational agent for medical appointment scheduling",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
conversation_agent = ConversationAgent()
rag_service = RAGService()
calendly_service = CalendlyService()
database_service = DatabaseService()
notification_service = NotificationService()
analytics_service = AnalyticsService(database_service)
scheduling_service = SchedulingService(database_service)
scheduling_logic = SchedulingLogic()

# Pydantic models for API
class ChatRequest(BaseModel):
    message: str = Field(..., description="User's message")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")

class ChatResponse(BaseModel):
    response: str = Field(..., description="Agent's response")
    context: Dict[str, Any] = Field(..., description="Updated context")
    intent: str = Field(..., description="Detected intent")

class FAQRequest(BaseModel):
    query: str = Field(..., description="FAQ query")

class FAQResponse(BaseModel):
    answer: str = Field(..., description="FAQ answer")
    sources: List[str] = Field(..., description="Source documents")

class AvailabilityRequest(BaseModel):
    appointment_type: str = Field(..., description="Type of appointment")
    preferred_date: Optional[str] = Field(None, description="Preferred date (YYYY-MM-DD)")

class AvailabilityResponse(BaseModel):
    slots: List[Dict[str, Any]] = Field(..., description="Available time slots")

class AppointmentTypesResponse(BaseModel):
    types: List[Dict[str, Any]] = Field(..., description="Appointment types")

class DoctorsResponse(BaseModel):
    doctors: List[Dict[str, Any]] = Field(..., description="Doctors")

class ClinicInfoResponse(BaseModel):
    clinic: Dict[str, Any] = Field(..., description="Clinic information")

class BookingRequest(BaseModel):
    appointment_type: str = Field(..., description="Type of appointment")
    start_time: str = Field(..., description="Start time in ISO format")
    patient_info: Dict[str, str] = Field(..., description="Patient information")

class BookingResponse(BaseModel):
    booking_id: str = Field(..., description="Booking confirmation ID")
    status: str = Field(..., description="Booking status")
    details: Dict[str, Any] = Field(..., description="Booking details")

# API Routes
@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Medical Appointment Scheduling Agent API", "status": "healthy"}

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """Main chat endpoint for conversational agent"""
    try:
        result = await conversation_agent.process_message(request.message, request.context)
        return {
            "response": result["response"],
            "context": result["context"],
            "intent": result["intent"]
        }
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/faq")
async def faq_endpoint(request: FAQRequest):
    """FAQ query endpoint using RAG"""
    try:
        result = await rag_service.query_faqs(request.query)
        return {
            "answer": result["answer"],
            "sources": result["sources"]
        }
    except Exception as e:
        logger.error(f"FAQ endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/availability")
async def availability_endpoint(appointment_type: str, preferred_date: Optional[str] = None):
    """Get available appointment slots"""
    try:
        # Basic validation
        if not appointment_type:
            raise HTTPException(status_code=400, detail="Appointment type is required")

        # Get appointment type details first
        appointment_types = await database_service.get_appointment_types()
        apt_type = next((t for t in appointment_types if t.get('name') == appointment_type), None)

        if not apt_type:
            raise HTTPException(status_code=400, detail="Invalid appointment type")

        # Get doctors who handle this appointment type
        doctors = await database_service.get_doctors()
        available_doctors = [d for d in doctors if apt_type['id'] in d.get('appointment_types', [])]

        if not available_doctors:
            return {"slots": []}

        # Use scheduling service to get available slots for the first available doctor
        # In production, you might want to return slots for all doctors or let user choose
        doctor_id = available_doctors[0]['id']

        if preferred_date:
            slots = await scheduling_service.find_available_slots(
                doctor_id, apt_type['id'], preferred_date, apt_type.get('duration_minutes', 30)
            )
        else:
            # Default to today if no date provided
            from datetime import datetime
            today = datetime.now().strftime("%Y-%m-%d")
            slots = await scheduling_service.find_available_slots(
                doctor_id, apt_type['id'], today, apt_type.get('duration_minutes', 30)
            )

        return {"slots": slots}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Availability endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/book")
async def booking_endpoint(request: BookingRequest, background_tasks: BackgroundTasks):
    """Book an appointment"""
    try:
        # Basic validation
        if not request.start_time or not request.appointment_type:
            raise HTTPException(status_code=400, detail="Missing required fields")

        # Check availability first
        appointment_type = request.appointment_type
        start_time = request.start_time

        # Get appointment type details
        appointment_types = await database_service.get_appointment_types()
        apt_type = next((t for t in appointment_types if t.get('name') == appointment_type), None)

        if not apt_type:
            raise HTTPException(status_code=400, detail="Invalid appointment type")

        duration = apt_type.get('duration_minutes', 30)

        from datetime import datetime, timedelta
        from dateutil import parser
        start_dt = parser.parse(start_time)
        end_dt = start_dt + timedelta(minutes=duration)

        # Check for conflicts
        is_available = await database_service.check_availability(
            appointment_type, start_time, duration
        )

        if not is_available:
            raise HTTPException(status_code=409, detail="Time slot not available")

        # Generate booking ID
        booking_id = f"APT{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Prepare appointment data
        appointment_data = {
            "booking_id": booking_id,
            "appointment_type": appointment_type,
            "start_time": start_time,
            "end_time": end_dt.isoformat(),
            "patient_info": request.patient_info,
            "status": "confirmed",
            "calendly_event_id": None
        }

        # Save to database
        created_appointment = await database_service.create_appointment(appointment_data)

        # Send confirmation notification
        background_tasks.add_task(
            send_notification_background,
            "confirmation",
            created_appointment
        )

        # Schedule Calendly event in background if configured
        if settings.CALENDLY_API_KEY:
            background_tasks.add_task(
                create_calendly_event_background,
                booking_id,
                appointment_type,
                start_time,
                request.patient_info
            )

        return {
            "booking_id": booking_id,
            "status": "confirmed",
            "details": {
                "appointment_type": appointment_type,
                "start_time": start_time,
                "end_time": end_dt.isoformat(),
                "patient_info": request.patient_info
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Booking endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.put("/api/appointments/{appointment_id}")
async def reschedule_endpoint(appointment_id: str, request: BookingRequest):
    """Reschedule an appointment"""
    try:
        # Basic validation
        if not appointment_id or not appointment_id.startswith('APT'):
            raise HTTPException(status_code=400, detail="Invalid appointment ID")

        # Check if appointment exists
        existing_appointment = await database_service.get_appointment(appointment_id)
        if not existing_appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")

        # Get appointment type details
        appointment_types = await database_service.get_appointment_types()
        apt_type = next((t for t in appointment_types if t.get('name') == request.appointment_type), None)

        if not apt_type:
            raise HTTPException(status_code=400, detail="Invalid appointment type")

        appointment_type = request.appointment_type
        start_time = request.start_time
        duration = apt_type.get('duration_minutes', 30)

        from datetime import timedelta
        from dateutil import parser
        start_dt = parser.parse(start_time)
        end_dt = start_dt + timedelta(minutes=duration)

        is_available = await database_service.check_availability(
            appointment_type, start_time, duration
        )

        if not is_available:
            raise HTTPException(status_code=409, detail="New time slot not available")

        # Update appointment
        update_data = {
            "appointment_type": appointment_type,
            "start_time": start_time,
            "end_time": end_dt.isoformat(),
            "patient_info": request.patient_info
        }

        updated_appointment = await database_service.update_appointment(appointment_id, update_data)

        # Cancel old Calendly event and create new one if configured
        if settings.CALENDLY_API_KEY and existing_appointment.get("calendly_event_id"):
            # Cancel old event
            await calendly_service.cancel_event(existing_appointment["calendly_event_id"])

            # Create new event
            result = await calendly_service.create_event(
                appointment_id, appointment_type, start_time, request.patient_info
            )

            if "event_id" in result and not result.get("mock"):
                await database_service.update_appointment(appointment_id, {
                    "calendly_event_id": result["event_id"]
                })

        return {
            "booking_id": appointment_id,
            "status": "rescheduled",
            "details": {
                "appointment_type": appointment_type,
                "start_time": start_time,
                "end_time": end_dt.isoformat(),
                "patient_info": request.patient_info
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reschedule endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/api/appointments/{appointment_id}")
async def cancel_endpoint(appointment_id: str, background_tasks: BackgroundTasks, reason: Optional[str] = None):
    """Cancel an appointment"""
    try:
        # Basic validation
        if not appointment_id or not appointment_id.startswith('APT'):
            raise HTTPException(status_code=400, detail="Invalid appointment ID")

        # Check if appointment exists
        existing_appointment = await database_service.get_appointment(appointment_id)
        if not existing_appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")

        # Cancel in database
        cancelled = await database_service.cancel_appointment(appointment_id)
        if not cancelled:
            raise HTTPException(status_code=500, detail="Failed to cancel appointment")

        # Send cancellation notification
        background_tasks.add_task(
            send_notification_background,
            "cancellation",
            existing_appointment
        )

        # Cancel Calendly event if it exists
        if settings.CALENDLY_API_KEY and existing_appointment.get("calendly_event_id"):
            await calendly_service.cancel_event(existing_appointment["calendly_event_id"])

        return {"message": "Appointment cancelled successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cancel endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/appointments/{appointment_id}")
async def get_appointment_endpoint(appointment_id: str):
    """Get appointment details"""
    try:
        # Basic validation
        if not appointment_id or not appointment_id.startswith('APT'):
            raise HTTPException(status_code=400, detail="Invalid appointment ID")

        # Get appointment from database
        appointment = await database_service.get_appointment(appointment_id)
        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")

        return appointment
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get appointment endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/appointment-types")
async def get_appointment_types_endpoint():
    """Get all available appointment types"""
    try:
        types = await database_service.get_appointment_types()
        return {"types": types}
    except Exception as e:
        logger.error(f"Appointment types endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/doctors")
async def get_doctors_endpoint():
    """Get all available doctors"""
    try:
        doctors = await database_service.get_doctors()
        return {"doctors": doctors}
    except Exception as e:
        logger.error(f"Doctors endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/clinic-info")
async def get_clinic_info_endpoint():
    """Get clinic information"""
    try:
        clinic_info = await database_service.get_clinic_info()
        if not clinic_info:
            # Return default clinic info if none exists
            return {
                "clinic": {
                    "name": "Medical Center",
                    "address": "123 Medical Drive",
                    "phone": "555-123-4567",
                    "email": "info@medicalcenter.com",
                    "timezone": "America/New_York",
                    "policies": {},
                    "services": ["General Consultation", "Follow-up", "Physical Exam"],
                    "insurance_accepted": ["Blue Cross", "Aetna"],
                    "languages_spoken": ["English", "Spanish"]
                }
            }
        return {"clinic": clinic_info}
    except Exception as e:
        logger.error(f"Clinic info endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/mock-data")
async def mock_data_endpoint():
    """Mock data endpoint for testing"""
    return {
        "username": "testuser",
        "password": "testpass",
        "date": "2025-11-02",
        "time": "07:00:00",
        "clinic_info": {
            "name": "Medical Center",
            "hours": "Mon-Fri 9AM-5PM",
            "phone": "555-123-4567"
        },
        "appointment_types": [
            {"name": "General Consultation", "duration": 30},
            {"name": "Follow-up", "duration": 15},
            {"name": "Physical Exam", "duration": 45},
            {"name": "Specialist Consultation", "duration": 60}
        ]
    }

@app.get("/api-docs")
async def swagger_docs_endpoint():
    """Swagger documentation endpoint"""
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "Medical Appointment Scheduling Agent API",
            "version": "1.0.0",
            "description": "API for medical appointment scheduling"
        },
        "paths": {
            "/api/chat": {"post": {"summary": "Chat endpoint"}},
            "/api/faq": {"post": {"summary": "FAQ query endpoint"}},
            "/api/availability": {"get": {"summary": "Get available slots"}},
            "/api/book": {"post": {"summary": "Book appointment"}},
            "/api/appointments/{id}": {
                "get": {"summary": "Get appointment"},
                "put": {"summary": "Reschedule appointment"},
                "delete": {"summary": "Cancel appointment"}
            },
            "/api/appointment-types": {"get": {"summary": "Get appointment types"}},
            "/api/doctors": {"get": {"summary": "Get doctors"}},
            "/api/clinic-info": {"get": {"summary": "Get clinic information"}}
        }
    }

# Admin endpoints for managing dynamic data
@app.post("/api/admin/appointment-types")
async def create_appointment_type_endpoint(appointment_type: Dict[str, Any]):
    """Create a new appointment type (Admin only)"""
    try:
        created_type = await database_service.create_appointment_type(appointment_type)
        return created_type
    except Exception as e:
        logger.error(f"Create appointment type error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/admin/doctors")
async def create_doctor_endpoint(doctor: Dict[str, Any]):
    """Create a new doctor (Admin only)"""
    try:
        created_doctor = await database_service.create_doctor(doctor)
        return created_doctor
    except Exception as e:
        logger.error(f"Create doctor error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.put("/api/admin/clinic-info")
async def update_clinic_info_endpoint(clinic_data: Dict[str, Any]):
    """Update clinic information (Admin only)"""
    try:
        updated_clinic = await database_service.update_clinic_info(clinic_data)
        return updated_clinic
    except Exception as e:
        logger.error(f"Update clinic info error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Analytics endpoints
@app.get("/api/analytics/appointments")
async def get_appointment_analytics(start_date: Optional[str] = None, end_date: Optional[str] = None):
    """Get appointment analytics"""
    try:
        metrics = await analytics_service.get_appointment_metrics(start_date, end_date)
        return metrics
    except Exception as e:
        logger.error(f"Appointment analytics error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/analytics/doctors")
async def get_doctor_analytics(doctor_id: Optional[str] = None, days: int = 30):
    """Get doctor performance analytics"""
    try:
        performance = await analytics_service.get_doctor_performance(doctor_id, days)
        return performance
    except Exception as e:
        logger.error(f"Doctor analytics error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/analytics/clinic")
async def get_clinic_analytics(days: int = 30):
    """Get clinic efficiency analytics"""
    try:
        efficiency = await analytics_service.get_clinic_efficiency(days)
        return efficiency
    except Exception as e:
        logger.error(f"Clinic analytics error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/analytics/revenue")
async def get_revenue_analytics(start_date: Optional[str] = None, end_date: Optional[str] = None):
    """Get revenue analytics"""
    try:
        revenue = await analytics_service.get_revenue_report(start_date, end_date)
        return revenue
    except Exception as e:
        logger.error(f"Revenue analytics error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/analytics/dashboard")
async def get_dashboard_summary():
    """Get dashboard summary data"""
    try:
        summary = await analytics_service.get_dashboard_summary()
        return summary
    except Exception as e:
        logger.error(f"Dashboard summary error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# Background tasks
async def create_calendly_event_background(booking_id: str, appointment_type: str,
                                         start_time: str, patient_info: Dict[str, str]):
    """Background task to create Calendly event"""
    try:
        result = await calendly_service.create_event(
            booking_id, appointment_type, start_time, patient_info
        )

        # Update appointment with Calendly event ID if successful
        if "event_id" in result and not result.get("mock"):
            await database_service.update_appointment(booking_id, {
                "calendly_event_id": result["event_id"]
            })

        logger.info(f"Calendly event created for booking {booking_id}")
    except Exception as e:
        logger.error(f"Failed to create Calendly event for booking {booking_id}: {e}")

async def send_notification_background(notification_type: str, appointment: Dict[str, Any]):
    """Background task to send notifications"""
    try:
        if notification_type == "confirmation":
            await notification_service.send_appointment_confirmation(appointment)
        elif notification_type == "reminder":
            hours_before = appointment.get("hours_before", 24)
            await notification_service.send_appointment_reminder(appointment, hours_before)
        elif notification_type == "cancellation":
            await notification_service.send_appointment_cancellation(appointment)

        logger.info(f"Notification sent: {notification_type} for booking {appointment.get('booking_id')}")
    except Exception as e:
        logger.error(f"Failed to send {notification_type} notification: {e}")

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    try:
        # Initialize database service
        await database_service.initialize()

        # Initialize RAG service
        await rag_service.initialize()

        # Initialize Calendly service if API key is available
        if settings.CALENDLY_API_KEY:
            await calendly_service.initialize()

        logger.info("All services initialized successfully")
    except Exception as e:
        logger.error(f"Startup initialization error: {e}")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )