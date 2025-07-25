# panel/views.py

from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings

from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
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
@authentication_classes([CsrfExemptSessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    Endpoint da API para fazer o logout do usuário.
    """
    logout(request) # Remove a sessão do usuário
    return Response({'success': True, 'message': 'Logout realizado com sucesso.'}, status=status.HTTP_200_OK)

@api_view(['GET'])
@authentication_classes([CsrfExemptSessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
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
    
# --- NOVAS VIEWS PARA SENHA ---

@api_view(['POST'])
@authentication_classes([CsrfExemptSessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def password_change_view(request):
    """
    Endpoint para um usuário LOGADO trocar a própria senha.
    Espera: { "current_password": "...", "new_password": "..." }
    """
    user = request.user
    current_password = request.data.get("current_password")
    new_password = request.data.get("new_password")

    if not user.check_password(current_password):
        return Response({"error": "A senha atual está incorreta."}, status=status.HTTP_400_BAD_REQUEST)

    user.set_password(new_password)
    user.save()
    
    # É importante atualizar a sessão para manter o usuário logado
    update_session_auth_hash(request, user)
    
    return Response({"success": "Senha alterada com sucesso."}, status=status.HTTP_200_OK)

@api_view(['POST'])
@authentication_classes([CsrfExemptSessionAuthentication, BasicAuthentication])
def password_reset_request_view(request):
    """
    Endpoint para solicitar a redefinição de senha.
    Espera: { "email": "..." }
    """
    email = request.data.get("email")
    try:
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        # Não informe ao usuário se o email existe ou não por segurança.
        return Response({"success": "Se um usuário com este email existir, um link de redefinição foi enviado."}, status=status.HTTP_200_OK)

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    
    # URL que o seu frontend em Next.js usará para a tela de redefinição
    reset_link = f"http://localhost:3000/resetar-senha/{uid}/{token}/" # Altere para a URL do seu frontend

    message = f"""
    Olá,

    Recebemos um pedido para redefinir a sua senha.
    Clique no link abaixo para continuar:
    {reset_link}

    Se você não fez este pedido, por favor ignore este email.

    Atenciosamente,
    Equipe Campo Inteligente
    """

    send_mail(
        subject="Redefinição de Senha - Campo Inteligente",
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )

    return Response({"success": "Se um usuário com este email existir, um link de redefinição foi enviado."}, status=status.HTTP_200_OK)


@api_view(['POST'])
@authentication_classes([CsrfExemptSessionAuthentication, BasicAuthentication])
def password_reset_confirm_view(request):
    """
    Endpoint para confirmar a redefinição de senha com o token.
    Espera: { "uid": "...", "token": "...", "new_password": "..." }
    """
    uid = request.data.get("uid")
    token = request.data.get("token")
    new_password = request.data.get("new_password")

    try:
        user_id = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=user_id)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.set_password(new_password)
        user.save()
        return Response({"success": "Sua senha foi redefinida com sucesso."}, status=status.HTTP_200_OK)
    else:
        return Response({"error": "O link é inválido ou já expirou."}, status=status.HTTP_400_BAD_REQUEST)