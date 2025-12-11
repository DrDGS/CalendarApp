from django.urls import path
from . import views

app_name = 'calendar_app'

urlpatterns = [
    path('', views.calendar_view, name='calendar'),
    path('add-event/', views.add_event_view, name='add_event'),
    path('delete-event/<int:event_id>/', views.delete_event_view, name='delete_event'),
]