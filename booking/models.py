from django.db import models
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.template.defaultfilters import slugify
from django_extensions.db.fields import AutoSlugField
from datetime import timedelta
from dateutil.relativedelta import relativedelta


class Event(models.Model):
    POLE_CLASS = 'PC'
    WORKSHOP = 'WS'
    OTHER_CLASS = 'CL'
    OTHER_EVENT = 'EV'
    EVENT_TYPE_CHOICES = (
        (POLE_CLASS, 'Pole level class'),
        (WORKSHOP, 'Workshop'),
        (OTHER_CLASS, 'Other class'),
        (OTHER_EVENT, 'Other event'),
    )

    name = models.CharField(max_length=255)
    type = models.CharField(max_length=2, choices=EVENT_TYPE_CHOICES, default=POLE_CLASS)
    description = models.TextField(blank=True)
    date = models.DateTimeField()
    location = models.CharField(max_length=255, default="Watermelon Studio")
    max_participants = models.PositiveIntegerField(null=True, blank=True, help_text="Leave blank if no max number of participants")
    contact_person = models.CharField(max_length=255, default="Gwen Burns")
    contact_email = models.EmailField(default="thewatermelonstudio@hotmail.com")
    cost = models.DecimalField(default=0, max_digits=8, decimal_places=2)
    advance_payment_required = models.BooleanField(default=False)
    payment_open = models.BooleanField(default=False)
    payment_info = models.TextField(blank=True)
    payment_link = models.URLField(blank=True, default="http://www.paypal.co.uk")
    payment_due_date = models.DateTimeField(null=True, blank=True)
    slug = AutoSlugField(populate_from='name', max_length=40, unique=True)

    def spaces_left(self):
        if self.max_participants:
            booked_number = Booking.objects.filter(event__id=self.id).count()
            return self.max_participants - booked_number
        else:
            return 100

    def get_absolute_url(self):
        return reverse("booking:event_detail", kwargs={'slug': self.slug})

    def __unicode__(self):
        return self.name


class Block(models.Model):
    """
    Block booking; blocks are 5 or 10 classes
    5 classes = GBP 32, 10 classes = GBP 62
    5 classes expires in 2 months, 10 classes expires in 4 months
    """
    SMALL_BLOCK_SIZE = 'SM'
    LARGE_BLOCK_SIZE = 'LG'
    SIZE_CHOICES = (
        (SMALL_BLOCK_SIZE, 'Five classes'),
        (LARGE_BLOCK_SIZE, 'Ten classes'),
    )
    COSTS = {
        SMALL_BLOCK_SIZE: 32,
        LARGE_BLOCK_SIZE: 62,
    }
    EXPIRES = {
        SMALL_BLOCK_SIZE: 2,
        LARGE_BLOCK_SIZE: 4,
    }

    user = models.ForeignKey(User, related_name='blocks')
    block_size = models.CharField(
        verbose_name='Number of classes in block',
        max_length=2,
        choices=SIZE_CHOICES,
        default=SMALL_BLOCK_SIZE,
    )
    start_date = models.DateTimeField(auto_now_add=True)
    paid = models.BooleanField(
        verbose_name='Payment made (as confirmed by participant)',
        default=False,
        help_text='Payment has been made by user'
    )
    payment_confirmed = models.BooleanField(
        default=False,
        help_text='Payment confirmed by admin/organiser'
    )

    def __unicode__(self):
        return "{} -- block size {} -- start {}".format(self.user.username,
                                                      self.block_size,
                                                      self.start_date.strftime(
                                                          '%d %b %Y %H:%M')
        )

    @property
    def cost(self):
        return self.COSTS[self.block_size]

    @property
    def expiry_date(self):
        return self.start_date + relativedelta(months=2)


class Booking(models.Model):
    user = models.ForeignKey(User, related_name='bookings')
    event = models.ForeignKey(Event, related_name='bookings')
    paid = models.BooleanField(
        verbose_name='Payment made (as confirmed by participant)',
        default=False,
        help_text='Payment has been made by user'
    )
    payment_confirmed = models.BooleanField(
        default=False,
        help_text='Payment confirmed by admin/organiser'
    )
    block = models.ForeignKey(Block, related_name='bookings', null=True)

    def confirm_space(self):
        self.paid = True
        self.payment_confirmed = True
        self.save()

    def space_confirmed(self):
        return not self.event.advance_payment_required or \
               self.event.cost == 0 or \
               self.payment_confirmed
    space_confirmed.boolean = True

    class Meta:
        unique_together = ('user', 'event')

    def get_absolute_url(self):
        return reverse("booking:booking_detail", args=[str(self.id)])

    def __unicode__(self):
        return "{} {}".format(str(self.event.name), str(self.user.username))

