
PROMPT PARA CODEX — ENDPOINT DISCOVER (LIQUIDITY POOLS)

Objetivo:
Criar endpoint backend simples para alimentar a tela Discover.

Stack:
- Python
- FastAPI
- PostgreSQL
- SQL puro (sem ORM)

Endpoint:
GET /api/discover/pools

Query params:
- network
- exchange
- timeframe_days (default 14)
- page (default 1)
- page_size (default 10)
- order_by
- order_dir

Tabelas:
- pools
- pool_hours

Query SQL simples:
- JOIN pools + pool_hours
- SUM, AVG, COUNT
- GROUP BY pool

Cálculos no Python:
- average_apr
- daily_fees_tvl_pct
- daily_volume_tvl_pct

Paginação e ordenação feitas no Python.

Response JSON:
Mesmo contrato definido no prompt do frontend.

Objetivo final:
Endpoint simples, performático e fácil de evoluir.
