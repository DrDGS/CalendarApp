from django.urls import path
from . import views

app_name = 'calendar_app'

urlpatterns = [
    path('', views.calendar_view, name='calendar'),
    path('add-event/', views.add_event_view, name='add_event'),
]