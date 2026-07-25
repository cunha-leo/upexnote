# Produto UpexNote

> Estado alinhado à versão desktop `0.24.2`. Para decisões, validações e histórico completo, consultar `PROJECT_CONTEXT.md`.

## Marca e propósito

**UpexFlow** é o ecossistema. **UpexNote** é o produto local-first para transcrever, organizar e explorar conversas.

> Transcreva, organize e explore suas conversas.

O produto atende especialmente reuniões com português de Portugal, português do Brasil e inglês técnico, preservando o transcript real como fonte de referência e tornando-o útil para leitura, pesquisa e evolução futura em contexto e estudo.

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

## Próximas frentes aprovadas, ainda não implementadas

1. Definir eventos externos reais para então criar o módulo de Integrações/Webhooks autenticado.
2. Contexto estruturado: resumo, decisões, ações, riscos e perguntas, sempre derivado e identificado.
3. Material de estudo: explicações, fluxos, tabelas, quiz e exportações.
4. Chat ancorado no material, sem transformar inferências em fatos do transcript.
5. Evolução operacional do suporte: filtros, SLA, prioridade, notificações e arquivo de evidências na infraestrutura prevista.

Captura ao vivo por microfone e loopback WASAPI, reprodução/síntese de voz e tradução contextual permanecem fases posteriores.
