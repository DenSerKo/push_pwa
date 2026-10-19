from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("push/subscribe/", views.subscribe, name="push_subscribe"),
    path("push/unsubscribe/", views.unsubscribe, name="push_unsubscribe"),
    path("push/send-test/", views.send_test, name="push_send_test"),
]
