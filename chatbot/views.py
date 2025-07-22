# chatbot/views.py

import json
import logging
import re
from asgiref.sync import async_to_sync

from django.http import JsonResponse
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .serializers import WebchatPayloadSerializer, WebhookPayloadSerializer, ChatbotResponseSerializer
from .services import ChatbotService

logger = logging.getLogger(__name__)
chatbot_service = ChatbotService()

@swagger_auto_schema(
    method='post',
    request_body=WebchatPayloadSerializer,
    responses={200: ChatbotResponseSerializer}
)
@api_view(['POST'])
@authentication_classes([])
@permission_classes([])
def webchat_view(request):
    serializer = WebchatPayloadSerializer(data=request.data)
    if not serializer.is_valid():
        logger.error("Erro de validação (Webchat): %s", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    session_id, message_text = data['session_id'], data['message']
    user_id = f"webchat_{session_id}"
    
    try:
        location_data = {"latitude": data['latitude'], "longitude": data['longitude']} if 'latitude' in data else None
        
        response_text = async_to_sync(chatbot_service.process_message)(
            user_id, message_text, "Visitante", 'webchat', location_data
        )
        
        return Response({"response": response_text, "session_id": session_id}, status=status.HTTP_200_OK)

    except Exception as e:
        logger.exception(f"Erro ao processar webchat para user_id: {user_id}")
        return Response(
            {"response": "Desculpe, ocorreu um erro no nosso servidor."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@swagger_auto_schema(method='post', request_body=WebhookPayloadSerializer)
@api_view(['POST'])
@authentication_classes([])
@permission_classes([])
def webhook_view(request):
    logger.info("Webhook recebido: %s", request.data)
    serializer = WebhookPayloadSerializer(data=request.data)
    if not serializer.is_valid():
        logger.error("Erro de validação (Webhook): %s", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    
    try:
        data_payload = data.get('data', {})
        key_data = data_payload.get('key', {})
        
        if data.get('event') != 'messages.upsert' or key_data.get('fromMe', False):
            return Response({"status": "ignorado"}, status=status.HTTP_200_OK)

        user_id = key_data.get('remoteJid')
        if not user_id:
            return Response({"status": "ignorado"}, status=status.HTTP_200_OK)

        push_name = data_payload.get('pushName', 'Usuário')
        message_data = data_payload.get('message', {})
        message_text = ""
        location_data = None

        if 'conversation' in message_data:
            message_text = message_data.get('conversation', '')
        elif 'extendedTextMessage' in message_data:
            message_text = message_data.get('extendedTextMessage', {}).get('text', '')
        elif 'locationMessage' in message_data:
            loc_msg = message_data['locationMessage']
            if 'degreesLatitude' in loc_msg and 'degreesLongitude' in loc_msg:
                location_data = {"latitude": loc_msg['degreesLatitude'], "longitude": loc_msg['degreesLongitude']}
        
        response_text = async_to_sync(chatbot_service.process_message)(
            user_id, message_text, push_name, 'whatsapp', location_data
        )

        if response_text:
            async_to_sync(chatbot_service.send_whatsapp_message)(user_id, response_text)
        
        return Response({"status": "ok"}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.exception(f"Erro interno ao processar webhook: {e}")
        return Response({"error": "Erro interno do servidor."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)