# MedAppAuto - Medical Appointment Scheduling System

## Overview

MedAppAuto is an intelligent medical appointment scheduling system that combines conversational AI with automated booking capabilities. The system provides a seamless experience for patients to schedule, reschedule, and manage medical appointments through natural language conversations.

## Features

### 🤖 Conversational AI Agent
- Natural language processing for appointment scheduling
- Context-aware conversations
- Intelligent intent classification
- FAQ knowledge base with RAG (Retrieval-Augmented Generation)

### 📅 Smart Scheduling
- Real-time availability checking
- Multiple appointment types (General Consultation, Follow-up, Specialist visits, etc.)
- Doctor-specific scheduling
- Time zone and buffer time management
- Conflict resolution

### 🔄 Appointment Management
- Book new appointments
- Reschedule existing appointments
- Cancel appointments with policy enforcement
- Status checking and confirmations

### 🏥 Healthcare Integration
- Calendly API integration for calendar management
- Comprehensive doctor and clinic information
- Multi-language support
- Insurance provider information

### 🎨 Modern Web Interface
- Responsive React frontend with Material-UI
- Real-time chat interface
- User authentication and authorization
- Mobile-friendly design

## Architecture

### Backend (Python/FastAPI)
```
backend/
├── main.py                 # FastAPI application entry point
├── config.py              # Application configuration
├── agent/
│   └── conversation_agent.py  # Conversational AI logic
├── api/
│   └── calendly_service.py    # Calendly API integration
├── models/
│   └── appointment.py         # Pydantic data models
├── rag/
│   └── rag_service.py         # FAQ knowledge base service
└── tools/
    └── scheduling_logic.py    # Appointment scheduling logic
```

### Frontend (React)
```
frontend/
├── public/
│   └── index.html
└── src/
    ├── App.js              # Main React application
    ├── ChatInterface.js    # Chat component
    ├── index.js           # React entry point
    └── index.css          # Global styles
```

### Data
```
data/
├── clinic_info.json       # Clinic information and policies
└── doctor_schedule.json   # Doctor schedules and availability
```

## Installation

### Prerequisites
- Python 3.8+
- Node.js 16+
- npm or yarn

### Backend Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd MedAppAuto
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

### Frontend Setup

1. **Install Node.js dependencies**
   ```bash
   cd frontend
   npm install
   ```

2. **Build the frontend**
   ```bash
   npm run build
   ```

## Configuration

### Environment Variables (.env)

```env
# Database
DATABASE_NAME=medical_appointments
DATABASE_URL=mongodb://localhost:27017

# API Keys
CALENDLY_API_KEY=your_calendly_api_key
OPENAI_API_KEY=your_openai_api_key

# Application Settings
HOST=0.0.0.0
PORT=8000
DEBUG=True

# Clinic Settings
CLINIC_NAME=MedAppAuto Medical Center
```

## Running the Application

### Development Mode

1. **Start the backend server**
   ```bash
   python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Start the frontend development server**
   ```bash
   cd frontend
   npm start
   ```

3. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Production Mode

1. **Build the frontend**
   ```bash
   cd frontend
   npm run build
   ```

2. **Start the production server**
   ```bash
   python backend/main.py
   ```

## API Endpoints

### Chat Endpoints
- `POST /api/chat` - Process chat messages
- `POST /api/faq` - Query FAQ knowledge base

### Appointment Endpoints
- `GET /api/availability` - Get available time slots
- `POST /api/book` - Book a new appointment
- `PUT /api/appointments/{id}` - Reschedule appointment
- `DELETE /api/appointments/{id}` - Cancel appointment
- `GET /api/appointments/{id}` - Get appointment details

### Authentication Endpoints
- `POST /api/auth/login` - User login
- `POST /api/auth/register` - User registration

## Testing

### Run Tests
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_conversation_agent.py

# Run with coverage
pytest --cov=backend tests/
```

### Test Structure
```
tests/
├── conftest.py                    # Pytest configuration and fixtures
├── test_conversation_agent.py     # Conversation agent tests
├── test_api_endpoints.py          # API endpoint tests
├── test_integration.py            # Integration tests
└── test_edge_cases.py             # Edge case tests
```

## Data Files

### Clinic Information (`data/clinic_info.json`)
Contains comprehensive clinic data including:
- Contact information
- Operating hours
- Services offered
- Insurance providers accepted
- Languages spoken
- Facility information
- Clinic policies

### Doctor Schedules (`data/doctor_schedule.json`)
Contains doctor information including:
- Doctor profiles and specialties
- Weekly schedules
- Appointment types offered
- Language capabilities

## Usage Examples

### Booking an Appointment
```
User: "I need to schedule a general consultation"
Agent: "I'd be happy to help you schedule a General Consultation (30 min). What day would work best for you?"

User: "Tomorrow morning"
Agent: "Based on your preference, here are the next available slots for your General Consultation:

1. Monday, November 4 at 9:00 AM
2. Monday, November 4 at 9:30 AM
3. Monday, November 4 at 10:00 AM
4. Monday, November 4 at 10:30 AM
5. Monday, November 4 at 11:00 AM

Which time slot works best for you? Please reply with the number (1-5)."

User: "2"
Agent: "Great! I've selected Monday, November 4 at 9:30 AM. Please provide your information to complete the booking: name, phone, and email."

User: "John Smith, 555-123-4567, john@email.com"
Agent: "Perfect! I've successfully booked your General Consultation.

📋 Booking Details:
• Confirmation #: APT20241103123045
• Patient: John Smith
• Date/Time: Monday, November 4 at 9:30 AM
• Type: General Consultation
• Duration: 30 minutes

You'll receive a confirmation email shortly. If you need to reschedule or cancel, please provide this confirmation number."
```

### Asking Clinic Information
```
User: "What are your operating hours?"
Agent: "🕐 Clinic Hours:
• Monday-Friday: 8:00 AM - 6:00 PM
• Saturday: 9:00 AM - 2:00 PM
• Sunday: Closed
• Major holidays: Closed

We recommend scheduling appointments during regular business hours."
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Email: support@medappauto.com
- Documentation: https://docs.medappauto.com
- Issues: https://github.com/medappauto/issues

## Roadmap

### Version 1.1.0
- [ ] Multi-language support
- [ ] Advanced scheduling algorithms
- [ ] Integration with EHR systems
- [ ] Patient portal features

### Version 1.2.0
- [ ] Mobile application
- [ ] Voice interaction capabilities
- [ ] Advanced analytics dashboard
- [ ] Third-party integrations

---

**MedAppAuto** - Making healthcare appointments effortless through intelligent automation.
