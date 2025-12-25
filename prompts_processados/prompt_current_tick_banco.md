# Prompt – Obter `current_tick` usando apenas dados do banco

## Objetivo
Calcular o `current_tick` de uma pool Uniswap v3 **sem consultar subgraph ou RPC**, utilizando apenas dados já armazenados no banco de dados.

O cálculo deve:
- Usar **SQL simples** para buscar o último estado da pool
- Executar **apenas contas no Python** para derivar o tick

---

## Premissas

- Existe uma tabela `pool_hours` com snapshots horários da pool
- O campo `sqrt_price_x96` está armazenado e representa o estado do preço no momento do snapshot
- O último snapshot representa o estado mais recente disponível

---

## SQL (simples)

Buscar o snapshot mais recente da pool:

```sql
SELECT
    sqrt_price_x96
FROM pool_hours
WHERE pool_id = :pool_id
ORDER BY period_start DESC
LIMIT 1;
```

Parâmetro:
- `:pool_id` → ID interno da pool

---

## Cálculo do tick (Python)

Definições matemáticas do Uniswap v3:

- `price = (sqrtPriceX96 / 2^96)²`
- `tick = floor( log(price) / log(1.0001) )`

Implementação:

```python
import math
from decimal import Decimal, getcontext

getcontext().prec = 50

Q96 = Decimal(2) ** 96


def tick_from_sqrt_price_x96(sqrt_price_x96: int) -> int:
    sqrt_price = Decimal(sqrt_price_x96) / Q96
    price = sqrt_price ** 2
    tick = math.floor(math.log(price) / math.log(1.0001))
    return tick
```

---

## Fluxo completo

1. Executar a query SQL para obter o `sqrt_price_x96` mais recente
2. Converter o valor para `int`
3. Calcular o `current_tick` usando a função Python

Exemplo:

```python
row = fetch_one(sql, {"pool_id": pool_id})

current_tick = tick_from_sqrt_price_x96(
    int(row["sqrt_price_x96"])
)
```

---

## Observações importantes

- O tick calculado representa o **estado mais recente disponível no banco**, não necessariamente o estado on-chain atual
- Para simulações, ranges concentrados e funcionalidade de *match ticks*, a precisão é suficiente
- Diferença esperada em relação ao subgraph: geralmente ≤ 1 tick

---

## Resultado esperado

O backend deve retornar:

```json
{
  "current_tick": 123456
}
```

Sem qualquer dependência externa (subgraph, RPC ou APIs).

