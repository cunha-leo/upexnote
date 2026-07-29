# UpexNote — instruções permanentes para agentes

Estas regras se aplicam a todo o repositório. Um `AGENTS.md` mais próximo pode acrescentar regras específicas de uma subárvore, sem enfraquecer privacidade, segurança ou preservação do trabalho existente.

## Antes de agir

1. Leia integralmente:
   - `docs/PROJECT_CONTEXT.md`
   - `docs/UX_PRODUCT_STANDARD.md`
   - `README.md`
   - este arquivo e quaisquer `AGENTS.md` nas pastas afetadas.
2. Confira sem modificar:
   - `git status --short`
   - `git log --oneline -15`
   - estrutura relevante em `apps/`, `services/`, `ops/` e `docs/`.
3. Preserve mudanças preexistentes no worktree.
4. Descubra o que já existe antes de propor backlog ou arquitetura nova.

## Regras não negociáveis

- Nunca exponha ou registre segredos, tokens, OAuth, senhas, credenciais, áudio, vídeo ou transcrições privadas.
- UpexNote é local-first: material bruto não sai da máquina sem ação e consentimento explícitos.
- O transcript bruto é referência imutável; limpeza, formatação, resumo e estudo são derivados identificados.
- Novos domínios de banco usam schema PostgreSQL separado, em inglês.
- UI/UX é requisito arquitetural e segue `docs/UX_PRODUCT_STANDARD.md`.
- Administração usa menu lateral hierárquico; não transformar submódulos em navegação principal por abas horizontais.
- Não executar deploy, mudanças externas ou operações destrutivas sem autorização específica.
- Não confundir protótipo visual com funcionalidade concluída: operações precisam funcionar de ponta a ponta.

## Forma de trabalho

- Trabalhe com autonomia dentro da tarefa autorizada; evite pausas e perguntas que possam ser resolvidas pelo repositório.
- Para mudanças: inspecione, implemente, valide proporcionalmente ao risco e faça verificação visual quando houver UI.
- Em feedback visual, considere sempre largura real da janela, collapse do menu, margens, overflow, hover, foco, estados vazios, light/dark e textos longos.
- Prefira fluxos simples e intuitivos; complexidade técnica não deve aparecer desnecessariamente para o utilizador.
- Ao finalizar uma etapa autorizada:
  1. execute validações;
  2. atualize `docs/PROJECT_CONTEXT.md` quando houver mudança relevante de estado ou decisão;
  3. crie commit claro;
  4. faça push após autorização aplicável e confirmação de segurança.

## Fonte de verdade

Use esta prioridade:

1. código e estado real do repositório;
2. `docs/PROJECT_CONTEXT.md`;
3. documentos arquiteturais específicos;
4. `docs/UX_PRODUCT_STANDARD.md`;
5. `docs/FUTURE_PRODUCT_IDEAS.md` e `docs/AI_MEDIA_EVOLUTION.md` para possibilidades futuras;
6. conversas antigas apenas como contexto complementar.

Leia `docs/ACCOUNT_CONTINUITY_HANDOFF.md` quando houver troca de conta, sessão ou agente.

## Vocabulário do utilizador

- “Ambiente” significa o navegador do Codex com os acessos de trabalho, não uma pasta ou documento do repositório.
- O ambiente costuma incluir GitHub, Google Cloud/API, Hostinger, EasyPanel/VPS e webmail.
- Não registrar cookies, sessões, senhas ou tokens desses serviços.
