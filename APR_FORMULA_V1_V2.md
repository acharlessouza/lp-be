# Como a APR e calculada no produto (v1 e v2)

## Objetivo deste documento
Este documento explica, em linguagem de negocio, como a simulacao de APR funciona hoje nas duas versoes:
- **v1** (`/v1/simulate/apr`)
- **v2** (`/v2/simulate/apr`, metodo exato)

A ideia e responder: **de onde vem cada numero** (`estimated_fees_24h_usd`, `monthly_usd`, `yearly_usd`, `fee_apr`).

---

## Conceitos basicos (comuns)

- **Fees da pool**: receita gerada pelas trocas da pool.
- **Sua participacao na pool**: quanto da liquidez ativa da faixa e sua.
- **APR de fees**: retorno anualizado de fees em relacao ao capital da posicao.

Formula final de APR (nas duas versoes):

`fee_apr = yearly_usd / deposit_usd`

Ou seja, se `yearly_usd = 1.200` e `deposit_usd = 10.000`, a APR de fees e `0,12` (12%).

---

## V1: calculo por historico horario (estimativa por share)

## 1) O que a v1 usa como entrada de dados
A v1 usa historico horario da pool e distribuicao de liquidez:
- fees por hora da pool (`pool_hourly`)
- ticks por hora (quando modo B)
- liquidez por hora (quando disponivel)
- ticks inicializados para montar curva de liquidez
- estado atual da pool (tick, preco, liquidez)

## 2) Definicao da faixa da posicao
A faixa pode ser definida por:
- `tick_lower` e `tick_upper`, ou
- `min_price` e `max_price` (convertidos para ticks), ou
- `full_range=true` (faixa total do protocolo)

## 3) Definicao do preco de calculo (`calculation_price`)
A v1 define um preco de referencia para converter valores:
- `current`: preco atual
- `custom`: preco informado
- `peak_liquidity_in_range`: preco no tick de maior liquidez da faixa
- `avg_liquidity_in_range`: preco medio ponderado por liquidez da faixa

Esse preco e usado para:
- converter entre token e USD
- derivar `deposit_usd` quando necessario

## 4) Calculo da sua liquidez (`L_user`)
Com os montantes de token0/token1 e a faixa escolhida, a v1 calcula a liquidez da posicao (`L_user`) via matematica Uniswap v3.

Se vier apenas `deposit_usd`, a v1 pode derivar valores de token com divisao 50/50 em USD no `calculation_price`.

## 5) Participacao por hora (share) e fees da posicao
Para cada hora do historico:
1. Verifica se a posicao estava "em range" naquela hora.
2. Se estiver em range, calcula a liquidez ativa da pool naquela hora (`L_pool_active`).
3. Calcula sua participacao:

`share_hora = L_user / (L_user + L_pool_active)`

4. Calcula fee da sua posicao na hora:

`fees_user_hora = fees_pool_hora * share_hora`

Se estiver fora da faixa, fee dessa hora = 0.

## 6) Consolidacao do periodo (horizon)
A v1 pega as ultimas `horizon_hours` (ex.: 24h, 7d, 14d) e soma as fees da posicao nesse periodo:

`fees_period_usd = soma(fees_user_hora no periodo)`

Depois normaliza para 24h pela media do periodo:

`estimated_fees_24h_usd = fees_period_usd / dias_efetivos_do_periodo`

## 7) Mensal, anual e APR
Na v1:
- `monthly_usd = estimated_fees_24h_usd * 30`
- `yearly_usd = estimated_fees_24h_usd * 365`
- `fee_apr = yearly_usd / deposit_usd`

Resumo: a v1 e uma estimativa baseada em historico horario + participacao estimada por liquidez.

---

## V2: calculo exato por bloco (feeGrowthInside)

A v2 usa a logica "exata" do Uniswap v3 entre dois blocos (A e B).

## 1) Escolha dos blocos A e B
- **B**: snapshot mais recente da pool.
- **A**: snapshot no lookback (`ts_B - lookback_days*86400`), pegando o timestamp mais proximo para tras.

Entao:

`seconds_delta = ts_B - ts_A`

## 2) Ticks obrigatorios em A e B
Para calcular exato, a v2 precisa dos 4 pontos:
- `(tick_lower, A)`
- `(tick_upper, A)`
- `(tick_lower, B)`
- `(tick_upper, B)`

Se faltar algum, a v2 tenta fallback on-demand (subgraph) para preencher `apr_exact.tick_snapshot`.

## 3) Fee growth inside em A e em B
Para cada token (0 e 1), em cada bloco (A e B):

- `global = feeGrowthGlobalX128`
- `outside_lower = feeGrowthOutsideX128 do tickLower`
- `outside_upper = feeGrowthOutsideX128 do tickUpper`
- `tick_current = tick da pool no bloco`

Calcula:

`feeGrowthBelow = outside_lower` se `tick_current >= tick_lower`, senao `global - outside_lower`

`feeGrowthAbove = outside_upper` se `tick_current < tick_upper`, senao `global - outside_upper`

`feeGrowthInside = global - feeGrowthBelow - feeGrowthAbove`

Depois:

`deltaInside = feeGrowthInside_B - feeGrowthInside_A`

## 4) Conversao de delta em fees da posicao
Com `L_user`:

`fees_token = (L_user * deltaInside) / 2^128`

Isso e feito para token0 e token1.

Depois converte para unidades humanas (decimais do token) e para USD:

`fees_period_usd = fees_token1 + (fees_token0 * used_price)`

Aqui `used_price` vem do `calculation_method` (current, custom, avg/peak etc.).

## 5) Normalizacao para 24h, mes e ano
Na v2:

`estimated_fees_period_usd = fees_period_usd`  (valor bruto entre A e B)

`estimated_fees_24h_usd = fees_period_usd * (86400 / seconds_delta)`

`yearly_usd = fees_period_usd * ((365*86400) / seconds_delta)`

`monthly_usd = yearly_usd / 12`

`fee_apr = yearly_usd / deposit_usd`

## 6) Metadados para auditoria
A v2 retorna `meta` com:
- `block_a_number`, `block_b_number`
- `ts_a`, `ts_b`
- `seconds_delta`
- `used_price`
- `warnings`

Isso facilita validar o resultado de negocio com transparencia.

---

## Diferenca pratica entre v1 e v2

- **v1**: estimativa por historico horario e share de liquidez por hora.
- **v2**: calculo exato de crescimento de fee dentro da faixa entre dois blocos.

Em termos de negocio:
- use a **v1** quando quiser leitura historica operacional com granularidade por hora.
- use a **v2** quando quiser simulacao mais fiel ao mecanismo matematico do Uniswap v3 entre dois pontos de tempo.

---

## Sobre `lookback_days` na v2
`lookback_days` muda o bloco A (inicio da janela).

Se 1D e 7D derem `estimated_fees_24h_usd` parecido, significa que a media diaria de fees na janela de 1 dia e na de 7 dias esta parecida.

Importante:
- `estimated_fees_period_usd` tende a mudar mais claramente com `lookback_days`.
- `estimated_fees_24h_usd` e normalizado para base diaria.

---

## Leitura rapida dos campos de saida

- `estimated_fees_period_usd`: fees totais no periodo analisado.
- `estimated_fees_24h_usd`: fees equivalentes por dia.
- `monthly_usd`: projecao mensal com base no diario.
- `yearly_usd`: projecao anual com base no diario.
- `fee_apr`: retorno anual de fees sobre o capital da posicao.
