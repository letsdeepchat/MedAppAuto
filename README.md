# MedAppAuto - Medical Appointment Scheduling System

An intelligent, conversational medical appointment scheduling system that automates the booking process through natural language interactions. Built with FastAPI backend and React frontend, featuring AI-powered conversation agents and comprehensive scheduling capabilities.

## 🚀 Features

### Core Functionality
- **Conversational AI Agent**: Natural language processing for appointment scheduling
- **Intelligent Scheduling**: Smart availability checking and conflict resolution
- **Multi-Specialty Support**: 25+ medical specialties with detailed doctor schedules
- **Real-time Availability**: Dynamic slot management and booking
- **FAQ System**: Comprehensive knowledge base for clinic information
- **Secure Authentication**: JWT-based user authentication and authorization

### Appointment Management
- **Multiple Appointment Types**: General Consultation, Follow-up, Physical Exam, Specialist Consultation
- **Flexible Scheduling**: Time zone support and buffer time management
- **Rescheduling & Cancellation**: Easy modification of existing appointments
- **Confirmation System**: Automated booking confirmations and reminders

### User Experience
- **Responsive Design**: Modern Material-UI interface
- **Real-time Chat**: Instant messaging with the AI assistant
- **Context Awareness**: Intelligent conversation flow management
- **Mobile Friendly**: Optimized for all device sizes

## 🏗️ Architecture

### Backend (FastAPI)
- **Framework**: FastAPI with async support
- **Database**: MongoDB with Motor driver
- **Authentication**: JWT tokens with secure password hashing
- **AI Integration**: OpenAI GPT models for conversation processing
- **Vector Database**: ChromaDB for FAQ knowledge base
- **External APIs**: Calendly integration for calendar management

### Frontend (React)
- **Framework**: React 18 with hooks
- **UI Library**: Material-UI (MUI) components
- **State Management**: React state with local storage persistence
- **HTTP Client**: Fetch API with automatic token handling
- **Responsive Design**: Mobile-first approach

### Data Layer
- **Clinic Information**: Comprehensive JSON data with 30+ services, policies, and facilities
- **Doctor Schedules**: 25 doctors across multiple specialties with detailed availability
- **Knowledge Base**: RAG system for intelligent FAQ responses

## 📋 Prerequisites

- **Python**: 3.8+
- **Node.js**: 14+
- **MongoDB**: 4.4+
- **npm** or **yarn**

## 🛠️ Installation & Setup

### Backend Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd MedAppAuto
   ```

2. **Create Python virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Start MongoDB**
   ```bash
   # Ensure MongoDB is running on default port 27017
   mongod
   ```

6. **Run the backend server**
   ```bash
   python backend/main.py
   ```
   Server will start on `http://localhost:8000`

### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd frontend
   ```

2. **Install Node.js dependencies**
   ```bash
   npm install
   ```

3. **Start the development server**
   ```bash
   npm start
   ```
   Frontend will be available on `http://localhost:3000`

## 🔧 Configuration

### Environment Variables (.env)

```env
# Database
MONGODB_URL=mongodb://localhost:27017/medappauto

# Authentication
JWT_SECRET=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# AI Integration
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-3.5-turbo

# Calendly Integration (Optional)
CALENDLY_API_KEY=your-calendly-api-key
CALENDLY_BASE_URL=https://api.calendly.com/v1

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=true
```

## 🚀 Usage

### Starting the Application

1. **Start Backend**: `python backend/main.py`
2. **Start Frontend**: `cd frontend && npm start`
3. **Access Application**: Open `http://localhost:3000` in your browser

### User Registration & Login

1. **Register**: Create a new account with username and password
2. **Login**: Authenticate to access the scheduling system
3. **Chat Interface**: Start conversing with the AI assistant

### Scheduling Appointments

**Example Conversation:**
```
User: I need to schedule a general consultation
Assistant: I'd be happy to help you schedule a General Consultation (30 minutes). What day would work best for you?

User: Tomorrow morning
Assistant: Based on your preference, here are the next available slots for your General Consultation:

1. Monday, November 1 at 9:00 AM
2. Monday, November 1 at 10:00 AM
3. Monday, November 1 at 11:00 AM
4. Monday, November 1 at 2:00 PM
5. Monday, November 1 at 3:00 PM

Which time slot works best for you? Please reply with the number (1-5).

User: 2
Assistant: Perfect! I've successfully booked your General Consultation.

📋 Booking Details:
• Confirmation #: APT20241101100001
• Patient: John Doe
• Date/Time: Monday, November 1 at 10:00 AM
• Type: General Consultation
• Duration: 30 minutes

You'll receive a confirmation email shortly.
```

### FAQ Queries

The system can answer questions about:
- Clinic hours and location
- Services and specialties
- Insurance and billing
- Appointment policies
- Parking and accessibility

## 📁 Project Structure

```
MedAppAuto/
├── backend/
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py               # Configuration settings
│   ├── agent/
│   │   └── conversation_agent.py # AI conversation agent
│   ├── api/
│   │   └── calendly_service.py  # Calendly API integration
│   ├── models/
│   │   └── appointment.py       # Pydantic models
│   ├── rag/
│   │   └── rag_service.py       # RAG knowledge base service
│   └── tools/
│       └── scheduling_logic.py  # Scheduling algorithms
├── frontend/
│   ├── src/
│   │   ├── App.js              # Main React component
│   │   ├── ChatInterface.js    # Chat UI component
│   │   └── index.js            # React entry point
│   └── package.json            # Node.js dependencies
├── data/
│   ├── clinic_info.json        # Clinic information and FAQs
│   └── doctor_schedule.json    # Doctor schedules and availability
├── tests/
│   ├── test_conversation_agent.py
│   ├── test_api_endpoints.py
│   ├── test_integration.py
│   └── test_edge_cases.py
├── requirements.txt            # Python dependencies
├── .env.example               # Environment template
└── README.md                  # This file
```

## 🧪 Testing

### Backend Tests
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_conversation_agent.py

# Run with coverage
pytest --cov=backend tests/
```

### Frontend Tests
```bash
cd frontend
npm test
```

## 🔒 Security Features

- **JWT Authentication**: Secure token-based authentication
- **Password Hashing**: bcrypt for secure password storage
- **CORS Protection**: Configured for allowed origins only
- **Input Validation**: Pydantic models for data validation
- **Rate Limiting**: API rate limiting to prevent abuse
- **Audit Logging**: Comprehensive logging for security events

## 📊 API Documentation

Once the backend is running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Key Endpoints

- `POST /api/chat` - Main chat endpoint
- `POST /api/faq` - FAQ query endpoint
- `GET /api/availability` - Check available slots
- `POST /api/book` - Book appointment
- `PUT /api/appointments/{id}` - Reschedule appointment
- `DELETE /api/appointments/{id}` - Cancel appointment

## 🚀 Deployment

### Production Backend
```bash
# Using uvicorn
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4

# Using gunicorn
gunicorn backend.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### Production Frontend
```bash
cd frontend
npm run build
# Serve build/ directory with nginx or similar
```

### Docker Deployment
```dockerfile
# Build backend image
docker build -t medappauto-backend .

# Build frontend image
docker build -t medappauto-frontend ./frontend

# Run with docker-compose
docker-compose up
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -am 'Add feature'`
4. Push to branch: `git push origin feature-name`
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- **Issues**: GitHub Issues
- **Documentation**: This README and inline code documentation
- **Community**: GitHub Discussions

## 🔄 Future Enhancements

- **Multi-language Support**: Additional language options for international users
- **Advanced AI Features**: Integration with more sophisticated LLM models
- **Mobile App**: Native mobile applications for iOS and Android
- **Video Consultations**: Integrated telemedicine capabilities
- **Analytics Dashboard**: Administrative insights and reporting
- **Integration APIs**: Third-party EHR system integrations
- **Voice Interface**: Voice-based appointment scheduling
- **Smart Notifications**: AI-powered reminder systems

---

**MedAppAuto** - Revolutionizing medical appointment scheduling with AI-powered conversational interfaces.
