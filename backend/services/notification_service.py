"""
Notification Service for email and SMS reminders
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List, Optional
import httpx
from datetime import datetime, timezone

try:
    from config import settings
except ImportError:
    # Mock settings for testing
    class MockSettings:
        SMTP_SERVER = "smtp.gmail.com"
        SMTP_PORT = 587
        SMTP_USERNAME = None
        SMTP_PASSWORD = None
        TWILIO_ACCOUNT_SID = None
        TWILIO_AUTH_TOKEN = None
        TWILIO_PHONE_NUMBER = None
    settings = MockSettings()


class NotificationService:
    """Service for sending notifications via email and SMS"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.twilio_sid = settings.TWILIO_ACCOUNT_SID
        self.twilio_token = settings.TWILIO_AUTH_TOKEN
        self.twilio_phone = settings.TWILIO_PHONE_NUMBER

    async def send_email(self, to_email: str, subject: str, body: str, html_body: Optional[str] = None) -> bool:
        """Send email notification"""
        if not self.smtp_username or not self.smtp_password:
            self.logger.warning("SMTP credentials not configured, skipping email")
            return False

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.smtp_username
            msg['To'] = to_email

            # Add text body
            text_part = MIMEText(body, 'plain')
            msg.attach(text_part)

            # Add HTML body if provided
            if html_body:
                html_part = MIMEText(html_body, 'html')
                msg.attach(html_part)

            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.sendmail(self.smtp_username, to_email, msg.as_string())
            server.quit()

            self.logger.info(f"Email sent to {to_email}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    async def send_sms(self, to_phone: str, message: str) -> bool:
        """Send SMS notification via Twilio"""
        if not self.twilio_sid or not self.twilio_token or not self.twilio_phone:
            self.logger.warning("Twilio credentials not configured, skipping SMS")
            return False

        try:
            async with httpx.AsyncClient() as client:
                url = f"https://api.twilio.com/2010-04-01/Accounts/{self.twilio_sid}/Messages.json"
                data = {
                    'From': self.twilio_phone,
                    'To': to_phone,
                    'Body': message
                }
                auth = (self.twilio_sid, self.twilio_token)

                response = await client.post(url, data=data, auth=auth)

                if response.status_code == 201:
                    self.logger.info(f"SMS sent to {to_phone}")
                    return True
                else:
                    self.logger.error(f"Failed to send SMS: {response.status_code} - {response.text}")
                    return False

        except Exception as e:
            self.logger.error(f"Failed to send SMS to {to_phone}: {e}")
            return False

    async def send_appointment_reminder(self, appointment: Dict[str, Any], hours_before: int) -> bool:
        """Send appointment reminder notification"""
        try:
            patient_info = appointment.get('patient_info', {})
            appointment_type = appointment.get('appointment_type', {})
            doctor = appointment.get('doctor', {})

            # Format reminder message
            reminder_time = f"{hours_before} hour{'s' if hours_before != 1 else ''}"
            appointment_time = datetime.fromisoformat(appointment['start_time'].replace('Z', '+00:00'))

            subject = f"Appointment Reminder - {reminder_time} away"

            text_body = f"""
Dear {patient_info.get('name', 'Patient')},

This is a reminder for your upcoming appointment:

Appointment Type: {appointment_type.get('name', 'Medical Appointment')}
Doctor: {doctor.get('name', 'Dr. Assigned')}
Date & Time: {appointment_time.strftime('%B %d, %Y at %I:%M %p')}
Location: Medical Center

Please arrive 15 minutes early for check-in.

If you need to reschedule or cancel, please contact us.

Best regards,
Medical Center Team
            """.strip()

            html_body = f"""
<html>
<body>
<h2>Appointment Reminder</h2>
<p>Dear {patient_info.get('name', 'Patient')},</p>

<p>This is a reminder for your upcoming appointment:</p>

<ul>
<li><strong>Appointment Type:</strong> {appointment_type.get('name', 'Medical Appointment')}</li>
<li><strong>Doctor:</strong> {doctor.get('name', 'Dr. Assigned')}</li>
<li><strong>Date & Time:</strong> {appointment_time.strftime('%B %d, %Y at %I:%M %p')}</li>
<li><strong>Location:</strong> Medical Center</li>
</ul>

<p>Please arrive 15 minutes early for check-in.</p>

<p>If you need to reschedule or cancel, please contact us.</p>

<p>Best regards,<br>Medical Center Team</p>
</body>
</html>
            """

            # Send email if patient has email
            email_sent = False
            if patient_info.get('email'):
                email_sent = await self.send_email(
                    patient_info['email'],
                    subject,
                    text_body,
                    html_body
                )

            # Send SMS if patient has phone and SMS is enabled in settings
            sms_sent = False
            if patient_info.get('phone'):
                sms_body = f"Reminder: Your {appointment_type.get('name', 'appointment')} with {doctor.get('name', 'Dr. Assigned')} is in {reminder_time}. {appointment_time.strftime('%m/%d %I:%M %p')}"
                sms_sent = await self.send_sms(patient_info['phone'], sms_body)

            return email_sent or sms_sent

        except Exception as e:
            self.logger.error(f"Failed to send appointment reminder: {e}")
            return False

    async def send_appointment_confirmation(self, appointment: Dict[str, Any]) -> bool:
        """Send appointment confirmation notification"""
        try:
            patient_info = appointment.get('patient_info', {})
            appointment_type = appointment.get('appointment_type', {})
            doctor = appointment.get('doctor', {})

            appointment_time = datetime.fromisoformat(appointment['start_time'].replace('Z', '+00:00'))

            subject = "Appointment Confirmed"

            text_body = f"""
Dear {patient_info.get('name', 'Patient')},

Your appointment has been confirmed:

Appointment Type: {appointment_type.get('name', 'Medical Appointment')}
Doctor: {doctor.get('name', 'Dr. Assigned')}
Date & Time: {appointment_time.strftime('%B %d, %Y at %I:%M %p')}
Location: Medical Center
Booking ID: {appointment.get('booking_id', 'N/A')}

Please arrive 15 minutes early for check-in.

If you need to make changes, please contact us.

Best regards,
Medical Center Team
            """.strip()

            # Send email if patient has email
            email_sent = False
            if patient_info.get('email'):
                email_sent = await self.send_email(
                    patient_info['email'],
                    subject,
                    text_body
                )

            # Send SMS confirmation
            sms_sent = False
            if patient_info.get('phone'):
                sms_body = f"Confirmed: {appointment_type.get('name', 'Appointment')} with {doctor.get('name', 'Dr. Assigned')} on {appointment_time.strftime('%m/%d %I:%M %p')}. ID: {appointment.get('booking_id', 'N/A')}"
                sms_sent = await self.send_sms(patient_info['phone'], sms_body)

            return email_sent or sms_sent

        except Exception as e:
            self.logger.error(f"Failed to send appointment confirmation: {e}")
            return False

    async def send_appointment_cancellation(self, appointment: Dict[str, Any]) -> bool:
        """Send appointment cancellation notification"""
        try:
            patient_info = appointment.get('patient_info', {})
            appointment_type = appointment.get('appointment_type', {})

            subject = "Appointment Cancelled"

            text_body = f"""
Dear {patient_info.get('name', 'Patient')},

Your appointment has been cancelled:

Appointment Type: {appointment_type.get('name', 'Medical Appointment')}
Booking ID: {appointment.get('booking_id', 'N/A')}

If you'd like to reschedule, please contact us.

Best regards,
Medical Center Team
            """.strip()

            # Send email if patient has email
            email_sent = False
            if patient_info.get('email'):
                email_sent = await self.send_email(
                    patient_info['email'],
                    subject,
                    text_body
                )

            # Send SMS cancellation notice
            sms_sent = False
            if patient_info.get('phone'):
                sms_body = f"Cancelled: Your {appointment_type.get('name', 'appointment')} (ID: {appointment.get('booking_id', 'N/A')}) has been cancelled."
                sms_sent = await self.send_sms(patient_info['phone'], sms_body)

            return email_sent or sms_sent

        except Exception as e:
            self.logger.error(f"Failed to send appointment cancellation: {e}")
            return False

    async def close(self):
        """Close any connections"""
        pass