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

## Endpoints (a definir)
- `POST /v1/allocate` (principal, autenticado).
- Simulacoes de APR (rotas, payloads e respostas em definicao).
- Consultas auxiliares de pools, tokens e precos (se necessario).

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
  "tick_range": 6000,
  "range_min": 2833.5,
  "range_max": 3242.4
}
```

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
