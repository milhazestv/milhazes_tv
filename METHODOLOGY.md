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

1. **Podcast e emissão não são a mesma coisa.** A versão em podcast de uma rubrica pode ser cortada ou ligeiramente mais longa do que o que foi para o ar. A diferença não é conhecida nem é estimada.
2. **Cobertura parcial.** Intervenções que o canal não publica em podcast nem em vídeo não são contabilizadas.
3. **Atribuição de tempo partilhado.** Um bloco com vários intervenientes não permite saber quem falou quanto tempo sem análise de áudio. Ver abaixo.
4. **Deteção por texto.** Nas fontes sem elenco fixo, o interveniente é detetado pelo título e pela descrição. Um bloco mal titulado pelo emissor não é apanhado.

## Regra de atribuição

Um bloco de 20 minutos com dois intervenientes admite duas leituras:

- **Tempo rateado** (`shared_equal`): 10 minutos a cada. É a leitura por omissão, por ser a conservadora.
- **Bloco integral** (`each_full`): 20 minutos a cada. Mede presença em antena, não tempo de fala.

O dataset guarda `duration_s` e `credited_s` em campos separados, por isso as duas leituras são sempre reconstruíveis sem nova recolha. O site permite alternar entre elas.

## Auditoria

- O dataset completo está em `docs/data/appearances.json` e é descarregável a partir do próprio site.
- A recolha corre em integração contínua, nunca à mão. O histórico de commits mostra cada alteração.
- As regras de atribuição estão todas num único ficheiro, `collector/attribute.py`, com menos de cem linhas.
- A configuração de temas e intervenientes está em `config/trackers.yml`. Nenhuma decisão editorial está escondida no código.

## Correções

Erros factuais são corrigidos e a correção fica visível no histórico. Registos nunca são apagados em silêncio.

## Âmbito

O projeto publica quantidades de tempo de emissão. Não caracteriza conteúdos, não atribui intenções e não avalia a qualidade do que é dito. Quem quiser tirar conclusões tem os dados para o fazer.
