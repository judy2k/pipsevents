from datetime import date
from django import forms
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.forms.models import inlineformset_factory, BaseInlineFormSet

from booking.models import Booking, Event, Block
from booking.widgets import DateSelectorWidget


MONTH_CHOICES = {
            1: 'January',
            2: 'February',
            3: 'March',
            4: 'April',
            5: 'May',
            6: 'June',
            7: 'July',
            8: 'August',
            9: 'September',
            10: 'October',
            11: 'November',
            12: 'December',
        }


class BookingCreateForm(forms.ModelForm):

    class Meta:
        model = Booking
        fields = ['event', ]


class BlockCreateForm(forms.ModelForm):

    class Meta:
        model = Block
        fields = ('block_type', )


class CreateClassesForm(forms.Form):
    date = forms.DateField(
        label="Date", widget=DateSelectorWidget, required=False, initial=date.today()
    )

    def clean_date(self):
        if not self.cleaned_data['date']:
            day = self.data.get('date_0')
            month = MONTH_CHOICES.get(int(self.data.get('date_1')))
            year = self.data.get('date_2')
            raise forms.ValidationError(_('Invalid date {} {} {}'.format(day, month, year)))
        return self.cleaned_data['date']


class EmailUsersForm(forms.Form):
    subject = forms.CharField(max_length=255, required=True)
    from_address = forms.EmailField(max_length=255,
                                    initial=settings.DEFAULT_FROM_EMAIL,
                                    required=True)
    cc = forms.BooleanField(label="Send a copy to this address", initial=True)
    message = forms.CharField(widget=forms.Textarea, required=True)


def get_event_names(event_type):

    def callable():
        event_names = set([event.name for event in Event.objects.filter(
            event_type__event_type=event_type, date__gte=timezone.now()
        ).order_by('name')])
        NAME_CHOICES = [(item, item) for i, item in enumerate(event_names)]
        NAME_CHOICES.insert(0, ('', 'All'))
        return tuple(sorted(NAME_CHOICES))

    return callable


class EventFilter(forms.Form):
    name = forms.ChoiceField(choices=get_event_names('EV'))


def get_user_blocks(user, event_type):
    blocks = [block.id for block in Block.objects.filter(
        block_type__event_type=event_type, user=user
    ) if block.active_block()]
    return Block.objects.filter(id__in=blocks).order_by('start_date')


class BlockModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return "Start date: {}".format(obj.start_date.strftime('%d %b %y'))


class UserModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return "{} {} ({})".format(obj.first_name, obj.last_name, obj.username)


class BookingInlineFormSet(BaseInlineFormSet):

    def add_fields(self, form, index):
        super(BookingInlineFormSet, self).add_fields(form, index)
        if form.initial.get('user'):
            user = form.instance.user
            event_type = form.instance.event.event_type
            block = form.instance.block
            form.fields['block'] = BlockModelChoiceField(
                queryset=get_user_blocks(user, event_type),
                initial=block, required=False,
                widget=forms.Select(attrs={'class': 'custom-select'})
            )
            form.fields['user']=forms.ModelChoiceField(
                queryset=User.objects.all(),
                initial=user,
                widget=forms.Select(attrs={'class': 'hide'})
            )
            form.fields['userdisplay'] = UserModelChoiceField(
                queryset=User.objects.all(),
                initial=user,
                required=False,
                widget=forms.Select(attrs={
                    'class': 'custom-select',
                    'data-style': 'btn-info',
                    'disabled': 'disabled'})
            )
        else:
            form.fields['block'] = BlockModelChoiceField(
                queryset=Block.objects.none(),
                required=False,
                widget=forms.Select(attrs={'class': 'custom-select'}))
            form.fields['user'] = UserModelChoiceField(
                queryset=User.objects.all(),
                widget=forms.Select(attrs={'class': 'custom-select'}))

    def clean(self):
        super(BookingInlineFormSet, self).clean()
        for form in self.forms:
            if not form.cleaned_data.get('block'):
                form.cleaned_data['block'] = None


def set_toggle_attrs(on_text='Yes', off_text='No', label_text=''):
    return {
        'class': 'toggle-checkbox',
        'data-size': 'small',
        'data-on-color': 'success',
        'data-off-color': 'danger',
        'data-on-text': on_text,
        'data-off-text': off_text,
        'data-label-text': label_text,
    }

BookingRegisterFormSet = inlineformset_factory(
    Event,
    Booking,
    fields=('user', 'paid', 'payment_confirmed', 'block', 'status',
            'attended'),
    can_delete=False,
    extra=2,
    formset=BookingInlineFormSet,
    widgets={
        'paid': forms.CheckboxInput(attrs=set_toggle_attrs()),
        'attended': forms.CheckboxInput(attrs=set_toggle_attrs()),
        'status': forms.Select(attrs={'class': 'custom-select'})
        }
    )