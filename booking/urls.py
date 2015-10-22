from django.conf.urls import patterns, url
from django.views.generic import RedirectView
from booking.views import EventListView, EventDetailView, BookingListView, \
    BookingHistoryListView, BookingCreateView, BookingUpdateView, \
    BookingDeleteView, BlockCreateView, BlockListView, TicketBookingListView, \
    TicketedEventListView, TicketCreateView, TicketBookingHistoryListView, \
    TicketBookingView

urlpatterns = patterns('',
    url(r'^bookings/$', BookingListView.as_view(), name='bookings'),
    url(r'^booking-history/$', BookingHistoryListView.as_view(),
        name='booking_history'),
    url(r'^booking/update/(?P<pk>\d+)/$', BookingUpdateView.as_view(),
        name='update_booking'),
    url(r'^booking/update/(?P<pk>\d+)/cancelled/$',
        'booking.views.update_booking_cancelled',
        name='update_booking_cancelled'),
    url(r'^booking/cancel/(?P<pk>\d+)/$', BookingDeleteView.as_view(),
        name='delete_booking'),
    url(r'^events/(?P<event_slug>[\w-]+)/cancellation-period-past/$',
        'booking.views.cancellation_period_past', name='cancellation_period_past'),
    url(r'^events/(?P<event_slug>[\w-]+)/duplicate/$',
        'booking.views.duplicate_booking', name='duplicate_booking'),
    url(r'^events/(?P<event_slug>[\w-]+)/full/$', 'booking.views.fully_booked',
        name='fully_booked'),
    url(r'^events/(?P<event_slug>[\w-]+)/book/$', BookingCreateView.as_view(),
        name='book_event'),
    url(
        r'^events/(?P<slug>[\w-]+)/$', EventDetailView.as_view(),
        {'ev_type': 'event'}, name='event_detail'
    ),
    url(
        r'^events/$', EventListView.as_view(), {'ev_type': 'events'},
        name='events'
    ),
    url(
        r'^classes/(?P<slug>[\w-]+)/$',  EventDetailView.as_view(),
        {'ev_type': 'lesson'}, name='lesson_detail'),
    url(
        r'^classes/$', EventListView.as_view(), {'ev_type': 'lessons'},
        name='lessons'
    ),

    url(r'^blocks/$', BlockListView.as_view(), name='block_list'),
    url(r'^blocks/new/$', BlockCreateView.as_view(), name='add_block'),
    url(r'^blocks/existing/$', 'booking.views.has_active_block',
        name='has_active_block'),
    url(r'^not-available/$', 'booking.views.permission_denied',
        name='permission_denied'),
    url(
        r'^ticketed-events/$', TicketedEventListView.as_view(),
        name='ticketed_events'
    ),
    url(r'^ticketed_events/(?P<event_slug>[\w-]+)/purchase/$',
        TicketCreateView.as_view(),
        name='book_ticketed_event'),
    url(r'^ticket-bookings/$', TicketBookingListView.as_view(), name='ticket_bookings'),
    url(r'^ticket-bookings/(?P<ref>[\w-]+)/$', TicketBookingView.as_view(), name='ticket_booking'),
    url(r'^ticket-booking-history/$', TicketBookingHistoryListView.as_view(),
        name='ticket_booking_history'),
    url(r'^$', RedirectView.as_view(url='/classes/', permanent=True)),
    )
