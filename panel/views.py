# panel/views.py

from django.contrib.auth import authenticate, login, logout
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

# CORREÇÃO: Importamos um tipo de autenticação que não exige o token CSRF
from rest_framework.authentication import SessionAuthentication, BasicAuthentication

class CsrfExemptSessionAuthentication(SessionAuthentication):
    """
    Esta classe de autenticação desativa a verificação CSRF.
    É útil para APIs consumidas por clientes JavaScript ou para testes no Postman.
    """
    def enforce_csrf(self, request):
        return  # Não faz nada, efetivamente desativando a verificação.

# --- VIEWS DA API ---

@api_view(['POST'])
# CORREÇÃO: Usamos a nossa classe que desativa o CSRF
@authentication_classes([CsrfExemptSessionAuthentication, BasicAuthentication])
def login_view(request):
    """
    Endpoint da API para autenticar um usuário.
    Espera um JSON com 'username' e 'password'.
    """
    username = request.data.get('username')
    password = request.data.get('password')

    user = authenticate(request, username=username, password=password)

    if user is not None:
        login(request, user) # Cria a sessão para o usuário
        return Response({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email
            }
        }, status=status.HTTP_200_OK)
    else:
        return Response(
            {'success': False, 'error': 'Credenciais inválidas'}, 
            status=status.HTTP_401_UNAUTHORIZED
        )

@api_view(['POST'])
# CORREÇÃO: Usamos a nossa classe que desativa o CSRF
@authentication_classes([CsrfExemptSessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated]) # Só permite o logout se o usuário estiver logado
def logout_view(request):
    """
    Endpoint da API para fazer o logout do usuário.
    """
    logout(request) # Remove a sessão do usuário
    return Response({'success': True, 'message': 'Logout realizado com sucesso.'}, status=status.HTTP_200_OK)

@api_view(['GET'])
# CORREÇÃO: Usamos a nossa classe que desativa o CSRF
@authentication_classes([CsrfExemptSessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated]) # Protege este endpoint
def user_data_view(request):
    """
    Endpoint de exemplo para buscar dados do usuário logado.
    """
    user = request.user
    return Response({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name
    })