"""
Utilitario partilhado: divide um ficheiro de audio/video em blocos WAV (16kHz mono).
Os cortes de bloco sao feitos em pontos de silencio (nao a meio de frases), seguindo
a recomendacao da OpenAI: "avoid breaking the audio up mid-sentence".

iter_wav_chunks() nao toca no conteudo do audio - usado pela Deepgram, que ja
trata silencio corretamente por si so.

iter_wav_chunks_skip_silence() e so para a OpenAI/whisper-1: salta trechos de
silencio longos (para evitar alucinacao em loop), mas preserva um mapa exato
para converter os timestamps devolvidos de volta para o audio original -
os tempos finais NAO ficam desalinhados.
"""
import io
import wave
import numpy as np
import av


def load_full_audio(path, sample_rate=16000):
    container = av.open(path)
    stream = container.streams.audio[0]
    resampler = av.AudioResampler(format="s16", layout="mono", rate=sample_rate)
    chunks = []
    for frame in container.decode(stream):
        for rframe in resampler.resample(frame):
            chunks.append(rframe.to_ndarray())
    container.close()
    audio = np.concatenate(chunks, axis=1).flatten()
    return audio, sample_rate


def _find_quiet_point(audio, center, search_radius, window=800):
    lo = max(0, center - search_radius)
    hi = min(len(audio), center + search_radius)
    if hi - lo <= window:
        return center
    best_idx = center
    best_energy = None
    step = max(window // 2, 1)
    for i in range(lo, hi - window, step):
        seg = audio[i:i + window]
        energy = np.abs(seg.astype(np.int64)).mean()
        if best_energy is None or energy < best_energy:
            best_energy = energy
            best_idx = i + window // 2
    return best_idx


def _chunk_boundaries(total, chunk_samples, audio, search_radius):
    if total <= chunk_samples:
        return [0, total]
    boundaries = [0]
    pos = chunk_samples
    while pos < total:
        split = _find_quiet_point(audio, pos, search_radius)
        split = max(split, boundaries[-1] + 1)
        boundaries.append(split)
        pos = split + chunk_samples
    boundaries.append(total)
    return boundaries


def _wav_bytes(seg, sr):
    buf = io.BytesIO()
    w = wave.open(buf, "wb")
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(sr)
    w.writeframes(seg.tobytes())
    w.close()
    return buf.getvalue()


def iter_wav_chunks(path, chunk_seconds=1500, sample_rate=16000, search_radius_seconds=5):
    """
    Gera tuplos (start_sec, end_sec, wav_bytes). NAO altera o audio (silencio
    incluido, sem cortes). Garante cobertura total (soma dos blocos = duracao
    total), com o corte entre blocos escolhido num ponto de silencio local
    para nao partir frases a meio.
    """
    audio, sr = load_full_audio(path, sample_rate)
    total = len(audio)
    chunk_samples = int(chunk_seconds * sr)
    search_radius = int(search_radius_seconds * sr)
    boundaries = _chunk_boundaries(total, chunk_samples, audio, search_radius)

    for i in range(len(boundaries) - 1):
        start, end = boundaries[i], boundaries[i + 1]
        yield (start / sr, end / sr, _wav_bytes(audio[start:end], sr))


def detect_speech_intervals(audio, sample_rate, silence_amplitude=500, min_gap_seconds=2.0, pad_seconds=0.3):
    """
    Devolve lista de intervalos (start_sample, end_sample) com fala, fundindo
    pausas curtas (< min_gap_seconds, ficam intactas no audio) e so "saltando"
    silencios longos (>= min_gap_seconds). Mantem pad_seconds de audio real
    (nao sintetico) em cada lado do corte, para uma transicao suave.
    """
    abs_audio = np.abs(audio.astype(np.int32))
    is_silent = abs_audio < silence_amplitude
    n = len(audio)
    min_gap_samples = int(min_gap_seconds * sample_rate)
    pad_samples = int(pad_seconds * sample_rate)

    long_silences = []
    i = 0
    while i < n:
        if is_silent[i]:
            j = i
            while j < n and is_silent[j]:
                j += 1
            if j - i >= min_gap_samples:
                long_silences.append((i, j))
            i = j
        else:
            i += 1

    intervals = []
    prev_end = 0
    for (cut_start, cut_end) in long_silences:
        seg_start = prev_end
        seg_end = min(cut_start + pad_samples, n)
        if seg_end > seg_start:
            intervals.append((seg_start, seg_end))
        prev_end = max(cut_end - pad_samples, seg_end)
    if prev_end < n:
        intervals.append((prev_end, n))

    return intervals


def iter_wav_chunks_skip_silence(path, chunk_seconds=1500, sample_rate=16000, search_radius_seconds=5,
                                  min_gap_seconds=2.0, splice_gap_seconds=0.3):
    """
    Como iter_wav_chunks, mas primeiro remove silencios longos (>= min_gap_seconds)
    do audio enviado ao modelo (evita alucinacao em loop do whisper-1 durante
    silencio prolongado). Insere splice_gap_seconds de silencio sintetico entre
    trechos colados, para evitar cliques na juncao.

    Devolve (generator_de_chunks, to_original, original_duration_seconds).
    to_original(t) converte um timestamp no audio enviado (compacto) de volta
    para o timestamp no audio original, para os timestamps finais NAO ficarem
    desalinhados do video. original_duration_seconds e a duracao real do
    audio original (para validar cobertura no fim).
    """
    audio, sr = load_full_audio(path, sample_rate)
    original_duration_seconds = len(audio) / sr
    intervals = detect_speech_intervals(audio, sr, min_gap_seconds=min_gap_seconds)

    splice_samples = int(splice_gap_seconds * sr)
    splice_buf = np.zeros(splice_samples, dtype=audio.dtype)

    pieces = []
    # time_map cobre TODO o audio compacto sem buracos: (c_start, c_end, o_start, o_end).
    # Inclui entradas para os buffers de splice (mapeadas para o intervalo de silencio
    # original que representam), para que nenhum timestamp devolvido pela API caia
    # num ponto sem mapeamento.
    time_map = []
    cursor = 0
    for idx, (s, e) in enumerate(intervals):
        piece = audio[s:e]
        pieces.append(piece)
        c_start = cursor / sr
        cursor += len(piece)
        c_end = cursor / sr
        time_map.append((c_start, c_end, s / sr, e / sr))
        if idx < len(intervals) - 1:
            pieces.append(splice_buf)
            splice_c_start = cursor / sr
            cursor += splice_samples
            splice_c_end = cursor / sr
            next_orig_start = intervals[idx + 1][0] / sr
            time_map.append((splice_c_start, splice_c_end, e / sr, next_orig_start))

    removed_total = (len(audio) - sum(len(p) for p in pieces)) / sr
    audio_compact = np.concatenate(pieces) if pieces else audio
    if removed_total > 1:
        print(f"Silencio longo saltado (nao enviado ao modelo): {removed_total:.1f}s no total "
              f"(timestamps finais mantem-se alinhados ao video original)")

    def to_original(t_compact_global):
        if not time_map:
            return t_compact_global
        for (c_start, c_end, o_start, o_end) in time_map:
            if c_start <= t_compact_global <= c_end + 1e-6:
                span = c_end - c_start
                if span <= 0:
                    return o_start
                frac = (t_compact_global - c_start) / span
                return o_start + frac * (o_end - o_start)
        # t esta para alem do fim mapeado (nao devia acontecer) - usa o ultimo ponto
        last = time_map[-1]
        return last[3] + (t_compact_global - last[1])

    total = len(audio_compact)
    chunk_samples = int(chunk_seconds * sr)
    search_radius = int(search_radius_seconds * sr)
    boundaries = _chunk_boundaries(total, chunk_samples, audio_compact, search_radius)

    def gen():
        for i in range(len(boundaries) - 1):
            start, end = boundaries[i], boundaries[i + 1]
            yield (start / sr, end / sr, _wav_bytes(audio_compact[start:end], sr))

    return gen(), to_original, original_duration_seconds
