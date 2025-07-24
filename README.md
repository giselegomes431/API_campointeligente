# 🌾 API Campo Inteligente (Backend Django)

Este repositório contém o backend do projeto **Campo Inteligente**, desenvolvido em **Django** com **Django REST Framework**. A API é responsável por processar mensagens do chatbot, integrar serviços externos (OpenAI, OpenWeather, Evolution API para WhatsApp) e gerenciar os dados dos usuários agrícolas.

---

## 🚀 Funcionalidades Principais

- ✅ Integração com chatbot (webchat e WhatsApp via Evolution API)
- ✅ Registro e atualização de usuários
- ✅ Respostas inteligentes com a API da OpenAI
- ✅ Previsão do tempo com dados do OpenWeather
- ✅ Comunicação automatizada via WhatsApp
- ✅ Estrutura extensível para novas funções (ex: controle de rebanho, estoque agrícola, simulações)

---

## 🛠 Tecnologias Utilizadas

- **Python 3.8+**
- **Django** + **Django REST Framework**
- **Django Channels** + **ASGI** (suporte a WebSockets)
- **PostgreSQL**
- **Uvicorn** + **Daphne** (servidores assíncronos)
- **httpx** (requisições HTTP assíncronas)
- **python-dotenv** (variáveis de ambiente)
- **openai** (integração com GPT)
- **drf-yasg** (documentação Swagger/OpenAPI)
- **django-cors-headers** (suporte a CORS)
- **psycopg2-binary** (conector PostgreSQL)
- *(opcional)* **djangorestframework-simplejwt** (autenticação JWT)

---

## ⚙️ Como Rodar Localmente

### 📋 Pré-requisitos

- Python 3.8+
- pip
- PostgreSQL
- Git

### 1. Clone o Repositório

```bash
git clone https://github.com/giselegomes431/API_campointeligente.git
cd API_campointeligente
```

### 2. Crie um Ambiente Virtual

```bash
python -m venv venv

# Windows:
.
venv\Scripts\activate

# macOS/Linux:
source venv/bin/activate
```

### 3. Instale as Dependências

```bash
pip install -r requirements.txt
```

---

## 📦 Exemplo de `requirements.txt`

```txt
Django>=3.2
djangorestframework
django-cors-headers
django-channels
uvicorn
daphne
httpx
python-dotenv
openai
asgiref
drf-yasg
psycopg2-binary
djangorestframework-simplejwt
```

---

### 4. Configure o `.env`

Crie um arquivo `.env` na mesma pasta onde está o `manage.py` com o seguinte conteúdo:

```ini
SECRET_KEY='sua_chave_secreta_aqui'
DEBUG=True

DB_NAME='campo_inteligente'
DB_USER='postgres'
DB_PASSWORD='sua_senha'
DB_HOST='localhost'
DB_PORT='5432'

OPENAI_API_KEY='sua_chave_openai'
OPENWEATHER_API_KEY='sua_chave_openweather'
EVOLUTION_API_KEY='sua_chave_evolution'
EVOLUTION_API_URL='http://localhost:8080'
EVOLUTION_INSTANCE_NAME='nome_da_instancia'
```

> ⚠️ **Importante:** não suba esse arquivo para o GitHub. Adicione `.env` ao seu `.gitignore`.

---

### 5. Configure o Banco de Dados

Certifique-se de que o banco está criado e acessível:

```bash
python manage.py makemigrations chatbot
python manage.py migrate
```

---

### 6. Coleta de Arquivos Estáticos

```bash
python manage.py collectstatic
```

---

### 7. Rode o Servidor (ASGI/Uvicorn)

```bash
uvicorn campointeligente.asgi:application --reload
```

Acesse: [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## 📨 Endpoints e Documentação

| Recurso                      | Endpoint                                   |
|-----------------------------|--------------------------------------------|
| Webhook WhatsApp (POST)     | `/api/v1/chatbot/webhook/`                |
| Webchat (POST)              | `/api/v1/chatbot/webchat/`                |
| Swagger (UI interativa)     | `/api/v1/swagger/`                         |
| Redoc (Documentação limpa)  | `/api/v1/redoc/`                           |

---

## 🧪 Estrutura do Projeto

```
API_campointeligente/
│
├── campointeligente/           # Configurações principais (settings.py, asgi.py, etc.)
│
├── chatbot/                    # App do chatbot (views, models, urls, etc.)
│
├── staticfiles/                # Arquivos estáticos coletados
│
├── manage.py                   # Entrada do projeto
│
├── .env                        # Configurações sensíveis (NÃO versionar)
│
└── requirements.txt            # Dependências do projeto
```

---

## 👤 Contato

Desenvolvido por **Gisele Gomes**

- 📧 belagisa14@gmail.com  
- 💼 [LinkedIn](https://www.linkedin.com/in/gisele-gomes-oliveira-037bb1128)  
- 📸 [Instagram](https://www.instagram.com/belagisa13)  
- 🐙 [GitHub](https://github.com/giselegomes431)

---

## 📄 Licença

Este projeto está licenciado sob a **Licença MIT**.  
Veja o arquivo [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/giselegomes431/API_campointeligente/blob/main/LICENSE)
 para mais detalhes.
