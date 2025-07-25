# panel/serializers.py

from rest_framework import serializers
from django.contrib.auth.models import User
from chatbot.models import Organizacao, Administrador # Importe os modelos da app chatbot

# --- Serializer para Organizações ---

class OrganizacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organizacao
        fields = ['id', 'nome', 'cnpj', 'data_criacao']
        read_only_fields = ['id', 'data_criacao'] # Estes campos são gerados automaticamente

    def validate_cnpj(self, value):
        """
        Validação customizada para garantir que o CNPJ seja único.
        """
        if Organizacao.objects.filter(cnpj=value).exists():
            raise serializers.ValidationError("Uma organização com este CNPJ já existe.")
        return value

# --- Serializer para criar Administradores ---

class AdministradorCreateSerializer(serializers.Serializer):
    """
    Serializer para criar um novo Administrador e o seu User associado.
    Este não é um ModelSerializer porque ele cria dois objetos diferentes (User e Administrador).
    """
    # Dados para o modelo User do Django
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    
    # Dados para o seu modelo Administrador
    nome = serializers.CharField(required=True, max_length=255)
    cargo = serializers.CharField(required=False, allow_blank=True, max_length=50)
    organizacao_id = serializers.IntegerField(required=True)

    def validate_email(self, value):
        """Verifica se o email já está em uso."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Um usuário com este email já existe.")
        return value

    def validate_organizacao_id(self, value):
        """Verifica se a organização informada existe."""
        if not Organizacao.objects.filter(pk=value).exists():
            raise serializers.ValidationError(f"A organização com ID {value} não foi encontrada.")
        return value

    def create(self, validated_data):
        """
        Lógica para criar o User e o Administrador.
        """
        # 1. Cria o User padrão do Django (isso hasheia a senha automaticamente)
        user = User.objects.create_user(
            username=validated_data['email'], # Usamos o email como username
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['nome'].split(' ')[0],
            is_staff=True # Marca o usuário como staff, permitindo acesso ao admin do Django
        )

        # 2. Cria o seu modelo Administrador, ligando-o ao User e à Organização
        administrador = Administrador.objects.create(
            user=user, # Assumindo que você adicionará o campo 'user' ao seu modelo Administrador
            organizacao_id=validated_data['organizacao_id'],
            nome=validated_data['nome'],
            email=validated_data['email'],
            cargo=validated_data.get('cargo', '')
        )
        
        return administrador

class AdministradorReadOnlySerializer(serializers.ModelSerializer):
    """Serializer para exibir os dados de um administrador, sem a senha."""
    organizacao_nome = serializers.CharField(source='organizacao.nome', read_only=True)
    
    class Meta:
        model = Administrador
        fields = ['id', 'nome', 'email', 'cargo', 'organizacao_id', 'organizacao_nome']