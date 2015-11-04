from django.test import TestCase
from django.conf import settings
from django.core import management
from django.core import mail
from django.db.models import Q
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, timedelta
from allauth.socialaccount.models import SocialApp
from mock import patch
from model_mommy import mommy

from booking.models import Event, Booking, EventType, BlockType, \
    TicketBooking, Ticket
from timetable.models import Session


class ManagementCommandsTests(TestCase):

    def test_setup_fb(self):
        self.assertEquals(SocialApp.objects.all().count(), 0)
        management.call_command('setup_fb')
        self.assertEquals(SocialApp.objects.all().count(), 1)

    def test_create_timetable_sessions(self):
        self.assertEquals(Session.objects.all().count(), 0)
        management.call_command('create_timetable')
        self.assertEquals(Session.objects.all().count(), 18)

    def test_create_timetable_sessions_also_creates_event_types(self):
        self.assertEquals(Session.objects.all().count(), 0)
        self.assertEquals(EventType.objects.all().count(), 0)
        management.call_command('create_timetable')
        self.assertEquals(Session.objects.all().count(), 18)
        self.assertEquals(EventType.objects.all().count(), 5)

    def test_create_sessions_does_not_make_duplicates(self):
        self.assertEquals(Session.objects.all().count(), 0)
        self.assertEquals(EventType.objects.all().count(), 0)
        management.call_command('create_timetable')
        self.assertEquals(Session.objects.all().count(), 18)
        self.assertEquals(EventType.objects.all().count(), 5)
        management.call_command('create_timetable')
        self.assertEquals(Session.objects.all().count(), 18)
        self.assertEquals(EventType.objects.all().count(), 5)

    def test_create_pip_room_hire_sessions(self):
        self.assertEquals(Session.objects.all().count(), 0)
        management.call_command('create_pip_hire_sessions')
        self.assertEquals(Session.objects.all().count(), 8)
        for session in Session.objects.all():
            self.assertEqual(session.name, "Pip Room Hire")
            self.assertEqual(session.event_type.event_type, "RH")

    def test_create_pip_room_hire_sessions_creates_RH_event_type(self):
        self.assertEquals(Session.objects.all().count(), 0)
        self.assertEquals(EventType.objects.all().count(), 0)
        management.call_command('create_pip_hire_sessions')
        self.assertEquals(Session.objects.all().count(), 8)
        self.assertEquals(EventType.objects.all().count(), 1)
        et = EventType.objects.first()
        self.assertEqual(et.event_type, "RH")
        self.assertEqual(et.subtype, 'Studio/room hire')

    def test_create_pip_room_hire_sessions_does_not_create_duplicates(self):
        self.assertEquals(Session.objects.all().count(), 0)
        self.assertEquals(EventType.objects.all().count(), 0)
        management.call_command('create_pip_hire_sessions')
        self.assertEquals(Session.objects.all().count(), 8)
        self.assertEquals(EventType.objects.all().count(), 1)
        management.call_command('create_pip_hire_sessions')
        self.assertEquals(Session.objects.all().count(), 8)
        self.assertEquals(EventType.objects.all().count(), 1)
