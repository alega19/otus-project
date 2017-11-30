from django.conf.urls import url

from . import views


urlpatterns = [
    url(r'^signup$', views.registration_view, name='registration'),
    url(r'^login$', views.login_view, name='login'),
    url(r'^logout$', views.logout_view, name='logout'),
    url(r'^settings$', views.settings_view, name='settings')
]
