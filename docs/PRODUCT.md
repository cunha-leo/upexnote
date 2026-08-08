# Produto UpexNote

> Estado alinhado à versão desktop `0.29.1`. Para decisões, validações e histórico completo, consultar `PROJECT_CONTEXT.md`.

## Marca e propósito

**UpexFlow** é o ecossistema. **UpexNote** é o produto local-first para transcrever, organizar e explorar conversas.

> Transcreva, organize e explore suas conversas.

O produto atende especialmente reuniões com português de Portugal, português do Brasil e inglês técnico, preservando o transcript real como fonte de referência e tornando-o útil para leitura, pesquisa e evolução futura em contexto e estudo.

A direção vigente organiza essa evolução em três camadas: **transcript como fonte, prévia estruturada para compreensão rápida e Caderno para edição, estudo e conhecimento pessoal**. A prévia validada já existe; o Caderno é arquitetura aprovada, ainda não implementada.

Essa direção foi concebida e arquitetada por Leonardo Cunha como parte do desenvolvimento sistêmico do UpexNote. Leonardo possui capacidade demonstrada para conceber e construir o produto de ponta a ponta; a IA amplia pesquisa, produção e implementação sob sua direção, correção e aceite. O fato de `Developer` não ser seu rótulo profissional principal não reduz a capacidade técnica nem transfere autoria arquitetural para a IA.

## O que já está entregue

- Transcrição de ficheiros de áudio e vídeo por motores cloud escolhidos explicitamente pelo utilizador e alternativa local.
- Resultado com progresso, custo, duração, idioma, diarização e validação; `raw` e `clean` permanecem distintos.
- Biblioteca por utilizador, pesquisa, detalhe, edição do texto clean, problemas, histórico e auditoria.
- Preferências completas: temas, densidade, tipografia, zoom e UI em PT/EN/ES.
- Identidade por e-mail/senha, Google e GitHub, recuperação de senha e sessão persistente.
- Administração com MFA, utilizadores, atividade, auditoria, telemetria e suporte em navegação lateral hierárquica.
- Telemetria estritamente opcional, anónima e limitada a campos operacionais aprovados.
- Suporte com casos, conversas, estados, atribuição e evidências sem armazenar binários no banco.
- Perfil completo no rodapé com identidade, papel, informações da conta e preparação para avatar futuro.
- Data Studio com catálogo por schema, construtor visual, SQL Editor, Saved Queries e diagramas ER por schema, tabela ou consulta.
- Documentos estruturados derivados acessíveis pela Biblioteca: faixa no transcript, leitor em só leitura, blocos semânticos, campos, glossário, cópia e retorno à origem; ADF-01 passo 2, pontos 1 e 3, validados na v0.29.1.

## Princípios de produto

1. O transcript bruto é imutável e nunca é substituído silenciosamente por resumo, limpeza ou conteúdo gerado.
2. Vídeo bruto não sai da máquina automaticamente. Áudio só é enviado a cloud quando o utilizador escolhe um motor cloud.
3. Privacidade e custo devem ficar claros antes de processar.
4. Credenciais nunca aparecem em ficheiros versionados, argumentos, logs, screenshots ou chat.
5. Acessibilidade, temas claro/escuro, contraste, foco e estados explícitos são requisitos de produto.
6. Administração navega pelo menu lateral; submódulos não usam abas horizontais como menu principal.
7. Cada domínio novo recebe schema PostgreSQL próprio, em inglês.

## Experiência operacional

Módulos com dados seguem, quando aplicável:

```text
visão geral → filtros → lista/fila → detalhe → ação ou contexto
```

A pessoa precisa compreender onde está, o que pode fazer, o resultado da ação e como avançar ou retornar sem se perder. Tabelas devem ser legíveis em desktop normal sem barra horizontal exposta; ações secundárias usam ícones com rótulos acessíveis.

O produto cresce por prateleiras: `Transcriptions`, `Documents`, `Notebooks`, `Settings` e `Administration` possuem responsabilidades reconhecíveis e podem expandir internamente sem transformar o menu principal ou o schema `public` em depósitos gerais. O contrato do futuro Caderno está em `NOTEBOOK_ARCHITECTURE.md`.

## Backlog atual, ainda não implementado

1. Concluir o volume persistente, o job e o manifesto de arquivo das evidências de suporte.
2. Tornar a telemetria agregada mais acionável sem quebrar consentimento ou anonimato.
3. Acrescentar scheduler, jobs, eventos e entregas às Saved Queries.
4. Evoluir suporte com filtros, SLA futuro, prioridade, atribuição, notificações e histórico.
5. Evoluir a prévia estruturada já legível para criação pela interface e passagem controlada ao Caderno, sem confundir leitura derivada com edição pessoal.
6. Implementar material de estudo: explicações, fluxos, tabelas, quiz e exportações.
7. Implementar chat ancorado no material, sem transformar inferências em fatos do transcript.
8. Retomar Integrações/Webhooks somente após contratos concretos de consultas, eventos e automações.

Captura ao vivo por microfone e loopback WASAPI, reprodução/síntese de voz e tradução contextual permanecem fases posteriores.
