from django.shortcuts import render, reverse
from django.contrib import auth
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods, require_POST
from django.http import HttpResponseRedirect

from .forms import RegistrationModelForm, LoginForm, SettingsModelForm


@require_http_methods(['GET', 'POST'])
def registration_view(req):
    if req.method == 'POST':
        form = RegistrationModelForm(req.POST)
        if form.is_valid():
            form.save()
            auth.login(req, form.instance)
            return HttpResponseRedirect(reverse('vksearch:communities'))
    else:
        form = RegistrationModelForm()
    return render(req, 'registration.html', {'form': form})


@require_http_methods(['GET', 'POST'])
def login_view(req):
    if req.method == 'POST':
        form = LoginForm(req, data=req.POST)
        if form.is_valid():
            user = form.user
            auth.login(req, user)
            return HttpResponseRedirect(reverse('vksearch:communities'))
    else:
        form = LoginForm()
    return render(req, 'login.html', {'form': form})


@require_POST
@login_required(login_url='/user/login', redirect_field_name=None)
def logout_view(req):
    auth.logout(req)
    return HttpResponseRedirect(reverse('user:login'))


@require_http_methods(['GET', 'POST'])
@login_required(login_url='/user/login', redirect_field_name=None)
def settings_view(req):
    user = req.user
    if req.method == 'POST':
        form = SettingsModelForm(req.POST, instance=user)
        if form.is_valid():
            form.save()
            auth.login(req, form.instance)
            return HttpResponseRedirect(reverse('user:settings'))
    else:
        form = SettingsModelForm(instance=user)
    return render(req, 'settings.html', {'form': form})
