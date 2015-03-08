from django.contrib import admin
from django.forms import ModelForm
from suit.widgets import EnclosedInput
from timetable.models import Session


class SessionForm(ModelForm):
    class Meta:
        widgets = {
            # You can also use prepended and appended together
            'cost': EnclosedInput(prepend='£'),
        }


class SessionAdmin(admin.ModelAdmin):
    list_display = ('day', 'time', 'name')
    ordering = ('day', 'time')
    fields = ('name', 'day', 'time', 'type', 'description', 'location',
              'max_participants', 'contact_person', 'contact_email',
              'cost', 'payment_open')
    model = Session
    form = SessionForm


admin.site.register(Session, SessionAdmin)