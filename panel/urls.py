# panel/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Endpoints de Autenticação da API
    path('login/', views.login_view, name='api_login'),
    path('logout/', views.logout_view, name='api_logout'),
    
    # Endpoint de exemplo para dados protegidos
    path('user-data/', views.user_data_view, name='api_user_data'),
]