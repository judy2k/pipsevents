from datetime import timedelta
from model_mommy import mommy

from django.core.urlresolvers import reverse
from django.core import mail
from django.test import TestCase
from django.contrib.auth.models import User, Permission
from django.contrib.messages.storage.fallback import FallbackStorage
from django.utils import timezone

from booking.models import Booking, Block
from booking.tests.helpers import _create_session, format_content
from studioadmin.views import (
    UserListView,
    user_blocks_view,
    user_bookings_view,
)
from studioadmin.tests.test_views.helpers import TestPermissionMixin


class UserListViewTests(TestPermissionMixin, TestCase):

    def _get_response(self, user, form_data={}):
        url = reverse('studioadmin:users')
        session = _create_session()
        request = self.factory.get(url, form_data)
        request.session = session
        request.user = user
        messages = FallbackStorage(request)
        request._messages = messages
        view = UserListView.as_view()
        return view(request)

    def test_cannot_access_if_not_logged_in(self):
        """
        test that the page redirects if user is not logged in
        """
        url = reverse('studioadmin:users')
        resp = self.client.get(url)
        redirected_url = reverse('account_login') + "?next={}".format(url)
        self.assertEquals(resp.status_code, 302)
        self.assertIn(redirected_url, resp.url)

    def test_cannot_access_if_not_staff(self):
        """
        test that the page redirects if user is not a staff user
        """
        resp = self._get_response(self.user)
        self.assertEquals(resp.status_code, 302)
        self.assertEquals(resp.url, reverse('booking:permission_denied'))

    def test_instructor_group_cannot_access(self):
        """
        test that the page redirects if user is in the instructor group but is
        not a staff user
        """
        resp = self._get_response(self.instructor_user)
        self.assertEquals(resp.status_code, 302)
        self.assertEquals(resp.url, reverse('booking:permission_denied'))

    def test_can_access_as_staff_user(self):
        """
        test that the page can be accessed by a staff user
        """
        resp = self._get_response(self.staff_user)
        self.assertEquals(resp.status_code, 200)

    def test_all_users_are_displayed(self):
        mommy.make_recipe('booking.user', _quantity=6)
        # 9 users total, incl self.user, self.instructor_user self.staff_user
        self.assertEqual(User.objects.count(), 9)
        resp = self._get_response(self.staff_user)
        self.assertEqual(
            list(resp.context_data['users']), list(User.objects.all())
        )

    def test_display_regular_students(self):
        not_reg_student = mommy.make_recipe('booking.user')
        reg_student = mommy.make_recipe('booking.user')
        perm = Permission.objects.get(codename='is_regular_student')
        reg_student.user_permissions.add(perm)
        reg_student.save()

        resp = self._get_response(self.staff_user)
        resp.render()
        self.assertIn(
            'id="regular_student_button" value="{}">Yes'.format(reg_student.id),
            str(resp.content)
        )
        self.assertIn(
            'id="regular_student_button" value="{}">No'.format(not_reg_student.id),
            str(resp.content)
        )

    def test_change_regular_student(self):
        not_reg_student = mommy.make_recipe('booking.user')
        reg_student = mommy.make_recipe('booking.user')
        perm = Permission.objects.get(codename='is_regular_student')
        reg_student.user_permissions.add(perm)
        reg_student.save()

        self.assertTrue(reg_student.has_perm('booking.is_regular_student'))
        self._get_response(
            self.staff_user, {'change_user': [reg_student.id]}
        )
        changed_student = User.objects.get(id=reg_student.id)
        self.assertFalse(changed_student.has_perm('booking.is_regular_student'))

        self.assertFalse(not_reg_student.has_perm('booking.is_regular_student'))
        self._get_response(
            self.staff_user, {'change_user': [not_reg_student.id]}
        )
        changed_student = User.objects.get(id=not_reg_student.id)
        self.assertTrue(changed_student.has_perm('booking.is_regular_student'))

    def test_cannot_remove_regular_student_for_superuser(self):
        reg_student = mommy.make_recipe('booking.user')
        superuser = mommy.make_recipe(
            'booking.user', first_name='Donald', last_name='Duck', username='dd'
        )
        superuser.is_superuser = True
        superuser.save()
        perm = Permission.objects.get(codename='is_regular_student')
        reg_student.user_permissions.add(perm)
        reg_student.save()

        self.assertTrue(reg_student.has_perm('booking.is_regular_student'))
        self.assertTrue(superuser.has_perm('booking.is_regular_student'))
        self._get_response(
            self.staff_user, {'change_user': [reg_student.id]}
        )
        changed_student = User.objects.get(id=reg_student.id)
        self.assertFalse(changed_student.has_perm('booking.is_regular_student'))

        resp = self._get_response(
            self.staff_user, {'change_user': [superuser.id]}
        )
        # status hasn't changed
        self.assertTrue(superuser.has_perm('booking.is_regular_student'))
        self.assertIn(
            'Donald Duck (dd) is a superuser; you cannot remove permissions',
            format_content(resp.rendered_content)
        )


class UserBookingsViewTests(TestPermissionMixin, TestCase):

    def setUp(self):
        super(UserBookingsViewTests, self).setUp()
        self.future_user_bookings = mommy.make_recipe(
            'booking.booking', user=self.user, paid=True,
            payment_confirmed=True, event__date=timezone.now()+timedelta(3),
            status='OPEN',
            _quantity=2
        )
        self.past_user_bookings = mommy.make_recipe(
            'booking.booking', user=self.user, paid=True,
            payment_confirmed=True, event__date=timezone.now()-timedelta(3),
            status='OPEN',
            _quantity=2
        )
        self.future_cancelled_bookings = mommy.make_recipe(
            'booking.booking', user=self.user, paid=True,
            payment_confirmed=True, event__date=timezone.now()+timedelta(3),
            status='CANCELLED',
            _quantity=2
        )
        self.past_cancelled_bookings = mommy.make_recipe(
            'booking.booking', user=self.user, paid=True,
            payment_confirmed=True, event__date=timezone.now()-timedelta(3),
            status='CANCELLED',
            _quantity=2
        )
        mommy.make_recipe(
            'booking.booking', paid=True,
            payment_confirmed=True, event__date=timezone.now()+timedelta(3),
            _quantity=2
        )

    def formset_data(self, extra_data={}):
        data = {
            'bookings-TOTAL_FORMS': 2,
            'bookings-INITIAL_FORMS': 2,
            'bookings-0-id': self.future_user_bookings[0].id,
            'bookings-0-event': self.future_user_bookings[0].event.id,
            'bookings-0-status': self.future_user_bookings[0].status,
            'bookings-0-paid': self.future_user_bookings[0].paid,
            'bookings-1-id': self.future_user_bookings[1].id,
            'bookings-1-event': self.future_user_bookings[1].event.id,
            'bookings-1-status': self.future_user_bookings[1].status,
            'bookings-1-deposit_paid': self.future_user_bookings[1].deposit_paid,
            'bookings-1-paid': self.future_user_bookings[1].paid,
            }

        for key, value in extra_data.items():
            data[key] = value

        return data

    def _get_response(self, user, user_id, booking_status='future'):
        url = reverse(
            'studioadmin:user_bookings_list',
            kwargs={'user_id': user_id, 'booking_status': booking_status}
        )
        session = _create_session()
        request = self.factory.get(url)
        request.session = session
        request.user = user
        messages = FallbackStorage(request)
        request._messages = messages
        return user_bookings_view(
            request, user_id, booking_status=booking_status
        )

    def _post_response(
        self, user, user_id, form_data, booking_status='future'
        ):
        url = reverse(
            'studioadmin:user_bookings_list',
            kwargs={'user_id': user_id, 'booking_status': booking_status}
        )
        form_data['booking_status'] = [booking_status]
        session = _create_session()
        request = self.factory.post(url, form_data)
        request.session = session
        request.user = user
        messages = FallbackStorage(request)
        request._messages = messages
        return user_bookings_view(
            request, user_id, booking_status=booking_status
        )

    def test_cannot_access_if_not_logged_in(self):
        """
        test that the page redirects if user is not logged in
        """
        url = reverse(
            'studioadmin:user_bookings_list',
            kwargs={'user_id': self.user.id, 'booking_status': 'future'}
        )
        resp = self.client.get(url)
        redirected_url = reverse('account_login') + "?next={}".format(url)
        self.assertEquals(resp.status_code, 302)
        self.assertIn(redirected_url, resp.url)

    def test_cannot_access_if_not_staff(self):
        """
        test that the page redirects if user is not a staff user
        """
        resp = self._get_response(self.user, self.user.id)
        self.assertEquals(resp.status_code, 302)
        self.assertEquals(resp.url, reverse('booking:permission_denied'))

    def test_instructor_group_cannot_access(self):
        """
        test that the page redirects if user is in the instructor group but is
        not a staff user
        """
        resp = self._get_response(self.instructor_user, self.user.id)
        self.assertEquals(resp.status_code, 302)
        self.assertEquals(resp.url, reverse('booking:permission_denied'))

    def test_can_access_as_staff_user(self):
        """
        test that the page can be accessed by a staff user
        """
        resp = self._get_response(self.staff_user, self.user.id)
        self.assertEquals(resp.status_code, 200)

    def test_view_users_bookings(self):
        """
        Test only user's bookings for future events shown by default
        """
        self.assertEqual(Booking.objects.count(), 10)
        resp = self._get_response(self.staff_user, self.user.id)
        # get all but last form (last form is the empty extra one)
        booking_forms = resp.context_data['userbookingformset'].forms[:-1]
        # show future bookings, both open and cancelled
        self.assertEqual(
            len(booking_forms),
            len(self.future_user_bookings) + len(self.future_cancelled_bookings)
        )

        self.assertEqual(
            [booking.instance for booking in booking_forms],
            self.future_user_bookings + self.future_cancelled_bookings
        )

    def test_filter_bookings_by_booking_status(self):

        # future bookings
        resp = self._get_response(self.staff_user, self.user.id, 'future')
        # get all but last form (last form is the empty extra one)
        booking_forms = resp.context_data['userbookingformset'].forms[:-1]
        self.assertEqual(len(booking_forms), 4)
        self.assertEqual(
            [booking.instance for booking in booking_forms],
            self.future_user_bookings + self.future_cancelled_bookings
        )

        # past bookings
        resp = self._get_response(self.staff_user, self.user.id, 'past')
        # get all but last form (last form is the empty extra one)
        booking_forms = resp.context_data['userbookingformset'].forms[:-1]
        self.assertEqual(len(booking_forms), 4)
        self.assertEqual(
            sorted([booking.instance.id for booking in booking_forms]),
            sorted([
                       bk.id for bk in
                       self.past_user_bookings + self.past_cancelled_bookings
                    ])
        )

    def test_can_update_booking(self):
        self.assertFalse(self.future_user_bookings[0].deposit_paid)
        self.assertTrue(self.future_user_bookings[0].paid)
        form_data = self.formset_data({'bookings-0-paid': False,
        'formset_submitted': 'Submit'})

        self._post_response(self.staff_user, self.user.id, form_data=form_data)
        booking = Booking.objects.get(id=self.future_user_bookings[0].id)
        self.assertFalse(booking.deposit_paid)
        self.assertFalse(booking.paid)
        self.assertFalse(booking.payment_confirmed)

    def test_can_update_booking_deposit_paid(self):

        unpaid_booking = mommy.make_recipe(
            'booking.booking', user=self.user,
            event__date=timezone.now()+timedelta(3),
            status='OPEN',
        )
        self.assertFalse(unpaid_booking.paid)
        self.assertFalse(unpaid_booking.deposit_paid)

        extra_data = {
            'bookings-TOTAL_FORMS': 3,
            'bookings-INITIAL_FORMS': 3,
            'bookings-2-id': unpaid_booking.id,
            'bookings-2-event': unpaid_booking.event.id,
            'bookings-2-status': unpaid_booking.status,
            'bookings-2-deposit_paid': True,
            'bookings-2-paid': unpaid_booking.paid,
            'formset_submitted': 'Submit'
        }

        form_data = self.formset_data(extra_data)

        self._post_response(self.staff_user, self.user.id, form_data=form_data)
        unpaid_booking.refresh_from_db()
        self.assertTrue(unpaid_booking.deposit_paid)
        self.assertFalse(unpaid_booking.paid)
        self.assertFalse(unpaid_booking.payment_confirmed)

    def test_can_add_booking(self):
        self.assertEqual(Booking.objects.count(), 10)
        event = mommy.make_recipe('booking.future_EV')
        form_data = self.formset_data(
            {
                'bookings-TOTAL_FORMS': 3,
                'bookings-2-event': event.id,
                'bookings-2-status': 'OPEN'
            }
        )
        resp = self._post_response(
            self.staff_user, self.user.id, form_data=form_data
        )
        self.assertEqual(Booking.objects.count(), 11)

        bookings = Booking.objects.filter(event=event)
        self.assertEqual(len(bookings), 1)

        booking = bookings[0]
        self.assertEqual(booking.user, self.user)

    def test_changing_booking_status_updates_payment_status_also(self):
        self.assertEqual(self.future_user_bookings[0].status, 'OPEN')
        self.assertTrue(self.future_user_bookings[0].paid)
        self.assertTrue(self.future_user_bookings[0].payment_confirmed)
        form_data = self.formset_data(
            {
                'bookings-0-status': 'CANCELLED'
            }
        )
        self._post_response(
            self.staff_user, self.user.id, form_data=form_data
        )

        booking = Booking.objects.get(id=self.future_user_bookings[0].id)
        self.assertEqual(booking.status, 'CANCELLED')
        self.assertFalse(booking.paid)
        self.assertFalse(booking.payment_confirmed)

    def test_can_assign_booking_to_available_block(self):
        booking = mommy.make_recipe(
            'booking.booking',
            event__date=timezone.now()+timedelta(2),
            user=self.user,
            paid=False,
            payment_confirmed=False
        )
        block = mommy.make_recipe(
            'booking.block', block_type__event_type=booking.event.event_type,
            user=self.user
        )
        self.assertFalse(booking.block)
        form_data = self.formset_data(
            {
                'bookings-TOTAL_FORMS': 3,
                'bookings-INITIAL_FORMS': 3,
                'bookings-2-id': booking.id,
                'bookings-2-event': booking.event.id,
                'bookings-2-status': booking.status,
                'bookings-2-block': block.id
            }
        )
        self._post_response(
            self.staff_user, self.user.id, form_data=form_data
        )

        booking = Booking.objects.get(id=booking.id)
        self.assertEqual(booking.block, block)
        self.assertTrue(booking.paid)
        self.assertTrue(booking.payment_confirmed)

    def test_create_new_block_booking(self):
        event1 = mommy.make_recipe('booking.future_EV')
        block1 = mommy.make_recipe(
            'booking.block', block_type__event_type=event1.event_type,
            user=self.user
        )

        form_data = self.formset_data(
            {
                'bookings-TOTAL_FORMS': 3,
                'bookings-2-event': event1.id,
                'bookings-2-status': 'OPEN',
                'bookings-2-block': block1.id
            }
        )
        self._post_response(
            self.staff_user, self.user.id, form_data=form_data
        )
        booking = Booking.objects.get(event=event1)
        self.assertEqual(booking.block, block1)


    def test_cannot_create_new_block_booking_with_wrong_blocktype(self):
        event1 = mommy.make_recipe('booking.future_EV')
        event2 = mommy.make_recipe('booking.future_EV')

        block1 = mommy.make_recipe(
            'booking.block', block_type__event_type=event1.event_type,
            user=self.user
        )
        block2 = mommy.make_recipe(
            'booking.block', block_type__event_type=event2.event_type,
            user=self.user
        )
        self.assertEqual(Booking.objects.count(), 10)
        form_data = self.formset_data(
            {
                'bookings-TOTAL_FORMS': 3,
                'bookings-2-event': event1.id,
                'bookings-2-status': 'OPEN',
                'bookings-2-block': block2.id
            }
        )
        resp = self._post_response(
            self.staff_user, self.user.id, form_data=form_data
        )
        errors = resp.context_data['userbookingformset'].errors
        self.assertIn(
            {
                'block': ['{} (type "{}") can only be block-booked with a ' \
                          '"{}" block type.'.format(
                    event1, event1.event_type, event1.event_type
                )] \
            },
            errors)
        bookings = Booking.objects.filter(event=event1)
        self.assertEqual(len(bookings), 0)
        self.assertEqual(Booking.objects.count(), 10)

    def test_cannot_overbook_block(self):
        event_type = mommy.make_recipe('booking.event_type_PC')
        event = mommy.make_recipe('booking.future_EV', event_type=event_type)
        event1 = mommy.make_recipe('booking.future_EV', event_type=event_type)
        block = mommy.make_recipe(
            'booking.block', block_type__event_type=event_type,
            block_type__size=1,
            user=self.user
        )
        form_data = self.formset_data(
            {
                'bookings-TOTAL_FORMS': 3,
                'bookings-2-event': event.id,
                'bookings-2-status': 'OPEN',
                'bookings-2-block': block.id
            }
        )

        # create new booking with this block
        self._post_response(
            self.staff_user, self.user.id, form_data=form_data
        )
        self.assertEqual(Booking.objects.count(), 11)
        bookings = Booking.objects.filter(event=event)
        self.assertEqual(len(bookings), 1)
        new_booking = bookings[0]
        self.assertEqual(new_booking.block, block)

        # block is now full
        block = Block.objects.get(id=block.id)
        self.assertTrue(block.full)

        form_data = self.formset_data(
            {
                'bookings-TOTAL_FORMS': 4,
                'bookings-INITIAL_FORMS': 3,
                'bookings-2-id': new_booking.id,
                'bookings-2-event': event.id,
                'bookings-2-status': new_booking.status,
                'bookings-3-event': event1.id,
                'bookings-3-block': block.id,
                'bookings-3-status': 'OPEN'
            }
        )
        # try to create new booking with this block
        resp = self._post_response(
            self.staff_user, self.user.id, form_data=form_data
        )
        errors = resp.context_data['userbookingformset'].errors
        self.assertIn(
            {
                'block': ['Block selected for {} is now full. ' \
                            'Add another block for this user or confirm ' \
                            'payment was made directly.'.format(event1)] \
            },
            errors)

    def test_cannot_create_new_block_booking_when_no_available_blocktype(self):
        event1 = mommy.make_recipe('booking.future_EV')
        event2 = mommy.make_recipe('booking.future_PC')

        block1 = mommy.make_recipe(
            'booking.block', block_type__event_type=event1.event_type,
            user=self.user
        )

        self.assertEqual(Booking.objects.count(), 10)
        form_data = self.formset_data(
            {
                'bookings-TOTAL_FORMS': 3,
                'bookings-2-event': event2.id,
                'bookings-2-status': 'OPEN',
                'bookings-2-block': block1.id
            }
        )
        resp = self._post_response(
            self.staff_user, self.user.id, form_data=form_data
        )
        errors = resp.context_data['userbookingformset'].errors
        self.assertIn(
            {
                'block': ['{} ({} type "{}") cannot be ' \
                            'block-booked'.format(
                    event2, 'class', event2.event_type
                )]
            },
            errors)
        bookings = Booking.objects.filter(event=event2)
        self.assertEqual(len(bookings), 0)
        self.assertEqual(Booking.objects.count(), 10)

    def test_cannot_add_booking_to_full_event(self):
        event = mommy.make_recipe('booking.future_EV', max_participants=2)
        mommy.make_recipe('booking.booking', event=event, _quantity=2)
        form_data = self.formset_data(
            {
                'bookings-TOTAL_FORMS': 3,
                'bookings-2-event': event.id,
                'bookings-2-status': 'OPEN'
            }
        )
        resp = self._post_response(
            self.staff_user, self.user.id, form_data=form_data
        )
        # redirects and doesn't make booking
        self.assertEqual(resp.status_code, 302)
        # new booking has not been made
        bookings = Booking.objects.filter(event=event)
        self.assertEqual(len(bookings), 2)

    def test_formset_unchanged(self):
        """
        test formset submitted unchanged redirects back to user bookings list
        """
        resp = self._post_response(
            self.staff_user, self.user.id, form_data=self.formset_data(
                {'formset_submitted': 'Submit'}
            )
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            resp.url,
            reverse(
                'studioadmin:user_bookings_list',
                kwargs={'user_id': self.user.id, 'booking_status': 'future'}
            )
        )

    def test_create_new_booking_as_free_class(self):
        event1 = mommy.make_recipe(
            'booking.future_PC',
            event_type__subtype='Pole level class'
        )
        block1 = mommy.make_recipe(
            'booking.block', block_type__event_type=event1.event_type,
            user=self.user
        )

        form_data = self.formset_data(
            {
                'bookings-TOTAL_FORMS': 3,
                'bookings-2-event': event1.id,
                'bookings-2-status': 'OPEN',
                'bookings-2-free_class': True
            }
        )
        self._post_response(
            self.staff_user, self.user.id, form_data=form_data
        )
        booking = Booking.objects.get(event=event1)
        self.assertTrue(booking.free_class)
        self.assertTrue(booking.paid)
        self.assertTrue(booking.payment_confirmed)

    def test_cannot_assign_free_class_to_normal_block(self):
        event1 = mommy.make_recipe(
            'booking.future_PC',
            event_type__subtype='Pole level class'
        )
        block1 = mommy.make_recipe(
            'booking.block', block_type__event_type=event1.event_type,
            user=self.user
        )
        form_data = self.formset_data(
            {
                'bookings-TOTAL_FORMS': 3,
                'bookings-2-event': event1.id,
                'bookings-2-status': 'OPEN',
                'bookings-2-block': block1.id,
                'bookings-2-free_class': True
            }
        )
        resp = self._post_response(
            self.staff_user, self.user.id, form_data=form_data
        )
        errors = resp.context_data['userbookingformset'].errors
        self.assertIn(
            {
                'free_class': ['"Free class" cannot be assigned to a block.']
            },
            errors)
        bookings = Booking.objects.filter(event=event1)
        self.assertEqual(len(bookings), 0)

    def test_confirmation_email_sent_if_data_changed(self):
        form_data = self.formset_data(
            {
                'bookings-0-status': 'CANCELLED',
                'bookings-0-send_confirmation': 'on',
            }
        )
        resp = self._post_response(
            self.staff_user, self.user.id, form_data=form_data
        )
        self.assertEqual(len(mail.outbox), 1)

    def test_confirmation_email_not_sent_if_data_unchanged(self):
        form_data=self.formset_data(
            {'formset_submitted': 'Submit',
            'bookings-0-send_confirmation': 'on'}
        )
        resp = self._post_response(
            self.staff_user, self.user.id, form_data=form_data
            )
        self.assertEqual(len(mail.outbox), 0)

    def test_cannot_assign_cancelled_booking_to_available_block(self):
        booking = mommy.make_recipe(
            'booking.booking',
            event__date=timezone.now()+timedelta(2),
            user=self.user,
            paid=False,
            payment_confirmed=False,
            status='CANCELLED'
        )
        block = mommy.make_recipe(
            'booking.block', block_type__event_type=booking.event.event_type,
            user=self.user
        )
        self.assertFalse(booking.block)
        form_data = self.formset_data(
            {
                'bookings-TOTAL_FORMS': 3,
                'bookings-INITIAL_FORMS': 3,
                'bookings-2-id': booking.id,
                'bookings-2-event': booking.event.id,
                'bookings-2-status': booking.status,
                'bookings-2-block': block.id
            }
        )
        resp = self._post_response(
            self.staff_user, self.user.id, form_data=form_data
        )

        booking.refresh_from_db()
        self.assertFalse(booking.block)
        self.assertFalse(booking.paid)
        self.assertFalse(booking.payment_confirmed)

        errors = resp.context_data['userbookingformset'].errors
        self.assertIn(
            {
                'block': [
                    'A cancelled booking cannot be assigned to a ' \
                    'block.  Please change status of booking for {} to "OPEN" ' \
                    'before assigning block'.format(booking.event)
                ]
            },
            errors)

    def test_cannot_assign_booking_for_cancelled_event_to_available_block(self):
        event = mommy.make_recipe('booking.future_EV', cancelled=True)
        booking = mommy.make_recipe(
            'booking.booking',
            event=event,
            user=self.user,
        )
        block = mommy.make_recipe(
            'booking.block', block_type__event_type=event.event_type,
            user=self.user
        )
        self.assertFalse(booking.block)
        form_data = self.formset_data(
            {
                'bookings-TOTAL_FORMS': 3,
                'bookings-INITIAL_FORMS': 3,
                'bookings-2-id': booking.id,
                'bookings-2-event': event.id,
                'bookings-2-status': booking.status,
                'bookings-2-block': block.id
            }
        )
        resp = self._post_response(
            self.staff_user, self.user.id, form_data=form_data
        )

        booking.refresh_from_db()
        self.assertFalse(booking.block)

        errors = resp.context_data['userbookingformset'].errors
        self.assertIn(
            {'block': [
                'Cannot assign booking for cancelled event {} to a '
                'block'.format(event)
                ],
             'status': [
                'Cannot reopen booking for cancelled event {}'.format(event)
                ]},
            errors
        )

    def test_reopen_booking_for_cancelled_event(self):
        event = mommy.make_recipe('booking.future_EV', cancelled=True)
        booking = mommy.make_recipe(
            'booking.booking',
            event=event,
            user=self.user,
            status="CANCELLED"
        )

        self.assertFalse(booking.block)
        form_data = self.formset_data(
            {
                'bookings-TOTAL_FORMS': 3,
                'bookings-INITIAL_FORMS': 3,
                'bookings-2-id': booking.id,
                'bookings-2-event': event.id,
                'bookings-2-status':'OPEN',
            }
        )
        resp = self._post_response(
            self.staff_user, self.user.id, form_data=form_data
        )

        booking.refresh_from_db()
        self.assertEqual(booking.status, 'CANCELLED')

        errors = resp.context_data['userbookingformset'].errors
        self.assertIn(
            {
                'status': [
                    'Cannot reopen booking for cancelled event {}'.format(event)
                ]
            },
            errors)

    def test_assign_booking_for_cancelled_event_to_free_class(self):
        event = mommy.make_recipe('booking.future_EV', cancelled=True)
        booking = mommy.make_recipe(
            'booking.booking',
            event=event,
            user=self.user,
            status='CANCELLED'
        )

        self.assertFalse(booking.block)
        form_data = self.formset_data(
            {
                'bookings-TOTAL_FORMS': 3,
                'bookings-INITIAL_FORMS': 3,
                'bookings-2-id': booking.id,
                'bookings-2-event': event.id,
                'bookings-2-free_class': True,
                'bookings-2-status': booking.status
            }
        )
        resp = self._post_response(
            self.staff_user, self.user.id, form_data=form_data
        )

        booking.refresh_from_db()
        self.assertFalse(booking.free_class)

        errors = resp.context_data['userbookingformset'].errors
        self.assertIn(
            {
                'free_class': [
                    'Cannot assign booking for cancelled event {} as free '
                    'class'.format(event)
                ]
            },
            errors)

    def test_assign_booking_for_cancelled_event_as_paid(self):
        event = mommy.make_recipe('booking.future_EV', cancelled=True)
        booking = mommy.make_recipe(
            'booking.booking',
            event=event,
            user=self.user,
            status='CANCELLED'
        )

        self.assertFalse(booking.block)
        form_data = self.formset_data(
            {
                'bookings-TOTAL_FORMS': 3,
                'bookings-INITIAL_FORMS': 3,
                'bookings-2-id': booking.id,
                'bookings-2-event': event.id,
                'bookings-2-paid': True,
                'bookings-2-status': booking.status
            }
        )
        resp = self._post_response(
            self.staff_user, self.user.id, form_data=form_data
        )

        booking.refresh_from_db()
        self.assertFalse(booking.paid)
        self.assertFalse(booking.payment_confirmed)

        errors = resp.context_data['userbookingformset'].errors
        self.assertIn(
            {
                'paid': [
                    'Cannot assign booking for cancelled event {} as '
                    'paid'.format(event)
                ]
            },
            errors)

    def test_assign_booking_for_cancelled_event_as_deposit_paid(self):
        event = mommy.make_recipe('booking.future_EV', cancelled=True)
        booking = mommy.make_recipe(
            'booking.booking',
            event=event,
            user=self.user,
            status='CANCELLED'
        )

        self.assertFalse(booking.block)
        form_data = self.formset_data(
            {
                'bookings-TOTAL_FORMS': 3,
                'bookings-INITIAL_FORMS': 3,
                'bookings-2-id': booking.id,
                'bookings-2-event': event.id,
                'bookings-2-deposit_paid': True,
                'bookings-2-status': booking.status
            }
        )
        resp = self._post_response(
            self.staff_user, self.user.id, form_data=form_data
        )

        booking.refresh_from_db()
        self.assertFalse(booking.paid)
        self.assertFalse(booking.payment_confirmed)

        errors = resp.context_data['userbookingformset'].errors
        self.assertIn(
            {
                'deposit_paid': [
                    'Cannot assign booking for cancelled event {} as '
                    'deposit paid'.format(event)
                ]
            },
            errors)

    def test_can_assign_free_class_to_free_class_block(self):
        # TODO
        pass

    def test_reopen_cancelled_booking(self):
        # TODO
        pass

    def test_remove_block_from_booking(self):
        # TODO
        pass

    def test_new_booking_uses_last_in_10_blocks_block(self):
        """
        Checking for and creating the free block is done at the model level;
        check this is triggered from the studioadmin user bookings changes too
        """
        # TODO
        pass

    def test_using_last_in_10_blocks_block_free_block_already_exists(self):
        """
        Also done at the model level; if free class block already exists, a
        new one is not created
        Check correct messages shown in content
        """
        # TODO
        pass

    def test_email_errors_when_sending_confirmation(self):
        # TODO
        pass

    def test_cancel_booking_for_full_event_emails_waiting_list(self):
        # TODO
        pass

    def test_email_errors_when_sending_waiting_list_email(self):
        # TODO
        pass


class UserBlocksViewTests(TestPermissionMixin, TestCase):

    def setUp(self):
        super(UserBlocksViewTests, self).setUp()
        self.block = mommy.make_recipe('booking.block', user=self.user)

    def _get_response(self, user, user_id):
        url = reverse(
            'studioadmin:user_blocks_list',
            kwargs={'user_id': user_id}
        )
        session = _create_session()
        request = self.factory.get(url)
        request.session = session
        request.user = user
        messages = FallbackStorage(request)
        request._messages = messages
        return user_blocks_view(request, user_id)

    def _post_response(self, user, user_id, form_data):
        url = reverse(
            'studioadmin:user_blocks_list',
            kwargs={'user_id': user_id}
        )
        session = _create_session()
        request = self.factory.post(url, form_data)
        request.session = session
        request.user = user
        messages = FallbackStorage(request)
        request._messages = messages
        return user_blocks_view(request, user_id)

    def formset_data(self, extra_data={}):

        data = {
            'blocks-TOTAL_FORMS': 1,
            'blocks-INITIAL_FORMS': 1,
            'blocks-0-id': self.block.id,
            'blocks-0-block_type': self.block.block_type.id,
            'blocks-0-start_date': self.block.start_date.strftime('%d/%m/%y')
            }

        for key, value in extra_data.items():
            data[key] = value

        return data

    def test_cannot_access_if_not_logged_in(self):
        """
        test that the page redirects if user is not logged in
        """
        url = reverse(
            'studioadmin:user_blocks_list',
            kwargs={'user_id': self.user.id}
        )
        resp = self.client.get(url)
        redirected_url = reverse('account_login') + "?next={}".format(url)
        self.assertEquals(resp.status_code, 302)
        self.assertIn(redirected_url, resp.url)

    def test_cannot_access_if_not_staff(self):
        """
        test that the page redirects if user is not a staff user
        """
        resp = self._get_response(self.user, self.user.id)
        self.assertEquals(resp.status_code, 302)
        self.assertEquals(resp.url, reverse('booking:permission_denied'))

    def test_instructor_group_cannot_access(self):
        """
        test that the page redirects if user is in the instructor group but is
        not a staff user
        """
        resp = self._get_response(self.instructor_user, self.user.id)
        self.assertEquals(resp.status_code, 302)
        self.assertEquals(resp.url, reverse('booking:permission_denied'))

    def test_can_access_as_staff_user(self):
        """
        test that the page can be accessed by a staff user
        """
        resp = self._get_response(self.staff_user, self.user.id)
        self.assertEquals(resp.status_code, 200)

    def test_view_users_blocks(self):
        """
        Test only user's bookings for future events shown by default
        """
        new_user = mommy.make_recipe('booking.user')
        new_blocks = mommy.make_recipe(
            'booking.block', user=new_user, _quantity=2
        )
        self.assertEqual(Block.objects.count(), 3)
        resp = self._get_response(self.staff_user, new_user.id)
        # get all but last form (last form is the empty extra one)
        block_forms = resp.context_data['userblockformset'].forms[:-1]
        self.assertEqual(len(block_forms), 2)

        new_blocks.reverse()  # blocks are shown in reverse order by start date
        self.assertEqual(
            [block.instance for block in block_forms],
            new_blocks
        )

    def test_can_update_block(self):
        self.assertFalse(self.block.paid)
        resp = self._post_response(
            self.staff_user, self.user.id,
            self.formset_data({'blocks-0-paid': True})
        )
        block = Block.objects.get(id=self.block.id)
        self.assertTrue(block.paid)

    def test_can_create_block(self):
        block_type = mommy.make_recipe('booking.blocktype')
        self.assertEqual(Block.objects.count(), 1)
        resp = self._post_response(
            self.staff_user, self.user.id,
            self.formset_data(
                {
                    'blocks-TOTAL_FORMS': 2,
                    'blocks-1-block_type': block_type.id
                }
            )
        )
        self.assertEqual(Block.objects.count(), 2)

    def test_formset_unchanged(self):
        """
        test formset submitted unchanged redirects back to user block list
        """
        resp = self._post_response(
            self.staff_user, self.user.id, form_data=self.formset_data()
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            resp.url,
            reverse(
                'studioadmin:user_blocks_list',
                kwargs={'user_id': self.user.id}
            )
        )

    def test_delete_block(self):
        # TODO
        pass

    def test_submitting_with_form_errors_shows_messages(self):
        # TODO (add new block with incorrect date format)
        pass

