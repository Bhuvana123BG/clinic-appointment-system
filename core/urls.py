from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    # Auth
    path('patient/login/', views.patient_login, name='patient_login'),
    path('patient/register/', views.patient_register, name='patient_register'),
    path('doctor/login/', views.doctor_login, name='doctor_login'),
    path('logout/', views.logout_view, name='logout'),
    path('post-login/', views.post_login, name='post_login'),
     # Dashboards
    path('patient/dashboard/', views.patient_dashboard, name='patient_dashboard'),
    path('doctor/dashboard/', views.doctor_dashboard, name='doctor_dashboard'),
    # Patient features
    path('patient/make-appointment/', views.make_appointment, name='make_appointment'),
    path('patient/doctor/<int:doctor_id>/', views.doctor_detail, name='doctor_detail'),
     path("doctor/<int:doctor_id>/request/", views.request_appointment, name="request_appointment"),
    path('patient/request/<int:doctor_id>/', views.request_appointment, name='request_appointment'),
    path('patient/history/', views.patient_history, name='patient_history'),
    path("patient/history/<str:status>/", views.patient_history_status, name="patient_history_status"),
    path("patient/appointment/edit/<int:appointment_id>/", views.edit_appointment, name="edit_appointment"),
    # Patient profile
    path('patient/profile/', views.patient_profile, name='patient_profile'),
    path('patient/profile/edit/', views.patient_profile_edit, name='patient_profile_edit'),
    # Doctor features
    path('doctor/requests/', views.doctor_requests, name='doctor_requests'),
    path('doctor/requests/<int:appt_id>/approve/', views.approve_request, name='approve_request'),
    path('doctor/requests/<int:appt_id>/reject/', views.reject_request, name='reject_request'),
    path('doctor/history/', views.doctor_history, name='doctor_history'),
    path('doctor/history/<str:status>/', views.doctor_history_status, name='doctor_history_status'),
    # Doctor profile
    path('doctor/profile/', views.doctor_profile, name='doctor_profile'),
    path('doctor/profile/edit/', views.doctor_profile_edit, name='doctor_profile_edit'),
]
