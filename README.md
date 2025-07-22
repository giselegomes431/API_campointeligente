# API Campo Inteligente (Backend Django)

Este repositório contém o código-fonte da API backend para o projeto "Campo Inteligente", desenvolvida em Django com Django REST Framework. Esta API é responsável por gerenciar a lógica do chatbot, interação com serviços externos (OpenAI, OpenWeather, Evolution API para WhatsApp) e persistência de dados do usuário.

## Funcionalidades Principais

* **Integração com Chatbot:** Processa mensagens de entrada do webchat e de webhooks do WhatsApp.
* **Gerenciamento de Usuários:** Registra e atualiza informações de usuários agrícolas.
* **Comunicação com IA:** Utiliza a API do OpenAI para respostas inteligentes.
* **Previsão do Tempo:** Integração com OpenWeather para fornecer dados climáticos.
* **Comunicação WhatsApp:** Envio de mensagens via Evolution API.
* **Estrutura Extensível:** Projetado para adicionar futuras funcionalidades agrícolas (estoque, rebanho, simulação de safra, etc.).

## Tecnologias Utilizadas

* **Python 3.8+**
* **Django** (Framework web)
* **Django REST Framework (DRF)** (Para construção de APIs RESTful)
* **Uvicorn / ASGI** (Servidor assíncrono para Django Channels)
* **Django Channels** (Para comunicação assíncrona e WebSockets, fundamental para a Evolution API)
* **PostgreSQL** (Banco de Dados - configurável)
* **`python-dotenv`** (Para carregar variáveis de ambiente de arquivos `.env`)
* **`httpx`** (Cliente HTTP assíncrono para requisições externas)
* **`openai`** (SDK para a API OpenAI)
* **`asgiref`** (Utilitários ASGI para o Django)
* **`drf-yasg`** (Se estiver usando para geração de documentação Swagger/OpenAPI)
* **`psycopg2-binary`** (Adaptador PostgreSQL para Python)
* **`djangorestframework-simplejwt`** (Se estiver usando autenticação JWT)

## Como Rodar o Projeto Localmente

Siga os passos abaixo para configurar e rodar o backend da API em seu ambiente de desenvolvimento.

### Pré-requisitos

* Python 3.8 ou superior
* pip (gerenciador de pacotes Python)
* PostgreSQL (servidor de banco de dados rodando localmente ou acessível remotamente)
* Git

### 1. Clonar o Repositório

Primeiro, clone este repositório para sua máquina local:

```bash
git clone [https://github.com/giselegomes431/API_campointeligente.git](https://github.com/giselegomes431/API_campointeligente.git)
cd API_campointeligente
2. Configurar o Ambiente Virtual
É altamente recomendado criar um ambiente virtual para isolar as dependências do projeto.

Bash

python -m venv venv
# No Windows:
.\venv\Scripts\activate
# No macOS/Linux:
source venv/bin/activate
3. Instalar Dependências
Com o ambiente virtual ativado, instale todas as bibliotecas Python necessárias listadas no requirements.txt:

Bash

pip install -r requirements.txt
4. Configurar Variáveis de Ambiente
Crie um arquivo chamado .env na raiz do diretório campointeligente (ou seja, na mesma pasta onde está o manage.py e a pasta campointeligente interna). Este arquivo NÃO deve ser adicionado ao controle de versão do Git.

Preencha o arquivo .env com suas credenciais e configurações. Abaixo está um exemplo do que você deve incluir, substituindo os valores pelos seus:

Ini, TOML

# campointeligente/.env
# Chave secreta do Django (gerada automaticamente ao criar um projeto Django)
SECRET_KEY='sua_chave_secreta_aqui'

# Modo Debug (True para desenvolvimento, False para produção)
DEBUG=True

# --- Banco de Dados PostgreSQL ---
DB_NAME='campo_inteligente'
DB_USER='postgres'
DB_PASSWORD='senha123'
DB_HOST='localhost'
DB_PORT='5432'

# --- Chaves de API e Configurações de Serviços Externos ---
OPENAI_API_KEY='sua_chave_openai_aqui'
OPENWEATHER_API_KEY='sua_chave_openweather_aqui'
EVOLUTION_API_KEY='sua_chave_evolution_aqui'
EVOLUTION_API_URL='http://endereco_da_sua_evolution_api:porta' # Ex: http://localhost:8080
EVOLUTION_INSTANCE_NAME='nome_da_sua_instancia'
Importante: Substitua os valores de exemplo pelas suas chaves de API e configurações de banco de dados reais.

5. Configurar o Banco de Dados
Certifique-se de que um servidor PostgreSQL esteja rodando e que o banco de dados campo_inteligente (ou o nome que você definiu em DB_NAME no .env) exista e seja acessível pelo usuário e senha configurados.

Após configurar o .env, aplique as migrações do banco de dados para criar as tabelas necessárias:

Bash

python manage.py makemigrations chatbot
python manage.py migrate
6. Rodar o Servidor
Para iniciar o servidor Django utilizando Uvicorn (que fornece suporte a ASGI para Django Channels), execute o seguinte comando na raiz do projeto (API_campointeligente/):

Bash

uvicorn campointeligente.asgi:application --reload
O servidor estará disponível em http://127.0.0.1:8000/.

Endpoints da API
Webhook para WhatsApp (Evolution API): POST /api/v1/chatbot/webhook/

Endpoint para Webchat: POST /api/v1/chatbot/webchat/

Se você tiver a biblioteca drf-yasg configurada no seu projeto Django para gerar documentação, você poderá acessá-la em:

Swagger UI: http://127.0.0.1:8000/api/v1/swagger/

Redoc: http://127.0.0.1:8000/api/v1/redoc/

Contato
Para dúvidas, sugestões ou colaborações, entre em contato com [Seu Nome/Email ou link para contato, ex: giselegomes431@email.com].

Licença
Este projeto está licenciado sob a Licença MIT. Veja o arquivo LICENSE para mais detalhes.
