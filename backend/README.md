# Backend do Expenses

O backend usa FastAPI, SQLAlchemy, Alembic e PostgreSQL. A API oferece cadastro, edição, exclusão e consulta mensal de gastos, incluindo parcelamentos.

## Organização

O projeto é um monólito modular. Cada domínio fica em `app/modules/` e separa:

- `model.py`: representação das tabelas pelo SQLAlchemy;
- `schema.py`: contratos de entrada e saída da API;
- `service.py`: regras e consultas do domínio;
- `controller.py`: rotas HTTP do domínio.

Os módulos existentes incluem `auth`, `categories`, `expenses`, `income_entries` e `payment_methods`. Código compartilhado fica em `app/shared/`; conexão e configuração ficam na raiz de `app/`.

## Configuração

1. Crie um banco PostgreSQL.
2. Copie `.env.example` para `.env`, ajuste `DATABASE_URL` e configure as chaves de autenticação descritas abaixo.
3. Crie e ative um ambiente virtual Python.
4. Instale as dependências: `pip install -r requirements.txt`.
5. Faça um backup do banco e aplique as migrações: `alembic upgrade head`.

As revisões até `20261022_0007` criam as tabelas financeiras e de autenticação. A revisão `20261024_0008` atribui os dados antigos a uma única conta, cria chaves compostas de propriedade e passa os três catálogos para cada usuário. Se houver dados antigos, ela exige exatamente um usuário e interrompe a transação quando a propriedade não for inequívoca ou houver nomes que colidam após normalização. Faça o backup, pare a aplicação durante a atualização e confirme os dados antes de reabrir o serviço.

Novas contas recebem seus catálogos padrão durante o cadastro ou o primeiro login Google. Para inicializar manualmente uma conta existente ainda sem catálogos, execute a partir de `backend`:

```powershell
python -m app.seed --user-id <UUID-DA-CONTA>
```

O seeder registra a inicialização uma única vez. Repeti-lo não restaura padrões que tenham sido renomeados ou excluídos.

## Autenticação e chaves

Todas as rotas de negócio exigem `Authorization: Bearer <access_token>`. A conta pode ser criada com e-mail e senha ou na primeira autenticação Google. Senhas têm no mínimo 12 caracteres e são armazenadas como hash Argon2id. Access tokens JWT RS256 duram 15 minutos. O refresh token rotativo é enviado somente em cookie `HttpOnly`, `SameSite=Lax`; em produção, defina `AUTH_COOKIE_SECURE=true` e use HTTPS. O cookie usa `AUTH_COOKIE_PATH=/api/auth`, que corresponde ao proxy `/api` do Vite. Ajuste o caminho se a API pública usar outro prefixo.

Gere valores diferentes para `AUTH_ENCRYPTION_KEY`, `AUTH_LOOKUP_KEY` e `AUTH_TOKEN_SECRET`, com o comando abaixo três vezes no PowerShell, e copie cada saída para o `.env`:

```powershell
[Convert]::ToBase64String([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
```

`AUTH_ENCRYPTION_KEY` cifra e-mails, nomes e identificadores Google com AES-256-GCM. `AUTH_LOOKUP_KEY` cria índices HMAC para busca/identificação e hash de refresh tokens. `AUTH_TOKEN_SECRET` assina o cookie temporário do fluxo OAuth. A chave de dados tem versão (`AUTH_ENCRYPTION_KEY_VERSION`); para iniciar uma rotação, configure `AUTH_ENCRYPTION_KEY_V2` com uma nova chave e altere a versão para `2`. Os dados existentes mantêm o prefixo da versão anterior e continuam legíveis enquanto a chave antiga estiver disponível. Guarde todas as chaves fora do banco e dos arquivos versionados; perder uma chave de criptografia torna os campos pessoais correspondentes irrecuperáveis.

Gere um par RSA para assinar JWTs e codifique os arquivos PEM em Base64:

```powershell
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:3072 -out jwt-private.pem
openssl pkey -in jwt-private.pem -pubout -out jwt-public.pem
[Convert]::ToBase64String([IO.File]::ReadAllBytes('jwt-private.pem'))
[Convert]::ToBase64String([IO.File]::ReadAllBytes('jwt-public.pem'))
```

Copie as duas saídas para `AUTH_JWT_PRIVATE_KEY_B64` e `AUTH_JWT_PUBLIC_KEY_B64`. A chave privada deve ficar somente no backend. Não a coloque em `VITE_` nem no repositório.

O botão Google fica habilitado pela rota `/auth/google/start` quando `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` e `GOOGLE_REDIRECT_URI` estiverem configurados. No desenvolvimento com Vite, registre `http://localhost:5173/api/auth/google/callback` como URL de redirecionamento autorizada no Google Cloud Console. O fluxo usa Authorization Code com PKCE, `state` e `nonce`; o backend valida a assinatura e as claims do ID token. O botão abre uma janela auxiliar e, se o navegador bloqueá-la, a tela oferece continuar na mesma aba. O resultado é enviado à janela principal sem tokens; a sessão é recuperada pelo cookie de refresh `HttpOnly`.

No desenvolvimento local, `iniciar.ps1` desativa o access log do Uvicorn para não registrar o código OAuth e o `state` recebidos na URL de callback.

Se um e-mail Google corresponder a uma conta local existente, o vínculo automático só é permitido para Gmail ou para um domínio Workspace confirmado pelo Google. Para outros domínios, a pessoa pode continuar usando e-mail e senha; o vínculo da identidade Google exige suporte para evitar associação indevida.

Cada conta vê somente suas despesas, entradas e catálogos. Cadastros de referência podem ser renomeados ou excluídos logicamente; o histórico continua disponível pelo ID original.

## Importar gastos de planilhas

Depois de instalar as dependências e aplicar as migrações, deixe as planilhas mensais
na pasta Downloads e confira a prévia com:

    python -m app.import_expenses --user-id <UUID-DA-CONTA>

A prévia não altera o banco. Depois de conferir os itens, execute:

    python -m app.import_expenses --user-id <UUID-DA-CONTA> --apply

O importador também aceita caminhos de arquivos .xlsx após o comando. Cada linha de
origem é registrada para evitar a duplicação quando os mesmos arquivos são enviados
novamente. As compras iniciadas nos arquivos são salvas com os valores observados
nas primeiras parcelas; os outros meses são gerados a partir da primeira cobrança.

## Gastos e parcelamentos

`POST /expenses` e `PUT /expenses/{expense_id}` recebem os campos atuais `description`, `amount`, `expense_date`, `category_id` e `payment_method_id`, além de:

- `payment_type`: `one_time` (padrão) ou `installments`;
- `installment_count`: quantidade de parcelas, de 1 a 1200; parcelados precisam de pelo menos 2;
- `amount_type`: `total` (padrão) ou `installment`;
- `first_installment_date`: opcional; por padrão, usa `expense_date`.

`amount` representa o total quando `amount_type` é `total`, ou o valor de cada parcela quando é `installment`. O total da compra fica salvo em `expenses.amount`. Para um total parcelado, as parcelas após a primeira usam a divisão arredondada para baixo a duas casas; a primeira recebe o restante, para que a soma coincida com o total. Por exemplo, R$ 100,01 em 3 vezes resulta em R$ 33,35, R$ 33,33 e R$ 33,33. As datas seguintes mantêm o dia da primeira cobrança, usando o último dia do mês quando o dia original não existe.

`GET /expenses` lista cobranças programadas, não compras únicas. Com `month=AAAA-MM`, retorna somente cobranças daquele mês; `start_month` e `end_month` filtram um intervalo inclusivo de até 120 meses. O intervalo não pode ser enviado junto com `month`. Também aceita `category_id` e `payment_method_id`; esses parâmetros podem ser combinados com busca e período. `amount_due` é o valor da parcela daquela linha e `total_amount` é o total da compra. O campo `id` continua sendo o gasto, utilizado nas rotas PUT e DELETE; `installment_id` identifica a cobrança. `total` na paginação conta cobranças.

Para o frontend:

- `GET /categories`, `/income-categories` e `/payment-methods` retornam os cadastros ativos do usuário em ordem alfabética. `?include_deleted=true` inclui os excluídos para filtros e gestão histórica.
- `POST`, `PUT /{id}` e `DELETE /{id}` estão disponíveis nas três rotas de referência. O DELETE preenche `deleted_at` e preserva despesas, entradas e parcelas antigos; criar ou renomear um cadastro ativo com nome já usado retorna 409.
- `GET /expenses/recent?limit=10` retorna compras únicas em ordem de cadastro mais recente (`created_at`, com o ID como desempate). O limite aceito é de 1 a 50.
- `GET /expenses/summary` exige `start_month` e `end_month` (`AAAA-MM`) e aceita também `category_id`, `payment_method_id` e `search`. Retorna `total_amount_due`, uma lista de `monthly_totals` e outra de `category_totals`. O total é a soma das cobranças dentro dos filtros; meses sem cobranças são preenchidos com zero. O período aceita até 120 meses inclusivos.

A consulta de resumo agrega os valores de `expense_installments.amount` pelo mês de vencimento e pela categoria em uma consulta ao banco. Assim, o total e os gráficos usam o mesmo recorte sem baixar cobranças em páginas sequenciais nem somar o preço total da compra em todos os meses.

Uma requisição parcelada pode usar, por exemplo, `"amount": "1200.00"`, `"amount_type": "total"`, `"payment_type": "installments"` e `"installment_count": 6`. A mesma compra pode usar `"amount": "200.00"` e `"amount_type": "installment"`.

O PUT continua atualizando o gasto inteiro. Mudanças no valor, nas datas ou na quantidade recalculam o cronograma; mudanças apenas na descrição, categoria ou meio de pagamento preservam as cobranças. DELETE remove o gasto e todas as cobranças. A documentação interativa fica em `/docs` enquanto o servidor está em execução.

## Entradas e reembolsos

A migração `20261022_0006` cria `income_categories` e `income_entries`; `20261024_0008` atribui esses dados ao proprietário e ativa catálogos individuais.

- `GET /income-categories` lista categorias de entrada e informa `requires_expense_category`; o campo permanece independente do nome. Depois de haver uma entrada vinculada, a regra não pode mudar.
- `GET /income-entries` lista entradas paginadas; aceita `start_month`, `end_month`, `income_category_id`, `expense_category_id` e `search`.
- `POST /income-entries`, `PUT /income-entries/{id}` e `DELETE /income-entries/{id}` fazem o CRUD de entradas.

Toda entrada usa valor positivo e data de recebimento. Categorias com `requires_expense_category=true` (Reembolso) exigem `expense_category_id`; as demais rejeitam esse campo. Salários e outros ganhos não reduzem despesas.

`GET /expenses/history?month=AAAA-MM` retorna cobranças e reembolsos em uma página combinada, globalmente ordenada pelo vencimento ou recebimento, conforme o tipo. Aceita `page`, `page_size` (até 100), `search`, `category_id` e `payment_method_id`. Busca e categoria se aplicam aos dois tipos; meio de pagamento filtra cobranças, mantendo reembolsos. A resposta identifica cada linha por `kind` e inclui os totais brutos, de reembolso e líquidos sobre todos os resultados filtrados. Os valores dos itens permanecem positivos na API; a interface mostra reembolsos negativos e em vermelho.

`GET /expenses/summary` retorna `gross_expense_amount`, `reimbursement_amount` e `net_expense_amount`, também detalhados em `monthly_totals` e `category_totals`. A regra é bruto por vencimento das parcelas menos reembolsos pela data de recebimento. `amount_due` e `total_amount_due` continuam no contrato como aliases do valor líquido. Um filtro por meio de pagamento exclui reembolsos do resumo, pois ainda não há meio de recebimento associado a eles.

## Testes

Instale as dependências de desenvolvimento e execute os testes a partir da pasta `backend`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```

Os testes da API usam SQLite em memória; não criam, alteram ou removem dados do PostgreSQL local.
