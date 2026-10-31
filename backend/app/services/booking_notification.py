"""Best-effort confirmation after a successful database commit."""
import logging
from app.domain.models.models import Booking, User, Resource
from app.services.email_service import send_booking_confirmation_email
from app.services.receipt import build_receipt_pdf

logger = logging.getLogger(__name__)

def notify_booking(db, booking_id):
    try:
        booking = db.get(Booking, booking_id)
        user = db.get(User, booking.user_id)
        resource = db.get(Resource, booking.resource_id)
        pdf = build_receipt_pdf(booking, user, resource)
        return send_booking_confirmation_email(
            to_email=user.email,
            subject=f'Booking confirmed: {resource.name}',
            body_text=(f'Hi {user.name},\n\nYour booking is confirmed.\n'
                       f'Sport: {resource.type.value}\nFacility: {resource.name}\n'
                       f'Date: {booking.start_time:%A, %d %B %Y}\n'
                       f'Time: {booking.start_time:%I:%M %p} - {booking.end_time:%I:%M %p} (Asia/Kolkata)\n'
                       f'Booking ID: {booking.id}\n\nYour PDF receipt is attached.\nCampusSphere'),
            pdf_bytes=pdf, pdf_filename=f'campussphere-{booking.id}.pdf')
    except Exception:
        logger.exception('Confirmation failed after booking commit; booking remains confirmed')
        return False
