# AGENTS — PROTOCOLO DE INICIALIZAÇÃO LIFE

Versão do protocolo: 1.0  
Responsável: Leonardo Cunha  
Status: ativo

# 1\. OBJETIVO

Este arquivo é uma instrução operacional para qualquer nova conversa ou projeto LIFE. Quando Leonardo pedir para ler este arquivo, inicializar o LIFE ou carregar o contexto LIFE, execute o protocolo inteiro sem pedir que ele repita seu histórico.

A sessão só pode ser considerada contextualizada depois de verificar e, quando necessário, ler integralmente os dois documentos canônicos nesta ordem:

Dossiê/Manifesto LIFE — identidade, trajetória, arquitetura cognitiva, método de trabalho, capacidades, limites e forma de interpretar Leonardo.

Contexto Vivo de Decisão — estado atual, fatos recentes, ramos ativos, ramos abstraídos, critérios, registros formais de decisão e próximos passos.

O Dossiê sempre vem primeiro. O Contexto Vivo sempre vem depois.

# 2\. PASTA E FONTES CANÔNICAS

Use exclusivamente a pasta abaixo como fonte oficial:

Pasta: 00- Manifesto\&Decisions  
ID: 1mTd5Zv12Pniqs2-YqF0IfUC0KoY-Wpsb  
URL: https://drive.google.com/drive/folders/1mTd5Zv12Pniqs2-YqF0IfUC0KoY-Wpsb

Não escolher cópias homônimas existentes em outras pastas.

Localize dentro dessa pasta a versão mais alta de cada família.

## Dossiê/Manifesto LIFE

Padrão: Dossie\_Leonardo\_Cunha\_LIFE\_v\<versão\>.docx  
Linha de base em 5 de agosto de 2026: v1.0  
Arquivo: Dossie\_Leonardo\_Cunha\_LIFE\_v1.0.docx  
ID: 1K6hfpV3F4cCu1yg2H5WMr0WCbbY286lu

## Contexto Vivo de Decisão

Padrão: Contexto\_Vivo\_Decisao\_Portugal\_Brasil\_Leonardo\_v\<versão\>.docx  
Linha de base em 5 de agosto de 2026: v2.4  
Arquivo: Contexto\_Vivo\_Decisao\_Portugal\_Brasil\_Leonardo\_v2.4.docx  
ID: 1K5fmbx5kLMY1UYB9anY-YVE\_P0uA\_\_Sx

As linhas de base não são fixas. Sempre verificar se existe versão posterior na pasta canônica.

# 3\. ESTADO MÍNIMO DA SESSÃO

Mantenha estes marcadores na sessão:

LIFE\_DOSSIER\_LOADED\_VERSION  
LIFE\_DOSSIER\_LOADED\_FILE\_ID  
LIFE\_DOSSIER\_LOADED\_MODIFIED\_TIME  
LIFE\_CONTEXT\_LOADED\_VERSION  
LIFE\_CONTEXT\_LOADED\_FILE\_ID  
LIFE\_CONTEXT\_LOADED\_MODIFIED\_TIME  
LIFE\_BOOTSTRAP\_COMPLETE

Não considerar um documento já lido apenas porque existem memórias, resumos, trechos, mensagens anteriores ou conhecimento aproximado. Ele só está carregado quando o conteúdo integral daquela versão foi lido nesta sessão e os marcadores correspondentes podem ser identificados.

# 4\. REGRA CONDICIONAL DE LEITURA

Para cada documento, compare versão, ID e data de modificação do Drive com o estado da sessão.

Ler integralmente quando ocorrer qualquer uma destas condições:

• não existe versão registrada na sessão;  
• não existe prova de leitura integral na sessão;  
• a versão do Drive é maior que a versão carregada;  
• o ID do arquivo mudou;  
• a data de modificação é posterior à registrada na sessão;  
• existe dúvida sobre cortes, lacunas, trechos omitidos ou leitura incompleta.

Não reler somente quando todas estas condições forem verdadeiras:

• a versão da sessão é idêntica à versão mais recente do Drive;  
• o ID é o mesmo;  
• a data de modificação é a mesma;  
• a leitura integral já foi concluída nesta sessão.

Se a sessão indicar versão maior do que a existente na pasta, não fazer downgrade silencioso. Informar a divergência e preservar a versão mais nova já carregada até localizar a fonte correta ou receber orientação de Leonardo.

# 5\. LEITURA INTEGRAL OBRIGATÓRIA

Quando a leitura for necessária:

• abrir o arquivo completo, não apenas o resultado de busca;  
• ler do início ao fim, em ordem;  
• ler todo o conteúdo textual, parágrafo por parágrafo e linha por linha;  
• não abstrair, não pular capítulos e não selecionar apenas partes relevantes;  
• não usar resumo, memória, índice, capa, snippet ou busca como substituto;  
• não interromper para pedir autorização entre blocos;  
• quando a ferramenta exigir leitura em partes, continuar automaticamente do ponto exato em que parou, sem lacunas nem duplicações;  
• não começar análise estratégica, aconselhamento ou atualização documental antes de concluir os dois documentos;  
• declarar claramente qualquer falha de acesso ou leitura e nunca afirmar leitura integral sem evidência operacional suficiente.

# 6\. ORDEM DE EXECUÇÃO

## ETAPA A — DESCOBERTA

Listar os arquivos da pasta canônica, identificar a maior versão do Dossiê e do Contexto Vivo e comparar versão, ID e data de modificação com o estado da sessão.

## ETAPA B — DOSSIÊ/MANIFESTO LIFE

Aplicar a regra condicional. Quando necessário, ler integralmente. Depois registrar versão, ID e data de modificação carregados.

## ETAPA C — CONTEXTO VIVO DE DECISÃO

Executar somente depois da Etapa B. Aplicar a mesma regra condicional. Quando necessário, ler integralmente. Depois registrar versão, ID e data de modificação carregados.

## ETAPA D — ATIVAÇÃO DA SESSÃO

Depois que os dois documentos estiverem atualizados:

• definir LIFE\_BOOTSTRAP\_COMPLETE \= true;  
• usar o Dossiê como base de identidade, método, capacidades e estilo cognitivo;  
• usar o Contexto Vivo como base do estado decisório atual e das prioridades;  
• continuar sem pedir que Leonardo repita informações já presentes nesses documentos.

# 7\. HIERARQUIA DE INTERPRETAÇÃO

Ao trabalhar depois da leitura, usar esta precedência:

1\. instrução explícita mais recente de Leonardo na conversa atual;  
2\. evidência primária e fatos datados;  
3\. Contexto Vivo mais recente para estado, decisões e prioridades;  
4\. Dossiê LIFE mais recente para identidade, método, capacidades e limites;  
5\. interpretações e hipóteses, sempre identificadas como tais.

O Dossiê não substitui uma decisão posterior registrada no Contexto Vivo. O Contexto Vivo não apaga a identidade e o método estruturados no Dossiê.

# 8\. FIDELIDADE E LIMITES

• preservar a terminologia, a arquitetura e os contrastes dos documentos;  
• não reduzir Leonardo a desenvolvedor, generalista superficial, analista burocrático ou testador manual;  
• não transformar hipótese em fato nem propaganda em evidência;  
• não reabrir ramo abstraído sem fato estrutural novo ou instrução explícita;  
• não sobrescrever versões anteriores ao atualizar documentos;  
• criar nova versão conforme o esquema definido no Contexto Vivo;  
• não carregar outros cadernos, cursos ou anexos no bootstrap inicial, salvo pedido explícito ou necessidade da tarefa.

## 8.1. VALIDAÇÃO VISUAL DE DOCUMENTOS

Quando o Dossiê, o Contexto Vivo ou outro documento canônico estiver em `DOCX` ou `PDF`, a leitura textual não substitui a renderização das páginas. Imagens, diagramas, tabelas, cabeçalhos, rodapés e elementos de layout também compõem o conteúdo integral.

Para tarefas de leitura visual, revisão, criação ou edição documental:

• converter `DOCX` para PDF com LibreOffice em modo headless;  
• rasterizar o PDF com Poppler ou ferramenta equivalente, gerando uma imagem por página;  
• conferir a contagem e revisar visualmente todas as páginas;  
• depois de qualquer edição, repetir a renderização e a revisão completas;  
• nunca afirmar leitura integral ou fidelidade visual quando as imagens ou páginas não puderam ser processadas;  
• em caso de falha, diagnosticar ferramentas, `PATH`, permissões, diretório temporário, URI do perfil, fontes e imagens antes de recorrer a extração textual.

Configuração conhecida desta máquina Windows:

```text
LibreOffice/soffice:
C:\Users\cunha\AppData\Local\Programs\LibreOfficeCodex\program\soffice.exe

Poppler (pdfinfo/pdftoppm):
C:\Users\cunha\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin
```

Se necessário, adicionar esses diretórios ao `PATH` do processo atual. No Windows, fornecer o perfil temporário do LibreOffice como URI válida `file:///C:/...`, preferencialmente gerada por `Path(...).resolve().as_uri()`, nunca como `file://C:\...`.

Em cloud ou outro ambiente, localizar ferramentas equivalentes. Se não houver capacidade real de renderizar páginas e imagens, declarar a limitação e não substituir silenciosamente a validação visual por leitura de texto.

# 9\. RESPOSTA AO CONCLUIR

Quando houve leitura:

Bootstrap LIFE concluído. Dossiê vX lido integralmente; Contexto Vivo vY lido integralmente; sessão atualizada.

Quando ambos já estavam carregados e idênticos:

Bootstrap LIFE verificado. Dossiê vX e Contexto Vivo vY já estavam integralmente carregados nesta sessão e permanecem idênticos às versões canônicas do Drive.

Quando apenas um precisou ser atualizado, informar qual foi relido, qual foi reaproveitado e as versões correspondentes.

Não apresentar resumo extenso automaticamente. O objetivo do bootstrap é absorver o contexto e ficar pronto para a tarefa seguinte.

# 10\. COMANDO DE ATIVAÇÃO RECOMENDADO

Leia o arquivo AGENTS.md da pasta 00- Manifesto\&Decisions e execute integralmente o protocolo de inicialização LIFE.

Depois disso, esta instrução deve conduzir toda a descoberta, comparação e leitura sem exigir que Leonardo reescreva o contexto.  
