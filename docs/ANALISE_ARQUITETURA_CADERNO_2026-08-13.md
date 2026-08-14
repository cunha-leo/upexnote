# Análise arquitetural — Caderno (Notebooks): por que os bugs se repetem

**Contexto:** esta análise foi pedida explicitamente depois de uma sequência de correções pontuais (v0.36.2 → v0.36.6) que resolveram sintomas individuais, mas continuaram a expor a mesma classe de problema a cada teste seguinte. O pedido foi claro: não mais remendo — entender a causa sistémica.

---

## 1. O que está realmente a acontecer (evidência, não opinião)

Fui ao código medir, não estimar. Três factos concretos sustentam tudo o que se segue.

### Facto 1 — Cada ação do utilizador é um processo do SO inteiro, do zero

`worker_command()` em `lib.rs` chama `Command::new(...)` e `cmd.spawn()`. Isto não é uma chamada de função nem uma mensagem para um processo já vivo — é o Windows a criar um processo novo, carregar o interpretador Python (ou o `.exe` do PyInstaller), importar os módulos, executar, imprimir JSON no stdout, e morrer. Isto acontece a cada `invoke()` do frontend, sem exceção.

### Facto 2 — Abrir UMA nota dispara SEIS desses processos, em série de decisão mas paralelos na rede

Em `openNote()` (App.tsx, linha 2266 em diante):

```
notebook_note_item   (obrigatório, bloqueia o ecrã)
loadAnnotations()    → invoke notebook_annotations
loadReferences()     → invoke notebook_references
loadLinks()          → invoke notebook_links
loadKeywords()       → invoke notebook_keywords
loadGlossary()       → invoke notebook_glossary
```

Seis spawns de processo, seis handshakes ao Postgres (via túnel SSH), para mostrar UMA nota. E isto é só ao abrir — `load()` da árvore já gasta dois (`notebook_ensure_default` + `notebook_tree`) antes de sequer chegar aqui.

### Facto 3 — Existe precedente de processo persistente no próprio projeto, mas só é usado para o túnel

`db.py` tem um `tunnel-keep` (linha 944) — um processo Python que fica vivo, mantém o túnel SSH aberto, e cada `connect()` subsequente tenta primeiro esse "caminho rápido" (`_keeper_port()`) antes de abrir túnel próprio. Ou seja: **já resolvemos exatamente este problema para o túnel SSH, mas nunca aplicámos a mesma ideia ao worker Python em si.** Continuamos a pagar o custo de arranque do interpretador/processo em cada ação, mesmo com o túnel já quente.

### Facto 4 — O frontend não tem uma fonte única de verdade

`NotebooksView` e `LibraryView` são dois componentes React que ficam **ambos montados o tempo todo** (a troca de separador é CSS, não desmontagem). Cada um tem o seu próprio estado:

- `NotebooksView`: `collections`, `notes` (a árvore completa)
- `LibraryView`: `nbCollections` (uma cópia paralela, só para o dropdown do diálogo "Salvar no Caderno")

Não existe um store partilhado nem um mecanismo de invalidação entre eles. A única forma de um separador saber que o outro mudou algo é (a) o utilizador forçar um reload manual, ou (b) o canal ad-hoc `openRequest`/`notebookOpenRequest`, que só cobre o caminho específico "abrir no caderno a partir da Biblioteca" — e mesmo esse só foi corrigido agora, nesta ronda, porque `loadedOnce` impedia qualquer recarregamento depois do primeiro mount.

---

## 2. Por que cada correção individual só empurrou o problema

Repare no padrão dos últimos 5 bugs relatados:

| Sintoma relatado | Causa raiz real | O que a correção pontual resolveu |
|---|---|---|
| Erro antigo preso no ecrã | `openNote()` não limpava `error` | Só esse `useState` |
| Nota apagada "ressuscitava" | cache local nunca purgada no delete | Só a função de delete |
| CRUD lento/inaceitável | `await load()` bloqueante antes de cada ação | Só as 5 funções de CRUD |
| "Salvar no Caderno" não navegava | falta uma linha de código (`onOpenInNotebook`) nunca chamada | Só essa chamada |
| Coleção nova invisível na árvore | `loadedOnce` trava recarregamento entre separadores | Só o caminho `openRequest` |
| "Loading..." eterno na nota recém-criada | backend devolvia só `{id}`, forçando 2ª viagem sem cache | Só essa resposta |

Todos estes bugs têm a **mesma raiz dupla**: (1) não há um único lugar onde o estado do Caderno vive e se atualiza, e (2) cada ação paga o preço total de um processo+túnel+query novos porque não há nada persistente do lado do worker a servir pedidos. Eu estava a encontrar e fechar buracos individuais num sistema que gera buracos novos por construção — cada área nova que o utilizador testava (criar pasta, salvar da Biblioteca, reabrir nota) era uma superfície nova do MESMO problema estrutural, ainda não testada. Por isso parecia infinito.

Isto confirma exactamente o que disseste: não é falta de cuidado técnico em cada correção (validei sempre com `tsc`/`ast`), é que a arquitetura de base — "cada ação é um processo efémero + cada componente guarda a sua cópia de estado" — **gera** esta classe de bug como propriedade estrutural, não como acidente.

---

## 3. Causa raiz sistémica (a resposta direta à pergunta "o que aconteceu")

**O Caderno foi construído como uma sequência de funcionalidades adicionadas incrementalmente (árvore → notas → anotações → referências → links → versões → glossário...), cada uma com o seu próprio `invoke`, o seu próprio `useState`, e sem uma camada de dados desenhada para servir todas elas.** A cache que existe (localStorage `NB_TREE_CACHE_PREFIX`/`NB_NOTE_CACHE_PREFIX`) foi adicionada depois, por cima, ficheiro a ficheiro — é sintoma tratado, não arquitetura.

Duas decisões de desenho, tomadas cedo e nunca revistas, são a causa raiz:

1. **Modelo de execução:** um processo do SO por ação, em vez de um worker persistente com um protocolo de pedido/resposta (o `tunnel-keep` prova que isto é perfeitamente viável no vosso stack — só nunca foi generalizado).
2. **Modelo de estado no frontend:** estado local por componente, em vez de uma fonte única (store) com invalidação explícita entre vistas.

Enquanto estas duas coisas não mudarem, qualquer nova funcionalidade no Caderno (Export, Versões, Glossário, o resto do backlog) vai reintroduzir a mesma classe de bug: lentidão percebida (processo novo a cada clique) e inconsistência entre separadores (sem fonte única de verdade).

---

## 4. Plano de correção real (não incremental) — priorizado

### Fase A — Worker persistente (resolve a lentidão na origem)

Trocar "um processo por comando" por um **processo worker de longa duração**, falando um protocolo simples por stdin/stdout (uma linha JSON = um pedido, uma linha JSON = uma resposta — o `tunnel-keep` já mostra que manter um processo Python vivo em Windows funciona bem neste projeto). O Rust deixa de fazer `spawn()` a cada `invoke`; passa a escrever no stdin do worker já vivo e ler a resposta.

Impacto: elimina o custo de arranque de processo (o maior componente da lentidão percebida) em praticamente todas as ações — não só no Caderno, em todo o app. É a mudança de maior alavancagem.

Risco/esforço: médio-alto — precisa de gestão de ciclo de vida do processo (arranque, crash-restart, fila de pedidos concorrentes), mas o precedente do `tunnel-keep` reduz o risco técnico.

### Fase B — Endpoint composto para abrir nota

Enquanto a Fase A não está pronta, um ganho imediato e de baixo risco: criar `notebook_note_open(id)` no worker que devolve, numa só resposta, o item + anotações + referências + links + keywords + glossário (uma query composta no `db.py`, não seis). Isto sozinho corta 6 processos/handshakes para 1 em cada abertura de nota — mesmo sem tocar no modelo de execução.

### Fase C — Store único de estado do Caderno

Extrair `collections`/`notes` para um estado partilhado (Context ou store simples) usado tanto por `NotebooksView` como por `LibraryView`, com um mecanismo explícito de invalidação (evento "coleções mudaram" disparado por qualquer mutação, ouvido por quem precisar) em vez do canal ad-hoc atual e do `loadedOnce` que trava atualizações.

### Fase D — Cache como camada coerente, não bolted-on

Consolidar `NB_TREE_CACHE_PREFIX`/`NB_NOTE_CACHE_PREFIX`/Library cache num único módulo de cache com uma política clara (TTL, invalidação por mutação, um só sítio a decidir "isto está stale") em vez de cada função de mutação lembrar-se manualmente de chamar `removeNbNoteCache`/`writeNbTreeCache`.

---

## 5. Recomendação de ordem

B antes de A: B é pequeno, isolado, e resolve visivelmente a lentidão de abrir notas em dias, não semanas. A é a mudança estrutural maior — vale a pena, mas é um projeto à parte, não uma correção desta sessão. C deve andar a par de B (já que B toca nas mesmas funções que geram o problema de estado duplicado). D fecha depois, quando B e C já estabilizaram os pontos de mutação.

Isto não é mais uma lista de "bugs a corrigir" — é uma mudança de como o Caderno busca e guarda dados. Só depois disto o produto para de gerar esta classe de bug a cada funcionalidade nova.
