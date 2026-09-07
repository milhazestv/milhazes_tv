# Metodologia

Este documento é a peça mais importante do projeto. Sem ele, os números não valem nada.

## O que é medido

O tempo de emissão de blocos identificáveis, com data e duração publicadas pelo próprio canal emissor, atribuídos a um tema e a um interveniente.

## Critério de inclusão

A unidade medida é a rubrica, não o assunto de cada episódio.

Quando uma rubrica entra no tema, entra por inteiro: todos os seus blocos contam, seja qual for o assunto tratado nesse dia. Um episódio do Guerra Fria conta na íntegra quer trate da Ucrânia, do Médio Oriente ou da Venezuela.

A razão é simples e é uma limitação assumida: este projeto não transcreve nem analisa o conteúdo emitido, e por isso não sabe, episódio a episódio, de que se falou. Contar por assunto exigiria caracterizar conteúdos, que é precisamente o que o projeto não faz. Contar a rubrica inteira é uma regra objetiva, verificável por quem quiser, e que não depende de nenhum juízo sobre o que foi dito.

Quem discordar da inclusão de uma rubrica tem a lista completa em `config/trackers.yml` e o dataset por bloco para refazer a conta com outro critério.

## O que não é medido

Não é um censo total da emissão. Não existe acesso público e gratuito a monitorização completa de grelhas em Portugal. O serviço de referência do setor é comercial e não tem API aberta.

O que este projeto publica é, portanto, um **limite inferior**: o tempo real é igual ou superior ao contabilizado, nunca inferior.

## Fontes

| Tipo | O que dá | Fiabilidade |
|---|---|---|
| Feeds RSS de podcast dos próprios canais | data e duração declaradas pelo emissor, por episódio | alta |
| YouTube Data API v3 dos canais | duração real do vídeo publicado | média |

Cada registo guarda a fonte que o originou e o URL original. Nada entra no dataset sem proveniência.

## Data de emissão

A data de um bloco é a data em que foi para o ar, não a data em que o episódio foi publicado em podcast. As duas divergem, muitas vezes por dias.

Quando o emissor declara a data no próprio texto ("emitido na SIC a 7 de setembro"), é essa que conta. Quando não declara, usa-se a data de publicação, que é o melhor dado disponível. Cada registo guarda as duas datas e diz qual foi usada, nos campos `date`, `published_at` e `date_source`, para que a diferença possa ser verificada sem voltar à fonte.

Uma data declarada só é aceite se cair numa janela plausível face à publicação, ou seja, no mesmo dia ou até 45 dias antes. Fora dessa janela, a leitura é considerada duvidosa e prevalece a data de publicação. É uma escolha conservadora: preferimos uma data menos precisa a uma data errada.

## Limitações assumidas

1. **Podcast e emissão não são a mesma coisa.** A versão em podcast de uma rubrica pode ser cortada ou ligeiramente mais longa do que o que foi para o ar. A diferença não é conhecida nem é estimada. Para reduzir este risco, as fontes que misturam conteúdo exclusivo de podcast com emissões de TV exigem prova textual de que o episódio foi para o ar (`require_broadcast_evidence`); sem essa prova, o episódio fica de fora e é registado na quarentena.
2. **Cobertura parcial.** Intervenções que o canal não publica em podcast nem em vídeo não são contabilizadas.
3. **Atribuição de tempo partilhado.** Um bloco com vários intervenientes não permite saber quem falou quanto tempo sem análise de áudio. Ver abaixo.
4. **Deteção por texto.** Nas fontes sem elenco fixo, o interveniente é detetado pelo título e pela descrição. Um bloco mal titulado pelo emissor não é apanhado.
5. **A prova de emissão é textual.** Um episódio emitido cuja sinopse não o declare fica de fora. Isso reduz o total publicado e nunca o aumenta, o que é coerente com publicar um limite inferior.
6. **Um feed pode conter mais do que uma rubrica.** Quando isso acontece, cada episódio é classificado por regras de título e duração (`segments`, em `config/trackers.yml`), nunca por múltiplas fontes a apontar para o mesmo feed, o que duplicaria tempo. A mesma regra define o elenco do episódio, para que um bloco de uma rubrica de um só comentador não seja creditado aos dois.
7. **O canal e o horário de uma rubrica mudam ao longo do tempo.** O canal registado é o da configuração atual da fonte ou do segmento, o que é uma simplificação para blocos antigos.

## Deduplicação entre fontes

Se, por engano de configuração, duas fontes alguma vez apontarem para o mesmo episódio de origem, apenas a primeira conta; a segunda é posta de lado e registada com o motivo. Isto é verificado numa corrida completa (ver `tests/test_classification.py`), não é apenas uma intenção de código.

## Definição formal

Esta secção é deliberadamente técnica, e é a única página do site onde isso acontece. As restantes páginas usam linguagem corrente; aqui, a precisão importa mais do que a fluidez de leitura.

**Bloco.** Um bloco `B` é um evento de emissão identificado, com três propriedades: uma duração `D(B)` em segundos, uma data `t(B)`, e um conjunto de intervenientes identificados `P(B) = {p₁, ..., pₙ}`, com `n = |P(B)| ≥ 1`.

### Tempo atribuído a um interveniente, por bloco

Para um interveniente `p ∈ P(B)`, definem-se exatamente duas funções de atribuição:

```
leitura dividida  (shared_equal):  c_dividido(p, B) = D(B) / |P(B)|
leitura completa  (each_full):     c_completo(p, B) = D(B)
```

No site, estas duas leituras aparecem com os nomes "Tempo dividido" e "Tempo completo". São as únicas duas publicadas, por uma razão precisa: são as únicas duas que não exigem dados que este projeto não tem. Qualquer valor intermédio (por exemplo, "60/40 porque um fala mais") exigiria transcrição e diarização de áudio, ou seja, identificar quem fala, ao segundo, dentro de cada bloco, o que este projeto explicitamente não faz (ver Limitações). Sem esses dados, qualquer fração que não seja `1/n` ou `1` seria uma estimativa disfarçada de medição. Por isso ambas as leituras aqui publicadas são exatas, não aproximadas: cada uma é uma soma direta de números guardados, nunca um palpite.

As duas leituras são calculadas a partir da duração do bloco e do número de intervenientes, e nunca a partir de um valor pré-calculado por fonte. Assim, mudar a configuração de uma fonte não pode alterar o significado de nenhuma das duas leituras publicadas.

### Tempo total de um tema, num período

O erro mais fácil de cometer nesta conta é somar o tempo de todos os intervenientes de um bloco partilhado, o que daria a um bloco de 20 minutos com dois intervenientes um total de 40 minutos de emissão. Isso seria falso: só houve 20 minutos de televisão. Por isso, o tempo total de emissão de um tema `T`, entre as datas `t0` e `t1`, soma-se sobre o **conjunto de blocos distintos** desse período, nunca sobre as linhas atribuídas a cada interveniente:

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

Todos os quatro usam exatamente as fórmulas acima. Nenhum período tem uma regra de cálculo diferente dos outros: só o intervalo `[t0, t1]` muda.

### Nota sobre arredondamento

Os valores diários guardados em `docs/data/stats.json` são arredondados ao segundo antes de serem escritos. Somar `k` dias já arredondados pode divergir do total exato do período em, no máximo, `k` segundos, por acumulação do erro de arredondamento, nunca por um enviesamento sistemático (arredonda-se sempre ao valor mais próximo, nunca sempre para cima ou sempre para baixo). Numa escala de horas, este desvio é irrelevante: mesmo no pior caso, um período de 30 dias diverge no máximo 30 segundos, ou seja, menos de 0,003% de um total de 30 horas. Este limite está verificado em `tests/test_pipeline.py`, não é apenas uma alegação.

## Auditoria

- O dataset completo está em `docs/data/appearances.json` e é descarregável a partir do próprio site. Cada registo guarda a duração do bloco, o número de intervenientes, as duas datas, a origem da data e o excerto do texto que serviu de prova de emissão.
- Os episódios rejeitados nesta corrida, seja por serem anteriores ao início do tema, por não terem prova de emissão, por não terem interveniente identificado ou por estarem duplicados entre fontes, ficam em `docs/data/quarantine.json`, com o motivo e um excerto da sinopse. Nada desaparece em silêncio.
- A recolha corre em integração contínua, nunca à mão. O histórico de commits mostra cada alteração.
- As regras de atribuição estão todas num único ficheiro curto, `collector/attribute.py`, feito para ser lido por inteiro por quem quiser contestar os números.
- A configuração de temas, intervenientes e fontes está em `config/trackers.yml`. Nenhuma decisão editorial está escondida no código.

## Correções

Erros factuais são corrigidos e a correção fica visível no histórico. Registos nunca são apagados em silêncio.

## Âmbito

O projeto publica quantidades de tempo de emissão. Não caracteriza conteúdos, não atribui intenções e não avalia a qualidade do que é dito. Quem quiser tirar conclusões tem os dados para o fazer.
