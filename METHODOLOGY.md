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

## Regra de atribuição

Um bloco de 20 minutos com dois intervenientes admite duas leituras:

- **Tempo rateado** (`shared_equal`): 10 minutos a cada. É a leitura por omissão, por ser a conservadora.
- **Bloco integral** (`each_full`): 20 minutos a cada. Mede presença em antena, não tempo de fala.

O dataset guarda `duration_s` e `credited_s` em campos separados, por isso as duas leituras são sempre reconstruíveis sem nova recolha. O site permite alternar entre elas.

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
