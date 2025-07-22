# chatbot/services.py

import httpx
import openai
import re
from datetime import datetime, timezone
from typing import List

from django.conf import settings
from .models import Usuario, Prompt
from channels.db import database_sync_to_async # <-- ESTA LINHA CORRIGE O ERRO

# --- CONSTANTES ---
STATE_MAP = {
    'Acre': 'AC', 'Alagoas': 'AL', 'Amapá': 'AP', 'Amazonas': 'AM', 'Bahia': 'BA', 'Ceará': 'CE', 'Distrito Federal': 'DF',
    'Espírito Santo': 'ES', 'Goiás': 'GO', 'Maranhão': 'MA', 'Mato Grosso': 'MT', 'Mato Grosso do Sul': 'MS', 'Minas Gerais': 'MG',
    'Pará': 'PA', 'Paraíba': 'PB', 'Paraná': 'PR', 'Pernambuco': 'PE', 'Piauí': 'PI', 'Rio de Janeiro': 'RJ',
    'Rio Grande do Norte': 'RN', 'Rio Grande do Sul': 'RS', 'Rondônia': 'RO', 'Roraima': 'RR', 'Santa Catarina': 'SC',
    'São Paulo': 'SP', 'Sergipe': 'SE', 'Tocantins': 'TO'
}

class ChatbotService:
    def __init__(self):
        if settings.OPENAI_API_KEY:
            self.openai_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        else:
            self.openai_client = None

    @database_sync_to_async
    def _get_prompt(self, key: str) -> str:
        try:
            return Prompt.objects.get(key=key).text
        except Prompt.DoesNotExist:
            print(f"AVISO: Prompt com a chave '{key}' não encontrado no banco de dados.")
            return f"Prompt '{key}' não configurado."

    async def send_whatsapp_message(self, phone_number: str, text: str):
        url = f"{settings.EVOLUTION_API_URL}/message/sendText/{settings.EVOLUTION_INSTANCE_NAME}"
        headers = {"apikey": settings.EVOLUTION_API_KEY}
        payload = {"number": phone_number, "textMessage": {"text": text}}
        async with httpx.AsyncClient() as client:
            try:
                await client.post(url, json=payload, headers=headers, timeout=10)
            except Exception as e:
                print(f"ERRO DE API: Falha ao enviar mensagem. Erro: {e}")

    async def get_location_details_from_coords(self, lat: float, lon: float) -> dict:
        url = "http://api.openweathermap.org/geo/1.0/reverse"
        params = {"lat": lat, "lon": lon, "limit": 1, "appid": settings.OPENWEATHER_API_KEY}
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            if response.status_code == 200 and response.json():
                location = response.json()[0]
                state_abbr = STATE_MAP.get(location.get("state"), "")
                return {"city": location.get("name"), "state": state_abbr}
            return {}

    async def get_location_details_from_city(self, city: str) -> dict:
        url = "http://api.openweathermap.org/geo/1.0/direct"
        params = {"q": f"{city},BR", "limit": 1, "appid": settings.OPENWEATHER_API_KEY}
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            if response.status_code == 200 and response.json():
                location = response.json()[0]
                state_abbr = STATE_MAP.get(location.get("state"), "")
                return {"city": location.get("name"), "state": state_abbr, "lat": location.get("lat"), "lon": location.get("lon")}
            return {}

    @database_sync_to_async
    def get_or_create_user(self, user_identifier: str, push_name: str, channel: str) -> Usuario:
        user, created = Usuario.objects.get_or_create(
            whatsapp_id=user_identifier,
            defaults={'nome': push_name if channel == 'whatsapp' else '', 'organizacao_id': 1, 'contexto': {}}
        )
        if created:
            print(f"INFO: Novo usuário criado via {channel}: {user_identifier}")
        return user

    @database_sync_to_async
    def save_user(self, user: Usuario):
        user.ultima_atividade = datetime.now(timezone.utc)
        user.save()

    def _reset_all_flow_flags(self, context: dict) -> dict:
        keys_to_remove = [key for key in context if key.startswith('awaiting_')]
        for key in keys_to_remove:
            context.pop(key, None)
        return context

    async def process_message(self, user_identifier: str, message_text: str, push_name: str, channel: str, location_data: dict = None) -> str:
        user = await self.get_or_create_user(user_identifier, push_name, channel)
        context = user.contexto or {}
        message_lower = message_text.lower().strip()
        
        response_text = ""

        if message_lower in ['reiniciar', 'recomeçar', 'inicio', 'menu']:
            user.nome = ''
            user.contexto = {}
            await self.save_user(user)
            return await self.process_message(user_identifier, "", push_name, channel)

        if not user.nome and not context.get('awaiting_initial_name'):
            context['awaiting_initial_name'] = True
            user.contexto = context
            await self.save_user(user)
            response_text = await self._get_prompt('welcome_ask_name')

        elif context.get('awaiting_initial_name'):
            user.nome = message_text.strip().title()
            context['awaiting_initial_name'] = False
            context['awaiting_location'] = True
            user.contexto = context
            await self.save_user(user)
            prompt_key = 'welcome_ask_location_whatsapp' if channel == 'whatsapp' else 'welcome_ask_location_web'
            prompt_template = await self._get_prompt(prompt_key)
            response_text = prompt_template.format(user_nome=user.nome)

        elif context.get('awaiting_location'):
            thank_you_message = ""
            location_processed = False
            
            if channel == 'whatsapp' and location_data:
                details = await self.get_location_details_from_coords(location_data['latitude'], location_data['longitude'])
                if details:
                    user.cidade, user.estado = details.get('city'), details.get('state')
                    thank_you_template = await self._get_prompt('location_received_whatsapp')
                    thank_you_message = thank_you_template.format(user_nome=user.nome)
                    location_processed = True
            elif channel == 'webchat' and message_text:
                details = await self.get_location_details_from_city(message_text)
                if details:
                    user.cidade, user.estado = details.get('city'), details.get('state')
                    thank_you_template = await self._get_prompt('location_received_web')
                    thank_you_message = thank_you_template.format(cidade=user.cidade, user_nome=user.nome)
                    location_processed = True
                else:
                    response_text = f"Não consegui encontrar a cidade '{message_text}'. Pode tentar de novo?"
            
            if location_processed:
                context = self._reset_all_flow_flags(context)
                user.contexto = context
                await self.save_user(user)
                main_menu_text = await self._get_prompt('main_menu_v2')
                if channel == 'whatsapp':
                    await self.send_whatsapp_message(user_identifier, thank_you_message)
                    response_text = main_menu_text
                else:
                    response_text = f"{thank_you_message}\n\n{main_menu_text}"
            elif not response_text:
                response_text = await self._get_prompt('location_error')
        
        else:
            fallback_template = await self._get_prompt('default_fallback')
            menu_text = await self._get_prompt('main_menu_v2')
            nome_curto = user.nome.split(' ')[0] if user.nome else 'você'
            response_text = f"{fallback_template.format(user_nome=nome_curto)}\n\n{menu_text}"
        
        return response_text