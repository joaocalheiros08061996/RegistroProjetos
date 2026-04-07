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

## Docker (FastAPI)

### Build da imagem

```bash
docker build -t registro-projetos:latest .
```

### Rodar local com Docker

```bash
docker run --rm -p 8000:8000 --env-file .env registro-projetos:latest
```

Endpoints:

- App: `http://127.0.0.1:8000/app`
- Docs: `http://127.0.0.1:8000/docs`

## Subir para o GitHub

```bash
git add Dockerfile .dockerignore README.md
git commit -m "chore: add docker setup for fastapi and render deploy flow"
git push origin main
```

> Se sua branch principal for `master`, troque `main` por `master`.

## Deploy no Render com Dockerfile

1. Acesse o painel da Render: https://dashboard.render.com/
2. Clique em `New +` > `Web Service`.
3. Conecte o repositório `RegistroProjetos`.
4. Em `Environment`, escolha `Docker`.
5. A Render detecta e usa o `Dockerfile` na raiz automaticamente.
6. Defina as variáveis de ambiente:
   - `DATABASE_URL`
   - `SUPABASE_ISSUER`
   - `SUPABASE_AUDIENCE`
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
7. Crie o serviço e aguarde o deploy.

Porta:

- A aplicação já escuta em `8000` dentro do container.
