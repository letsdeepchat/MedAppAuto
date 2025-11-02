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

        # Use database service to get available slots
        if preferred_date:
            slots = await database_service.get_available_slots(appointment_type, preferred_date)
        else:
            # Default to today if no date provided
            from datetime import datetime
            today = datetime.now().strftime("%Y-%m-%d")
            slots = await database_service.get_available_slots(appointment_type, today)

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

        # Calculate end time based on appointment type
        duration_map = {
            "General Consultation": 30,
            "Follow-up": 15,
            "Physical Exam": 45,
            "Specialist Consultation": 60
        }
        duration = duration_map.get(appointment_type, 30)

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

        # Check availability for new time
        appointment_type = request.appointment_type
        start_time = request.start_time

        duration_map = {
            "General Consultation": 30,
            "Follow-up": 15,
            "Physical Exam": 45,
            "Specialist Consultation": 60
        }
        duration = duration_map.get(appointment_type, 30)

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
async def cancel_endpoint(appointment_id: str, reason: Optional[str] = None):
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
            }
        }
    }

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

# Background task for Calendly event creation
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