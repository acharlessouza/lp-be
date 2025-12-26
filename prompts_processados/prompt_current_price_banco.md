# Prompt – Substituir `get_current_price` usando apenas dados do banco

## Objetivo
Substituir o método `get_current_price` que hoje consulta o subgraph da Uniswap por uma implementação que utilize **apenas dados já armazenados no banco de dados**, sem chamadas externas (subgraph ou RPC).

O resultado deve ser **funcionalmente equivalente** ao campo `token1Price` retornado pelo subgraph.

---

## Comportamento atual (referência)

O método atual retorna:

- `token1Price` da pool
- Significado: **preço de 1 token0 expresso em token1**

Exemplo (WETH / USDT):
- Retorno ≈ `2952`
- Interpretação: `1 WETH = 2952 USDT`

---

## Premissas do banco

Existe a tabela `pool_hours` com as colunas:

- `token0_price` → preço de token0 em token1
- `token1_price` → preço de token1 em token0
- `sqrt_price_x96` → estado canônico do preço

A ingestão segue a convenção do subgraph Uniswap v3:

```
 token0_price * token1_price ≈ 1
```

---

## SQL (simples)

Buscar o snapshot mais recente da pool:

```sql
SELECT
    token0_price
FROM pool_hours
WHERE pool_id = :pool_id
ORDER BY period_start DESC
LIMIT 1;
```

Parâmetro:
- `:pool_id` → ID interno da pool

---

## Implementação Python (substituição direta)

```python
from decimal import Decimal


def get_current_price_from_db(pool_id: int) -> Decimal:
    row = fetch_one(SQL_GET_CURRENT_PRICE, {"pool_id": pool_id})

    if not row or row["token0_price"] is None:
        raise ValueError("Pool price not found in database.")

    return Decimal(row["token0_price"])
```

Este método é **equivalente 1:1** ao retorno do `token1Price` do subgraph.

---

## Alternativa canônica (opcional)

Caso seja desejável eliminar dependência de colunas derivadas, o preço pode ser calculado a partir de `sqrt_price_x96`.

### SQL

```sql
SELECT
    sqrt_price_x96
FROM pool_hours
WHERE pool_id = :pool_id
ORDER BY period_start DESC
LIMIT 1;
```

### Python

```python
from decimal import Decimal, getcontext

getcontext().prec = 50
Q96 = Decimal(2) ** 96


def price_from_sqrt_price_x96(sqrt_price_x96: int) -> Decimal:
    sqrt_price = Decimal(sqrt_price_x96) / Q96
    return sqrt_price ** 2  # token1 / token0
```

---

## Fluxo completo sugerido

1. Buscar o snapshot mais recente da pool via SQL
2. Retornar `token0_price` como preço atual
3. Usar `sqrt_price_x96` apenas como fallback ou validação

---

## Resultado esperado

O backend deve retornar:

```json
{
  "current_price": "2952.386222899943"
}
```

Sem qualquer dependência de subgraph, RPC ou APIs externas.

---

## Observações

- O valor retornado representa o **estado mais recente disponível no banco**, não necessariamente o estado on-chain em tempo real
- Para simulações, *match ticks*, ranges concentrados e APR, a precisão é suficiente
- Diferença esperada em relação ao subgraph: mínima e aceitável

