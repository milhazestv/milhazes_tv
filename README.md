# Milhazes TV

Contagem pública e auditável do tempo de emissão dedicado a temas recorrentes na televisão portuguesa.

Recolha automática diária, dataset aberto, metodologia publicada. Ver [METHODOLOGY.md](METHODOLOGY.md).

## Como funciona

```
config/trackers.yml   temas, intervenientes e fontes (a única coisa que se edita para crescer)
collector/             recolha, atribuição, classificação e agregação
docs/                  o site estático e o dataset publicado
docs/data/             appearances.json (dataset canónico), stats.json (agregados),
                       quarantine.json (itens rejeitados nesta corrida, com o motivo)
```

O ciclo é: fonte -> item bruto -> corte de data / prova de emissão -> classificação por segmento -> regra de atribuição -> registo append-only -> agregados -> site estático.

Nenhum módulo conhece um tema concreto. Acrescentar um tema novo é editar YAML, não código.

## Correr localmente

```bash
pip install -r requirements.txt
python -m unittest discover -s tests    # todos offline
python -m collector.main --dry-run      # recolhe sem escrever
python -m collector.main                # recolhe e escreve docs/data
python -m http.server -d docs 8000      # ver o site em localhost:8000
```

## Backfill histórico

O feed RSS ao vivo só devolve os últimos 100 episódios — um limite do publicador, não ajustável por quem consome o feed. Para cobrir desde o início do tema, há um comando à parte que reconstrói o histórico a partir de capturas arquivadas do feed no Wayback Machine:

```bash
python -m collector.backfill_wayback omny-guerra-fria
python -m collector.backfill_wayback omny-rogeiro-show --from 2022-02-24
```

Corre uma vez por fonte, não faz parte da recolha diária, e usa as mesmas regras de atribuição da recolha normal. Também está disponível como workflow manual no GitHub Actions ("backfill-historico"), para não depender da rede local.

## Acrescentar um tema

Editar `config/trackers.yml`:

```yaml
topics:
  - id: crime
    name: Crime na grelha
    question: Quanto tempo de emissão ocupam os programas dedicados a crime?
    since: '2022-01-01'
    enabled: true

subjects:
  - id: programa-x
    topic: crime
    display_name: Nome do programa
    match:
      any: [termo, outro termo]

sources:
  - id: fonte-nova
    type: podcast_rss
    topic: crime
    url: https://...
    channel: Canal
    program: Nome do programa
    roster: [programa-x]
    attribution: shared_equal
    confidence: high
    require_broadcast_evidence: true
```

O `roster` fixo usa-se quando todos os episódios da fonte contam sempre para os mesmos intervenientes. `roster: auto` usa-se quando os intervenientes têm de ser detetados a partir do título e da descrição.

Se um feed misturar mais do que uma rubrica (o mesmo publicador, vários programas no mesmo podcast), usar `segments` para classificar cada item por título e duração — ver o exemplo em `omny-rogeiro-show` no `trackers.yml`. Nunca configurar duas fontes a apontar para o mesmo feed ou para playlists derivadas umas das outras: a deduplicação entre fontes protege contra isso, mas o objetivo é nem chegar lá.

## Acrescentar um tipo de fonte

Criar `collector/sources/<tipo>.py`, herdar de `SourcePlugin`, decorar com `@register`, definir `type` e implementar `fetch()` devolvendo `RawItem`. Importar em `collector/main.py`. Mais nada.

## Segredos

`YT_API_KEY` é opcional. Sem ela, as fontes de YouTube são ignoradas em silêncio e o resto da recolha corre na mesma.

## Licença

Código: MIT. Dados: CC0. Ver [LICENSE](LICENSE).
