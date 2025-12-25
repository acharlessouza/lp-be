# Prompt — Implementação de Match Ticks (Backend)

Implemente no backend uma funcionalidade equivalente ao botão **“Match ticks”** usado em simuladores de pools do Uniswap v3.

O objetivo é **ajustar os preços mínimo, máximo e atual para os ticks válidos mais próximos da pool**, garantindo que os cálculos futuros (APR, fees, tempo em range) usem valores que realmente existem no protocolo.

---

## Objetivo do Endpoint

Dado um `pool_id` e um range de preços informado pelo usuário, retornar:

- `min_price_matched`
- `max_price_matched`
- `current_price_matched`

Todos **alinhados aos ticks válidos da pool**.

---

## Input esperado

```json
{
  "pool_id": 572,
  "min_price": 2833.5,
  "max_price": 3242.4
}
```

---

## Dados necessários no banco

Usar **queries simples**, sem joins complexos.

### Tabela `pools`
- `fee_tier`
- `token0_decimals`
- `token1_decimals`

### Tabela `pool_hours`
- último registro da pool  
- campos:
  - `token0_price`
  - `token1_price`
  - `period_start`

Consulta sugerida:
```sql
SELECT token0_price, token1_price
FROM pool_hours
WHERE pool_id = :pool_id
ORDER BY period_start DESC
LIMIT 1;
```

---

## Premissas importantes

- Os preços (`token0_price` / `token1_price`) **já estão normalizados pelos decimais**
- Não usar RPC nem dados on-chain
- Não calcular APR ou fees neste endpoint
- Usar Python para os cálculos

---

## Regras de cálculo

### 1. Tick spacing por fee tier

```python
TICK_SPACING = {
    100: 1,
    500: 10,
    3000: 60,
    10000: 200
}
```

Se o `fee_tier` não existir no dicionário, retornar erro.

---

### 2. Converter preço → tick

```python
import math

def price_to_tick(price: float) -> float:
    return math.log(price) / math.log(1.0001)
```

---

### 3. Ajustar para ticks válidos (Match Ticks)

```python
def match_tick(tick: float, spacing: int, mode: str):
    if mode == "lower":
        return math.floor(tick / spacing) * spacing
    if mode == "upper":
        return math.ceil(tick / spacing) * spacing
    if mode == "current":
        return round(tick / spacing) * spacing
```

---

### 4. Converter tick → preço

```python
def tick_to_price(tick: int) -> float:
    return 1.0001 ** tick
```

---

## Fluxo completo do cálculo

1. Buscar `fee_tier` da pool
2. Determinar `tick_spacing`
3. Converter:
   - `min_price → tick_lower`
   - `max_price → tick_upper`
   - `current_price → tick_current`
4. Ajustar ticks para o grid válido
5. Converter ticks ajustados de volta para preço
6. Retornar os preços ajustados

---

## Response esperado

```json
{
  "min_price_matched": 2832.97,
  "max_price_matched": 3244.11,
  "current_price_matched": 2952.38
}
```

---

## Estrutura sugerida do código

- `repository.py`  
  Consultas simples ao banco

- `match_ticks.py`  
  Lógica matemática de preço ↔ tick

- `handler.py`  
  Validação de input e montagem do response

---

## Resultado esperado

Esse endpoint deve permitir que o frontend:

- Atualize automaticamente os campos **Min Price**, **Max Price** e **Current Price**
- Replique fielmente o comportamento do botão **Match ticks**
- Use os valores corrigidos em simulações posteriores

---

## Observação final

O Match ticks **não muda a estratégia do usuário**, apenas corrige os preços para o grid real da pool, evitando cálculos irreais.
