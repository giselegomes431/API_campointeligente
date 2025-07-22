import httpx
import openai
import re
from datetime import datetime, timezone

from django.conf import settings
from .models import Usuario
from channels.db import database_sync_to_async

# --- CONSTANTES DO FLUXO DE CONVERSA ---
# É crucial que você copie e cole o conteúdo completo das suas listas originais aqui.
REGISTRATION_QUESTIONS = {
    "nome_completo": "Qual é o seu nome completo? 👤",
    "cpf": "Qual é o seu CPF? (apenas números, por favor) 🔢",
    "rg": "Qual é o seu RG? (apenas números, se possível) 🆔",
    "data_nascimento": "Qual a sua data de nascimento? (dd/mm/aaaa) 🎂",
    "sexo": "Qual o seu sexo? (Masculino ♂️, Feminino ♀️ ou Outro) ⚧️",
    "estado_civil": "Qual o seu estado civil? Escolha uma opção:\n1. Casado 💍\n2. Solteiro 🧍\n3. Viúvo 💔\n4. Divorciado 💔",
    "telefone_contato": "Qual o seu telefone para contato? (Ex: 11987654321) 📱",
    "email": "Você deseja adicionar um endereço de e-mail? 📧\n1. Sim\n2. Não",
    "endereco_tipo": "O seu endereço é rural ou urbano? 🏡🏙️\n1. Rural\n2. Urbano",
    "nome_propriedade": "Qual o nome da propriedade (se houver)? 🚜",
    "comunidade_bairro": "Qual a comunidade ou bairro? 🏘️",
    "municipio": "Qual o município? 📍",
    "estado_propriedade": "Qual o estado? (ex: BA, SP...) 🇧🇷",
    "cep": "Qual o CEP? ✉️",
    "ponto_referencia": "Você deseja adicionar um ponto de referência? 🗺️\n1. Sim\n2. Não",
    "dap_caf": "Possui DAP ou CAF? Se sim, informe o número. 📄",
    "tipo_producao": "A sua produção é de que tipo? 🧑‍🌾🏢\n1. Familiar\n2. Empresarial",
    "producao_organica": "A sua produção é orgânica? (Sim ou Não) ✅❌",
    "utiliza_irrigacao": "Utiliza irrigação? (Sim ou Não) 💧",
    "area_total_propriedade": "Qual a área total da propriedade (em hectares)? 📏",
    "area_cultivada": "Qual a área cultivada (em hectares)? 🌱",
    "culturas_produzidas": "Quais culturas você produz? (ex: milho, feijão...) 🌽🥔"
}
REGISTRATION_ORDER = [
    "nome_completo", "cpf", "rg", "data_nascimento", "sexo", "estado_civil", "telefone_contato", "email",
    "endereco_tipo", "nome_propriedade", "comunidade_bairro", "municipio", "estado_propriedade", "cep", "ponto_referencia",
    "dap_caf", "tipo_producao", "producao_organica", "utiliza_irrigacao", "area_total_propriedade", "area_cultivada", "culturas_produzidas"
]
MANDATORY_REGISTRATION_FIELDS = [
    "nome_completo", "cpf", "rg", "data_nascimento", "sexo", "estado_civil", "telefone_contato",
    "endereco_tipo", "nome_propriedade", "comunidade_bairro", "municipio", "estado_propriedade", "cep",
    "dap_caf", "tipo_producao", "producao_organica", "utiliza_irrigacao", "area_total_propriedade", "area_cultivada", "culturas_produzidas"
]


class ChatbotService:
    """
    Este serviço encapsula toda a lógica de negócio do chatbot,
    traduzida do seu ficheiro chatbot.py original para a arquitetura Django.
    """

    def __init__(self):
        if settings.OPENAI_API_KEY:
            self.openai_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        else:
            self.openai_client = None

    # --- MÉTODOS DE SERVIÇOS EXTERNOS ---

    async def send_whatsapp_message(self, phone_number: str, text: str):
        url = f"{settings.EVOLUTION_API_URL}/message/sendText/{settings.EVOLUTION_INSTANCE_NAME}"
        headers = {"apikey": settings.EVOLUTION_API_KEY}
        payload = {"number": phone_number, "textMessage": {"text": text}}
        async with httpx.AsyncClient() as client:
            try:
                await client.post(url, json=payload, headers=headers, timeout=10)
                print(f"INFO: Mensagem enviada para {phone_number}: '{text[:50]}...'")
            except Exception as e:
                print(f"ERRO DE API: Falha ao enviar mensagem. Erro: {e}")

    async def get_weather_data(self, city: str, country: str = "BR") -> dict:
        url = "http://api.openweathermap.org/data/2.5/weather"
        params = {"q": f"{city},{country}", "appid": settings.OPENWEATHER_API_KEY, "units": "metric", "lang": "pt_br"}
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError:
                return {"error": f"Cidade '{city}' não encontrada."}

    async def get_openai_response(self, prompt: str) -> str:
        if not self.openai_client:
            return "Desculpe, o serviço de IA não está configurado."
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"ERRO OPENAI: {e}")
            return "Ops! 🤖 Os meus circuitos estão um pouco sobrecarregados agora. Tente novamente."

    # --- MÉTODOS DE ACESSO À BASE DE DADOS (Assíncronos) ---

    @database_sync_to_async
    def get_or_create_user(self, user_identifier: str, push_name: str, channel: str) -> Usuario:
        """
        Obtém ou cria um usuário com base no identificador (whatsapp_id ou session_id).
        O 'channel' é usado para diferenciar a busca/criação.
        """
        if channel == 'whatsapp':
            user, created = Usuario.objects.get_or_create(
                whatsapp_id=user_identifier,
                defaults={'nome': push_name, 'organizacao_id': 1, 'contexto': {}}
            )
        elif channel == 'webchat':
            user, created = Usuario.objects.get_or_create(
                whatsapp_id=user_identifier, # user_identifier já virá como 'webchat_UUID'
                # Para webchat, comece com nome vazio para ativar a coleta na primeira interação
                defaults={'nome': '', 'organizacao_id': 1, 'contexto': {}} # <-- ALTERADO AQUI
            )
        else:
            raise ValueError("Canal de comunicação inválido.")

        if created:
            print(f"INFO: Novo utilizador criado via {channel}: {user_identifier}")
        return user

    @database_sync_to_async
    def save_user(self, user: Usuario):
        user.ultima_atividade = datetime.now(timezone.utc)
        user.save()

    # --- MÉTODOS DE LÓGICA E FORMATAÇÃO ---

    def _is_user_registered(self, user: Usuario) -> bool:
        context = user.contexto or {}
        for field in MANDATORY_REGISTRATION_FIELDS:
            if not context.get(field):
                return False
        return True

    def _get_main_menu(self, user: Usuario) -> str:
        cadastro_opcao_texto = "Atualizar o meu registo 📝" if self._is_user_registered(user) else "Fazer o meu registo 📝"
        return (
            f"Como posso ajudar agora, {user.nome}?\n\n"
            "1. Ver a Previsão do Tempo ☁️\n"
            "2. Bater um papo com a Iagro 🤖\n"
            "3. Gerir o meu Estoque 📦\n"
            "4. Cuidar do meu Rebanho 🐄\n"
            "5. Fazer Simulação de Safra 🌾\n"
            f"6. {cadastro_opcao_texto}\n"
            "7. Alertas de Pragas e Doenças 🐛\n"
            "8. Análise de Mercado 📈\n"
            "9. Saber a minha Localização 📍\n"
            "10. Outras Informações 💡"
        )

    async def _format_weather_response(self, cidade: str) -> str:
        clima_atual = await self.get_weather_data(cidade)
        if "error" in clima_atual:
            return f"Ops! 😔 Não consegui a previsão para {cidade}. Por favor, verifique o nome da cidade e tente novamente."
        
        desc = clima_atual['weather'][0]['description']
        temp = clima_atual['main']['temp']
        sensacao = clima_atual['main']['feels_like']
        humidade = clima_atual['main']['humidity']
        
        return (
            f"Previsão para {cidade.title()}:\n"
            f"🌡️ {desc.capitalize()}, {temp:.1f}°C (Sensação: {sensacao:.1f}°C)\n"
            f"💧 Humidade: {humidade}%\n\n"
            "Quer outra consulta ou voltar ao menu?"
        )

    def _reset_all_flow_flags(self, context: dict) -> dict:
        """Limpa todas as flags de estado para reiniciar o fluxo."""
        flags_to_reset = [key for key in context if key.startswith('awaiting_') or key.endswith('_active')]
        for flag in flags_to_reset:
            context[flag] = False
        context.pop("registration_step", None)
        return context

    # --- CÉREBRO PRINCIPAL DA CONVERSA ---

    async def process_message(self, user_identifier: str, message_text: str, push_name: str, channel: str) -> str:
        """
        Processa uma mensagem do utilizador, independentemente do canal.
        `user_identifier` pode ser whatsapp_id ou session_id.
        `channel` indica se é 'whatsapp' ou 'webchat'.
        """
        user = await self.get_or_create_user(user_identifier, push_name, channel)
        context = user.contexto or {}
        
        # --- LÓGICA DE PRIMEIRO CONTATO PARA COLETAR O NOME ---
        # Prioridade 1: Se o usuário não tem nome E não estamos já esperando o nome dele, pedir.
        if not user.nome and not context.get('awaiting_initial_name'):
            context['awaiting_initial_name'] = True
            user.contexto = context
            await self.save_user(user)
            return "Olá! Eu sou a Iagro, a sua assistente virtual para o campo. Para começarmos, como posso chamá-lo? 😊"

        # Prioridade 2: Se estamos esperando o nome do usuário, salvar o que ele enviou.
        if context.get('awaiting_initial_name'):
            user.nome = message_text.strip().title() # Salva o nome
            context = self._reset_all_flow_flags(context) # Limpa flags de outros fluxos
            context['awaiting_initial_name'] = False # Desativa a flag de espera do nome
            user.contexto = context
            await self.save_user(user)
            return f"Prazer em conhecê-lo, {user.nome}! 👋\n\n{self._get_main_menu(user)}"

        # --- FIM DA LÓGICA DE PRIMEIRO CONTATO ---

        # Esta linha deve vir DEPOIS da lógica de primeiro contato,
        # pois ela processa a mensagem para outros fluxos.
        message_lower = message_text.lower().strip()

        # --- INÍCIO DA MÁQUINA DE ESTADOS (fluxos de conversa normais) ---

        if context.get("conversational_mode_active"):
            if "menu" in message_lower or "voltar" in message_lower:
                context = self._reset_all_flow_flags(context)
                user.contexto = context
                await self.save_user(user)
                return f"Ok, {user.nome}! A sair do modo de conversa.\n\n{self._get_main_menu(user)}"
            
            prompt = f"Você é a Iagro... (seu prompt completo aqui)... Pergunta do utilizador: '{message_text}'"
            return await self.get_openai_response(prompt)

        if context.get("awaiting_weather_location"):
            cidade = message_text.strip().title()
            context = self._reset_all_flow_flags(context)
            context["awaiting_weather_follow_up_choice"] = True
            user.contexto = context
            await self.save_user(user)
            return await self._format_weather_response(cidade)
        
        if context.get("awaiting_weather_follow_up_choice"):
            context = self._reset_all_flow_flags(context)
            if "outra" in message_lower or "sim" in message_lower:
                context["awaiting_weather_location"] = True
            user.contexto = context
            await self.save_user(user)
            return "Para que outra cidade gostaria da previsão?" if context.get("awaiting_weather_location") else self._get_main_menu(user)

        # --- LÓGICA DO MENU PRINCIPAL ---

        if "1" in message_lower or "clima" in message_lower:
            context = self._reset_all_flow_flags(context)
            context["awaiting_weather_location"] = True
            user.contexto = context
            await self.save_user(user)
            return f"Para que cidade gostaria da previsão, {user.nome}? 📍"

        if "2" in message_lower or "papo" in message_lower:
            context = self._reset_all_flow_flags(context)
            context["conversational_mode_active"] = True
            user.contexto = context
            await self.save_user(user)
            return (f"Que bom conversar consigo, {user.nome}! 😊\n"
                            "Pode perguntar-me qualquer coisa sobre a sua lavoura ou rebanho. "
                            "Para voltar, basta digitar 'menu'.")
        
        # Resposta padrão
        user.contexto = context
        await self.save_user(user)
        return f"Desculpe, {user.nome}, não entendi. 🤔\n\n{self._get_main_menu(user)}"