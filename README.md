# Orders API

API REST para gerenciamento de clientes, produtos e pedidos, desenvolvida com **Python, FastAPI e PostgreSQL**.

O projeto demonstra práticas de desenvolvimento Backend, arquitetura em camadas, aplicação de regras de negócio, integridade transacional, controle de estoque, tratamento de exceções e testes automatizados.

O objetivo é apresentar uma aplicação organizada, testável e preparada para evoluções, simulando cenários comuns de sistemas comerciais.

---

## Sobre o projeto

A Orders API permite gerenciar clientes, produtos e pedidos por meio de endpoints REST.

A aplicação implementa regras de negócio para impedir operações inconsistentes, controlar a disponibilidade de estoque e preservar os dados envolvidos nas transações.

Entre os principais recursos estão:

- CRUD de clientes e produtos.
- Criação, consulta e listagem de pedidos.
- Cálculo automático dos valores dos pedidos.
- Registro do preço do produto no momento da compra.
- Controle de estoque durante a criação dos pedidos.
- Atualização de status dos pedidos.
- Cancelamento com devolução de estoque.
- Tratamento centralizado de exceções.
- Testes automatizados com banco de dados isolado.

---

## Tecnologias utilizadas

| Tecnologia | Aplicação |
|---|---|
| Python 3.11 | Linguagem de programação |
| FastAPI | Desenvolvimento da API REST |
| Pydantic 2 | Validação e estruturação dos dados |
| SQLAlchemy 2 | ORM e persistência |
| PostgreSQL 16 | Banco de dados relacional |
| Psycopg 3 | Driver PostgreSQL |
| Alembic | Controle de migrações |
| Pytest | Testes automatizados |
| Pytest-cov | Análise de cobertura |
| HTTPX2 | Cliente utilizado pelo TestClient |
| Docker | Execução do PostgreSQL |
| Git | Controle de versão |

---

## Arquitetura

O projeto utiliza arquitetura em camadas, separando responsabilidades e facilitando a manutenção e evolução da aplicação.

### Fluxo de processamento

```text
Requisição HTTP
      |
      v
   Routes
      |
      v
   Schemas
      |
      v
   Services
      |
      v
 Repositories
      |
      v
   Models
      |
      v
  PostgreSQL
```

### Responsabilidades

- **Routes:** recebem as requisições HTTP e disponibilizam os endpoints.
- **Schemas:** validam os dados de entrada e estruturam as respostas.
- **Services:** implementam as regras de negócio e coordenam as operações.
- **Repositories:** concentram as operações de acesso e persistência.
- **Models:** representam as entidades e relacionamentos do banco.
- **Database:** gerencia as conexões e sessões com o PostgreSQL.
- **Exceptions:** centralizam as exceções e seus respectivos códigos HTTP.
- **Migrations:** controlam a evolução da estrutura do banco com Alembic.
- **Tests:** verificam regras de negócio, integração e comportamento da API.

---

## Funcionalidades implementadas

### 1. Customers API

Gerenciamento de clientes.

- Cadastro de clientes.
- Consulta de cliente por identificador.
- Listagem de clientes.
- Atualização de dados.
- Exclusão de clientes.
- Validação de e-mail duplicado.
- Proteção contra exclusão de clientes associados a pedidos.

### 2. Products API

Gerenciamento de produtos.

- Cadastro de produtos.
- Consulta de produto por identificador.
- Listagem de produtos.
- Atualização de dados.
- Exclusão de produtos.
- Validação de preço e estoque.
- Proteção contra exclusão de produtos associados a pedidos.

### 3. Orders API

Gerenciamento do ciclo de vida dos pedidos.

- Criação de pedidos.
- Consulta de pedido por identificador.
- Listagem de pedidos.
- Associação de pedidos a clientes.
- Associação de produtos aos pedidos.
- Validação de clientes e produtos.
- Validação da disponibilidade de estoque.
- Cálculo automático do valor total.
- Registro do preço unitário no momento da compra.
- Atualização de status.
- Cancelamento de pedidos com devolução de estoque.

### 4. Regras de negócio e integridade transacional

As operações de criação de pedidos e atualização de status respeitam regras de integridade para evitar inconsistências nos dados.

Principais mecanismos:

- Cálculos financeiros utilizando `Decimal`.
- Validação de quantidades e disponibilidade de estoque.
- Rejeição de pedidos sem itens.
- Rejeição de produtos duplicados no mesmo pedido.
- Snapshot do preço unitário no momento da compra.
- Criação do pedido e dos itens na mesma transação.
- Atualização de estoque dentro da transação.
- Rollback em caso de falha.
- Bloqueio de registros com `SELECT FOR UPDATE`, protegendo o estoque durante o processamento concorrente.

### 5. Transições de status dos pedidos

O ciclo de vida dos pedidos possui transições controladas:

| Status atual | Próximos status permitidos |
|---|---|
| PENDING | CONFIRMED ou CANCELLED |
| CONFIRMED | COMPLETED ou CANCELLED |
| COMPLETED | Nenhum — estado final |
| CANCELLED | Nenhum — estado final |

No cancelamento, o estoque dos produtos é devolvido dentro da operação transacional.

A regra impede que um pedido já cancelado devolva o estoque novamente.

---

## Endpoints disponíveis

A API disponibiliza os seguintes endpoints:

### Health Check

| Método | Endpoint | Descrição |
|---|---|---|
| GET | `/health` | Verificação de saúde da aplicação |

### Customers

| Método | Endpoint | Descrição |
|---|---|---|
| POST | `/customers` | Cadastrar cliente |
| GET | `/customers` | Listar clientes |
| GET | `/customers/{customer_id}` | Consultar cliente |
| PUT | `/customers/{customer_id}` | Atualizar cliente |
| DELETE | `/customers/{customer_id}` | Excluir cliente |

### Products

| Método | Endpoint | Descrição |
|---|---|---|
| POST | `/products` | Cadastrar produto |
| GET | `/products` | Listar produtos |
| GET | `/products/{product_id}` | Consultar produto |
| PUT | `/products/{product_id}` | Atualizar produto |
| DELETE | `/products/{product_id}` | Excluir produto |

### Orders

| Método | Endpoint | Descrição |
|---|---|---|
| POST | `/orders` | Criar pedido |
| GET | `/orders` | Listar pedidos |
| GET | `/orders/{order_id}` | Consultar pedido |
| PATCH | `/orders/{order_id}/status` | Atualizar status do pedido |

---

## Exemplos de utilização

### Criar pedido

**POST `/orders`**

Requisição:

```json
{
  "customer_id": 1,
  "items": [
    {
      "product_id": 1,
      "quantity": 2
    },
    {
      "product_id": 2,
      "quantity": 3
    }
  ]
}
```

O cliente informa os identificadores e as quantidades. O Backend consulta os preços cadastrados, calcula os valores e controla a atualização do estoque.

**Observação:**: Os identificadores utilizados são ilustrativos. Antes de criar um pedido, cadastre um cliente e os produtos correspondentes.

### Atualizar status

**PATCH `/orders/{order_id}/status`**

Exemplo de requisição:

```json
{
  "status": "CONFIRMED"
}
```

As transições são validadas pela camada de serviços, respeitando as regras de negócio definidas para o ciclo de vida dos pedidos.

---

## Tratamento de exceções

A aplicação utiliza tratamento centralizado de exceções e respostas HTTP padronizadas.

| Situação | Código HTTP |
|---|---:|
| Recurso criado | 201 |
| Consulta ou atualização realizada | 200 |
| Exclusão realizada | 204 |
| Recurso não encontrado | 404 |
| Conflito com regras de negócio | 409 |
| Dados de entrada inválidos | 422 |

Exemplos de conflitos:

- E-mail de cliente já cadastrado.
- Estoque insuficiente.
- Exclusão de cliente ou produto associado a pedidos.
- Transição de status não permitida.

---

## Estrutura do projeto

```text
orders-api/
│
├── app/
│   ├── core/
│   ├── database/
│   ├── exceptions/
│   ├── models/
│   ├── repositories/
│   ├── routes/
│   ├── schemas/
│   ├── services/
│   └── main.py
│
├── migrations/
│   └── versions/
│
├── tests/
│   ├── integration/
│   ├── repositories/
│   ├── services/
│   ├── conftest.py
│   └── test_schemas_order.py
│
├── .env
├── .gitignore
├── alembic.ini
├── docker-compose.yml
├── pytest.ini
├── requirements.txt
└── README.md
```

---

## Como executar o projeto

### Pré-requisitos

- Python 3.11 ou superior.
- Git.
- Docker Desktop.
- PostgreSQL 16 (executado pelo Docker Compose).

### 1. Clonar o repositório

```bash
git clone https://github.com/AndersonDeOliveiraSoares/orders-api.git
cd orders-api
```

### 2. Criar o ambiente virtual

```bash
python -m venv .venv
```

Ativar no Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

### 3. Instalar as dependências

```bash
pip install -r requirements.txt
```

### 4. Configurar as variáveis de ambiente

Configure o arquivo `.env` com as variáveis necessárias para a conexão com o PostgreSQL.

O Docker Compose utiliza as variáveis:

- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`

Consulte `app/database/database_connection.py` para verificar a configuração de conexão utilizada pela aplicação.

Não publique credenciais ou senhas no repositório.

### 5. Iniciar o PostgreSQL

```bash
docker compose up -d db
```

O ambiente de desenvolvimento utiliza:

| Configuração | Valor |
|---|---|
| Container | orders-postgres |
| Imagem | postgres:16 |
| Banco | orders_db |
| Usuário | orders_user |
| Porta local | 5434 |
| Porta do container | 5432 |

### 6. Executar as migrações

```bash
alembic upgrade head
```

### 7. Executar a aplicação

```bash
uvicorn app.main:app --reload
```

A aplicação ficará disponível em:

- API: http://127.0.0.1:8000
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc
- Health Check: http://127.0.0.1:8000/health

---

## Banco de dados de testes

O projeto utiliza um banco de dados exclusivo para testes automatizados, separado do banco de desenvolvimento.

| Ambiente | Banco | Porta |
|---|---|---:|
| Desenvolvimento | orders_db | 5434 |
| Testes | orders_test_db | 5434 |

O banco de testes é utilizado pelas fixtures do Pytest, que criam a estrutura necessária e isolam as operações realizadas durante a execução dos testes.

Para criar o banco de testes no container:

```powershell
docker exec orders-postgres psql -U orders_user -d postgres -c "CREATE DATABASE orders_test_db;"
```

Essa criação deve ser realizada uma única vez no ambiente local.

---

## Testes automatizados

O projeto utiliza Pytest para validar o comportamento das diferentes camadas da aplicação.

### Executar todos os testes

```bash
pytest -q
```

### Executar testes de serviços

```bash
pytest tests/services/ -v
```

### Executar testes de integração

```bash
pytest tests/integration/ -v
```

### Executar testes de repositórios

```bash
pytest tests/repositories/ -v
```

### Executar com relatório de cobertura

```bash
pytest --cov=app --cov-report=term-missing
```

### Resultados atuais

| Indicador | Resultado |
|---|---:|
| Testes aprovados | 83 |
| Cobertura total | 97% |
| Warnings na última execução | 0 |

A suíte automatizada contempla testes de serviços, repositórios, schemas e integração HTTP.

Os testes verificam regras de negócio, validações, persistência, transações, rollback, controle de estoque e respostas da API.

---

## Roadmap de desenvolvimento

### Concluído

- [x] Estrutura inicial do projeto.
- [x] Configuração do FastAPI.
- [x] Endpoint de Health Check.
- [x] Schemas e validação com Pydantic 2.
- [x] Models com SQLAlchemy.
- [x] Repositories.
- [x] Services e regras de negócio.
- [x] Integração com PostgreSQL.
- [x] Migrações com Alembic.
- [x] Orders Core.
- [x] Customers API completa.
- [x] Products API completa.
- [x] Controle transacional de pedidos.
- [x] Atualização e validação de estoque.
- [x] Controle de concorrência com `SELECT FOR UPDATE`.
- [x] Transições de status e cancelamento de pedidos.
- [x] Devolução de estoque no cancelamento.
- [x] Tratamento centralizado de exceções.
- [x] Testes de serviços.
- [x] Testes de repositórios.
- [x] Testes de integração HTTP.
- [x] Banco de dados exclusivo para testes.
- [x] Isolamento das operações de teste.
- [x] Configuração de dependências com `requirements.txt`.

### Próximas evoluções

- [ ] Testes de concorrência com transações independentes.
- [ ] Idempotência na criação de pedidos.
- [ ] Transactional Outbox.
- [ ] Integração com RabbitMQ.
- [ ] Containerização completa da aplicação.
- [ ] Pipeline de CI/CD com GitHub Actions.
- [ ] Monitoramento e observabilidade.

---

## Autor

**Anderson Soares**

Desenvolvedor Backend | Python | FastAPI | SQL | Engenharia de Software

GitHub: [AndersonDeOliveiraSoares](https://github.com/AndersonDeOliveiraSoares)

Repositório: [orders-api](https://github.com/AndersonDeOliveiraSoares/orders-api)

---

*Projeto desenvolvido com foco em boas práticas de Engenharia de Software, arquitetura Backend, integridade de dados e qualidade de código.*