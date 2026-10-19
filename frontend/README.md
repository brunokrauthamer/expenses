# Expenses

Aplicação pessoal para registrar compras, consultar as compras recentes e acompanhar cobranças mês a mês. A interface usa React, navegação compartilhada com History API, cache de requisições reutilizado entre as rotas e gráficos SVG responsivos. Os dados de despesas são gravados na API e persistem no banco configurado pelo backend.

## Requisitos

- Node.js 20.19+ ou 22.12+
- pnpm
- Backend e PostgreSQL configurados conforme `../backend/README.md`

## Executar localmente

1. Instale as dependências: `pnpm install`.
2. No primeiro uso, cadastre as referências padrão no backend a partir de `backend`: `.venv\Scripts\python.exe -m app.seed`.
3. Ainda em `backend`, inicie a API: `.venv\Scripts\python.exe -m uvicorn app.main:app --reload`.
4. Em `frontend`, inicie o Vite: `pnpm dev`.
5. Abra o endereço informado pelo Vite, normalmente `http://localhost:5173`.

O Vite encaminha `/api` para `http://127.0.0.1:8000`. Se o backend estiver em outro endereço durante o desenvolvimento, defina `VITE_API_BASE_URL`. Em produção, disponibilize a API pela mesma origem em `/api` ou configure essa variável na compilação.

As rotas da interface são `/despesas` e `/consolidado`. Filtros do consolidado ficam na URL e podem ser preservados ao recarregar a página. As referências e os resultados são mantidos em cache local por até 30 minutos e 2 minutos, respectivamente.

Para gerar uma versão de produção, execute `pnpm build`. Os arquivos gerados ficam em `dist/`. A hospedagem deve redirecionar rotas da aplicação, como `/despesas` e `/consolidado`, para `index.html`.
