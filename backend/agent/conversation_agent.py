"""
Conversational Agent for Medical Appointment Scheduling
Handles natural language conversations, intent classification, and context management
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import re
import json

try:
    from config import settings
except ImportError:
    # Mock settings for testing
    class MockSettings:
        clinic_name = "Medical Center"
    settings = MockSettings()


class ConversationAgent:
    """Intelligent conversational agent for medical appointment scheduling"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Conversation state
        self.conversation_history: List[Dict[str, Any]] = []
        self.current_context: str = 'greeting'  # greeting, understanding_needs, slot_recommendation, booking_confirmation, faq, reschedule_request, cancel_request
        self.user_info: Dict[str, Any] = {}
        self.appointment_preferences: Dict[str, Any] = {}
        self.previous_context: Optional[str] = None

        # Appointment types configuration
        self.appointment_types = {
            'General Consultation': {'duration': 30, 'description': 'Comprehensive medical consultation'},
            'Follow-up': {'duration': 15, 'description': 'Follow-up visit after treatment'},
            'Physical Exam': {'duration': 45, 'description': 'Complete physical examination'},
            'Specialist Consultation': {'duration': 60, 'description': 'Consultation with medical specialist'}
        }

    def process_message_sync(self, user_message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Synchronous version of process_message for testing

        Args:
            user_message: The user's input message
            context: Additional context information

        Returns:
            Dict containing response, updated context, and detected intent
        """
        try:
            # Add user message to history
            self.conversation_history.append({
                'role': 'user',
                'content': user_message,
                'timestamp': datetime.now().isoformat()
            })

            # Classify intent
            intent = self._classify_intent(user_message)

            # Update context based on intent and current state
            self._update_context(intent, user_message)

            # Generate response based on context and intent
            response = self._generate_response(user_message, intent)

            # Add assistant response to history
            self.conversation_history.append({
                'role': 'assistant',
                'content': response,
                'timestamp': datetime.now().isoformat(),
                'intent': intent,
                'context': self.current_context
            })

            return {
                'response': response,
                'context': {
                    'current_context': self.current_context,
                    'appointment_preferences': self.appointment_preferences,
                    'user_info': self.user_info
                },
                'intent': intent
            }

        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            return {
                'response': "I'm experiencing technical difficulties. Please try again or contact our clinic directly.",
                'context': {'current_context': self.current_context},
                'intent': 'error'
            }

    async def process_message(self, user_message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Main method to process user messages and generate responses

        Args:
            user_message: The user's input message
            context: Additional context information

        Returns:
            Dict containing response, updated context, and detected intent
        """
        # For now, just call the sync version
        return self.process_message_sync(user_message, context)

    def _classify_intent(self, message: str) -> str:
        """
        Classify the user's intent from their message

        Args:
            message: User's input message

        Returns:
            Classified intent string
        """
        message_lower = message.lower()

        # Booking related intents
        if any(word in message_lower for word in ['book', 'schedule', 'appointment', 'make', 'set up']):
            return 'booking_request'

        # Rescheduling intents
        if any(word in message_lower for word in ['reschedule', 'change', 'move', 'different time', 'rescheduled', 'need to reschedule', 'i need to reschedule']):
            return 'reschedule_request'
        elif any(word in message_lower for word in ['i need to reschedule']):
            return 'reschedule_request'

        # Cancellation intents
        if any(word in message_lower for word in ['cancel', 'delete', 'remove', 'cancellation', 'what\'s your cancellation policy', 'cancellation policy']):
            return 'cancel_request'

        # Status checking intents
        if any(word in message_lower for word in ['status', 'check', 'when', 'confirmation']):
            return 'status_check'

        # FAQ related intents
        if any(word in message_lower for word in ['hours', 'time', 'location', 'address', 'parking',
                                                 'insurance', 'payment', 'billing', 'policy', 'covid', 'located', 'cancellation']):
            return 'faq_question'

        # Greeting intents
        if any(word in message_lower for word in ['hello', 'hi', 'hey', 'good morning', 'good afternoon']):
            return 'greeting'

        # Default to other
        return 'other'

    def _update_context(self, intent: str, message: str):
        """
        Update conversation context based on intent and message

        Args:
            intent: Classified intent
            message: User's message
        """
        # Context switching logic
        if intent == 'booking_request' and self.current_context in ['greeting', 'faq']:
            self.current_context = 'understanding_needs'
        elif intent == 'faq_question' and self.current_context not in ['booking_confirmation']:
            # Store current booking context to return to later
            if self.current_context != 'faq':
                self.previous_context = self.current_context
            self.current_context = 'faq'
        elif intent in ['reschedule_request', 'cancel_request']:
            self.current_context = 'managing_appointment'
        elif intent == 'status_check':
            self.current_context = 'checking_status'
        elif self.current_context == 'understanding_needs' and self.appointment_preferences.get('type'):
            # Move to slot recommendation if we have appointment type
            available_slots = self._get_mock_available_slots(message)
            if available_slots:
                self.current_context = 'slot_recommendation'
        elif intent == 'reschedule_request':
            self.current_context = 'reschedule_request'
        elif intent == 'cancel_request':
            self.current_context = 'cancel_request'
        elif self.current_context == 'reschedule_request':
            # Handle reschedule request
            return f"I understand you need to reschedule your appointment. To help you with this, I need to know your current appointment details. Could you please provide your appointment ID or the date/time of your current appointment?"
        elif self.current_context == 'cancel_request':
            # Handle cancel request
            return f"I understand you want to cancel your appointment. To proceed with the cancellation, I need to verify your appointment details. Could you please provide your appointment ID or the date/time of your appointment?"
        elif self.current_context == 'slot_recommendation':
            # Check if user selected a slot
            slot_match = re.search(r'\b(\d+)\b', message)
            if slot_match:
                slot_number = int(slot_match.group(1))
                if 1 <= slot_number <= 5:
                    self.current_context = 'booking_confirmation'
        elif self.current_context == 'booking_confirmation':
            # Extract patient info and complete booking
            patient_info = self._extract_patient_info(message)
            if patient_info.get('name'):
                self.current_context = 'booking_complete'

        # Return to previous context after FAQ
        if self.current_context == 'faq' and self.previous_context and not any(word in message.lower() for word in ['what', 'how', 'when', 'where', 'can']):
            self.current_context = self.previous_context
            self.previous_context = None

    def _generate_response(self, message: str, intent: str) -> str:
        """
        Generate appropriate response based on context and intent

        Args:
            message: User's message
            intent: Classified intent

        Returns:
            Generated response string
        """
        # Context-specific response generation
        if self.current_context == 'understanding_needs':
            return self._handle_understanding_needs(message)
        elif self.current_context == 'slot_recommendation':
            return self._handle_slot_recommendation(message)
        elif self.current_context == 'booking_confirmation':
            return self._handle_booking_confirmation(message)
        elif self.current_context == 'faq':
            return self._handle_faq(message)
        elif self.current_context == 'managing_appointment':
            return self._handle_appointment_management(intent, message)
        elif self.current_context == 'checking_status':
            return self._handle_status_check(message)
        else:
            # Default responses by intent
            return self._get_default_response(intent, message)

    def _handle_understanding_needs(self, message: str) -> str:
        """Handle understanding user appointment needs"""
        message_lower = message.lower()

        # Extract appointment type
        if 'general' in message_lower or 'consultation' in message_lower:
            self.appointment_preferences['type'] = 'General Consultation'
            self.appointment_preferences['duration'] = 30
            return "Perfect! I'd be happy to help you schedule a General Consultation (30 minutes). What day would work best for you? For example, you could say 'tomorrow morning' or 'next Tuesday afternoon'."
        elif 'follow' in message_lower or 'check' in message_lower:
            self.appointment_preferences['type'] = 'Follow-up'
            self.appointment_preferences['duration'] = 15
            return "Great! Let's schedule your Follow-up visit (15 minutes). What day would work best for you? Please let me know your preferred date and time."
        elif 'physical' in message_lower or 'exam' in message_lower:
            self.appointment_preferences['type'] = 'Physical Exam'
            self.appointment_preferences['duration'] = 45
            return "I'll help you schedule a Physical Exam (45 minutes). What day would work best for you? Please specify your preferred date and time."
        elif 'specialist' in message_lower:
            self.appointment_preferences['type'] = 'Specialist Consultation'
            self.appointment_preferences['duration'] = 60
            return "I'll assist you with scheduling a Specialist Consultation (60 minutes). What day would work best for you? Please let me know your preferred date and time."
        else:
            return "I'd be happy to help you schedule an appointment. We offer:\n• General Consultation (30 min)\n• Follow-up (15 min)\n• Physical Exam (45 min)\n• Specialist Consultation (60 min)\n\nWhat type of appointment would you like?"

    def _handle_slot_recommendation(self, message: str) -> str:
        """Handle slot recommendation and selection"""
        available_slots = self._get_mock_available_slots(message)

        if not available_slots:
            return "I don't have any slots available for that time. Would you like me to show you slots for the next few days instead? Or would you prefer a different appointment type?"

        return f"Based on your preference, here are the next available slots for your {self.appointment_preferences.get('type', 'appointment')}:\n\n" + \
               "\n".join([f"{i+1}. {slot}" for i, slot in enumerate(available_slots)]) + \
               "\n\nWhich time slot works best for you? Please reply with the number (1-5) or let me know if none of these work."

    def _handle_booking_confirmation(self, message: str) -> str:
        """Handle booking confirmation and patient info collection"""
        patient_info = self._extract_patient_info(message)

        if patient_info.get('name'):
            # Complete booking
            booking_id = f"APT{datetime.now().strftime('%Y%m%d%H%M%S')}"
            self.current_context = 'greeting'  # Reset context

            return f"Perfect! I've successfully booked your {self.appointment_preferences.get('type', 'appointment')}.\n\n📋 **Booking Details:**\n• **Confirmation #: {booking_id}\n• **Patient:** {patient_info['name']}\n• **Date/Time:** {self.appointment_preferences.get('selected_slot', 'TBD')}\n• **Type:** {self.appointment_preferences.get('type')}\n• **Duration:** {self.appointment_preferences.get('duration')} minutes\n\nYou'll receive a confirmation email shortly. If you need to reschedule or cancel, please provide this confirmation number.\n\nIs there anything else I can help you with today?"
        else:
            return "I need your complete information to book the appointment. Please provide your full name, phone number, and email address. For example: 'John Smith, 555-123-4567, john@email.com'"

    def _handle_faq(self, message: str) -> str:
        """Handle FAQ queries"""
        message_lower = message.lower()

        if 'hours' in message_lower or 'time' in message_lower:
            return "🕐 **Clinic Hours:**\n• Monday-Friday: 8:00 AM - 6:00 PM\n• Saturday: 9:00 AM - 2:00 PM\n• Sunday: Closed\n• Major holidays: Closed\n\nWe recommend scheduling appointments during regular business hours."
        elif 'location' in message_lower or 'address' in message_lower:
            return "📍 **Clinic Location:**\n123 Medical Center Drive\nDowntown Healthcare District\n\n🚗 **Parking:** Free parking available in our underground garage. Valet parking for elderly patients and those with mobility issues.\n\n🚌 **Public Transport:** Easily accessible by bus routes 15, 22, and 45."
        elif 'insurance' in message_lower:
            return "💳 **Accepted Insurance:**\n• Blue Cross Blue Shield\n• Aetna\n• Cigna\n• UnitedHealthcare\n• Medicare\n\n📞 **Verification:** Please call our billing department at (555) 123-4567 to verify your specific coverage and copays."
        elif 'parking' in message_lower:
            return "🚗 **Parking Information:**\n• Free parking in underground garage\n• Valet service available for elderly and mobility-impaired patients\n• Street parking available (2-hour limit)\n• Accessible parking spaces reserved near entrance"
        elif 'payment' in message_lower or 'billing' in message_lower:
            return "💰 **Payment Methods:**\n• Cash, credit cards (Visa, MC, AmEx)\n• Debit cards\n• Personal checks\n• Online payments via patient portal\n\n📋 **Billing:** Due at time of service unless prior arrangements made."
        elif 'cancel' in message_lower or 'cancellation' in message_lower:
            return "❌ **Cancellation Policy:**\n• 24+ hours notice: No fee\n• Within 24 hours: $50 fee\n• Same-day: $100 fee\n• No-shows: $100 fee\n\n📞 Call us or use patient portal to cancel."
        elif 'late' in message_lower or 'arrive' in message_lower:
            return "⏰ **Late Arrival Policy:**\n• Arrive 15+ minutes late: May need rescheduling\n• Please call if you'll be late\n• We reserve the right to reschedule if significantly delayed\n• Consider traffic/parking time when planning arrival"
        elif 'covid' in message_lower or 'mask' in message_lower:
            return "😷 **COVID-19 Policy:**\n• Masks required in common areas\n• Temperature checks at check-in\n• Social distancing maintained\n• Enhanced cleaning protocols\n• Reschedule if experiencing symptoms"
        else:
            return "❓ **Clinic Information:** I can help with:\n• 📅 Hours & scheduling\n• 📍 Location & parking\n• 💳 Insurance & billing\n• 📋 Policies (cancellation, late arrival, COVID)\n• 🏥 Services & procedures\n\nWhat specific information are you looking for?"

    def _handle_appointment_management(self, intent: str, message: str) -> str:
        """Handle appointment management (reschedule/cancel)"""
        if intent == 'reschedule_request':
            return "I can help you reschedule your appointment. Could you please provide your appointment confirmation number (starts with APT) or the original date/time of your appointment?"
        elif intent == 'cancel_request':
            return "I can help you cancel your appointment. Please note our 24-hour cancellation policy - cancellations within 24 hours may incur a $50 fee. Could you provide your appointment confirmation number or the date/time of your appointment?"
        else:
            return "How can I help you manage your appointment today?"

    def _handle_status_check(self, message: str) -> str:
        """Handle appointment status checking"""
        return "I'd be happy to check your appointment status. Could you please provide your appointment confirmation number (starts with APT) or the date/time of your appointment?"

    def _get_default_response(self, intent: str, message: str) -> str:
        """Get default responses for various intents"""
        if intent == 'greeting':
            return f"Hello! I'm {settings.clinic_name}'s intelligent scheduling assistant. I can help you:\n\n🗓️ **Schedule appointments** - Book consultations, follow-ups, exams\n❓ **Answer questions** - Clinic hours, location, insurance, policies\n🔄 **Manage bookings** - Reschedule or cancel appointments\n📋 **Check status** - View your upcoming appointments\n\nHow can I assist you today?"
        elif self.current_context == 'slot_recommendation':
            return f"Hello! I'm {settings.clinic_name}'s intelligent scheduling assistant. I can help you:\n\n🗓️ **Schedule appointments** - Book consultations, follow-ups, exams\n❓ **Answer questions** - Clinic hours, location, insurance, policies\n🔄 **Manage bookings** - Reschedule or cancel appointments\n📋 **Check status** - View your upcoming appointments\n\nHow can I assist you today?"
        elif intent == 'booking_request':
            self.current_context = 'understanding_needs'
            return "I'd be happy to help you schedule an appointment! We offer:\n• General Consultation (30 min)\n• Follow-up (15 min)\n• Physical Exam (45 min)\n• Specialist Consultation (60 min)\n\nWhat type of appointment would you like to schedule?"
        else:
            return "🤔 I'm here to help with appointment scheduling and clinic information. You can:\n\n• **Book appointments** - Tell me what type you need\n• **Ask questions** - About hours, location, insurance, etc.\n• **Manage bookings** - Reschedule or cancel existing appointments\n\nWhat would you like to help with today?"

    def _get_mock_available_slots(self, message: str) -> List[str]:
        """Generate mock available time slots based on user preference"""
        now = datetime.now()
        slots = []

        # Parse time preferences
        message_lower = message.lower()
        start_date = now

        if 'tomorrow' in message_lower:
            start_date = now + timedelta(days=1)
        elif 'next week' in message_lower:
            start_date = now + timedelta(days=7)
        elif 'next' in message_lower and 'monday' in message_lower:
            days_until_monday = (7 - now.weekday()) % 7 or 7
            start_date = now + timedelta(days=days_until_monday)

        # Generate mock slots
        for i in range(5):
            slot_date = start_date.replace(hour=9 + (i // 2), minute=(i % 2) * 30, second=0, microsecond=0)
            if slot_date.weekday() >= 5:  # Skip weekends
                slot_date += timedelta(days=(7 - slot_date.weekday()))

            time_string = slot_date.strftime("%A, %B %d at %I:%M %p")
            slots.append(time_string)

        return slots

    def _extract_patient_info(self, message: str) -> Dict[str, str]:
        """Extract patient information from message"""
        # Simple extraction - in production, use NLP
        parts = [part.strip() for part in message.split(',')]
        if len(parts) >= 3:
            return {
                'name': parts[0],
                'phone': parts[1],
                'email': parts[2],
                'reason': parts[3] if len(parts) > 3 else 'General consultation'
            }
        elif len(parts) == 1 and parts[0]:
            # Handle single name input
            return {
                'name': parts[0],
                'phone': '',
                'email': '',
                'reason': 'General consultation'
            }
        return {}

    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get the conversation history"""
        return self.conversation_history

    def reset_context(self):
        """Reset conversation context"""
        self.current_context = 'greeting'
        self.user_info = {}
        self.appointment_preferences = {}
        self.previous_context = None