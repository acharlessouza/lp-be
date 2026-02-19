# API de Simulacoes de APR (LP)

## Visao geral
- API em FastAPI para simulacoes de APR em pools de liquidez.
- Apenas usuarios autenticados podem acessar as rotas.
- Versionamento por prefixo: `/v1` e `/v2` (v2 atualmente disponivel para simulacao de APR exata).

## Autenticacao
- JWT via `Authorization: Bearer <token>`.
- Endpoint de login (publico, unico sem autenticacao):
  - `POST /v1/auth/login`
- Demais endpoints exigem JWT valido.

## Observabilidade e logging
- Logs estruturados (JSON) com `request_id` e `user_id` quando disponivel.
- Middleware para correlacao de requests.
- Metricas e traces (OpenTelemetry) planejados.

## Padrao de resposta de erro
```json
{
  "error": {
    "code": "string",
    "message": "string",
    "details": {}
  }
}
```

## Endpoints
- `POST /v1/allocate` (principal, autenticado).
- `POST /v1/liquidity-distribution`.
- `POST /v1/liquidity-distribution/default-range`.
- `GET /v1/pool-price`.
- `GET /v1/pools/{pool_address}/volume-history`.
- `POST /v1/estimated-fees`.
- `POST /v1/simulate/apr`.
- `POST /v2/simulate/apr`.
- `GET /v1/exchanges`.
- `GET /v1/exchanges/{exchange_id}/networks`.
- `GET /v1/exchanges/{exchange_id}/networks/{network_id}/tokens`.
- `GET /v1/exchanges/{exchange_id}/networks/{network_id}/pools`.
- `GET /v1/pools/by-address/{pool_address}`.
- `POST /v1/match-ticks`.
- `GET /v1/discover/pools`.

## POST /v1/allocate
Entrada:
```json
{
  "pool_address": "0xe1f083255e2133ef143f3c264611cfabb6133f9a",
  "chain_id": 2,
  "dex_id": 1,
  "amount": "1000",
  "full_range": false,
  "range1": "2500",
  "range2": "3500"
}
```

Notas:
- `full_range=true` ativa alocacao Full Range e o split e aproximado de 50/50 em valor USD.
- Com `full_range=true`, `range1` e `range2` sao opcionais.
- `range1` e `range2` devem ser informados como **preco do token0 em unidades de token1**
  (ex.: WETH/USDT = 2932.21) quando `full_range=false`.
- Implementacao interna segue arquitetura Hexagonal:
  - adapter HTTP em `app/api/routers/allocate.py`
  - use case em `app/application/use_cases/allocate.py`
  - regra de negocio em `app/domain/services/allocation.py`
  - adapters de saida em `app/infrastructure/**`

Resposta:
```json
{
  "pool_address": "0x...",
  "rede": "arbitrum",
  "taxa": 500,
  "token0_address": "0x...",
  "token0_symbol": "WETH",
  "token1_address": "0x...",
  "token1_symbol": "USDC",
  "amount_token0": "400.12",
  "amount_token1": "0.20",
  "price_token0_usd": "1",
  "price_token1_usd": "3000"
}
```

## POST /v1/liquidity-distribution
Entrada:
```json
{
  "pool_id": "0x4e68ccd3e89f51c3074ca5072bbac773960dfa36",
  "chain_id": 2,
  "dex_id": 1,
  "snapshot_date": "2025-12-24",
  "current_tick": 0,
  "center_tick": -198000,
  "tick_range": 6000,
  "range_min": 2833.5,
  "range_max": 3242.4
}
```

Notas:
- Use `center_tick` para pan (mover o centro do gráfico).
- Ajuste `tick_range` para zoom (janela maior/menor).
- `pool_id` aceita ID numerico legado ou `pool_address` (`0x...`).
- Se usar `pool_address`, `chain_id` e `dex_id` ajudam a desambiguar quando houver mais de uma pool com o mesmo endereco.
- O endpoint usa o ultimo `snapshot_at` disponivel em `public.pool_state_snapshots`.
- Quando `center_tick` nao e informado, o `current_tick` vem de `public.pool_state_snapshots.tick` (fallback: `public.pools.tick`).
- `snapshot_date` e ignorado neste fluxo.
- A liquidez plotada e a soma acumulada de `liquidity_net` (`public.pool_ticks_initialized`) ancorada na liquidez onchain (`public.pool_state_snapshots.liquidity`, fallback `public.pools.liquidity`).
- Implementacao interna segue arquitetura Hexagonal:
  - adapter HTTP em `app/api/routers/liquidity_distribution.py`
  - use case em `app/application/use_cases/get_liquidity_distribution.py`
  - regra de dominio em `app/domain/services/liquidity_distribution.py`
  - SQL em `app/infrastructure/db/repositories/liquidity_distribution_repository.py`

Erros possiveis:
- `400` quando parametros forem invalidos.
- `404` quando pool nao existir ou nao houver snapshot/liquidez disponivel.

Resposta:
```json
{
  "pool": { "token0": "WETH", "token1": "USDT" },
  "current_tick": -198000,
  "data": [
    { "tick": -198120, "liquidity": "2226...", "price": 2927.79 }
  ]
}
```

## POST /v1/liquidity-distribution/default-range
Entrada:
```json
{
  "pool_id": "0x4e68ccd3e89f51c3074ca5072bbac773960dfa36",
  "chain_id": 1,
  "dex_id": 1,
  "snapshot_date": "2026-02-16",
  "preset": "wide",
  "initial_price": 3021.11,
  "center_tick": null,
  "swapped_pair": false
}
```

Notas:
- `pool_id` aceita ID numerico legado ou `pool_address` (`0x...`).
- Se usar `pool_address`, `chain_id` e `dex_id` sao usados para desambiguar.
- `snapshot_date` e ignorado neste fluxo (o endpoint usa o ultimo snapshot disponivel).
- `preset` aceita:
  - `stable`: faixa estreita em torno do tick atual (`+- 3 * tick_spacing`).
  - `wide`: faixa percentual (`-50% / +100%`) com alinhamento para ticks utilizaveis.
  - valor padrao: `stable`.
- `initial_price` e opcional. Se nao for enviado, a API tenta derivar de `pools.price_token0_per_token1` e, como fallback, do tick atual.
- `center_tick` e opcional. Se enviado, substitui o tick atual da pool para o calculo.
- `tick_spacing` e obtido automaticamente da pool; fallback por `fee_tier` (100->1, 500->10, 3000->60, 10000->200).
- Quando `swapped_pair=true`, os precos retornados sao invertidos (`1/price`) e ordenados.
- Implementacao interna segue arquitetura Hexagonal:
  - adapter HTTP em `app/api/routers/liquidity_distribution.py`
  - use case em `app/application/use_cases/get_liquidity_distribution_default_range.py`
  - regra de dominio em `app/domain/services/liquidity_distribution_default_range.py`
  - SQL em `app/infrastructure/db/repositories/liquidity_distribution_repository.py`

Erros possiveis:
- `400` quando parametros forem invalidos.
- `404` quando pool nao existir.

Resposta:
```json
{
  "min_price": 2833.5,
  "max_price": 3242.4,
  "min_tick": -198120,
  "max_tick": -196880,
  "tick_spacing": 60
}
```

## GET /v1/pool-price
Query params:
- `pool_address` (string)
- `chain_id` (int)
- `dex_id` (int)
- `days` (int, > 0) ou `start` + `end` (ISO timestamp)

Exemplo:
`/v1/pool-price?pool_address=0x...&chain_id=2&dex_id=1&days=30`

Exemplo (pan):
`/v1/pool-price?pool_address=0x...&chain_id=2&dex_id=1&start=2025-01-01T00:00:00Z&end=2025-01-31T00:00:00Z`

Notas:
- O `price` atual usa o ultimo snapshot de `pool_state_snapshots` (fallback em `pools.price_token0_per_token1` / `pools.sqrt_price_x96`).
- Implementacao interna segue arquitetura Hexagonal:
  - adapter HTTP em `app/api/routers/pool_price.py`
  - use case em `app/application/use_cases/get_pool_price.py`
  - regra de dominio em `app/domain/services/pool_price.py`
  - SQL em `app/infrastructure/db/repositories/pool_price_repository.py`

Erros possiveis:
- `400` quando parametros forem invalidos (`days`, `start/end`).
- `404` quando pool nao existir ou nao houver preco atual para a pool.

Resposta:
```json
{
  "pool_address": "0x...",
  "days": 30,
  "stats": {
    "min": "2850.12",
    "max": "3150.55",
    "avg": "2999.98",
    "price": "3021.11"
  },
  "series": [
    { "timestamp": "2025-01-01T00:00:00", "price": "2950.11" }
  ]
}
```

## POST /v1/estimated-fees
Entrada:
```json
{
  "pool_id": 572,
  "days": 30,
  "min_price": "2800",
  "max_price": "3300",
  "deposit_usd": "10000",
  "amount_token0": "1.2",
  "amount_token1": "0"
}
```

Notas:
- O calculo de preco atual usa o ultimo snapshot de `pool_hours` (token0_price, com fallback para sqrt_price_x96).
- Implementacao interna segue arquitetura Hexagonal:
  - adapter HTTP em `app/api/routers/estimated_fees.py`
  - use case em `app/application/use_cases/estimate_fees.py`
  - regra de dominio em `app/domain/services/estimated_fees.py`
  - SQL em `app/infrastructure/db/repositories/estimated_fees_repository.py`

Erros possiveis:
- `400` quando parametros forem invalidos.
- `404` quando pool nao existir ou nao houver preco atual para a pool.

Resposta:
```json
{
  "estimated_fees_24h": "12.34",
  "monthly": { "value": "370.2", "percent": "3.7" },
  "yearly": { "value": "4500.0", "apr": "0.45" }
}
```

## GET /v1/pools/{pool_address}/volume-history
Query params:
- `days` (obrigatorio): quantidade de dias fechados (UTC) a retornar.
- `chainId` (opcional): filtra por chain quando informado.
- `dexId` (opcional): filtra por dex quando informado.
- `includePremium` (opcional, default `false`): mantido por compatibilidade.
- `exchange` (opcional, default `binance`): mantido por compatibilidade.
- `symbol0` e `symbol1` (opcionais): mantidos por compatibilidade.

Regras:
- Considera apenas dias fechados (UTC), excluindo o dia atual.
- Janela temporal: `start = today_utc - days`, `end = today_utc` (end exclusivo).
- Agregacao por dia UTC em `public.pool_hourly`:
  - `value = SUM(volume_usd)`
  - `fees_usd = SUM(COALESCE(fees_usd, 0))`
- `price_volatility_pct`, `correlation` e `geometric_mean_price` retornam sempre `null`.
- Retorna `200` com `[]` quando nao houver dados no periodo.

Erros possiveis:
- `400` quando `days` for invalido (`< 1` ou `> 365`) ou parametros invalidos.

Exemplo cURL:
```bash
curl "http://localhost:8000/v1/pools/0x4e68ccd3e89f51c3074ca5072bbac773960dfa36/volume-history?days=7&chainId=1&dexId=2" \
  -H "Authorization: Bearer <token>"
```

Resposta:
```json
{
  "volume_history": [
    { "time": "2026-02-09", "value": "9823.45", "fees_usd": "29.47" },
    { "time": "2026-02-10", "value": "12345.67", "fees_usd": "37.04" }
  ],
  "summary": {
    "tvl_usd": "61380000.00",
    "avg_daily_fees_usd": "150720.00",
    "daily_fees_tvl_pct": "0.2456",
    "avg_daily_volume_usd": "50240000.00",
    "daily_volume_tvl_pct": "81.86",
    "price_volatility_pct": null,
    "correlation": null,
    "geometric_mean_price": null
  }
}
```

Indice sugerido (se ainda nao existir):
```sql
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pool_hourly_pool_time
ON public.pool_hourly (pool_address, hour_start);
```

## POST /v1/simulate/apr
Entrada:
```json
{
  "pool_address": "0x4e68ccd3e89f51c3074ca5072bbac773960dfa36",
  "chain_id": 1,
  "dex_id": 2,
  "deposit_usd": "10000",
  "amount_token0": "1.2",
  "amount_token1": "0",
  "full_range": false,
  "tick_lower": -201000,
  "tick_upper": -195000,
  "min_price": null,
  "max_price": null,
  "horizon": "14d",
  "mode": "B",
  "calculation_method": "current",
  "custom_calculation_price": null,
  "lookback_days": 14
}
```

Notas:
- A pool e resolvida por `pool_address + chain_id + dex_id`.
- `full_range=true` habilita simulacao Full Range (Uniswap v3) e nao exige `tick_lower/tick_upper` nem `min_price/max_price`.
- Informe range por ticks (`tick_lower`/`tick_upper`) ou por preco (`min_price`/`max_price`).
- Em `full_range=true`, os ticks sao derivados de `MIN_TICK=-887272` e `MAX_TICK=887272`, alinhados por `tick_spacing`.
- `horizon` e dinamico: aceita valores positivos como `24h`, `7d`, `14d`, `30d` (ou numero sem sufixo, interpretado como dias).
- `mode=A` usa tick atual constante em todas as horas.
- `mode=B` usa caminho horario de ticks por snapshots; se faltar snapshot em alguma hora, o calculo cai para tick atual nessa hora e retorna warning.
- O share horario prioriza `pool_state_snapshots.liquidity` por hora (UTC). Quando faltar, usa fallback controlado.
- `calculation_method` aceita:
  - `current` (Current Price)
  - `avg_liquidity_in_range` (Average Liquidity In-Range)
  - `peak_liquidity_in_range` (Peak of Distribution In-Range)
  - `custom` (Custom Price)
- Quando `calculation_method=custom`, `custom_calculation_price` e obrigatorio e deve ser > 0.
- Se `deposit_usd` nao vier, a API tenta derivar a partir de `amount_token0/amount_token1` com preco atual da pool.
- Se vier apenas `deposit_usd` (sem amounts), a API deriva `amount_token0/amount_token1` via preco atual (split 50/50) para calcular liquidez da posicao.
- Implementacao interna segue arquitetura Hexagonal:
  - adapter HTTP em `app/api/routers/simulate_apr.py`
  - use case em `app/application/use_cases/simulate_apr.py`
  - regras de dominio em `app/domain/services/univ3_math.py`, `app/domain/services/liquidity.py` e `app/domain/services/apr_simulation.py`
  - SQL em `app/infrastructure/db/repositories/simulate_apr_repository.py`

Erros possiveis:
- `400` quando parametros forem invalidos.
- `404` quando pool nao existir ou faltarem dados para a simulacao.

Resposta:
```json
{
  "estimated_fees_24h_usd": "12.34",
  "monthly_usd": "370.20",
  "yearly_usd": "4500.00",
  "fee_apr": "0.45"
}
```

## POST /v2/simulate/apr
Entrada:
```json
{
  "pool_address": "0x4e68ccd3e89f51c3074ca5072bbac773960dfa36",
  "chain_id": 1,
  "dex_id": 2,
  "deposit_usd": "10000",
  "amount_token0": "1.2",
  "amount_token1": "0",
  "full_range": false,
  "tick_lower": -201000,
  "tick_upper": -195000,
  "min_price": null,
  "max_price": null,
  "horizon": "7d",
  "lookback_days": 7,
  "calculation_method": "current",
  "custom_calculation_price": null,
  "apr_method": "exact"
}
```

Notas:
- Endpoint v2 usa metodo exato por bloco (Uniswap v3 `feeGrowthInside`), com snapshot mais recente como bloco `B` e snapshot de lookback como bloco `A`.
- Fonte principal: `public.pool_state_snapshots` para estados A/B e `apr_exact.tick_snapshot` para `fee_growth_outside` nos ticks `lower/upper` em A/B.
- Quando algum tick obrigatorio (A/B x lower/upper) nao existe em `apr_exact.tick_snapshot`, a API dispara um fluxo on-demand: consulta o subgraph somente para os combos faltantes (maximo configuravel, default 4), faz upsert no banco e reprocessa.
- Guardrails do on-demand: timeout configuravel, retry com backoff exponencial e rate-limit minimo entre chamadas.
- Se faltarem snapshots/ticks obrigatorios, retorna erro explicito (`404`) sem fallback silencioso.
- Implementacao interna segue arquitetura Hexagonal:
  - adapter HTTP em `app/api/routers/simulate_apr_v2.py`
  - use case em `app/application/use_cases/simulate_apr_v2.py`
  - regra de dominio em `app/domain/services/univ3_fee_growth.py`
  - SQL em `app/infrastructure/db/repositories/simulate_apr_v2_repository.py`

Erros possiveis:
- `400` quando parametros forem invalidos.
- `404` quando faltarem dados para simulacao exata (snapshots/ticks/lookback).

Resposta:
```json
{
  "estimated_fees_period_usd": "0.84",
  "estimated_fees_24h_usd": "1.10",
  "monthly_usd": "33.45",
  "yearly_usd": "401.40",
  "fee_apr": "0.0401",
  "meta": {
    "block_a_number": 22001111,
    "block_b_number": 22011111,
    "ts_a": 1739664000,
    "ts_b": 1740268800,
    "seconds_delta": 604800,
    "used_price": "3021.11",
    "warnings": []
  }
}
```

## GET /v1/exchanges
Notas:
- Implementacao interna segue arquitetura Hexagonal:
  - router em `app/api/routers/catalog.py`
  - use cases em `app/application/use_cases/*`
  - SQL em `app/infrastructure/db/repositories/catalog_query_repository.py`

Resposta:
```json
[
  { "id": 1, "name": "uniswap" },
  { "id": 2, "name": "sushiswap" }
]
```

## GET /v1/exchanges/{exchange_id}/networks
Resposta:
```json
[
  { "id": 1, "name": "ethereum" },
  { "id": 2, "name": "arbitrum" }
]
```

## GET /v1/exchanges/{exchange_id}/networks/{network_id}/tokens
Query params (opcional):
- `token` (address) filtra por pools que contenham o token informado.

Resposta:
```json
[
  { "address": "0x...", "symbol": "WETH", "decimals": 18 },
  { "address": "0x...", "symbol": "USDC", "decimals": 6 }
]
```

## GET /v1/exchanges/{exchange_id}/networks/{network_id}/pools
Query params:
- `token0` (address)
- `token1` (address)

Exemplo:
`/v1/exchanges/1/networks/2/pools?token0=0x...&token1=0x...`

Resposta:
```json
[
  { "pool_address": "0x...", "fee_tier": 500 },
  { "pool_address": "0x...", "fee_tier": 3000 }
]
```

## GET /v1/pools/by-address/{pool_address}
Query params:
- `chain_id` (int).
- `exchange_id` (int).

Exemplo:
`/v1/pools/by-address/0x...?chain_id=2&exchange_id=1`

Resposta:
```json
{
  "id": "0x...",
  "dex_key": "uniswap-v3",
  "dex_name": "Uniswap",
  "dex_version": "v3",
  "chain_key": "arbitrum",
  "chain_name": "Arbitrum",
  "fee_tier": 500,
  "token0_address": "0x...",
  "token0_symbol": "WETH",
  "token0_decimals": 18,
  "token1_address": "0x...",
  "token1_symbol": "USDC",
  "token1_decimals": 6
}
```

## POST /v1/match-ticks
Entrada:
```json
{
  "pool_id": 572,
  "min_price": 2833.5,
  "max_price": 3242.4
}
```

Notas:
- Implementacao interna segue arquitetura Hexagonal:
  - adapter HTTP em `app/api/routers/match_ticks.py`
  - use case em `app/application/use_cases/match_ticks.py`
  - regra de dominio em `app/domain/services/match_ticks.py`
  - SQL em `app/infrastructure/db/repositories/match_ticks_repository.py`

Erros possiveis:
- `400` quando parametros forem invalidos.
- `404` quando pool nao existir ou nao houver preco atual.

Resposta:
```json
{
  "min_price_matched": 2832.97,
  "max_price_matched": 3244.11,
  "current_price_matched": 2952.38
}
```

## GET /v1/discover/pools
Query params:
- `network_id` (int, opcional)
- `exchange_id` (int, opcional)
- `token_symbol` (string, opcional)
- `timeframe_days` (int, 1-365, default 14)
- `page` (int, default 1)
- `page_size` (int, 1-100, default 10)
- `order_by` (pool_id | pool_address | pool_name | network | exchange | fee_tier | average_apr | price_volatility | tvl_usd | correlation | avg_daily_fees_usd | daily_fees_tvl_pct | avg_daily_volume_usd | daily_volume_tvl_pct)
- `order_dir` (asc | desc, default desc)

Exemplo:
`/v1/discover/pools?network_id=2&exchange_id=1&token_symbol=USDC&timeframe_days=30&page=1&page_size=10&order_by=average_apr&order_dir=desc`

Notas:
- Implementacao interna segue arquitetura Hexagonal:
  - adapter HTTP em `app/api/routers/discover_pools.py`
  - use case em `app/application/use_cases/discover_pools.py`
  - regra de dominio em `app/domain/services/discover_pools.py`
  - SQL em `app/infrastructure/db/repositories/discover_pools_repository.py`

Erros possiveis:
- `400` quando filtros/ordenacao/paginacao forem invalidos.

Resposta:
```json
{
  "page": 1,
  "page_size": 10,
  "total": 2,
  "data": [
    {
      "pool_id": 572,
      "pool_address": "0x...",
      "pool_name": "WETH / USDC",
      "network": "arbitrum",
      "exchange": "uniswap",
      "fee_tier": 500,
      "average_apr": "12.34",
      "price_volatility": null,
      "tvl_usd": "1234567.89",
      "correlation": null,
      "avg_daily_fees_usd": "123.45",
      "daily_fees_tvl_pct": "0.0001",
      "avg_daily_volume_usd": "9876.54",
      "daily_volume_tvl_pct": "0.0080"
    }
  ]
}
```

## Precificacao de tokens
- A API consulta o preco atual por `token` + `rede`.
- Prioridade:
  1) `PRICE_OVERRIDES` (JSON via env, por rede ou `default`).
  2) Coingecko por endereco (`0x...`) se nao houver override.
- Exemplo de override:
  - `PRICE_OVERRIDES={"polygon":{"usdc":"1","weth":"3000"}}`

## Itens em aberto
- Escopo exato das simulacoes e parametros de entrada.
- Politica de expiracao/refresh de JWT.
- Limites de rate e quotas por usuario.
