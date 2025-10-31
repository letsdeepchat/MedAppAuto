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
from rag.rag_service import RAGService
from api.calendly_service import CalendlyService
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

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Main chat endpoint for conversational agent"""
    try:
        result = await conversation_agent.process_message(request.message, request.context)
        return ChatResponse(
            response=result["response"],
            context=result["context"],
            intent=result["intent"]
        )
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/faq", response_model=FAQResponse)
async def faq_endpoint(request: FAQRequest):
    """FAQ query endpoint using RAG"""
    try:
        result = await rag_service.query_faqs(request.query)
        return FAQResponse(
            answer=result["answer"],
            sources=result["sources"]
        )
    except Exception as e:
        logger.error(f"FAQ endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/availability", response_model=AvailabilityResponse)
async def availability_endpoint(request: AvailabilityRequest):
    """Get available appointment slots"""
    try:
        slots = await scheduling_logic.get_available_slots(
            request.appointment_type,
            request.preferred_date
        )
        return AvailabilityResponse(slots=slots)
    except Exception as e:
        logger.error(f"Availability endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/book", response_model=BookingResponse)
async def booking_endpoint(request: BookingRequest, background_tasks: BackgroundTasks):
    """Book an appointment"""
    try:
        # Validate booking
        validation = scheduling_logic.validate_booking(
            request.appointment_type,
            request.start_time,
            request.patient_info
        )

        if not validation["is_valid"]:
            raise HTTPException(status_code=400, detail=validation["errors"])

        # Create booking
        booking = await scheduling_logic.create_booking(
            request.appointment_type,
            request.start_time,
            request.patient_info
        )

        # Schedule background task for Calendly integration if available
        if settings.CALENDLY_API_KEY:
            background_tasks.add_task(
                calendly_service.create_event,
                booking["id"],
                request.appointment_type,
                request.start_time,
                request.patient_info
            )

        return BookingResponse(
            booking_id=booking["id"],
            status="confirmed",
            details=booking
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Booking endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.put("/api/appointments/{appointment_id}", response_model=BookingResponse)
async def reschedule_endpoint(appointment_id: str, request: BookingRequest):
    """Reschedule an appointment"""
    try:
        result = await scheduling_logic.reschedule_appointment(
            appointment_id,
            request.start_time,
            request.appointment_type
        )

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])

        return BookingResponse(
            booking_id=appointment_id,
            status="rescheduled",
            details=result
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reschedule endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/api/appointments/{appointment_id}")
async def cancel_endpoint(appointment_id: str, reason: Optional[str] = None):
    """Cancel an appointment"""
    try:
        result = await scheduling_logic.cancel_appointment(appointment_id, reason)

        if not result["can_cancel"]:
            raise HTTPException(status_code=400, detail="Cannot cancel appointment")

        return {
            "message": "Appointment cancelled successfully",
            "fee": result["fee"],
            "policy_message": result["policy_message"]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cancel endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/appointments/{appointment_id}")
async def get_appointment_endpoint(appointment_id: str):
    """Get appointment details"""
    try:
        appointment = await scheduling_logic.get_appointment(appointment_id)
        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")
        return appointment
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get appointment endpoint error: {e}")
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

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    try:
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