# chatbot/views.py

import json
import logging
import asyncio # Para uso com async_to_sync se precisar de operações assíncronas
from django.http import JsonResponse
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema # <-- Importe swagger_auto_schema
from drf_yasg import openapi # <-- Importe openapi

# Importe seus serializers
from .serializers import WebchatPayloadSerializer, WebhookPayloadSerializer, ChatbotResponseSerializer 
# Importe seu serviço de chatbot
from .services import ChatbotService
from asgiref.sync import async_to_sync # Para chamar métodos assíncronos em views síncronas

logger = logging.getLogger(__name__)

# Instância do serviço de chatbot
chatbot_service = ChatbotService()

# --- WEBCHAT VIEW ---

@swagger_auto_schema(
    method='post',
    request_body=WebchatPayloadSerializer, # Define o serializer para o corpo da requisição
    responses={
        200: openapi.Response(
            description="Mensagem processada com sucesso e resposta do chatbot.",
            schema=ChatbotResponseSerializer # Define o serializer para a resposta de sucesso
        ),
        400: openapi.Response(
            description="Requisição inválida. Erros de validação do payload.",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'session_id': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), description="Mensagens de erro para o campo session_id."),
                    'message': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), description="Mensagens de erro para o campo message."),
                    # Adicione outros campos de erro se seu serializer puder retornar mais
                }
            )
        ),
        500: openapi.Response(
            description="Erro interno no servidor ao processar a mensagem.",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'resposta': openapi.Schema(type=openapi.TYPE_STRING, description="Mensagem de erro amigável.")
                }
            )
        )
    },
    operation_summary="Envia uma mensagem para o chatbot do webchat",
    operation_description=(
        "Este endpoint é utilizado pelo frontend do webchat para enviar mensagens ao chatbot. "
        "Ele recebe o ID da sessão e o texto da mensagem, processa-os usando o serviço de chatbot "
        "e retorna a resposta gerada."
    )
)
@api_view(['POST'])
@authentication_classes([]) # Sem autenticação para este endpoint, como é para um chatbot público
@permission_classes([])     # Sem permissões para este endpoint
def webchat_view(request):
    """
    Endpoint para comunicação com o chatbot via web (frontend).
    Recebe session_id e message e retorna a resposta do bot.
    """
    # Debugging: Imprime os dados brutos e parsados que a view recebe
    print("--- DEBUG WEBCHAT VIEW ---")
    print("Método da Requisição:", request.method)
    print("Cabeçalhos da Requisição (Headers):", request.headers)
    print("Corpo Bruto da Requisição (request.body):", request.body)
    print("Dados Parsados da Requisição (request.data):", request.data)
    print("--- FIM DEBUG WEBCHAT VIEW ---")

    serializer = WebchatPayloadSerializer(data=request.data)
    if not serializer.is_valid():
        logger.error("Erro de validação do Webchat Payload: %s", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    validated_data = serializer.validated_data
    session_id = validated_data['session_id']
    message_text = validated_data['message']
    
    user_id = f"webchat_{session_id}" # Prefixo para diferenciar usuários do webchat
    push_name = "Visitante" # Nome padrão para novos usuários do webchat

    try:
        # Chama o serviço de chatbot de forma assíncrona, usando async_to_sync
        response_text = async_to_sync(chatbot_service.process_message)(
            user_id, message_text, push_name, channel='webchat'
        )
        return Response({"response": response_text, "session_id": session_id}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.exception("Erro ao processar mensagem do webchat para user_id: %s", user_id)
        return Response(
            {"resposta": "Desculpe, ocorreu um erro no nosso servidor ao processar sua mensagem."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# --- WEBHOOK VIEW (para Evolution API) ---

@swagger_auto_schema(
    method='post',
    request_body=WebhookPayloadSerializer, # Define o serializer para o corpo da requisição do webhook
    responses={
        200: openapi.Response(
            description="Webhook recebido e processado com sucesso. Retorna um status de OK.",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'status': openapi.Schema(type=openapi.TYPE_STRING, description="Indica o sucesso da operação (e.g., 'ok')."),
                    'message': openapi.Schema(type=openapi.TYPE_STRING, description="Mensagem de feedback (opcional).")
                }
            )
        ),
        400: openapi.Response(
            description="Requisição inválida. Erros de validação do payload do webhook.",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'error': openapi.Schema(type=openapi.TYPE_STRING, description="Descrição do erro de validação.")
                }
            )
        ),
        500: openapi.Response(
            description="Erro interno no servidor ao processar o webhook.",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'error': openapi.Schema(type=openapi.TYPE_STRING, description="Mensagem de erro interno.")
                }
            )
        )
    },
    operation_summary="Recebe eventos de webhook da Evolution API (WhatsApp)",
    operation_description=(
        "Este endpoint é o ponto de entrada para os webhooks da Evolution API. "
        "Ele processa mensagens recebidas do WhatsApp, extrai o conteúdo relevante "
        "e as encaminha para o serviço de chatbot para geração de resposta. "
        "Espera uma payload JSON específica da Evolution API."
    )
)
@api_view(['POST'])
@authentication_classes([]) # Normalmente, webhooks não usam autenticação baseada em token HTTP,
@permission_classes([])     # mas podem ter uma chave secreta no corpo ou header para validação.
def webhook_view(request):
    """
    Endpoint para receber webhooks da Evolution API (WhatsApp).
    Processa mensagens recebidas do WhatsApp e as envia para o chatbot.
    """
    logger.info("Webhook recebido. Dados: %s", request.data)

    serializer = WebhookPayloadSerializer(data=request.data)
    if not serializer.is_valid():
        logger.error("Erro de validação do Webhook Payload: %s", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    validated_data = serializer.validated_data
    
    # Extração dos dados relevantes do webhook da Evolution API
    # ATENÇÃO: A estrutura exata do 'data' e 'message' dentro do webhook
    # pode variar. Ajuste conforme o que a sua instância da Evolution API envia.
    try:
        data_payload = validated_data['data']
        message_data = data_payload.get('message', {})
        
        # Verifica se é uma mensagem de texto e extrai o número e o texto
        if 'textMessage' in message_data:
            message_text = message_data['textMessage'].get('text', '')
            remote_jid = data_payload.get('key', {}).get('remoteJid', '')
            
            # O remoteJid vem como "55ddnnnnnnnn@s.whatsapp.net".
            # Precisamos extrair apenas os números para usar como user_id.
            # remove '@s.whatsapp.net' e qualquer caractere não numérico
            user_id = re.sub(r'[^0-9]', '', remote_jid.split('@')[0]) 

            # O 'pushName' pode estar em data.pushName ou data.sender.pushName, etc.
            # Ajuste conforme o JSON que a Evolution API envia.
            push_name = data_payload.get('pushName', 'Usuário WhatsApp') 

            if not user_id or not message_text:
                logger.warning("Webhook: user_id ou message_text não encontrados na payload.")
                return Response({"status": "ignorado", "message": "Dados insuficientes"}, status=status.HTTP_200_OK)

            # Chama o serviço de chatbot de forma assíncrona, usando async_to_sync
            response_text = async_to_sync(chatbot_service.process_message)(
                user_id, message_text, push_name, channel='whatsapp'
            )

            # Envia a resposta de volta para o WhatsApp via Evolution API (de forma assíncrona)
            async_to_sync(chatbot_service.send_whatsapp_message)(user_id, response_text)
            
            return Response({"status": "ok", "message": "Mensagem do webhook processada e resposta enviada."}, status=status.HTTP_200_OK)
        else:
            logger.info("Webhook: Tipo de mensagem não suportado ou sem texto.")
            # Você pode optar por responder a outros tipos de mensagem ou ignorá-los
            return Response({"status": "ignorado", "message": "Tipo de mensagem não suportado ou sem texto."}, status=status.HTTP_200_OK)

    except KeyError as e:
        logger.error("Erro na estrutura da payload do webhook: Campo '%s' ausente. Payload: %s", e, request.data)
        return Response({"error": f"Payload do webhook com formato inesperado. Campo '{e}' ausente."}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.exception("Erro interno ao processar webhook: %s", e)
        return Response({"error": "Erro interno do servidor ao processar o webhook."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)