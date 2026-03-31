# API Registro de Projetos

## Setup

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Variaveis de ambiente

Crie um arquivo `.env` com:

```env
DATABASE_URL=postgresql://...
SUPABASE_ISSUER=https://<project-ref>.supabase.co/auth/v1
SUPABASE_AUDIENCE=authenticated
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_ANON_KEY=<anon-key>
```

## Banco de dados

Execute o schema em [`infra/database/schema.sql`](/c:/Users/Joao.calheiros/Desktop/Resgistro%20de%20Atividades/RegistroProjetos/infra/database/schema.sql).

## Rodar API

```powershell
uvicorn api.main:app --reload
```

## Frontend

O frontend agora e servido pelo proprio FastAPI:

- Painel: `http://127.0.0.1:8000/app`
- Redirecionamento: `http://127.0.0.1:8000/ -> /app`
- Docs Swagger: `http://127.0.0.1:8000/docs`

No painel React:

1. Faça cadastro (`/register`) com usuario (email) e senha.
2. Faça login (`/login`) com o mesmo usuario e senha.
3. Acesse `/projects` para listar projetos do usuario autenticado.
4. Abra um projeto para ver detalhes, tarefas e criar novas tarefas.
5. Abra uma tarefa para iniciar, parar e encerrar.

## Testes

```powershell
python -m pytest tests/test_domain.py -v
python -m pytest tests/test_in_memory_repositories.py -v
python -m pytest tests/test_services.py -v
python -m pytest tests/test_api_projects.py -v
python -m pytest tests/test_api_tasks.py -v
python -m pytest -v
```
