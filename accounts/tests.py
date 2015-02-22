from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from accounts.forms import SignupForm
from accounts.views import ProfileUpdateView, profile
from booking.tests.helpers import set_up_fb
from model_mommy import mommy

class SignUpFormTests(TestCase):

    def test_signup_form(self):
        form_data = {'first_name': 'Test',
                     'last_name': 'User'}
        form = SignupForm(data=form_data)
        self.assertEqual(form.is_valid(), True)


class ProfileUpdateViewTests(TestCase):

    def setUp(self):
        set_up_fb()
        self.factory = RequestFactory()

    def test_updating_user_data(self):
        """
        Test custom view to allow users to update their details
        """
        user = mommy.make(User, username="test_user",
                          first_name="Test",
                          last_name="User",
                          )
        url = reverse('profile:update_profile')
        request = self.factory.post(
            url, {'username': user.username,
                  'first_name': 'Fred', 'last_name': user.last_name}
        )
        request.user = user
        view = ProfileUpdateView.as_view()
        resp = view(request)
        updated_user = User.objects.get(username="test_user")
        self.assertEquals(updated_user.first_name, "Fred")


class ProfileTest(TestCase):

    def setUp(self):
        set_up_fb()
        self.factory = RequestFactory()

    def test_profile_view(self):
        user = mommy.make(User)
        url = reverse('profile:profile')
        request = self.factory.get(url)
        request.user = user
        resp = profile(request)

        self.assertEquals(resp.status_code, 200)

