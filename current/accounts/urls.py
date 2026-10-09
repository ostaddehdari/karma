from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    path('management/users/', views.user_management, name='user_management'),
    path('management/users/add/', views.user_create_admin, name='user_create_admin'),
    path('management/users/<int:user_id>/edit/', views.user_edit_admin, name='user_edit_admin'),
    path('management/users/<int:user_id>/reset-password/', views.user_reset_password, name='user_reset_password'),
    path('management/users/<int:user_id>/toggle-active/', views.user_toggle_active, name='user_toggle_active'),
    path('management/users/merge-duplicates/', views.users_merge_duplicates, name='users_merge_duplicates'),
    path('management/users/reset-all-passwords/', views.users_reset_all_passwords, name='users_reset_all_passwords'),
]
