from django.utils import timezone
from datetime import time, timedelta, datetime, date
from booking.models import Event
from timetable.models import Session

def create_classes(week='this', input_date=None):
    """
    Creates a week's classes (mon-sun) from any given date.  Will create classes
    in the past if the date given is after Monday and week is "this".
    If no date is given, creates classes for the current week, or the next week.
    """
    if not input_date:
        input_date = date.today()
    if week == 'next':
        input_date = input_date + timedelta(7)

    mon = input_date - timedelta(days=input_date.weekday())
    tues = mon + timedelta(days=1)
    wed = mon + timedelta(days=2)
    thurs = mon + timedelta(days=3)
    fri = mon + timedelta(days=4)
    sat = mon + timedelta(days=5)
    sun = mon + timedelta(days=6)

    date_dict = {
        '01MON': mon,
        '02TUE': tues,
        '03WED': wed,
        '04THU': thurs,
        '05FRI': fri,
        '06SAT': sat,
        '07SUN': sun}

    timetable = Session.objects.all()
    for session in timetable:
        Event.objects.get_or_create(
            name=session.name,
            type=session.type,
            date=(datetime.combine(
                date_dict[session.day],
                session.time).replace(tzinfo=timezone.utc)),
            description=session.description,
            max_participants=session.max_participants,
            location=session.location,
            contact_person=session.contact_person,
            contact_email=session.contact_email,
            cost=session.cost,
            payment_open=session.payment_open
        )
