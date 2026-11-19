# Orders API

API REST para gerenciamento de pedidos, desenvolvida com Python e FastAPI, utilizando PostgreSQL, SQLAlchemy e arquitetura em camadas.

O projeto demonstra boas práticas de desenvolvimento Backend, separação de responsabilidades, validação de dados, regras de negócio, integridade transacional, controle de estoque e testes automatizados.

## Sobre o projeto

A Orders API é um projeto de portfólio desenvolvido para demonstrar conhecimentos em engenharia de software e desenvolvimento Backend com Python.

A aplicação permite criar e consultar pedidos, validando clientes, produtos e disponibilidade de estoque. Os valores dos pedidos são calculados no Backend, e as operações de criação e atualização de estoque são realizadas dentro de uma transação.

O projeto está sendo desenvolvido de forma incremental, priorizando organização, manutenibilidade, integridade dos dados e qualidade do código.

## Tecnologias utilizadas

- Python 3.11
- FastAPI
- Pydantic 2
- SQLAlchemy 2
- PostgreSQL 16
- Alembic
- Pytest
- HTTPX
- Docker

## Arquitetura do projeto

A aplicação utiliza arquitetura em camadas, separando as responsabilidades de cada componente.

```text
orders-api/
│
├── app/
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
│   ├── services/
│   ├── integration/
│   └── conftest.py
│
├── .env
├── .gitignore
├── alembic.ini
├── requirements.txt
└── README.md
```

### Responsabilidades das camadas

- **Routes:** recebem as requisições HTTP e disponibilizam os endpoints.
- **Schemas:** validam os dados de entrada e estruturam as respostas.
- **Services:** implementam as regras de negócio, cálculos e coordenação das transações.
- **Repositories:** concentram o acesso e a persistência dos dados.
- **Models:** representam as entidades e restrições do banco de dados.
- **Database:** gerencia as conexões e sessões com o PostgreSQL.
- **Exceptions:** centralizam as exceções da aplicação e seus respectivos códigos HTTP.
- **Migrations:** controlam a evolução da estrutura do banco com Alembic.
- **Tests:** validam regras de negócio e comportamento dos endpoints.

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
  PostgreSQL
```

As regras de negócio ficam concentradas na camada de serviços, evitando que as rotas assumam responsabilidades de persistência ou processamento.

## Funcionalidades implementadas

### Pedidos

- Criação de pedidos.
- Consulta de pedido por identificador.
- Listagem de pedidos.
- Associação de pedidos a clientes.
- Associação de produtos aos pedidos.
- Cálculo automático do valor total.
- Registro do preço unitário no momento da compra.

### Validações e regras de negócio

- Validação da existência do cliente.
- Validação da existência dos produtos.
- Validação de estoque disponível.
- Rejeição de quantidades inválidas.
- Rejeição de pedidos sem itens.
- Rejeição de produtos duplicados no mesmo pedido.
- Cálculo de valores utilizando `Decimal`.
- Atualização automática do estoque.

### Integridade transacional

- Criação do pedido e dos itens na mesma transação.
- Atualização do estoque na mesma transação.
- Rollback em caso de falha.
- Bloqueio de registros de produtos com `SELECT FOR UPDATE`, protegendo o estoque durante o processamento concorrente de pedidos.

### Tratamento de exceções

A aplicação possui tratamento centralizado de exceções, com respostas HTTP padronizadas.

| Situação | Código HTTP |
|---|---:|
| Pedido criado | 201 |
| Consulta realizada | 200 |
| Cliente não encontrado | 404 |
| Produto não encontrado | 404 |
| Pedido não encontrado | 404 |
| Estoque insuficiente | 409 |
| Dados de entrada inválidos | 422 |

## Endpoints disponíveis

| Método | Endpoint | Descrição |
|---|---|---|
| GET | `/health` | Verificação de saúde da aplicação |
| POST | `/orders` | Criação de pedido |
| GET | `/orders` | Listagem de pedidos |
| GET | `/orders/{order_id}` | Consulta de pedido |

### Exemplo de criação de pedido

**POST /orders**

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

O preço dos produtos e o valor total não são informados pelo cliente. Esses valores são obtidos e calculados pelo Backend.

Exemplo de resposta:

```json
{
  "id": 1,
  "customer_id": 1,
  "status": "PENDING",
  "total_amount": "7300.00",
  "created_at": "2026-11-19T10:00:00",
  "items": [
    {
      "product_id": 1,
      "quantity": 2,
      "unit_price": "3500.00",
      "subtotal": "7000.00"
    },
    {
      "product_id": 2,
      "quantity": 3,
      "unit_price": "100.00",
      "subtotal": "300.00"
    }
  ]
}
```

*Os identificadores e valores acima são ilustrativos.*

## Como executar o projeto

### Pré-requisitos

- Python 3.11 ou superior.
- Git.
- Docker.
- PostgreSQL 16 (pode ser executado em container).

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

### 4. Configurar o banco de dados

Configure as variáveis de conexão do PostgreSQL no arquivo `.env`, conforme a configuração utilizada em `app/database/database_connection.py`.

O ambiente de desenvolvimento utiliza PostgreSQL 16 em Docker, com a seguinte configuração:

- Banco: `orders_db`
- Usuário: `orders_user`
- Porta local: `5434`
- Porta do PostgreSQL no container: `5432`

Não publique credenciais ou senhas do banco no repositório.

### 5. Executar as migrações

```bash
alembic upgrade head
```

### 6. Executar a aplicação

```bash
uvicorn app.main:app --reload
```

A aplicação ficará disponível em:

- API: http://127.0.0.1:8000
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc
- Health Check: http://127.0.0.1:8000/health

## Testes automatizados

O projeto utiliza Pytest para validar regras de negócio e comportamento da API.

### Executar todos os testes

```bash
python -m pytest -v
```

### Executar testes de serviços

```bash
python -m pytest tests/services/ -v
```

### Executar testes de integração

```bash
python -m pytest tests/integration/ -v
```

### Cobertura atual

**33 testes automatizados aprovados.**

- 26 testes de serviços.
- 7 testes de integração HTTP.

Os testes verificam criação de pedidos, cálculos, validações, disponibilidade de estoque, rollback e códigos de resposta HTTP.

## Roadmap de desenvolvimento

- [x] Estrutura inicial do projeto.
- [x] Configuração do FastAPI.
- [x] Endpoint de Health Check.
- [x] Schemas e validação com Pydantic 2.
- [x] Models com SQLAlchemy.
- [x] Repositories.
- [x] Services e regras de negócio.
- [x] Integração com PostgreSQL.
- [x] Migrações com Alembic.
- [x] Criação e consulta de pedidos.
- [x] Processamento transacional de pedidos.
- [x] Atualização e validação de estoque.
- [x] Tratamento centralizado de exceções.
- [x] Controle de concorrência com bloqueio de registros.
- [x] Testes automatizados de serviços.
- [x] Testes de integração HTTP.
- [ ] Banco de dados exclusivo para testes.
- [ ] Testes de concorrência com transações independentes.
- [ ] Idempotência na criação de pedidos.
- [ ] Transactional Outbox.
- [ ] Integração com RabbitMQ.
- [ ] Containerização completa da aplicação.
- [ ] Pipeline de CI/CD.
- [ ] Monitoramento e observabilidade.

## Autor

**Anderson Soares**

Desenvolvedor Backend | Python | FastAPI | SQL | Engenharia de Software

GitHub: [AndersonDeOliveiraSoares](https://github.com/AndersonDeOliveiraSoares)
