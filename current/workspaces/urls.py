from django.urls import path
from . import views

urlpatterns = [
    path('', views.workspace_list, name='workspace_list'),
    path('new/', views.workspace_create, name='workspace_create'),
    path('import/', views.workspace_import, name='workspace_import'),
    path('<int:pk>/', views.workspace_detail, name='workspace_detail'),
    path('<int:pk>/logo/', views.workspace_logo, name='workspace_logo'),
    path('<int:pk>/edit/', views.workspace_edit, name='workspace_edit'),
    path('<int:pk>/delete/', views.workspace_delete, name='workspace_delete'),
    path('<int:pk>/export/', views.workspace_export, name='workspace_export'),
    path('<int:pk>/members/add/', views.member_add, name='member_add'),
    path('<int:pk>/members/<int:member_id>/edit/', views.member_edit, name='member_edit'),
    path('<int:pk>/members/<int:member_id>/delete/', views.member_delete, name='member_delete'),
]
