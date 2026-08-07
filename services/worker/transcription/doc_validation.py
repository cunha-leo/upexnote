"""
Gate de validacao raw<->clean (ADF-01, decisao 05/08/2026):

  "Antes de qualquer geracao de documento formatado, o sistema cruza raw e
  clean para confirmar que nenhum contexto foi perdido na limpeza. Só depois
  dessa validacao passar o clean segue para a formatacao."

O clean ja existe desde a transcricao (transcript_utils.mark_repetition_loops
marca/oculta loops de alucinacao detetados) — este modulo NAO reprocessa
audio nem mexe no clean; ele so confere, de forma independente, se a
diferenca de tamanho entre raw e clean é compatível com "só removeu
repetição/ruído" ou se parece ter perdido conteúdo real.

HEURISTICA v1 (documentada como tal de proposito): compara a razao de
palavras entre clean e raw. Perdas grandes e inexplicadas (clean muito menor
que o raw) sao a assinatura de um corte indevido; perdas pequenas/moderadas
sao esperadas (loops de alucinacao removidos, marcacoes de tempo mortas).
Isto NAO e um diff semantico - e uma rede de seguranca antes de gastar
dinheiro/tempo formatando algo que perdeu contexto. Pode ser refinada depois
(ex.: comparar nomes proprios/numeros preservados) sem mudar o contrato
{ok, ratio, problems} usado pelo chamador.
"""
import re

# Abaixo disto, a perda e' grande demais pra ser só ruído/loop removido.
MIN_WORD_RATIO_OK = 0.55
# Entre MIN_WORD_RATIO_OK e este valor: passa, mas com aviso (nao bloqueia).
MIN_WORD_RATIO_WARN = 0.75


def _word_count(text: str) -> int:
    if not text:
        return 0
    return len(re.findall(r"\w+", text, flags=re.UNICODE))


def validate_raw_clean(raw_text: str, clean_text: str) -> dict:
    """Devolve {"ok": bool, "ratio": float, "problems": [str, ...]}.

    ok=False bloqueia a formatacao (ver document-generate no cli.py) — a
    pessoa precisa de rever o transcript antes de gastar numa formatacao que
    partiria de uma base incompleta.
    """
    problems = []

    raw_words = _word_count(raw_text)
    clean_words = _word_count(clean_text)

    if raw_words == 0 and clean_words == 0:
        return {"ok": False, "ratio": 0.0, "problems": ["raw e clean estao ambos vazios."]}
    if raw_words == 0:
        # Sem raw pra comparar (transcricoes antigas/importadas sem raw
        # guardado) — nao bloqueia, so avisa. O clean e a unica fonte que existe.
        problems.append("Sem transcript raw disponivel para comparar — validacao limitada ao clean.")
        return {"ok": True, "ratio": None, "problems": problems}
    if clean_words == 0:
        return {"ok": False, "ratio": 0.0, "problems": ["Transcript clean esta vazio; nao ha o que formatar."]}

    ratio = clean_words / raw_words

    if ratio < MIN_WORD_RATIO_OK:
        problems.append(
            f"Clean tem só {ratio:.0%} das palavras do raw ({clean_words} de {raw_words}) — "
            f"perda maior do que o esperado só por remoção de ruído/repetição. Revê o transcript "
            f"antes de formatar."
        )
        return {"ok": False, "ratio": ratio, "problems": problems}

    if ratio < MIN_WORD_RATIO_WARN:
        problems.append(
            f"Clean tem {ratio:.0%} das palavras do raw ({clean_words} de {raw_words}) — "
            f"dentro do esperado para remoção de loops/ruído, mas vale conferir."
        )

    return {"ok": True, "ratio": ratio, "problems": problems}
