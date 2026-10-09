from django.urls import path
from . import views

urlpatterns = [
    path('', views.time_report, name='time_report'),
    path('project/<int:project_id>/manual/', views.worklog_manual_add, name='worklog_manual_add'),
    path('project/<int:project_id>/start/', views.timer_start, name='timer_start'),
    path('log/<int:log_id>/stop/', views.timer_stop, name='timer_stop'),
    path('log/<int:log_id>/delete/', views.worklog_delete, name='worklog_delete'),
]
