"""
Utilitarios partilhados de pos-processamento de transcricoes (usados por
todos os motores): deteccao de alucinacoes/loops, correcao de pequenos
recuos de timestamp, e validacao automatica de cobertura.
"""
import re


def normalize(text):
    return re.sub(r"[^\w]", "", text.lower())


# Frases que os modelos Whisper/GPT-4o-transcribe sao conhecidos por
# "alucinar" (vem de dados de treino com legendas), sobretudo perto de
# silencio/fim de audio - nao foram ditas por ninguem na reuniao.
KNOWN_HALLUCINATIONS = [
    "legendas pela comunidade amara",
    "subtitles by the amara",
    "amara.org",
    "thank you for watching",
    "thanks for watching",
    "please subscribe",
]


def is_known_hallucination(text):
    norm = normalize(text)
    return any(normalize(p) in norm for p in KNOWN_HALLUCINATIONS)


def enforce_monotonic_segments(segments, hard_fail_threshold=10.0):
    """
    Corrige pequenos recuos de tempo entre segmentos consecutivos. Isto e
    comum quando o proprio modelo devolve segmentos com ligeira sobreposicao
    interna - nao e um bug do nosso mapa de timestamps. So regista sem
    corrigir os recuos >= hard_fail_threshold; esses sao grandes o
    suficiente para indicarem um bug real no pipeline e devem continuar a
    fazer a validacao falhar.
    """
    corrected = []
    corrections = []
    prev_end = None
    for idx, (s, e, t) in enumerate(segments):
        if prev_end is not None and s < prev_end:
            gap = prev_end - s
            if gap < hard_fail_threshold:
                corrections.append(
                    f"segmento {idx} ({t[:40]!r}): start ajustado de {s:.2f}s para {prev_end:.2f}s "
                    f"(recuo de {gap:.2f}s, provavel sobreposicao interna do modelo)"
                )
                s = prev_end
                if e < s:
                    e = s
        corrected.append((s, e, t))
        prev_end = e
    return corrected, corrections


def validate_segments(segments, original_duration, loop_events=None, end_tolerance=15.0):
    """
    Validacao automatica (nao apenas visual) dos segmentos finais, em tempo
    do audio ORIGINAL. Timestamps validos NAO significam conteudo valido -
    por isso esta funcao exige as duas coisas em simultaneo:
      - start >= 0
      - end >= start
      - start >= end do segmento anterior (nao pode recuar no tempo)
      - o ultimo "end" deve estar perto da duracao original do audio
      - ZERO eventos de alucinacao (loop_events) - se houver, o conteudo
        desses trechos esta corrompido mesmo que os timestamps batam certo
    Devolve (ok: bool, problemas: list[str]).
    """
    problems = []
    prev_end = None
    for idx, (s, e, t) in enumerate(segments):
        if s < 0:
            problems.append(f"segmento {idx} ({t[:40]!r}): start negativo ({s:.2f}s)")
        if e < s:
            problems.append(f"segmento {idx} ({t[:40]!r}): end < start ({e:.2f}s < {s:.2f}s)")
        if prev_end is not None and s < prev_end - 0.05:
            problems.append(
                f"segmento {idx} ({t[:40]!r}): start ({s:.2f}s) recua em relacao ao end do anterior ({prev_end:.2f}s)"
            )
        prev_end = e

    if segments:
        last_end = segments[-1][1]
        if abs(last_end - original_duration) > end_tolerance:
            problems.append(
                f"ultimo end ({last_end:.2f}s) longe da duracao original do audio ({original_duration:.2f}s)"
            )
    else:
        problems.append("nenhum segmento gerado")

    if loop_events:
        lost_seconds = sum(e["end"] - e["start"] for e in loop_events)
        problems.append(
            f"conteudo corrompido: {len(loop_events)} evento(s) de alucinacao detetados, "
            f"~{lost_seconds:.1f}s de audio potencialmente perdidos em texto repetido"
        )

    return (len(problems) == 0), problems


def detect_repeated_passages(segments, min_window=4, min_chars=60):
    """
    Deteta um BLOCO de min_window+ segmentos consecutivos cujo texto
    concatenado se repete integralmente mais tarde na transcricao - apanha
    alucinacoes de "paragrafo inteiro repetido" (tipico do gpt-4o-transcribe:
    repete um trecho de dialogo de varias frases, nao so uma frase isolada).
    mark_repetition_loops sozinho nao via isto, porque so olha para segmentos
    individuais identicos CONSECUTIVOS.

    Devolve lista de (repeat_start_idx, repeat_end_idx) - os indices (em
    "segments") da SEGUNDA ocorrencia (a copia a marcar); a primeira
    ocorrencia fica intacta.
    """
    n = len(segments)
    norm_texts = [normalize(s[2]) for s in segments]
    seen = {}
    repeats = []
    covered_until = -1
    i = 0
    while i + min_window <= n:
        if i <= covered_until:
            i += 1
            continue
        window_key = "".join(norm_texts[i:i + min_window])
        if len(window_key) >= min_chars:
            if window_key in seen:
                first_i = seen[window_key]
                j = 0
                while (i + min_window + j < n and
                       first_i + min_window + j < i and
                       norm_texts[first_i + min_window + j] == norm_texts[i + min_window + j]):
                    j += 1
                repeat_end = i + min_window + j
                repeats.append((i, repeat_end))
                covered_until = repeat_end - 1
            else:
                seen.setdefault(window_key, i)
        i += 1
    return repeats


def mark_repetition_loops(segments, min_repeats=3, high_confidence_repeats=20,
                           min_plausible_seconds=0.3, min_window=4):
    """
    Deteta 3 tipos de alucinacao, sem apagar nada do original:
      1. Segmentos individuais identicos repetidos min_repeats+ vezes seguidas
         - MAS so marca como alucinacao se for implausivel como fala real:
         ou repete demais (>= high_confidence_repeats, nunca acontece numa
         reuniao real) ou o tempo medio por repeticao e fisicamente
         impossivel (< min_plausible_seconds - ninguem diz uma palavra em
         0.1s). Repeticoes curtas com ritmo de fala normal (ex.: varias
         pessoas a dizerem "obrigada"/"tchau" seguidas no fecho de uma
         reuniao com muita gente) sao mantidas como conteudo legitimo -
         confirmado empiricamente: whisper-1 repetiu "Obrigada" 7x a ~1s
         cada (fala real), enquanto o gpt-4o-transcribe repetiu "Obrigado"
         658x a ~0.07s cada (impossivel, alucinacao de texto).
      2. Blocos de min_window+ segmentos consecutivos que se repetem
         integralmente mais tarde na transcricao (ver detect_repeated_passages)
         - estes ficam sempre marcados, independentemente da duracao, porque
         um paragrafo inteiro repetido palavra-por-palavra nunca e conteudo
         legitimo de varias pessoas.
      3. Frases isoladas conhecidas de alucinacao (KNOWN_HALLUCINATIONS),
         mesmo sem se repetirem.
    Devolve (annotated, loop_events). annotated e uma lista de
    (start, end, texto, loop_id_ou_None) para o transcript limpo decidir o
    que colapsar.
    """
    n = len(segments)
    loop_id_per_idx = [None] * n
    loop_events = []
    next_id = 1

    i = 0
    while i < n:
        norm = normalize(segments[i][2])
        j = i + 1
        while j < n and normalize(segments[j][2]) == norm and norm != "":
            j += 1
        repeat_count = j - i
        if repeat_count >= min_repeats:
            total_duration = segments[j - 1][1] - segments[i][0]
            avg_duration = total_duration / repeat_count if repeat_count else 0
            is_hallucination = (
                repeat_count >= high_confidence_repeats
                or avg_duration < min_plausible_seconds
            )
            if is_hallucination:
                for k in range(i, j):
                    loop_id_per_idx[k] = next_id
                loop_events.append({
                    "id": next_id, "text": segments[i][2], "count": repeat_count,
                    "start": segments[i][0], "end": segments[j - 1][1],
                })
                next_id += 1
        i = j

    for (rep_start, rep_end) in detect_repeated_passages(segments, min_window=min_window):
        if any(loop_id_per_idx[k] is not None for k in range(rep_start, rep_end)):
            continue
        for k in range(rep_start, rep_end):
            loop_id_per_idx[k] = next_id
        combined_text = " ".join(segments[k][2] for k in range(rep_start, rep_end))
        preview = combined_text[:80] + ("..." if len(combined_text) > 80 else "")
        loop_events.append({
            "id": next_id, "text": preview, "count": rep_end - rep_start,
            "start": segments[rep_start][0], "end": segments[rep_end - 1][1],
            "reason": f"paragrafo de {rep_end - rep_start} frases repetido integralmente (ja visto antes na transcricao)",
        })
        next_id += 1

    for idx, (s, e, t) in enumerate(segments):
        if loop_id_per_idx[idx] is None and is_known_hallucination(t):
            loop_id_per_idx[idx] = next_id
            loop_events.append({
                "id": next_id, "text": t, "count": 1, "start": s, "end": e,
                "reason": "frase conhecida de alucinacao (nao foi dita por ninguem)",
            })
            next_id += 1

    annotated = [(s, e, t, loop_id_per_idx[idx]) for idx, (s, e, t) in enumerate(segments)]
    return annotated, loop_events


def split_into_pseudo_segments(text, block_start, block_end):
    """
    Para modelos que so devolvem texto por bloco (sem timestamps internos,
    ex.: gpt-4o-transcribe), aproxima timestamps por frase distribuindo o
    tempo do bloco proporcionalmente ao comprimento de cada frase. Nao e tao
    exato como os timestamps reais do whisper-1, mas da uma leitura util.
    """
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    parts = [p.strip() for p in parts if p.strip()]
    if not parts:
        return []

    total_chars = sum(len(p) for p in parts) or 1
    total_duration = block_end - block_start
    segments = []
    cursor = block_start
    for p in parts:
        frac = len(p) / total_chars
        seg_end = cursor + frac * total_duration
        segments.append((cursor, seg_end, p))
        cursor = seg_end
    return segments
