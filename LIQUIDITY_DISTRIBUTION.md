# Plano: Endpoint Liquidity Distribution (tick ativo)

## Objetivo
Expor um endpoint autenticado que retorna a **liquidez ativa por tick** e o
**preco derivado do tick**, seguindo o modelo Uniswap v3 / Metrix.

## Dependencias de dados
- Tabela `tick_snapshots` populada.
- Ingestao: `ACTIVE_POOLS_ONLY=false` e `STORE_TICKS=1`.
- Rodar: `python -m lp_jobs.app.main ingest --only ticks`.

## Requisicao
`POST /api/liquidity-distribution` (alias: `/v1/liquidity-distribution`)

Body:
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

Campos:
- `pool_id`: ID da pool no Postgres.
- `snapshot_date`: data do snapshot (YYYY-MM-DD).
- `current_tick`: requerido pelo contrato da API, mas o valor real vem do subgraph.
- `tick_range`: faixa de ticks ao redor do current tick.
- `range_min`/`range_max`: faixa de preco para destaque visual no frontend.

## Consulta base (SQL nativo)
- Liquidez ativa por tick via soma acumulada (`SUM(liquidity_net) OVER`).
- Preco derivado do tick:
  - `exp(tick * ln(1.0001)) * 10^(token0_decimals - token1_decimals)`.
- Filtragem por range: `tick_idx BETWEEN current_tick - tick_range AND current_tick + tick_range`.

## Resposta
```json
{
  "pool": { "token0": "WETH", "token1": "USDT" },
  "current_tick": -198000,
  "data": [
    { "tick": -198120, "liquidity": "2226...", "price": 2927.79 }
  ]
}
```

## Consideracoes
- O `current_tick` e obtido via subgraph oficial da Uniswap v3.
- Se nao houver dados no snapshot, retornar 404.
