# Metodologia

Este documento é a peça mais importante do projeto. Sem ele, os números não valem nada.

## O que é medido

O tempo de emissão de blocos identificáveis, com data e duração publicadas pelo próprio canal emissor, atribuídos a um tema e a um interveniente.

## O que não é medido

Não é um censo total da emissão. Não existe acesso público e gratuito a monitorização completa de grelhas em Portugal. O serviço de referência do setor é comercial e não tem API aberta.

O que este projeto publica é, portanto, um **limite inferior**: o tempo real é igual ou superior ao contabilizado, nunca inferior.

## Fontes

| Tipo | O que dá | Fiabilidade |
|---|---|---|
| Feeds RSS de podcast dos próprios canais | data e duração declaradas pelo emissor, por episódio | alta |
| YouTube Data API v3 dos canais | duração real do vídeo publicado | média |

Cada registo guarda a fonte que o originou e o URL original. Nada entra no dataset sem proveniência.

## Limitações assumidas

1. **Podcast e emissão não são a mesma coisa.** A versão em podcast de uma rubrica pode ser cortada ou ligeiramente mais longa do que o que foi para o ar. A diferença não é conhecida nem é estimada. Para reduzir este risco, as fontes que misturam conteúdo exclusivo de podcast com emissões de TV exigem prova textual de que o episódio foi para o ar (`require_broadcast_evidence`); sem essa prova, o episódio fica de fora e é registado na quarentena.
2. **Cobertura parcial.** Intervenções que o canal não publica em podcast nem em vídeo não são contabilizadas.
3. **Atribuição de tempo partilhado.** Um bloco com vários intervenientes não permite saber quem falou quanto tempo sem análise de áudio. Ver abaixo.
4. **Deteção por texto.** Nas fontes sem elenco fixo, o interveniente é detetado pelo título e pela descrição. Um bloco mal titulado pelo emissor não é apanhado.
5. **O feed ao vivo só cobre os últimos 100 episódios.** É um limite do publicador do feed, não ajustável por quem o consome. Para o histórico mais antigo, ver "Backfill histórico" abaixo.
6. **Um feed pode conter mais do que uma rubrica.** Quando isso acontece, cada episódio é classificado por regras de título e duração (`segments`, em `config/trackers.yml`), nunca por múltiplas fontes a apontar para o mesmo feed — isso duplicaria tempo.

## Backfill histórico

O feed RSS ao vivo de cada programa só devolve os últimos 100 episódios. Para cobrir o período desde o início do tema, sem essa restrição, existe um comando à parte que lê capturas arquivadas do feed no Wayback Machine (web.archive.org) em vários momentos ao longo do tempo, reconstruindo o histórico contínuo a partir da sobreposição dessas janelas:

```
python -m collector.backfill_wayback <id-da-fonte>
```

Corre uma vez por fonte (ou de vez em quando, para alargar a cobertura), não faz parte da recolha diária, e usa exatamente as mesmas regras de atribuição, classificação e corte de data da recolha normal — nada aqui tem um critério à parte.

## Deduplicação entre fontes

Se, por engano de configuração, duas fontes alguma vez apontarem para o mesmo episódio de origem, apenas a primeira conta — a segunda é posta de lado e registada com o motivo. Isto é verificado numa corrida completa (ver `tests/test_classification.py`), não é apenas uma intenção de código.

## Definição formal

Esta secção é deliberadamente técnica — é a única página do site onde isso acontece. As restantes páginas usam linguagem corrente; aqui, a precisão importa mais do que a fluidez de leitura.

**Bloco.** Um bloco `B` é um evento de emissão identificado, com três propriedades: uma duração `D(B)` em segundos, uma data `t(B)`, e um conjunto de intervenientes identificados `P(B) = {p₁, ..., pₙ}`, com `n = |P(B)| ≥ 1`.

### Tempo atribuído a um interveniente, por bloco

Para um interveniente `p ∈ P(B)`, definem-se exatamente duas funções de atribuição:

```
leitura dividida  (shared_equal):  c_dividido(p, B) = D(B) / |P(B)|
leitura completa  (each_full):     c_completo(p, B) = D(B)
```

No site, estas duas leituras aparecem com os nomes "Tempo dividido" e "Tempo completo". São as únicas duas publicadas, por uma razão precisa: são as únicas duas que não exigem dados que este projeto não tem. Qualquer valor intermédio (por exemplo, "60/40 porque um fala mais") exigiria transcrição e diarização de áudio — identificar quem fala, ao segundo, dentro de cada bloco — o que este projeto explicitamente não faz (ver Limitações). Sem esses dados, qualquer fração que não seja `1/n` ou `1` seria uma estimativa disfarçada de medição. Por isso ambas as leituras aqui publicadas são exatas, não aproximadas: cada uma é uma soma direta de números guardados, nunca um palpite.

### Tempo total de um tema, num período

O erro mais fácil de cometer nesta conta é somar o tempo de todos os intervenientes de um bloco partilhado — o que daria a um bloco de 20 minutos com dois intervenientes um total de 40 minutos de emissão. Isso seria falso: só houve 20 minutos de televisão. Por isso, o tempo total de emissão de um tema `T`, entre as datas `t0` e `t1`, soma-se sobre o **conjunto de blocos distintos** desse período — nunca sobre as linhas atribuídas a cada interveniente:

```
Emissão(T, t0, t1) = Σ D(B), para todo B com t(B) ∈ [t0, t1]
```

Cada bloco entra nesta soma exatamente uma vez, seja qual for o número de intervenientes.

### Tempo de um interveniente, num período

```
Tempo(p, t0, t1) = Σ c(p, B), para todo B com t(B) ∈ [t0, t1] e p ∈ P(B)
```

onde `c` é `c_dividido` ou `c_completo`, consoante a leitura escolhida no site.

### Períodos usados no site

| Período | t0 | t1 |
|---|---|---|
| Esta semana | segunda-feira da semana corrente | hoje |
| Este mês | dia 1 do mês corrente | hoje |
| Este ano | 1 de janeiro do ano corrente | hoje |
| Desde a guerra | data de início do tema (2022-02-24) | hoje |

Todos os quatro usam exatamente as fórmulas acima. Nenhum período tem uma regra de cálculo diferente dos outros — só o intervalo `[t0, t1]` muda.

### Nota sobre arredondamento

Os valores diários guardados em `docs/data/stats.json` são arredondados ao segundo antes de serem escritos. Somar `k` dias já arredondados pode divergir do total exato do período em, no máximo, `k` segundos — por acumulação do erro de arredondamento, nunca por um enviesamento sistemático (arredonda-se sempre ao valor mais próximo, nunca sempre para cima ou sempre para baixo). Numa escala de horas, este desvio é irrelevante: mesmo no pior caso, um período de 30 dias diverge no máximo 30 segundos, ou seja, menos de 0,003% de um total de 30 horas. Este limite está verificado em `tests/test_pipeline.py`, não é apenas uma alegação.

## Auditoria

- O dataset completo está em `docs/data/appearances.json` e é descarregável a partir do próprio site.
- Os episódios rejeitados nesta corrida — antes do início do tema, sem prova de emissão, sem interveniente identificado, ou duplicados entre fontes — ficam em `docs/data/quarantine.json`, com o motivo. Nada desaparece em silêncio.
- A recolha corre em integração contínua, nunca à mão. O histórico de commits mostra cada alteração.
- As regras de atribuição estão todas num único ficheiro, `collector/attribute.py`, com menos de cem linhas.
- A configuração de temas, intervenientes e fontes está em `config/trackers.yml`. Nenhuma decisão editorial está escondida no código.

## Correções

Erros factuais são corrigidos e a correção fica visível no histórico. Registos nunca são apagados em silêncio.

## Âmbito

O projeto publica quantidades de tempo de emissão. Não caracteriza conteúdos, não atribui intenções e não avalia a qualidade do que é dito. Quem quiser tirar conclusões tem os dados para o fazer.
