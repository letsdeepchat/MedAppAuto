"""
Test cases for the Conversation Agent
Tests intent classification, context management, and response generation
"""

import pytest
from datetime import datetime
from backend.agent.conversation_agent import ConversationAgent


class TestConversationAgent:
    """Test suite for ConversationAgent class"""

    @pytest.fixture
    def agent(self):
        """Create a fresh conversation agent for each test"""
        return ConversationAgent()

    def test_agent_initialization(self, agent):
        """Test that agent initializes with correct default values"""
        assert agent.current_context == 'greeting'
        assert agent.conversation_history == []
        assert agent.user_info == {}
        assert agent.appointment_preferences == {}

    def test_intent_classification_booking(self, agent):
        """Test booking-related intent classification"""
        # Direct booking intents
        assert agent._classify_intent("I want to book an appointment") == 'booking_request'
        assert agent._classify_intent("Schedule a consultation") == 'booking_request'
        assert agent._classify_intent("Make an appointment") == 'booking_request'

        # Rescheduling intents
        assert agent._classify_intent("I need to reschedule") == 'reschedule_request'
        assert agent._classify_intent("Change my appointment time") == 'reschedule_request'

        # Cancellation intents
        assert agent._classify_intent("Cancel my appointment") == 'cancel_request'
        assert agent._classify_intent("I want to delete my booking") == 'cancel_request'

    def test_intent_classification_faq(self, agent):
        """Test FAQ-related intent classification"""
        assert agent._classify_intent("What are your hours?") == 'faq_question'
        assert agent._classify_intent("Where are you located?") == 'faq_question'
        assert agent._classify_intent("Do you accept insurance?") == 'faq_question'
        assert agent._classify_intent("What's your cancellation policy?") == 'faq_question'

    def test_intent_classification_greeting(self, agent):
        """Test greeting intent classification"""
        assert agent._classify_intent("Hello") == 'greeting'
        assert agent._classify_intent("Hi there") == 'greeting'
        assert agent._classify_intent("Good morning") == 'greeting'

    def test_intent_classification_other(self, agent):
        """Test other/default intent classification"""
        assert agent._classify_intent("Thank you") == 'other'
        assert agent._classify_intent("That's helpful") == 'other'
        assert agent._classify_intent("Random message") == 'other'

    def test_context_update_booking_flow(self, agent):
        """Test context updates during booking flow"""
        # Start with greeting
        assert agent.current_context == 'greeting'

        # Booking request should move to understanding_needs
        agent._update_context('booking_request', "I want to book an appointment")
        assert agent.current_context == 'understanding_needs'

        # After setting appointment type, should move to slot_recommendation
        agent.appointment_preferences['type'] = 'General Consultation'
        agent._update_context('other', "tomorrow morning")
        # Note: This would need mock availability slots to fully test

    def test_context_update_faq_flow(self, agent):
        """Test context updates during FAQ flow"""
        agent.current_context = 'understanding_needs'

        # FAQ question should switch to FAQ context
        agent._update_context('faq_question', "What are your hours?")
        assert agent.current_context == 'faq'

        # After FAQ, should return to previous context
        agent._update_context('other', "Thanks for the info")
        assert agent.current_context == 'understanding_needs'

    def test_understanding_needs_response(self, agent):
        """Test response generation for understanding needs phase"""
        agent.current_context = 'understanding_needs'

        # Test appointment type recognition
        response = agent._handle_understanding_needs("I need a general consultation")
        assert "General Consultation" in response
        assert agent.appointment_preferences['type'] == 'General Consultation'

        response = agent._handle_understanding_needs("Follow-up visit")
        assert "Follow-up" in response
        assert agent.appointment_preferences['type'] == 'Follow-up'

    def test_slot_recommendation_response(self, agent):
        """Test slot recommendation response generation"""
        agent.current_context = 'slot_recommendation'
        agent.appointment_preferences['type'] = 'General Consultation'

        response = agent._handle_slot_recommendation("tomorrow morning")
        assert "available slots" in response.lower()
        assert "1." in response  # Should show numbered options

    def test_booking_confirmation_response(self, agent):
        """Test booking confirmation response generation"""
        agent.current_context = 'booking_confirmation'
        agent.appointment_preferences = {
            'type': 'General Consultation',
            'selected_slot': 'Tomorrow at 10:00 AM',
            'duration': 30
        }

        # Test with complete patient info
        message = "John Smith, 555-123-4567, john@email.com"
        response = agent._handle_booking_confirmation(message)

        assert "successfully booked" in response.lower()
        assert "APT" in response  # Should contain booking ID
        assert agent.current_context == 'greeting'  # Should reset context

    def test_faq_responses(self, agent):
        """Test FAQ response generation"""
        agent.current_context = 'faq'

        # Test hours FAQ
        response = agent._handle_faq("What are your hours?")
        assert "hours" in response.lower()
        assert "monday-friday" in response.lower()

        # Test location FAQ
        response = agent._handle_faq("Where are you located?")
        assert "location" in response.lower()
        assert "parking" in response.lower()

        # Test insurance FAQ
        response = agent._handle_faq("Do you accept insurance?")
        assert "insurance" in response.lower()
        assert "accepted" in response.lower()

    def test_appointment_management_responses(self, agent):
        """Test appointment management response generation"""
        # Test reschedule request
        response = agent._handle_appointment_management('reschedule_request', "I need to change my appointment")
        assert "reschedule" in response.lower()
        assert "confirmation number" in response.lower()

        # Test cancel request
        response = agent._handle_appointment_management('cancel_request', "Cancel my appointment")
        assert "cancel" in response.lower()
        assert "policy" in response.lower()

    def test_status_check_response(self, agent):
        """Test status check response generation"""
        agent.current_context = 'checking_status'

        response = agent._handle_status_check("Check my appointment status")
        assert "confirmation number" in response.lower()
        assert "date/time" in response.lower()

    def test_default_responses(self, agent):
        """Test default response generation for various intents"""
        # Test greeting response
        response = agent._get_default_response('greeting', "Hello")
        assert "scheduling assistant" in response.lower()
        assert "book" in response.lower()

        # Test booking request response
        response = agent._get_default_response('booking_request', "I want to book")
        assert "appointment" in response.lower()
        assert "General Consultation" in response

    def test_patient_info_extraction(self, agent):
        """Test patient information extraction from messages"""
        # Test complete info extraction
        message = "John Smith, 555-123-4567, john@email.com"
        info = agent._extract_patient_info(message)

        assert info['name'] == 'John Smith'
        assert info['phone'] == '555-123-4567'
        assert info['email'] == 'john@email.com'

        # Test incomplete info
        message = "John Smith"
        info = agent._extract_patient_info(message)
        assert info.get('name') == 'John Smith'
        assert 'phone' not in info

    def test_conversation_history(self, agent):
        """Test conversation history management"""
        # Initially empty
        assert agent.conversation_history == []

        # Add user message
        agent.conversation_history.append({
            'role': 'user',
            'content': 'Hello',
            'timestamp': datetime.now().isoformat()
        })

        assert len(agent.conversation_history) == 1
        assert agent.conversation_history[0]['role'] == 'user'
        assert agent.conversation_history[0]['content'] == 'Hello'

    def test_context_reset(self, agent):
        """Test context reset functionality"""
        # Set some state
        agent.current_context = 'booking_confirmation'
        agent.user_info = {'name': 'John'}
        agent.appointment_preferences = {'type': 'Consultation'}

        # Reset
        agent.reset_context()

        assert agent.current_context == 'greeting'
        assert agent.user_info == {}
        assert agent.appointment_preferences == {}

    @pytest.mark.asyncio
    async def test_process_message_basic_flow(self, agent):
        """Test the main process_message method"""
        # Test greeting
        result = await agent.process_message("Hello")

        assert 'response' in result
        assert 'context' in result
        assert 'intent' in result
        assert result['intent'] == 'greeting'
        assert "scheduling assistant" in result['response'].lower()

        # Check conversation history
        assert len(agent.conversation_history) == 2  # User + assistant
        assert agent.conversation_history[0]['role'] == 'user'
        assert agent.conversation_history[1]['role'] == 'assistant'

    @pytest.mark.asyncio
    async def test_process_message_booking_flow(self, agent):
        """Test booking flow through process_message"""
        # Start booking
        result = await agent.process_message("I want to book an appointment")
        assert result['intent'] == 'booking_request'
        assert agent.current_context == 'understanding_needs'

        # Specify appointment type
        result = await agent.process_message("General consultation")
        assert "General Consultation" in result['response']
        assert agent.appointment_preferences['type'] == 'General Consultation'

    @pytest.mark.asyncio
    async def test_process_message_faq_flow(self, agent):
        """Test FAQ flow through process_message"""
        # Ask FAQ
        result = await agent.process_message("What are your hours?")
        assert result['intent'] == 'faq_question'
        assert agent.current_context == 'faq'
        assert "monday-friday" in result['response'].lower()

    @pytest.mark.asyncio
    async def test_process_message_error_handling(self, agent):
        """Test error handling in process_message"""
        # This should handle gracefully even with invalid inputs
        result = await agent.process_message("")

        assert 'response' in result
        assert 'context' in result
        assert 'intent' in result
        # Should not crash, should return some response