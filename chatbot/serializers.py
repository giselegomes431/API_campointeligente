# chatbot/serializers.py

from rest_framework import serializers

class WebchatPayloadSerializer(serializers.Serializer):
    """
    Serializer para o payload de mensagens recebidas do cliente web (frontend).
    Define os campos esperados e suas propriedades para validação e documentação.
    """
    session_id = serializers.CharField(
        max_length=255, 
        required=True, 
        help_text="ID da sessão única do usuário no webchat."
    )
    message = serializers.CharField(
        max_length=1000, 
        required=True, 
        help_text="Conteúdo da mensagem de texto enviada pelo usuário."
    )

class WebhookPayloadSerializer(serializers.Serializer):
    """
    Serializer para o payload de webhooks recebidos da Evolution API (WhatsApp).
    Baseado na estrutura de webhook de mensagens de texto recebidas.
    """
    # A estrutura exata pode variar dependendo da configuração do seu webhook na Evolution API.
    # Esta é uma estrutura comum para mensagens de texto:
    
    event = serializers.CharField(
        required=True,
        help_text="Tipo do evento do webhook (ex: 'message.create')."
    )
    instance = serializers.JSONField(
        required=True,
        help_text="Dados da instância da Evolution API."
    )
    data = serializers.JSONField(
        required=True,
        help_text="Dados principais do evento, contendo a mensagem."
    )
    
    # Campo aninhado para 'data.key' (informações de identificação da mensagem)
    # Exemplo: data.key.remoteJid (o número do WhatsApp do remetente)
    # A validação de JSONField é mais flexível, mas você pode aninhar outros serializers se quiser mais granularidade.
    
    def validate(self, attrs):
        """
        Validação personalizada para garantir que o webhook é um evento de mensagem de texto.
        Você pode adicionar mais validações aqui se necessário.
        """
        event_type = attrs.get('event')
        data_payload = attrs.get('data')

        if event_type != 'message.create':
            raise serializers.ValidationError({"event": "Apenas eventos 'message.create' são suportados neste webhook."})
        
        if not data_payload or not data_payload.get('message'):
            raise serializers.ValidationError({"data": "Payload de dados ou mensagem ausente no webhook."})
            
        # Você pode querer verificar o tipo de mensagem aqui (textMessage, imageMessage, etc.)
        # Ex: if 'textMessage' not in data_payload.get('message', {}):
        #        raise serializers.ValidationError({"message": "Apenas mensagens de texto são suportadas."})

        return attrs

# Serializer para a resposta de sucesso da API (se necessário para documentação)
class ChatbotResponseSerializer(serializers.Serializer):
    """
    Serializer para a estrutura de resposta padrão do chatbot.
    """
    response = serializers.CharField(help_text="A resposta gerada pelo chatbot.")
    session_id = serializers.CharField(
        max_length=255, 
        help_text="O ID da sessão do usuário, retornado para persistência no frontend."
    )