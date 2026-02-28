# Repository Guidelines (lp-be)

> **Objetivo deste documento**: definir um padrão arquitetural rígido para evitar acoplamento, duplicação de regra de negócio e “classes deus”.
> Todas as mudanças no projeto e **todas as novas atividades** devem seguir estas regras.

---

## 1) Padrão Arquitetural Obrigatório (Hexagonal / Ports & Adapters)

Este projeto deve seguir **Arquitetura Hexagonal (Ports & Adapters)**.

**Definições usadas neste repositório:**
- **Core** = `domain/` + `application/` (onde vivem regras e casos de uso). O core **não conhece** detalhes externos.
- **Ports** = interfaces (contratos) definidas pelo core, em `application/ports/`.
- **Adapters** = implementações dos ports, em `infrastructure/` (DB, HTTP clients, cache, mensageria) e `api/` (HTTP/FastAPI como adaptador de entrada).

### 1.1. Princípios inegociáveis
1. **Regra de negócio é única e centralizada**: qualquer cálculo (ex.: APR, pricing, match de ticks, distribuição, etc.) deve existir em **um único lugar** no core (Domain/Application). Não duplicar em routers, repositories, clients ou scripts.
2. **Inversão de dependência (sempre para dentro)**:
   - O core (`domain` + `application`) **não importa** DB/HTTP/FastAPI.
   - Adapters (`infrastructure` e `api`) dependem do core para implementar e conectar.
3. **Sem “métodos que fazem tudo”**: carregar dados + calcular + formatar resposta + persistir deve ser dividido por responsabilidades.
4. **Trocar query/fonte de dados não pode exigir alterar cálculo**: mudanças de schema, query, joins, import, índices, etc. devem ficar confinadas ao adapter (infra) desde que o contrato (port) seja mantido.
5. **Toda feature deve nascer já neste padrão**: durante migração pode coexistir código legado, mas todo código novo segue o padrão alvo.
6. **É proibido usar fallback no fluxo de negócio**: as implementações devem funcionar no **fluxo principal**. Se faltar dado obrigatório, o comportamento correto é falhar explicitamente com erro claro (não degradar para caminho alternativo silencioso).
7. **Operações de escrita devem ser atômicas**: todo fluxo que execute `insert`, `update` ou `delete` deve rodar dentro de **transação explícita**; se qualquer etapa falhar, deve ocorrer **rollback completo** (nunca commit parcial).

---

## 2) Estrutura de Pastas Alvo (Target Structure)

A estrutura abaixo é a referência. Ao refatorar, mover o código gradualmente para esse padrão.

```
app/
  main.py                        # cria FastAPI app e inclui routers

  api/                           # ADAPTER DE ENTRADA (HTTP/FastAPI)
    routers/
    deps.py                      # wiring/DI (injeção de dependências)
    schemas/                     # Pydantic (boundary HTTP)
    errors.py                    # mapeamento de erros -> HTTP

  application/                   # CORE (casos de uso/orquestração)
    use_cases/
    ports/                       # PORTS: interfaces (Protocol) definidas pelo core
    dto/                         # DTOs internos do core (opcional)

  domain/                        # CORE (regras puras do negócio)
    entities/
    value_objects/
    services/                    # cálculos/políticas puras
    exceptions.py

  infrastructure/                # ADAPTERS DE SAÍDA (detalhes externos)
    db/
      repositories/              # SQL nativo aqui (sem ORM)
      mappers/                   # row -> domain/dto
    clients/                     # subgraph/http clients, SDKs
    caching/
    messaging/

  shared/                        # cross-cutting (neutro; sem FastAPI)
    config.py
    logging.py
    time.py
```

### 2.1. Situação atual do repositório
Hoje existem pastas como `app/repositories/`, `app/services/`, `app/schemas/`, `app/models/`.

**Regra de migração**:
- Código pode coexistir temporariamente.
- **Qualquer arquivo tocado em refactor** deve ser movido/adequado para o padrão.
- **Qualquer feature nova** já deve nascer em `domain/application/infrastructure/api`.

---

## 3) Regras de Dependência (Import Rules)

### 3.1. O que cada camada pode importar

**`app/domain/**` (CORE)**
- ✅ Python stdlib
- ✅ `typing`, `dataclasses`, `decimal`, `math` (se necessário)
- ✅ estruturas do próprio domain
- ❌ FastAPI, Pydantic
- ❌ DB drivers, SQL, psycopg, asyncpg, etc.
- ❌ httpx/requests, SDKs externos
- ❌ qualquer coisa em `app/infrastructure/**` ou `app/api/**`
- ❌ ler env/config diretamente (preferir receber valores via parâmetros)

**`app/application/**` (CORE)**
- ✅ `app/domain/**`
- ✅ `app/application/ports/**`
- ✅ `app/shared/**` (somente utilidades neutras)
- ❌ FastAPI/Pydantic (boundary é na API)
- ❌ SQL/DB drivers/queries
- ❌ httpx/requests/SDKs
- ❌ importar adapters de `infrastructure`

**`app/infrastructure/**` (ADAPTERS DE SAÍDA)**
- ✅ pode importar `app/application/ports/**` para implementar
- ✅ pode importar `app/domain/**` e `app/application/**` (DTOs) para mapear
- ✅ pode importar libs de DB/HTTP e código específico

**`app/api/**` (ADAPTER DE ENTRADA)**
- ✅ FastAPI e Pydantic
- ✅ `app/application/use_cases/**`
- ✅ `app/api/schemas/**`
- ❌ SQL direto
- ❌ regra de negócio/cálculo (isso fica no core)

### 3.2. Proibições explícitas
- `domain` e `application` (core) **nunca** importam `fastapi`, `pydantic`, `requests`, `httpx`, libs de banco, ou qualquer coisa de `infrastructure`.
- Routers/handlers (`app/api/**`) **nunca** escrevem SQL e **nunca** contêm regras de negócio.

> Se uma mudança exigir quebrar essas regras, a arquitetura está sendo violada e deve ser redesenhada.

---

## 4) Contratos (Ports) e Adapters

### 4.1. Ports (interfaces) – onde ficam e como escrever
- Ports ficam em: `app/application/ports/`
- Devem ser `Protocol` (typing) e pequenos/cohesos.
- Assinaturas devem falar em **DTOs/Domain** (não rows/tuplas/dicts crus).
- Ports representam o que o core **precisa** do mundo externo (DB, HTTP, cache) e/ou o que ele **oferece** (casos de uso, quando fizer sentido).

Exemplos (nomes ilustrativos):
- `PoolDataPort.get_pool_state(pool_id) -> PoolState`
- `TickDataPort.get_tick_snapshots(pool_id, start, end) -> list[TickSnapshot]`
- `PricePort.get_price(asset, at) -> PriceSnapshot`

### 4.2. Adapters (infra) – implementações
- Implementações ficam em `app/infrastructure/**`.
- Podem existir múltiplas implementações para o mesmo port:
  - `DbPoolDataAdapter` (SQL)
  - `SubgraphPoolDataAdapter` (HTTP)
  - `CachedPoolDataAdapter` (cache)

**Regra**: mudar query/schema/fonte de dados significa alterar **apenas** o adapter, mantendo o port estável.

### 4.3. Mapeamento obrigatório (rows → domain/dto)
- Queries SQL retornam rows/tuplas/dicts.
- Um `mapper` converte row → `domain/dto`.
- Use cases não devem receber “row do banco”.

---

## 5) Use Cases (Application Layer / Core)

### 5.1. Responsabilidade
Use case:
- coordena o fluxo (buscar dados via ports → chamar cálculo do domain → montar resposta)
- define transação/unidade de trabalho (se existir)
- valida invariantes de aplicação (ex.: input coerente, permissões, consistência de datas)

Use case **não**:
- faz SQL
- faz HTTP
- conhece Pydantic/FastAPI

### 5.2. Forma padrão
- Um arquivo por caso de uso em `app/application/use_cases/`
- Nomear como verbo + objeto: `simulate_apr.py`, `get_pool_details.py`
- Expor um método `execute(input: ...) -> output`
- Dependências entram por construtor (injeção)

### 5.3. Inputs/Outputs
- `api/schemas` (Pydantic) só existe na camada HTTP.
- `application/dto` (opcional) para entradas/saídas internas (dataclasses/TypedDict).
- O domínio não deve depender de DTOs HTTP.

---

## 6) Domain (Core / Regras de Negócio)

### 6.1. Onde fica o cálculo (APR etc.)
- Cálculos e políticas ficam em `app/domain/services/` (ou `value_objects/` quando fizer sentido).
- Preferir funções puras ou classes pequenas.

### 6.2. Regras para “não misturar cálculos”
- Um módulo deve ter **um tema** (ex.: `apr.py`, `fees.py`, `ticks.py`, `pricing.py`).
- Não juntar “APR + distribuição de liquidez + parsing de ticks + IO” no mesmo lugar.
- Se houver variações, separar por estratégia/arquivo (`apr_uniswap_v3.py`, `apr_v2.py`, etc.).

### 6.3. Sem dependência de infraestrutura
- Nada de env vars, DB, HTTP, caches.
- Domain deve ser testável sem mocks de infra (apenas dados de entrada).

---

## 7) API / FastAPI (Adapter de Entrada)

### 7.1. Responsabilidade
- Receber request
- Validar/parsear via Pydantic (`app/api/schemas`)
- Chamar use case
- Converter output em response
- Mapear exceções para HTTP

### 7.2. Proibições
- Router não escreve SQL.
- Router não chama DB direto.
- Router não implementa regra de negócio.

### 7.3. Padrão de versionamento de rota
- **Obrigatório**: todo endpoint HTTP deve usar prefixo de versão `/v1`.
- Mesmo que um prompt solicite outro padrão (ex.: `/api/...`), a implementação final no projeto deve seguir `/v1/...`.

---

## 8) Banco de Dados e SQL (Adapter de Saída)

- **Obrigatório**: acesso ao DB via **SQL nativo** (sem ORM), preservando a regra existente.
- SQL fica em `app/infrastructure/db/repositories/`.
- Repositórios SQL implementam ports da aplicação.

Regras:
1. Query deve ser isolada (função/método específico), sem lógica de negócio junto.
2. Transformação row → domain/dto via `mappers/`.
3. Sem “query espalhada” em múltiplos lugares para o mesmo caso de uso.
4. Fluxos com escrita (`insert`/`update`/`delete`) devem usar transação fim-a-fim no caso de uso/adapter e garantir rollback em qualquer erro.

---

## 9) Tratamento de Erros

### 9.1. Domain Exceptions
- `app/domain/exceptions.py`: exceções do negócio (ex.: `InvalidInput`, `PoolNotFound`, etc.)

### 9.2. Application Exceptions
- Use cases podem levantar exceções próprias (ex.: `Unauthorized`, `Conflict`) ou reaproveitar do domain.

### 9.3. API mapping
- `app/api/errors.py` faz o mapeamento para HTTP (status code + payload padrão).
- Não “printar” erro no meio do core.

---

## 10) Convenções de Nomeação e Tipagem

- PEP8, 4 espaços, type hints.
- `Protocol` para ports.
- DTOs:
  - `api/schemas`: Pydantic
  - `application/dto`: dataclasses/TypedDict (opcional), **sem** Pydantic
- Entidades/VOs no domain: dataclasses preferencialmente.

---

## 11) Padrão para Novas Atividades (o que o Codex deve gerar sempre)

Toda atividade (feature/bugfix/refactor) deve vir com:

1. **Objetivo (1–3 frases)**
2. **Ports envolvidos** (novos/alterados) + assinaturas
3. **Adapters envolvidos** (DB/HTTP/cache/API)
4. **Arquivos a criar/alterar** (lista)
5. **Passos pequenos** (idealmente 3–10 passos)
6. **Critérios de aceite** (bullets)
7. **Testes** (mesmo que mínimos)

### 11.1. Checklist obrigatório antes de finalizar uma entrega
- [ ] Core (`domain`/`application`) não importou FastAPI/Pydantic
- [ ] Core não importou `infrastructure`
- [ ] Router não tem regra de negócio
- [ ] SQL ficou apenas em `infrastructure/db`
- [ ] Cálculo de negócio está único e reutilizável
- [ ] Mudança de query/fonte não exigiria mexer no cálculo (port estável)
- [ ] Não foi implementado fallback no fluxo principal; ausência de dado obrigatório retorna erro explícito
- [ ] Todo fluxo com `insert`/`update`/`delete` está transacional e com rollback garantido em caso de erro

---

## 12) Documentação de API
- Qualquer endpoint novo ou alterado deve ser documentado em `API.md` com:
  - rota, método
  - exemplo de request/response
  - erros possíveis

---

## 13) Prompts (processo interno)
- Prompts só são considerados finalizados quando o usuário disser explicitamente.
- Quando finalizados, mover de `prompts_pendentes/` para `prompts_processados/`.

---

## 14) Build/Dev
- `python -m venv env && source env/bin/activate`
- `pip install -r requirements.txt`
- `./runme.sh` (ou `uvicorn app.main:app --reload`)

---

## 15) Response Language
- Sempre responder em **Português**.
