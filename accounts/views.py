from django.shortcuts import render, HttpResponse, get_object_or_404
from django.views.generic import UpdateView
from django.contrib.auth.models import User
from braces.views import LoginRequiredMixin


def profile(request):
    return render(request, 'account/profile.html')


class ProfileUpdateView(LoginRequiredMixin, UpdateView):

    model = User
    template_name = 'account/update_profile.html'
    fields = ('username', 'first_name', 'last_name',)

    def get_object(self):
        return get_object_or_404(User, email=self.request.user.email)
