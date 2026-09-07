# Metodologia

Este documento e a peca mais importante do projecto. Sem ele os numeros nao valem nada.

## O que e medido

O tempo de emissao de blocos identificaveis, com data e duracao publicadas pelo proprio canal emissor, atribuidos a um tema e a um interveniente.

## O que nao e medido

Nao e um censo total da emissao. Nao existe acesso publico e gratuito a monitorizacao completa de grelhas em Portugal. O servico de referencia do setor e comercial e nao tem API aberta.

O que este projecto publica e portanto um **limite inferior**: o tempo real e igual ou superior ao contabilizado, nunca inferior.

## Fontes

| Tipo | O que da | Fiabilidade |
|---|---|---|
| Feeds RSS de podcast dos proprios canais | data e duracao declaradas pelo emissor, por episodio | alta |
| YouTube Data API v3 dos canais | duracao real do video publicado | media |

Cada registo guarda a fonte que o originou e o URL original. Nada entra no dataset sem proveniencia.

## Limitacoes assumidas

1. **Podcast e emissao nao sao a mesma coisa.** A versao em podcast de uma rubrica pode ser cortada ou ligeiramente mais longa do que o que foi para o ar. A diferenca nao e conhecida e nao e estimada.
2. **Cobertura parcial.** Intervencoes que o canal nao publica em podcast nem em video nao sao contabilizadas.
3. **Atribuicao de tempo partilhado.** Um bloco com varios intervenientes nao permite saber quem falou quanto tempo sem analise de audio. Ver abaixo.
4. **Deteccao por texto.** Nas fontes sem elenco fixo, o interveniente e detectado pelo titulo e descricao. Um bloco mal titulado pelo emissor nao e apanhado.

## Regra de atribuicao

Um bloco de 20 minutos com dois intervenientes admite duas leituras:

- **Tempo rateado** (`shared_equal`): 10 minutos a cada. E a leitura por omissao, por ser a conservadora.
- **Bloco integral** (`each_full`): 20 minutos a cada. Mede presenca em antena, nao tempo de fala.

O dataset guarda `duration_s` e `credited_s` em campos separados, por isso as duas leituras sao sempre reconstruiveis sem nova recolha. O site permite alternar entre elas.

## Auditoria

- O dataset completo esta em `docs/data/appearances.json` e e descarregavel do proprio site.
- A recolha corre em integracao continua, nunca a mao. O historico de commits mostra cada alteracao.
- As regras de atribuicao estao todas num unico ficheiro, `collector/attribute.py`, com menos de cem linhas.
- A configuracao de temas e intervenientes esta em `config/trackers.yml`. Nenhuma decisao editorial esta escondida no codigo.

## Correccoes

Erros factuais sao corrigidos e a correccao fica visivel no historico. Registos nunca sao apagados em silencio.

## Ambito

O projecto publica quantidades de tempo de emissao. Nao caracteriza conteudos, nao atribui intencoes e nao avalia a qualidade do que e dito. Quem quiser tirar conclusoes tem os dados para o fazer.
