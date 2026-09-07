# Milhazes TV

Contagem publica e auditavel do tempo de emissao dedicado a temas recorrentes na televisao portuguesa.

Recolha automatica diaria, dataset aberto, metodologia publicada. Ver [METHODOLOGY.md](METHODOLOGY.md).

## Como funciona

```
config/trackers.yml   temas, intervenientes e fontes (a unica coisa que se edita para crescer)
collector/            recolha, atribuicao e agregacao
docs/                 o site estatico e o dataset publicado
docs/data/            appearances.json (dataset canonico) e stats.json (agregados)
```

O ciclo e: fonte -> item bruto -> regra de atribuicao -> registo append-only -> agregados -> site estatico.

Nenhum modulo conhece um tema concreto. Acrescentar um tema novo e editar YAML, nao codigo.

## Correr localmente

```bash
pip install -r requirements.txt
python -m unittest discover -s tests    # 17 testes, todos offline
python -m collector.main --dry-run      # recolhe sem escrever
python -m collector.main                # recolhe e escreve docs/data
python -m http.server -d docs 8000      # ver o site em localhost:8000
```

## Acrescentar um tema

Editar `config/trackers.yml`:

```yaml
topics:
  - id: crime
    name: Crime na grelha
    question: Quanto tempo de emissao ocupam os programas dedicados a crime?
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
```

O `roster` fixo usa-se quando todos os episodios da fonte contam sempre para os mesmos intervenientes. `roster: auto` usa-se quando os intervenientes tem de ser detectados a partir do titulo e da descricao.

## Acrescentar um tipo de fonte

Criar `collector/sources/<tipo>.py`, herdar de `SourcePlugin`, decorar com `@register`, definir `type` e implementar `fetch()` devolvendo `RawItem`. Importar em `collector/main.py`. Mais nada.

## Segredos

`YT_API_KEY` e opcional. Sem ela, as fontes de YouTube sao ignoradas em silencio e o resto da recolha corre na mesma.

## Licenca

Codigo: MIT. Dados: CC0. Ver [LICENSE](LICENSE).
