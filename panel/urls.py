# panel/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Endpoints de Autenticação da API
    path('login/', views.login_view, name='api_login'),
    path('logout/', views.logout_view, name='api_logout'),
    
    # Endpoint de exemplo para dados protegidos
    path('user-data/', views.user_data_view, name='api_user_data'),
    
    # Endpoints para troca e recuperação de senha
    path('password/change/', views.password_change_view, name='api_password_change'),
    path('password/reset/', views.password_reset_request_view, name='api_password_reset_request'),
    path('password/reset/confirm/', views.password_reset_confirm_view, name='api_password_reset_confirm'),
]