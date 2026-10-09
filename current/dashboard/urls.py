from django.urls import path
from .views import dashboard, search

urlpatterns = [
    path('dashboard/', dashboard, name='dashboard'),
    path('search/', search, name='global_search'),
]
