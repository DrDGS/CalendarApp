from django.urls import path
from . import views

app_name = 'calendar_app'

urlpatterns = [
    path('', views.calendar_view, name='calendar'),
    path('add-event/', views.add_event_view, name='add_event'),
    path('delete-event/<str:event_id>/', views.delete_event_view, name='delete_event'),
    path('ai-analysis/', views.get_ai_analysis, name='ai_analysis'),
    path('upload-url/', views.upload_url, name='upload_url'), 
    path('analyze-docx/', views.analyze_docx_view, name='analyze_docx'), 
]