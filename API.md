# API de Simulacoes de APR (LP)

## Visao geral
- API em FastAPI para simulacoes de APR em pools de liquidez.
- Apenas usuarios autenticados podem acessar as rotas.
- Versionamento por prefixo: `/v1`.

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
- `POST /api/liquidity-distribution` (alias: `/v1/liquidity-distribution`).
- `GET /api/pool-price`.
- `POST /api/estimated-fees`.
- `GET /v1/exchanges`.
- `GET /v1/exchanges/{exchange_id}/networks`.
- `GET /v1/exchanges/{exchange_id}/networks/{network_id}/tokens`.
- `GET /v1/exchanges/{exchange_id}/networks/{network_id}/pools`.
- `GET /v1/pools/by-address/{pool_address}`.
- `POST /v1/match-ticks`.

## POST /v1/allocate
Entrada:
```json
{
  "pool_address": "0xe1f083255e2133ef143f3c264611cfabb6133f9a",
  "rede": "arbitrum",
  "amount": "1000",
  "range1": "2500",
  "range2": "3500"
}
```

Notas:
- `range1` e `range2` devem ser informados como **preco do token0 em unidades de token1**
  (ex.: WETH/USDT = 2932.21).

Resposta:
```json
{
  "pool_id": 1,
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

## POST /api/liquidity-distribution
Alias: `/v1/liquidity-distribution`.
Entrada:
```json
{
  "pool_id": 572,
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
- Quando `center_tick` nao e informado, o `current_tick` e calculado pelo banco usando `pool_hours`.

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

## GET /api/pool-price
Query params:
- `pool_id` (int)
- `days` (int, > 0) ou `start` + `end` (ISO timestamp)

Exemplo:
`/api/pool-price?pool_id=572&days=30`

Exemplo (pan):
`/api/pool-price?pool_id=572&start=2025-01-01T00:00:00Z&end=2025-01-31T00:00:00Z`

Notas:
- O `price` atual usa o ultimo snapshot de `pool_hours` (token0_price, com fallback para sqrt_price_x96).

Resposta:
```json
{
  "pool_id": 572,
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

## POST /api/estimated-fees
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

Resposta:
```json
{
  "estimated_fees_24h": "12.34",
  "monthly": { "value": "370.2", "percent": "3.7" },
  "yearly": { "value": "4500.0", "apr": "0.45" }
}
```

## GET /v1/exchanges
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
- `network` (string).
- `exchange_id` (int).

Exemplo:
`/v1/pools/by-address/0x...?network=arbitrum&exchange_id=1`

Resposta:
```json
{
  "id": 572,
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

Resposta:
```json
{
  "min_price_matched": 2832.97,
  "max_price_matched": 3244.11,
  "current_price_matched": 2952.38
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
