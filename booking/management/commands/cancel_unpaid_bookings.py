'''
Check for unpaid bookings and cancel where:
booking.status = OPEN
paid = False
payment_due_date < timezone.now()
date - canellation_period < timezone.now()
Email user that their booking has been cancelled
'''
import logging
from datetime import timedelta

from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import get_template
from django.template import Context
from django.core.management.base import BaseCommand
from django.core import management

from booking.models import Booking

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Cancel unpaid bookings that are past payment_due_date or '
    'cancellation_period'
    def handle(self, *args, **options):
        bookings = [booking for booking in Booking.objects.filter(
            event__date__gte=timezone.now(),
            event__advance_payment_required=True,
            status='OPEN',
            paid=False,
            payment_confirmed=False) if
            booking.event.date - timedelta(
                hours=booking.event.cancellation_period
            ) < timezone.now() or
            booking.event.payment_due_date < timezone.now()]

        for booking in bookings:
            ctx = Context({
                  'booking': booking,
                  'event': booking.event,
                  'date': booking.event.date.strftime('%A %d %B'),
                  'time': booking.event.date.strftime('%I:%M %p'),
            })
            # send mails to users
            send_mail('{} Booking cancelled: {}'.format(
                settings.ACCOUNT_EMAIL_SUBJECT_PREFIX, booking.event.name),
                get_template(
                    'booking/email/booking_auto_cancelled.txt'
                ).render(ctx),
                settings.DEFAULT_FROM_EMAIL,
                [booking.user.email],
                html_message=get_template(
                    'booking/email/booking_auto_cancelled.html'
                    ).render(ctx),
                fail_silently=False)
            booking.status = 'CANCELLED'
            booking.block = None
            booking.save()
            logger.info('Booking id {} for event {}, user {} has been '
                        'automatically cancelled'.format(
                            booking.id, booking.event, booking.user
                            )
                        )

        if bookings:
            # send single mail to Studio
            send_mail('{} Booking{} been automatically cancelled'.format(
                settings.ACCOUNT_EMAIL_SUBJECT_PREFIX,
                ' has' if len(bookings) == 1 else 's have'),
                get_template(
                    'booking/email/booking_auto_cancelled_studio_email.txt'
                ).render({'bookings': bookings}),
                settings.DEFAULT_FROM_EMAIL,
                [settings.DEFAULT_STUDIO_EMAIL],
                html_message=get_template(
                    'booking/email/booking_auto_cancelled_studio_email.html'
                    ).render({'bookings': bookings}),
                fail_silently=False)
            self.stdout.write(
                'Cancellation emails sent for booking ids {}'.format(
                    ', '.join([str(booking.id) for booking in bookings])
                )
            )
        else:
            self.stdout.write('No bookings to cancel')
