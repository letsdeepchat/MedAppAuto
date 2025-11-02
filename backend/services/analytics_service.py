"""
Analytics Service for appointment and clinic metrics
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from collections import defaultdict


class AnalyticsService:
    """Service for generating analytics and reports"""

    def __init__(self, database_service):
        self.logger = logging.getLogger(__name__)
        self.database_service = database_service

    async def get_appointment_metrics(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        """Get comprehensive appointment metrics"""
        try:
            # Set default date range (last 30 days)
            if not end_date:
                end_date = datetime.now(timezone.utc).isoformat()
            if not start_date:
                start_dt = datetime.now(timezone.utc) - timedelta(days=30)
                start_date = start_dt.isoformat()

            # Get appointments in date range
            appointments = await self.database_service.get_appointments_by_date_range(start_date, end_date)

            # Calculate metrics
            total_appointments = len(appointments)
            confirmed_appointments = len([a for a in appointments if a.get('status') == 'confirmed'])
            cancelled_appointments = len([a for a in appointments if a.get('status') == 'cancelled'])
            completed_appointments = len([a for a in appointments if a.get('status') == 'completed'])

            # Appointment types breakdown
            appointment_types = defaultdict(int)
            for appointment in appointments:
                apt_type = appointment.get('appointment_type', {}).get('name', 'Unknown')
                appointment_types[apt_type] += 1

            # Doctor utilization
            doctor_utilization = defaultdict(int)
            for appointment in appointments:
                doctor_name = appointment.get('doctor', {}).get('name', 'Unknown')
                doctor_utilization[doctor_name] += 1

            # Revenue metrics (if pricing is available)
            total_revenue = 0
            for appointment in appointments:
                price = appointment.get('appointment_type', {}).get('price', 0)
                if appointment.get('status') in ['confirmed', 'completed']:
                    total_revenue += price

            # Daily appointment counts
            daily_counts = defaultdict(int)
            for appointment in appointments:
                date = appointment['created_at'][:10]  # YYYY-MM-DD
                daily_counts[date] += 1

            return {
                "period": {
                    "start_date": start_date,
                    "end_date": end_date
                },
                "summary": {
                    "total_appointments": total_appointments,
                    "confirmed_appointments": confirmed_appointments,
                    "cancelled_appointments": cancelled_appointments,
                    "completed_appointments": completed_appointments,
                    "cancellation_rate": (cancelled_appointments / total_appointments * 100) if total_appointments > 0 else 0,
                    "total_revenue": total_revenue
                },
                "breakdown": {
                    "by_appointment_type": dict(appointment_types),
                    "by_doctor": dict(doctor_utilization),
                    "daily_counts": dict(daily_counts)
                }
            }

        except Exception as e:
            self.logger.error(f"Error generating appointment metrics: {e}")
            raise

    async def get_doctor_performance(self, doctor_id: Optional[str] = None, days: int = 30) -> Dict[str, Any]:
        """Get doctor performance metrics"""
        try:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)

            # Get appointments for the period
            appointments = await self.database_service.get_appointments_by_date_range(
                start_date.isoformat(), end_date.isoformat()
            )

            # Filter by doctor if specified
            if doctor_id:
                appointments = [a for a in appointments if a.get('doctor', {}).get('id') == doctor_id]

            # Group by doctor
            doctor_stats = {}

            for appointment in appointments:
                doctor_name = appointment.get('doctor', {}).get('name', 'Unknown')

                if doctor_name not in doctor_stats:
                    doctor_stats[doctor_name] = {
                        'total_appointments': 0,
                        'completed_appointments': 0,
                        'cancelled_appointments': 0,
                        'revenue': 0.0,
                        'appointment_types': defaultdict(int)
                    }

                stats = doctor_stats[doctor_name]

                stats['total_appointments'] += 1

                if appointment.get('status') == 'completed':
                    stats['completed_appointments'] += 1
                elif appointment.get('status') == 'cancelled':
                    stats['cancelled_appointments'] += 1

                # Revenue
                price = appointment.get('appointment_type', {}).get('price', 0)
                if appointment.get('status') in ['confirmed', 'completed']:
                    stats['revenue'] += price

                # Appointment types
                apt_type = appointment.get('appointment_type', {}).get('name', 'Unknown')
                stats['appointment_types'][apt_type] += 1

            # Calculate rates and averages
            for doctor, stats in doctor_stats.items():
                total = stats['total_appointments']
                if total > 0:
                    stats['completion_rate'] = (stats['completed_appointments'] / total) * 100
                    stats['cancellation_rate'] = (stats['cancelled_appointments'] / total) * 100
                    stats['average_revenue_per_appointment'] = stats['revenue'] / total
                else:
                    stats['completion_rate'] = 0
                    stats['cancellation_rate'] = 0
                    stats['average_revenue_per_appointment'] = 0

                stats['appointment_types'] = dict(stats['appointment_types'])

            return {
                "period_days": days,
                "doctor_performance": dict(doctor_stats)
            }

        except Exception as e:
            self.logger.error(f"Error generating doctor performance metrics: {e}")
            raise

    async def get_clinic_efficiency(self, days: int = 30) -> Dict[str, Any]:
        """Get clinic efficiency metrics"""
        try:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)

            appointments = await self.database_service.get_appointments_by_date_range(
                start_date.isoformat(), end_date.isoformat()
            )

            # Calculate no-show rate (assuming completed = attended)
            total_scheduled = len([a for a in appointments if a.get('status') in ['confirmed', 'completed']])
            attended = len([a for a in appointments if a.get('status') == 'completed'])
            no_show_rate = ((total_scheduled - attended) / total_scheduled * 100) if total_scheduled > 0 else 0

            # Average wait time (mock data - would need actual tracking)
            avg_wait_time = 8.5  # minutes

            # Patient satisfaction (mock data - would need survey system)
            satisfaction_score = 4.2  # out of 5

            # Peak hours analysis
            hourly_distribution = defaultdict(int)
            for appointment in appointments:
                if appointment.get('status') in ['confirmed', 'completed']:
                    hour = datetime.fromisoformat(appointment['start_time'].replace('Z', '+00:00')).hour
                    hourly_distribution[hour] += 1

            # Most popular appointment types
            type_popularity = defaultdict(int)
            for appointment in appointments:
                apt_type = appointment.get('appointment_type', {}).get('name', 'Unknown')
                type_popularity[apt_type] += 1

            return {
                "period_days": days,
                "efficiency_metrics": {
                    "no_show_rate": no_show_rate,
                    "average_wait_time_minutes": avg_wait_time,
                    "patient_satisfaction_score": satisfaction_score,
                    "total_appointments": len(appointments)
                },
                "peak_hours": dict(sorted(hourly_distribution.items())),
                "popular_appointment_types": dict(sorted(type_popularity.items(), key=lambda x: x[1], reverse=True))
            }

        except Exception as e:
            self.logger.error(f"Error generating clinic efficiency metrics: {e}")
            raise

    async def get_revenue_report(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        """Generate revenue report"""
        try:
            if not end_date:
                end_date = datetime.now(timezone.utc).isoformat()
            if not start_date:
                start_dt = datetime.now(timezone.utc) - timedelta(days=30)
                start_date = start_dt.isoformat()

            appointments = await self.database_service.get_appointments_by_date_range(start_date, end_date)

            # Revenue by appointment type
            revenue_by_type = defaultdict(float)
            revenue_by_doctor = defaultdict(float)
            daily_revenue = defaultdict(float)

            for appointment in appointments:
                if appointment.get('status') in ['confirmed', 'completed']:
                    price = appointment.get('appointment_type', {}).get('price', 0)

                    # By type
                    apt_type = appointment.get('appointment_type', {}).get('name', 'Unknown')
                    revenue_by_type[apt_type] += price

                    # By doctor
                    doctor_name = appointment.get('doctor', {}).get('name', 'Unknown')
                    revenue_by_doctor[doctor_name] += price

                    # Daily
                    date = appointment['created_at'][:10]
                    daily_revenue[date] += price

            total_revenue = sum(revenue_by_type.values())

            return {
                "period": {
                    "start_date": start_date,
                    "end_date": end_date
                },
                "total_revenue": total_revenue,
                "revenue_breakdown": {
                    "by_appointment_type": dict(revenue_by_type),
                    "by_doctor": dict(revenue_by_doctor),
                    "daily_revenue": dict(daily_revenue)
                },
                "averages": {
                    "revenue_per_appointment": total_revenue / len([a for a in appointments if a.get('status') in ['confirmed', 'completed']]) if appointments else 0,
                    "revenue_per_day": total_revenue / (datetime.fromisoformat(end_date.replace('Z', '+00:00')) - datetime.fromisoformat(start_date.replace('Z', '+00:00'))).days if appointments else 0
                }
            }

        except Exception as e:
            self.logger.error(f"Error generating revenue report: {e}")
            raise

    async def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get summary data for dashboard"""
        try:
            # Today's appointments
            today = datetime.now(timezone.utc).date()
            today_start = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc).isoformat()
            today_end = datetime.combine(today, datetime.max.time(), tzinfo=timezone.utc).isoformat()

            today_appointments = await self.database_service.get_appointments_by_date_range(today_start, today_end)

            # Upcoming appointments (next 7 days)
            week_end = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
            upcoming_appointments = await self.database_service.get_appointments_by_date_range(
                datetime.now(timezone.utc).isoformat(), week_end
            )

            # Recent metrics (last 7 days)
            week_metrics = await self.get_appointment_metrics(
                (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            )

            return {
                "today": {
                    "total_appointments": len(today_appointments),
                    "confirmed_appointments": len([a for a in today_appointments if a.get('status') == 'confirmed']),
                    "upcoming_appointments": len([a for a in today_appointments if a.get('status') == 'confirmed' and
                                                datetime.fromisoformat(a['start_time'].replace('Z', '+00:00')) > datetime.now(timezone.utc)])
                },
                "upcoming_week": {
                    "total_appointments": len(upcoming_appointments),
                    "by_day": defaultdict(int)
                },
                "recent_metrics": week_metrics["summary"]
            }

        except Exception as e:
            self.logger.error(f"Error generating dashboard summary: {e}")
            raise