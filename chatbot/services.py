# chatbot/services.py

import httpx
import openai
import re
from datetime import datetime, timezone
from typing import List, Dict

from django.conf import settings
from .models import Usuario, Prompt, State
from channels.db import database_sync_to_async

class ChatbotService:
    def __init__(self):
        if settings.OPENAI_API_KEY:
            self.openai_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        else:
            self.openai_client = None
        
        # Inicializa os mapas como vazios para serem carregados depois de forma assíncrona
        self.state_map_by_name: Dict[str, str] = {}
        self.state_map_by_abbr: List[str] = []

    async def _load_state_maps_if_needed(self):
        """
        Carrega os mapas de estado do banco de dados de forma assíncrona,
        apenas se eles ainda não tiverem sido carregados.
        """
        if not self.state_map_by_name:
            states = await self._get_all_states()
            self.state_map_by_name = {state.name: state.abbreviation for state in states}
            self.state_map_by_abbr = [state.abbreviation for state in states]

    @database_sync_to_async
    def _get_all_states(self) -> List[State]:
        return list(State.objects.all())

    # --- MÉTODOS AUXILIARES E DE API ---

    async def _parse_city_from_input(self, text: str) -> str:
        """Limpa a entrada do usuário para extrair apenas o nome da cidade."""
        await self._load_state_maps_if_needed() # Garante que os mapas estão carregados
        cleaned_text = re.split(r'[-/]', text)[0]
        words = cleaned_text.strip().split()
        if len(words) > 1 and words[-1].upper() in self.state_map_by_abbr:
            return " ".join(words[:-1]).strip()
        return cleaned_text.strip()

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

    async def get_weather_data(self, city: str) -> dict:
        url = "http://api.openweathermap.org/data/2.5/weather"
        params = {"q": f"{city},BR", "appid": settings.OPENWEATHER_API_KEY, "units": "metric", "lang": "pt_br"}
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            return response.json() if response.status_code == 200 else {"error": f"Cidade '{city}' não encontrada."}

    async def get_location_details_from_coords(self, lat: float, lon: float) -> dict:
        await self._load_state_maps_if_needed()
        url = "http://api.openweathermap.org/geo/1.0/reverse"
        params = {"lat": lat, "lon": lon, "limit": 1, "appid": settings.OPENWEATHER_API_KEY}
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            if response.status_code == 200 and response.json():
                location = response.json()[0]
                state_abbr = self.state_map_by_name.get(location.get("state"), "")
                return {"city": location.get("name"), "state": state_abbr}
            return {}

    async def get_location_details_from_city(self, city: str) -> dict:
        await self._load_state_maps_if_needed()
        url = "http://api.openweathermap.org/geo/1.0/direct"
        params = {"q": f"{city},BR", "limit": 1, "appid": settings.OPENWEATHER_API_KEY}
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            if response.status_code == 200 and response.json():
                location = response.json()[0]
                state_abbr = self.state_map_by_name.get(location.get("state"), "")
                return {"city": location.get("name"), "state": state_abbr, "lat": location.get("lat"), "lon": location.get("lon")}
            return {}

    @database_sync_to_async
    def get_or_create_user(self, user_identifier: str, push_name: str, channel: str) -> Usuario:
        user, _ = Usuario.objects.get_or_create(
            whatsapp_id=user_identifier,
            defaults={'nome': push_name if channel == 'whatsapp' else '', 'organizacao_id': 1, 'contexto': {}}
        )
        return user

    @database_sync_to_async
    def save_user(self, user: Usuario):
        user.save()

    def _reset_all_flow_flags(self, context: dict) -> dict:
        keys_to_remove = [key for key in context if key.startswith('awaiting_')]
        for key in keys_to_remove:
            context.pop(key, None)
        return context

    async def _format_weather_response(self, cidade: str) -> str:
        cidade_limpa = await self._parse_city_from_input(cidade)
        clima_atual = await self.get_weather_data(cidade_limpa)

        if "error" in clima_atual or clima_atual.get("cod") != 200:
            prompt_template = await self._get_prompt('weather_city_not_found')
            return prompt_template.format(cidade=cidade_limpa)
        
        prompt_template = await self._get_prompt('weather_dynamic_response')
        return prompt_template.format(
            cidade=clima_atual.get('name', cidade_limpa),
            descricao=clima_atual['weather'][0]['description'].capitalize(),
            temperatura=f"{clima_atual['main']['temp']:.1f}",
            sensacao=f"{clima_atual['main']['feels_like']:.1f}",
            umidade=clima_atual['main']['humidity']
        )

    async def process_message(self, user_identifier: str, message_text: str, push_name: str, channel: str, location_data: dict = None) -> str:
        await self._load_state_maps_if_needed()
        user = await self.get_or_create_user(user_identifier, push_name, channel)
        context = user.contexto or {}
        message_lower = message_text.lower().strip()
        response_text = ""

        # --- COMANDOS GLOBAIS (Prioridade Máxima) ---
        if message_lower in ['reiniciar', 'recomeçar', 'inicio']:
            user.nome, user.contexto = '', {}
            await self.save_user(user)
            return await self.process_message(user_identifier, "", push_name, channel)
        
        if message_lower == 'menu':
            user.contexto = self._reset_all_flow_flags(context)
            await self.save_user(user)
            return await self._get_prompt('main_menu_v2') if user.nome else await self.process_message(user_identifier, "", push_name, channel)

        # --- FLUXOS DE ESTADO (Verifica se o bot está esperando uma resposta) ---
        current_state = next((state for state in context if state.startswith('awaiting_')), None)

        if current_state == 'awaiting_location':
            thank_you_message = ""
            location_processed = False
            if channel == 'whatsapp' and location_data:
                details = await self.get_location_details_from_coords(location_data['latitude'], location_data['longitude'])
                if details:
                    user.cidade, user.estado = details.get('city'), details.get('state')
                    template = await self._get_prompt('location_received_whatsapp')
                    thank_you_message = template.format(user_nome=user.nome)
                    location_processed = True
            elif channel == 'webchat' and message_text:
                city_name = await self._parse_city_from_input(message_text)
                details = await self.get_location_details_from_city(city_name)
                if details:
                    user.cidade, user.estado = details.get('city'), details.get('state')
                    template = await self._get_prompt('location_received_web')
                    thank_you_message = template.format(cidade=user.cidade, user_nome=user.nome)
                    location_processed = True
                else:
                    template = await self._get_prompt('location_not_found_web')
                    response_text = template.format(cidade=city_name)
            
            if location_processed:
                user.contexto = self._reset_all_flow_flags(context)
                await self.save_user(user)
                main_menu_text = await self._get_prompt('main_menu_v2')
                if channel == 'whatsapp':
                    await self.send_whatsapp_message(user_identifier, thank_you_message)
                    response_text = main_menu_text
                else:
                    response_text = f"{thank_you_message}\n\n{main_menu_text}"
            elif not response_text:
                response_text = await self._get_prompt('location_error')

        elif current_state == 'awaiting_weather_location_choice':
            user.contexto = self._reset_all_flow_flags(context)
            if any(s in message_lower for s in ["1", "minha", "atual"]):
                if user.cidade:
                    response_text = await self._format_weather_response(user.cidade)
                    user.contexto['awaiting_weather_followup'] = True
                else:
                    user.contexto['awaiting_location'] = True
                    response_text = await self._get_prompt('weather_location_not_found')
            elif any(s in message_lower for s in ["2", "outra"]):
                user.contexto['awaiting_weather_location'] = True
                response_text = await self._get_prompt('weather_ask_another_city')
            else:
                response_text = await self._get_prompt('weather_choice_invalid')
            await self.save_user(user)

        elif current_state == 'awaiting_weather_location':
            cidade = message_text.strip()
            formatted_response = await self._format_weather_response(cidade)
            if "Ops! 😔" not in formatted_response:
                user.contexto = self._reset_all_flow_flags(context)
                user.contexto['awaiting_weather_followup'] = True
                await self.save_user(user)
            response_text = formatted_response
        
        elif current_state == 'awaiting_weather_followup':
            user.contexto = self._reset_all_flow_flags(context)
            if any(s in message_lower for s in ["sim", "outra", "cidade"]):
                user.contexto['awaiting_weather_location'] = True
                response_text = await self._get_prompt('weather_ask_another_city')
            else:
                response_text = await self._get_prompt('main_menu_v2')
            await self.save_user(user)

        # --- FLUXO DE ONBOARDING (se não estiver em nenhum estado) ---
        elif not user.nome:
            if not context.get('awaiting_initial_name'):
                user.contexto = {'awaiting_initial_name': True}
                await self.save_user(user)
                response_text = await self._get_prompt('welcome_ask_name')
            else: # Está aguardando o nome
                user.nome = message_text.strip().title()
                user.contexto = {'awaiting_location': True}
                await self.save_user(user)
                prompt_key = 'welcome_ask_location_whatsapp' if channel == 'whatsapp' else 'welcome_ask_location_web'
                prompt_template = await self._get_prompt(prompt_key)
                response_text = prompt_template.format(user_nome=user.nome)
        
        # --- ROTEAMENTO DO MENU PRINCIPAL (se nenhum outro fluxo foi ativado) ---
        else:
            if any(s in message_lower for s in ["[1]", "1", "clima"]):
                user.contexto = {'awaiting_weather_location_choice': True}
                await self.save_user(user)
                response_text = await self._get_prompt('weather_submenu_choice')
            elif any(s in message_lower for s in ["[2]", "2", "plantio"]):
                response_text = await self._get_prompt('feature_planting_wip')
            elif any(s in message_lower for s in ["[3]", "3", "preços"]):
                response_text = await self._get_prompt('feature_prices_wip')
            elif any(s in message_lower for s in ["[4]", "4", "relatórios"]):
                response_text = await self._get_prompt('feature_reports_wip')
            elif any(s in message_lower for s in ["[5]", "5", "safra"]):
                response_text = await self._get_prompt('feature_harvest_wip')
            else:
                fallback_template = await self._get_prompt('default_fallback')
                menu_text = await self._get_prompt('main_menu_v2')
                response_text = f"{fallback_template.format(user_nome=user.nome.split(' ')[0])}\n\n{menu_text}"
        
        return response_text