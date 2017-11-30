from django.conf.urls import url
from . import views


urlpatterns = [
    url(r'^$', views.communities_view, name='communities')
]
