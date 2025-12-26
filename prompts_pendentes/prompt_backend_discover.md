
PROMPT PARA CODEX — BACKEND ENDPOINT DISCOVER (LIQUIDITY POOLS)

Objetivo:
Implementar o endpoint GET /api/discover/pools responsável por alimentar a tela Discover (Liquidity Pools).

Regras obrigatórias:
- SQL simples (JOIN + filtros + SUM / AVG / COUNT + GROUP BY)
- Cálculos derivados exclusivamente no Python
- Sem ORM
- Sem APIs externas
- Sem CTEs ou subqueries complexas

Tabelas assumidas:
pools:
- id
- pool_address
- token0_symbol
- token1_symbol
- fee_tier
- exchange_id
- network_id

pool_hours:
- pool_id
- period_start
- tvl_usd
- fees_usd
- volume_usd
- token0_price
- token1_price

networks:
- id
- name

exchanges:
- id
- name

Endpoint:
GET /api/discover/pools

Query params:
- network: string | null
- exchange: string | null
- timeframe_days: int = 14
- page: int = 1
- page_size: int = 10 (máx 100)
- order_by: string = "average_apr"
- order_dir: "asc" | "desc"

Contrato de resposta:
{
  "page": number,
  "page_size": number,
  "total": number,
  "data": [
    {
      "pool_id": number,
      "pool_address": string,
      "pool_name": string,
      "network": string,
      "exchange": string,
      "fee_tier": number,
      "average_apr": number,
      "price_volatility": number | null,
      "tvl_usd": number,
      "correlation": number | null,
      "avg_daily_fees_usd": number,
      "daily_fees_tvl_pct": number,
      "avg_daily_volume_usd": number,
      "daily_volume_tvl_pct": number
    }
  ]
}

Janela de tempo:
Calcular no Python:
start_dt = now_utc - timedelta(days=timeframe_days)

SQL base:
SELECT
  p.id AS pool_id,
  p.pool_address,
  n.name AS network_name,
  e.name AS exchange_name,
  p.token0_symbol,
  p.token1_symbol,
  p.fee_tier,
  AVG(ph.tvl_usd) AS avg_tvl_usd,
  SUM(ph.fees_usd) AS total_fees_usd,
  AVG(ph.fees_usd) AS avg_hourly_fees_usd,
  AVG(ph.volume_usd) AS avg_hourly_volume_usd,
  COUNT(*) AS samples
FROM pools p
JOIN pool_hours ph ON ph.pool_id = p.id
JOIN networks n ON n.id = p.network_id
JOIN exchanges e ON e.id = p.exchange_id
WHERE ph.period_start >= %(start_dt)s
  AND (%(network)s IS NULL OR n.name = %(network)s)
  AND (%(exchange)s IS NULL OR e.name = %(exchange)s)
GROUP BY
  p.id, p.pool_address, n.name, e.name, p.token0_symbol, p.token1_symbol, p.fee_tier;

Cálculos no Python:
- tvl_usd = avg_tvl_usd
- avg_daily_fees_usd = avg_hourly_fees_usd * 24
- avg_daily_volume_usd = avg_hourly_volume_usd * 24
- daily_fees_tvl_pct = avg_daily_fees_usd / tvl_usd (se tvl_usd > 0)
- daily_volume_tvl_pct = avg_daily_volume_usd / tvl_usd (se tvl_usd > 0)
- average_apr = (total_fees_usd / tvl_usd) * (365 / timeframe_days) * 100
- pool_name = "{token0_symbol} / {token1_symbol}"
- price_volatility = null
- correlation = null

Ordenação:
- Feita no Python
- Campos permitidos:
  average_apr, tvl_usd, avg_daily_fees_usd,
  avg_daily_volume_usd, daily_fees_tvl_pct,
  daily_volume_tvl_pct

Paginação:
- Feita no Python após ordenação
- offset = (page - 1) * page_size

Validações:
- timeframe_days entre 1 e 365
- page >= 1
- page_size entre 1 e 100
- order_dir apenas asc ou desc

Objetivo final:
Endpoint simples, previsível, fácil de manter e pronto para alimentar o frontend Discover.
