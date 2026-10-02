# LGPD Fácil

Compliance LGPD para PME — scanner de site, classificação determinística de
dado pessoal, relatório e políticas de privacidade geradas por IA.

Arquitetura e decisões técnicas: `docs/adr/`. Roadmap de produto e stack:
`ROTEIR~1.MD` / `STACK_~1.MD` / `PLANO_~1.MD`.

## Estrutura

```
backend/   FastAPI + SQLAlchemy + Alembic — API, scanner, classificador, IA
frontend/  React + Vite + TypeScript — consome a API
docs/adr/  Architecture Decision Records
```

## Rodando o backend localmente

```bash
cd backend
python -m venv venv
venv/Scripts/activate        # Windows; source venv/bin/activate no Linux/Mac
pip install -r requirements.txt

cp .env.example .env         # preencha DATABASE_URL, SUPABASE_*, GEMINI_API_KEY
playwright install chromium  # fallback do scanner para sites com JS pesado
alembic upgrade head
uvicorn app.main:app --reload
```

API em `http://localhost:8000`, docs interativas em `http://localhost:8000/docs`.

### Fila de scans (opcional)

Sem `REDIS_URL` no `.env`, `POST /scans` roda via `BackgroundTasks` do FastAPI
— funciona, mas o scan se perde se a API reiniciar no meio. Com Redis
configurado, os scans vão para uma fila real (RQ) e um worker separado os
processa:

```bash
docker run -d --name lgpd-redis -p 6379:6379 redis:7-alpine
# no .env: REDIS_URL=redis://localhost:6379/0

# num segundo terminal, com o venv ativado:
python -m app.worker
```

### Testes do backend

Testes que não tocam o banco rodam sempre. Os que tocam banco (auth,
onboarding, companies) exigem um Postgres descartável — nunca aponte
`TEST_DATABASE_URL` para o banco do projeto:

```bash
docker run -d --name lgpd-test-db \
  -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=lgpd_test \
  -p 5433:5432 postgres:16

# no .env: TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5433/lgpd_test
pytest
```

`ruff check .` e `pyright app` rodam no CI a cada PR que toca `backend/`.

## Rodando o frontend localmente

```bash
cd frontend
npm install
cp .env.example .env.local   # preencha VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY
npm run dev
```

Frontend em `http://localhost:5173`, esperando a API em `http://localhost:8000`
(configurável via `VITE_API_BASE_URL`).

### Testes do frontend

```bash
npm run lint
npm run format:check
npx tsc -b
npm run test
npm run build
```

Tudo isso roda no CI a cada PR que toca `frontend/`.

## Variáveis de ambiente

Ver `backend/.env.example` e `frontend/.env.example` para a lista completa e
onde obter cada valor (Supabase, Google AI Studio).

## Estado atual

Sprints 0–5 do `PLANO_~1.MD` implementados: autenticação (Supabase Auth +
JWKS), scanner v1, classificação determinística de dado pessoal, relatório
executivo e políticas geradas por IA (Gemini, com camada de abstração para
trocar por Anthropic depois), frontend completo consumindo a API.

Pendente: fila assíncrona real (hoje `BackgroundTasks` do FastAPI faz esse
papel), cobrança via Stripe, testes end-to-end com Playwright, deploy.
