# Orders API

API REST para gerenciamento de clientes, produtos e pedidos, desenvolvida com **Python 3.11, FastAPI e PostgreSQL 16**.

O projeto demonstra práticas de Engenharia de Software e desenvolvimento Backend, incluindo arquitetura em camadas, regras de negócio, integridade transacional, controle de concorrência, mensageria com RabbitMQ, padrão Transactional Outbox, idempotência e testes automatizados.

O objetivo é simular componentes e desafios comuns de sistemas comerciais, com foco em consistência de dados, confiabilidade, organização do código e qualidade de software.

---

## Sumário

- [Visão geral](#visão-geral)
- [Tecnologias utilizadas](#tecnologias-utilizadas)
- [Arquitetura](#arquitetura)
- [Funcionalidades](#funcionalidades)
- [Regras de negócio e integridade transacional](#regras-de-negócio-e-integridade-transacional)
- [Ciclo de vida dos pedidos](#ciclo-de-vida-dos-pedidos)
- [Integração e processamento assíncrono](#integração-e-processamento-assíncrono)
- [Observabilidade e logs](#observabilidade-e-logs)
- [Endpoints disponíveis](#endpoints-disponíveis)
- [Tratamento de erros](#tratamento-de-erros)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Configuração e execução local](#configuração-e-execução-local)
- [Banco de dados de testes](#banco-de-dados-de-testes)
- [Testes automatizados](#testes-automatizados)
- [Integração contínua](#integração-contínua)
- [Roadmap](#roadmap)

---

## Visão geral

A Orders API permite gerenciar clientes, produtos e pedidos por meio de endpoints REST.

A aplicação implementa regras de negócio para controlar operações comerciais, disponibilidade de estoque e ciclo de vida dos pedidos.

### Principais recursos

- CRUD de clientes e produtos.
- Criação, consulta e listagem de pedidos.
- Cálculo automático dos valores dos pedidos.
- Registro do preço do produto no momento da compra.
- Controle transacional de estoque.
- Proteção contra vendas concorrentes acima do estoque disponível.
- Atualização e cancelamento de pedidos.
- Devolução de estoque no cancelamento.
- Idempotência na criação de pedidos por chave de requisição.
- Transactional Outbox para registro de eventos na mesma transação do pedido.
- Publicador de eventos com confirmação do RabbitMQ.
- Consumidor RabbitMQ com controle de mensagens duplicadas.
- Estratégia de Retry e Dead Letter Queue (DLQ).
- Logs estruturados e correlation ID.
- Testes automatizados e integração contínua com GitHub Actions.

---

## Tecnologias utilizadas

| Tecnologia | Aplicação |
|---|---|
| Python 3.11 | Linguagem principal |
| FastAPI | Desenvolvimento da API REST |
| Pydantic 2 | Validação de dados |
| SQLAlchemy 2 | ORM e persistência |
| PostgreSQL 16 | Banco de dados relacional |
| Psycopg 3 | Driver PostgreSQL |
| Alembic | Migrações de banco |
| RabbitMQ 4 | Mensageria |
| Pika 1.5 | Comunicação com RabbitMQ |
| Pytest | Testes automatizados |
| Pytest-cov | Cobertura de testes |
| HTTPX | Cliente HTTP utilizado nos testes |
| Docker Compose | Infraestrutura local |
| GitHub Actions | Integração contínua |
| Git | Controle de versão |

---

## Arquitetura

O projeto utiliza arquitetura em camadas, separando responsabilidades e facilitando manutenção, testes e evolução.

### Fluxo da API

```text
Cliente HTTP
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

- **Routes:** recebem requisições HTTP e disponibilizam os endpoints.
- **Schemas:** validam os dados de entrada e estruturam as respostas.
- **Services:** implementam regras de negócio e coordenam operações.
- **Repositories:** concentram operações de acesso e persistência.
- **Models:** representam entidades e relacionamentos.
- **Database:** gerencia conexões e sessões com PostgreSQL.
- **Exceptions:** centralizam exceções e respostas HTTP.
- **Migrations:** controlam a evolução do banco com Alembic.
- **Tests:** verificam regras de negócio, integração e comportamento da API.
- **Messaging:** concentra a comunicação com RabbitMQ.
- **Worker:** executa o processamento assíncrono dos eventos.

---

## Funcionalidades

### 1. Customers API

Gerenciamento de clientes:

- Cadastro de clientes.
- Consulta por identificador.
- Listagem de clientes.
- Atualização de dados.
- Exclusão de clientes.

### 2. Products API

Gerenciamento de produtos:

- Cadastro de produtos.
- Consulta por identificador.
- Listagem de produtos.
- Atualização de dados.
- Exclusão de produtos.

### 3. Orders API

Gerenciamento do ciclo de vida dos pedidos:

- Criação de pedidos.
- Consulta por identificador.
- Listagem de pedidos.
- Associação de pedidos a clientes.
- Associação de produtos aos pedidos.
- Validação de clientes e produtos.
- Verificação de estoque disponível.
- Cálculo automático do valor total.
- Registro do preço unitário no momento da compra.
- Atualização de status.
- Cancelamento com devolução de estoque.

---

## Regras de negócio e integridade transacional

As operações de pedidos respeitam regras de integridade para evitar inconsistências.

Principais mecanismos:

- Validação da existência de clientes e produtos.
- Validação de estoque disponível.
- Bloqueio de registros com `SELECT FOR UPDATE` para proteger o estoque durante operações concorrentes.
- Criação do pedido e dos itens na mesma transação.
- Atualização de estoque dentro da transação.
- Rollback em caso de falha.
- Idempotência na criação de pedidos por chave de requisição.

### Idempotência na criação de pedidos

A API permite utilizar uma chave de idempotência na criação de pedidos.

O comportamento implementado contempla:

- Mesma chave e mesmo payload: retorna o pedido previamente criado.
- Mesma chave e payload diferente: retorna conflito HTTP 409.
- Requisição sem chave: segue o fluxo normal de criação.

Esse mecanismo evita a criação duplicada de pedidos em situações de repetição de requisições.

---

## Ciclo de vida dos pedidos

As transições de status são controladas pelas regras de negócio.

| Status atual | Próximos status permitidos |
|---|---|
| PENDING | CONFIRMED, CANCELLED |
| CONFIRMED | COMPLETED, CANCELLED |
| COMPLETED | Nenhum |
| CANCELLED | Nenhum |

No cancelamento, o estoque dos produtos é devolvido dentro da operação transacional.

A regra impede que um pedido cancelado devolva o estoque novamente.

### Cobertura automatizada das transições

Os testes de integração validam os principais caminhos do ciclo de vida dos pedidos:

- `PENDING` para `CONFIRMED`.
- `CONFIRMED` para `COMPLETED`.
- Cancelamento de pedidos `PENDING` e `CONFIRMED`, com devolução do estoque.
- Bloqueio do cancelamento de pedidos `COMPLETED`.
- Bloqueio de um segundo cancelamento de pedidos `CANCELLED`.
- Bloqueio de transições não permitidas, como `PENDING` diretamente para `COMPLETED`.
- Retorno HTTP 404 para pedido inexistente.
- Retorno HTTP 422 para status inválido.

Essa cobertura também verifica se o estoque permanece consistente quando uma transição é rejeitada.

---

## Integração e processamento assíncrono

O projeto possui uma estrutura de mensageria baseada em RabbitMQ, utilizando o padrão Transactional Outbox para garantir a persistência dos eventos relacionados às operações de negócio.

### Transactional Outbox

Durante a criação do pedido, o evento correspondente é registrado na tabela Outbox dentro da mesma transação do banco de dados.

Isso evita que o pedido seja confirmado sem que o registro do evento também seja persistido.

O `OutboxPublisher` implementa:

- Consulta de eventos pendentes.
- Publicação no exchange `orders`.
- Roteamento pela chave `order.created`.
- Mensagens persistentes.
- Publicação com `mandatory=True`.
- Publisher Confirms para verificar a confirmação do RabbitMQ.
- Atualização do evento para publicado após confirmação.
- Tratamento de falhas e rollback.

O Outbox Publisher é executado automaticamente pelo Worker em uma thread separada, consultando eventos pendentes a cada 5 segundos e publicando lotes de até 100 eventos.

### RabbitMQ Consumer e Worker

O projeto possui um Worker independente, executado por:

```powershell
python -m app.worker.main
```

O Worker executa o Outbox Publisher periodicamente e mantém o Consumer aguardando mensagens na fila `orders.events`.

O consumidor implementa:

- Conexão com RabbitMQ.
- Consumo da fila `orders.events`.
- Validação do conteúdo JSON.
- Identificação dos eventos por `event_id`.
- Registro de eventos processados na tabela `processed_events`.
- Confirmação de mensagens com ACK.
- Encaminhamento de mensagens inválidas para DLQ.
- Estratégia de Retry com até duas novas tentativas.
- Confirmação de publicação das mensagens de Retry.

### Idempotência no consumidor

A tabela `processed_events` armazena os identificadores dos eventos já registrados.

O consumidor utiliza uma operação de inserção com `ON CONFLICT DO NOTHING`, evitando registrar o mesmo evento mais de uma vez.

Mensagens duplicadas são reconhecidas e confirmadas sem novo processamento.

O método `process_event()` valida o tipo do evento, o agregado e a consistência do identificador do pedido, além de registrar o processamento em log estruturado.

O controle de idempotência impede o processamento repetido de eventos já registrados.

Não há uma segunda operação de negócio associada ao evento nesta versão.

### Fluxo de processamento

```text
Criação do pedido
       |
       v
Transação PostgreSQL
       |
       +------> Pedido e itens
       |
       +------> Registro na Outbox
                    |
                    v
             Outbox Publisher
                    |
                    v
                RabbitMQ
                    |
                    v
              orders.events
                    |
                    v
              RabbitMQ Consumer
                    |
                    v
          Registro de idempotência
                    |
                    v
          Validação e log do evento
                    |
                    v
                   ACK
```

### Retry e Dead Letter Queue

A topologia de mensageria utiliza:

| Componente | Finalidade |
|---|---|
| `orders` | Exchange principal |
| `orders.events` | Fila principal |
| `orders.retry.exchange` | Exchange de Retry |
| `orders.retry` | Fila temporária de Retry |
| `orders.dlx` | Dead Letter Exchange |
| `orders.events.dlq` | Fila de mensagens rejeitadas |

O fluxo de Retry utiliza TTL de 30 segundos antes de devolver a mensagem à fila principal.

Após duas novas tentativas sem sucesso, a mensagem é encaminhada para a DLQ.

---

## Observabilidade e logs

O projeto utiliza logging estruturado em JSON.

Os registros incluem informações relevantes para rastreamento e diagnóstico, como:

- Timestamp.
- Nível do log.
- Logger.
- Event ID.
- Correlation ID.
- Identificador do agregado.
- Informações de erro e exceções.

O correlation ID permite relacionar operações e eventos pertencentes ao mesmo fluxo de processamento.

---

## Endpoints disponíveis

A API disponibiliza endpoints para:

| Recurso | Operações |
|---|---|
| Health Check | Verificação da disponibilidade da aplicação |
| Customers | Cadastro, consulta, listagem, atualização e exclusão |
| Products | Cadastro, consulta, listagem, atualização e exclusão |
| Orders | Criação, consulta e listagem de pedidos |
| Order Status | Atualização do status do pedido |

### Documentação interativa

Com a API em execução, a documentação pode ser acessada por:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

### Criar pedido

**POST `/orders`**

Exemplo de requisição:

```json
{
  "customer_id": 1,
  "items": [
    {
      "product_id": 1,
      "quantity": 2
    }
  ]
}
```

O Backend consulta os preços cadastrados, calcula os valores e controla a atualização do estoque.

Os identificadores são ilustrativos. Cadastre previamente o cliente e os produtos correspondentes.

### Atualizar status

**PATCH `/orders/{order_id}/status`**

Exemplo de requisição:

```json
{
  "status": "CONFIRMED"
}
```

As transições são validadas pela camada de serviços.

---

## Tratamento de erros

A aplicação possui tratamento centralizado de exceções, com respostas HTTP apropriadas para os cenários de erro.

Exemplos de conflitos:

- E-mail de cliente já cadastrado.
- Estoque insuficiente.
- Exclusão de cliente ou produto associado a pedidos.
- Chave de idempotência utilizada com payload diferente.
- Transição de status não permitida.

---

## Estrutura do projeto

```text
orders-api/
|
├── .github/
│   └── workflows/
│       └── tests.yml
|
├── app/
│   ├── core/
│   ├── database/
│   ├── exceptions/
│   ├── messaging/
│   ├── models/
│   ├── repositories/
│   ├── routes/
│   ├── schemas/
│   ├── services/
│   ├── worker/
│   └── main.py
|
├── migrations/
│   └── versions/
|
├── tests/
│   ├── integration/
│   ├── repositories/
│   ├── services/
│   └── conftest.py
|
├── .env.example
├── alembic.ini
├── docker-compose.yml
├── pytest.ini
├── requirements.txt
└── README.md
```

---

## Configuração e execução local

### Pré-requisitos

- Python 3.11 ou superior.
- Git.
- Docker Desktop com Docker Compose.

### 1. Clonar o repositório

```powershell
git clone https://github.com/AndersonDeOliveiraSoares/orders-api.git

cd orders-api
```

### 2. Criar o ambiente virtual

```powershell
python -m venv .venv
```

Ativar no Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Instalar as dependências

```powershell
pip install -r requirements.txt
```

### 4. Configurar as variáveis de ambiente

Crie o arquivo `.env` a partir do modelo:

```powershell
Copy-Item .env.example .env
```

Configure as variáveis:

```env
POSTGRES_DB=orders_db
POSTGRES_USER=orders_user
POSTGRES_PASSWORD=sua_senha

DB_HOST=localhost
DB_PORT=5434
```

Não publique credenciais ou senhas no repositório.

### 5. Iniciar PostgreSQL e RabbitMQ

```powershell
docker compose up -d
```

Serviços disponibilizados:

| Serviço | Endereço |
|---|---|
| PostgreSQL | `localhost:5434` |
| RabbitMQ | `localhost:5672` |
| RabbitMQ Management | `http://localhost:15672` |

O painel de administração do RabbitMQ utiliza as credenciais padrão `guest` / `guest` na configuração apresentada.

### 6. Executar as migrações

```powershell
alembic upgrade head
```

### 7. Executar a API

```powershell
uvicorn app.main:app --reload
```

A aplicação ficará disponível em:

- API: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- Health Check: `http://127.0.0.1:8000/health`

### 8. Executar o Worker

Em outro terminal, com o ambiente virtual ativado:

```powershell
python -m app.worker.main
```

O Worker executa o Outbox Publisher periodicamente e mantém o Consumer aguardando mensagens na fila `orders.events`.

**Observação:** nesta versão, PostgreSQL e RabbitMQ são executados pelo Docker Compose. A API e o Worker são executados diretamente no ambiente Python local.

---

## Banco de dados de testes

O projeto utiliza um banco exclusivo para testes automatizados, separado do banco de desenvolvimento.

| Ambiente | Banco | Porta |
|---|---|---:|
| Desenvolvimento | `orders_db` | 5434 |
| Testes | `orders_test_db` | 5434 |

Criar o banco de testes localmente:

```powershell
docker exec orders-postgres psql -U orders_user -d postgres -c "CREATE DATABASE orders_test_db;"
```

Essa criação deve ser realizada uma única vez no ambiente local.

As fixtures do Pytest criam a estrutura necessária e isolam as operações de cada teste por meio de transações.

---

## Testes automatizados

O projeto utiliza Pytest para validar as diferentes camadas da aplicação.

### Executar todos os testes

```powershell
pytest -v
```

### Executar testes de serviços

```powershell
pytest tests/services/ -v
```

### Executar testes de integração

```powershell
pytest tests/integration/ -v
```

### Executar testes de repositórios

```powershell
pytest tests/repositories/ -v
```

### Executar com relatório de cobertura

```powershell
pytest --cov=app --cov-report=term-missing
```

### Resultado validado

As execuções completas mais recentes registradas apresentaram os seguintes resultados:

| Execução | Testes aprovados | Testes reprovados | Duração |
|---|---:|---:|---:|
| GitHub Actions | 106 | 0 | 92,32 segundos |
| Ambiente local | 106 | 0 | 97,50 segundos |

A execução do GitHub Actions foi realizada em Ubuntu com Python 3.11.

A suíte contempla testes de API, serviços, repositórios, schemas, concorrência, idempotência, Outbox, integração com RabbitMQ e transições do ciclo de vida dos pedidos.

O arquivo `tests/integration/test_orders_api_additions.py` contém 9 testes específicos para as regras de atualização de status e consistência do estoque. Esses testes já estão incluídos no total de 106 testes.

---

## Integração contínua

O projeto possui pipeline de CI configurado em:

`.github/workflows/tests.yml`

O workflow é executado automaticamente em:

- Push na branch `main`.
- Pull Requests direcionados à branch `main`.

O pipeline:

1. Prepara o ambiente Python 3.11.
2. Inicializa PostgreSQL 16.
3. Inicializa RabbitMQ 4.
4. Instala as dependências.
5. Cria o banco exclusivo de testes.
6. Executa a suíte completa com Pytest por meio do comando `pytest -v`.

Como o workflow executa a suíte completa, os testes de integração das transições de status também fazem parte da validação contínua.

**Última execução do CI registrada:** 106 testes aprovados.

---

## Roadmap

### Concluído

- [x] Estrutura inicial do projeto.
- [x] API REST com FastAPI.
- [x] Customers API completa.
- [x] Products API completa.
- [x] Orders API.
- [x] Regras de negócio e controle transacional.
- [x] Ciclo de vida dos pedidos e validação das transições de status.
- [x] Testes de integração para transições permitidas e bloqueadas.
- [x] Devolução de estoque no cancelamento e validação da consistência do estoque.
- [x] Controle de concorrência com `SELECT FOR UPDATE`.
- [x] Idempotência na criação de pedidos.
- [x] Transactional Outbox.
- [x] Publicador com Publisher Confirms.
- [x] Integração com RabbitMQ.
- [x] Worker e Consumer.
- [x] Idempotência de eventos recebidos.
- [x] Retry e Dead Letter Queue.
- [x] Logging estruturado e correlation ID.
- [x] Testes automatizados.
- [x] Integração contínua com GitHub Actions.
- [x] Integração validada de ponta a ponta: Outbox → Publisher → RabbitMQ → Consumer.

### Próximas evoluções

- [ ] Containerização da API e do Worker junto à infraestrutura existente.
- [ ] Avaliar monitoramento e métricas como evolução futura.

---

## Repositório

GitHub: [orders-api](https://github.com/AndersonDeOliveiraSoares/orders-api)

---

*Projeto desenvolvido com foco em boas práticas de Engenharia de Software, arquitetura Backend, integridade de dados, mensageria e qualidade de código.*