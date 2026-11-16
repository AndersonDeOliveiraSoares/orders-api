# Orders API

API REST para gerenciamento de pedidos, desenvolvida com Python e FastAPI, com foco em arquitetura em camadas, regras de negócio, validação de dados, integridade transacional e testes automatizados.

## Sobre o projeto

A Orders API é um projeto de portfólio desenvolvido para demonstrar conhecimentos e boas práticas de engenharia de software e desenvolvimento Backend.

O projeto está sendo construído de forma incremental, utilizando uma arquitetura em camadas e separação clara de responsabilidades.

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

A aplicação utiliza uma arquitetura em camadas:

```text
app/
├── core/
├── database/
├── models/
├── repositories/
├── routes/
├── schemas/
└── main.py

tests/
```

### Responsabilidades das camadas

- **Routes:** recebem as requisições HTTP e disponibilizam os endpoints.
- **Schemas:** validam os dados de entrada e estruturam as respostas.
- **Services:** implementam as regras de negócio e a lógica da aplicação.
- **Repositories:** concentram o acesso e a persistência dos dados.
- **Models:** representam as entidades do banco de dados.
- **Database:** gerencia as conexões e sessões com o banco.
- **Core:** concentra configurações e componentes compartilhados da aplicação.

## Funcionalidades implementadas

- Estrutura inicial da aplicação FastAPI.
- Endpoint de verificação de saúde (`GET /health`).
- Schemas de criação de pedidos com Pydantic 2.
- Validação de identificadores e quantidades positivas.
- Prevenção de pedidos sem itens.
- Identificação e rejeição de produtos duplicados.
- Testes automatizados de validação com Pytest.

## Como executar o projeto

### Pré-requisitos

- Python 3.11 ou superior.
- Git.

### Instalação

Clone o repositório:

```bash
git clone https://github.com/AndersonDeOliveiraSoares/orders-api.git
cd orders-api
```

Crie o ambiente virtual:

```bash
python -m venv .venv
```

Ative o ambiente virtual no Windows:

```powershell
.venv\Scripts\Activate.ps1
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

### Executando a aplicação

```bash
uvicorn app.main:app --reload
```

Documentação interativa:

- Swagger UI: http://127.0.0.1:8000/docs
- Health Check: http://127.0.0.1:8000/health

### Executando os testes

```bash
pytest -v
```

## Roadmap de desenvolvimento

- [x] Estrutura inicial do projeto.
- [x] Configuração do FastAPI.
- [x] Endpoint de Health Check.
- [x] Schemas de criação de pedidos.
- [x] Validação dos dados de entrada.
- [x] Testes automatizados dos Schemas.
- [ ] Gerenciamento de clientes e produtos.
- [ ] Integração com PostgreSQL.
- [ ] Models e Repositories com SQLAlchemy.
- [ ] Migrações com Alembic.
- [ ] Endpoint de criação de pedidos.
- [ ] Processamento transacional de pedidos e atualização de estoque.
- [ ] Controle de concorrência.
- [ ] Idempotência.
- [ ] Transactional Outbox e RabbitMQ.
- [ ] Ambiente Docker.
- [ ] Testes de integração e ponta a ponta.

## Autor

**Anderson Soares**

Desenvolvedor Backend | Python | FastAPI | SQL | Engenharia de Software

GitHub: [AndersonDeOliveiraSoares](https://github.com/AndersonDeOliveiraSoares)