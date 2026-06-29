#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pb_correlate.py  -  CRAVA o campo do NUMERO SORTEADO da roleta Playtech.

================================================================================
O QUE FAZ
================================================================================
Depois que voce roda uma sessao com a captura de frames ligada, voce tem:

  1) logs/ptielive_frames.jsonl  -> os frames BINARIOS completos do WebSocket
                                     (wss://ielive-gateway.ptielive.com/ws),
                                     um frame por linha (JSON).
  2) os numeros que REALMENTE sairam (ground-truth), em ordem cronologica.

Esta ferramenta:
  - carrega e decodifica TODOS os frames (protobuf wire cru);
  - achata cada frame em caminhos de campo -> valor  (ex: "3.1.7" -> 5);
  - correlaciona cada (tipo_de_msg, caminho) com a sequencia real de numeros,
    testando o valor DIRETO e tambem o valor como INDICE-NA-RODA (WHEEL_LAYOUT);
  - rankeia os candidatos por taxa de acerto e imprime o VENCEDOR;
  - de quebra, detecta qual event-type (#3.1.7) marca os frames de resultado.

A ideia: voce nao precisa adivinhar o offset do protobuf. A verdade dos
numeros reais "ilumina" sozinha qual campo carrega o sorteio.

================================================================================
COMO USAR
================================================================================
1) Tenha os frames capturados:
       logs/ptielive_frames.jsonl

   Cada linha e um objeto JSON. O loader e TOLERANTE ao formato do payload e
   aceita qualquer um destes campos (nesta ordem de preferencia):
       payload_b64    : base64 dos bytes crus            (RECOMENDADO)
       payload_hex    : hex dos bytes crus
       payload_bytes  : repr de bytes  ("b'\\x0a...'")    (str(payload) do Python)
       payload        : idem payload_bytes
       payload_start  : repr truncado (fallback; pode perder o fim do frame)
   Campos opcionais usados p/ contexto: direction, url, ts/timestamp.

2) Tenha o ground-truth (numeros reais), de UMA destas formas:
       a) arquivo  logs/ground_truth.txt  -> um numero por linha, em ordem;
       b) via argv  -> ...py 7 32 0 15 ...
       c) via flag  -> --truth "7,32,0,15"

3) Rode:
       python -m tools.pb_correlate
       python tools/pb_correlate.py --truth "7,32,0,15,26"
       python tools/pb_correlate.py 7 32 0 15 26
       python tools/pb_correlate.py --frames logs/ptielive_frames.jsonl \
                                    --truth-file logs/ground_truth.txt

   Flags uteis:
       --frames <path>        caminho do .jsonl (default logs/ptielive_frames.jsonl)
       --truth-file <path>    caminho do ground_truth (default logs/ground_truth.txt)
       --truth "a,b,c"        ground-truth inline (virgula ou espaco)
       --only-game            so considera tipos "pt.live.game/*" (default: True)
       --all-types            considera TODOS os tipos de msg
       --min-hits <f>         taxa minima p/ aparecer no ranking (default 0.6)
       --top <n>              quantos candidatos listar (default 12)
       --dump-flatten <n>     imprime o flatten dos primeiros n frames e sai
                              (debug: ver os caminhos disponiveis)

Dependencia opcional: se existir core/playtech_decoder.py com uma funcao de
decode, ela e usada. Senao, esta ferramenta tem um parser wire embutido
(mesmo algoritmo do prototipo pbscout2.py) e roda 100% standalone.
================================================================================
"""

from __future__ import annotations

import argparse
import base64
import binascii
import json
import os
import struct
import sys
from collections import Counter, defaultdict

# ------------------------------------------------------------------ paths base
HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)                       # raiz do projeto
if PROJ not in sys.path:
    sys.path.insert(0, PROJ)

LOGS_DIR = os.path.join(PROJ, "logs")
DEFAULT_FRAMES = os.path.join(LOGS_DIR, "ptielive_frames.jsonl")
DEFAULT_TRUTH = os.path.join(LOGS_DIR, "ground_truth.txt")

# ------------------------------------------------------------------ wheel
# Layout europeu (mesma ordem usada em ai/smart_brain.py).
WHEEL_LAYOUT = [
    0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10, 5,
    24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26,
]
# posicao_na_roda -> numero
POS_TO_NUM = {pos: num for pos, num in enumerate(WHEEL_LAYOUT)}


# ============================================================================
# 1) DECODER  (usa core.playtech_decoder se houver; senao parser embutido)
# ============================================================================
def _load_external_decoder():
    """
    Tenta importar core.playtech_decoder e descobrir uma funcao de decode
    que receba bytes e devolva a arvore de campos. Aceita varios nomes comuns.
    Retorna (func, modulo) ou (None, None).
    """
    try:
        import core.playtech_decoder as ptd  # type: ignore
    except Exception:
        return None, None

    for name in ("decode_frame", "decode_bytes", "decode_payload", "decode", "parse"):
        fn = getattr(ptd, name, None)
        if callable(fn):
            return fn, ptd
    return None, ptd


def _read_varint(buf, i):
    shift = 0
    result = 0
    n = len(buf)
    while i < n:
        b = buf[i]
        i += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            return result, i
        shift += 7
        if shift > 63:          # varint malformado / truncado
            break
    raise IndexError("varint incompleto")


def _looks_text(b: bytes) -> bool:
    if not b:
        return False
    printable = sum(1 for c in b if 9 <= c <= 13 or 32 <= c <= 126)
    return printable / len(b) > 0.85


def _wire_decode(buf: bytes, depth: int = 0, maxd: int = 10):
    """
    Parser protobuf wire cru e recursivo. Tolerante a truncamento: para no
    primeiro byte que nao faz sentido em vez de estourar.
    Retorna lista de tuplas (numero_campo, tipo, valor), onde tipo e um de:
        "varint" | "i64" | "i32" | "str" | "bytes" | "msg"
    e em "msg" o valor e outra lista no mesmo formato.
    """
    out = []
    i = 0
    n = len(buf)
    while i < n:
        try:
            tag, i = _read_varint(buf, i)
        except IndexError:
            break
        field = tag >> 3
        wt = tag & 7
        if field == 0:
            break
        try:
            if wt == 0:                                   # varint
                v, i = _read_varint(buf, i)
                out.append((field, "varint", v))
            elif wt == 1:                                 # 64-bit
                if i + 8 > n:
                    break
                out.append((field, "i64", struct.unpack("<Q", buf[i:i + 8])[0]))
                i += 8
            elif wt == 2:                                 # length-delimited
                ln, i = _read_varint(buf, i)
                if ln < 0 or i + ln > n:
                    chunk = buf[i:n]
                    i = n
                else:
                    chunk = buf[i:i + ln]
                    i += ln
                sub = None
                if depth < maxd and chunk and not _looks_text(chunk):
                    try:
                        sub = _wire_decode(chunk, depth + 1, maxd)
                    except Exception:
                        sub = None
                if sub:
                    out.append((field, "msg", sub))
                elif _looks_text(chunk):
                    out.append((field, "str", chunk.decode("latin-1")))
                else:
                    out.append((field, "bytes", chunk))
            elif wt == 5:                                 # 32-bit
                if i + 4 > n:
                    break
                out.append((field, "i32", struct.unpack("<I", buf[i:i + 4])[0]))
                i += 4
            else:                                         # wt 3/4 (groups) -> para
                break
        except Exception:
            break
    return out


# decoder externo (se disponivel) tem prioridade
_EXT_DECODE, _EXT_MOD = _load_external_decoder()


def decode_frame(raw: bytes):
    """
    Decodifica os bytes de um frame para a arvore de campos.
    Normaliza qualquer retorno do decoder externo para o formato de tuplas
    (field, type, value) usado aqui. Em caso de duvida, cai no parser embutido.
    """
    if _EXT_DECODE is not None:
        try:
            tree = _EXT_DECODE(raw)
            norm = _normalize_tree(tree)
            if norm:
                return norm
        except Exception:
            pass
    return _wire_decode(raw)


def _normalize_tree(tree):
    """
    Aceita formatos comuns que um decoder externo pode devolver e converte
    para a lista de tuplas (field, type, value):
      - ja no formato de tuplas      -> retorna como esta;
      - dict {campo: valor}          -> converte (chaves viram numeros de campo);
      - lista de dicts c/ keys field/type/value.
    Retorna lista (possivelmente vazia) ou None se nao reconheceu.
    """
    if tree is None:
        return None
    # ja no formato (field, type, value)
    if isinstance(tree, list) and tree and isinstance(tree[0], tuple) and len(tree[0]) == 3:
        return tree
    # lista de dicts {field,type,value}
    if isinstance(tree, list) and tree and isinstance(tree[0], dict) and "field" in tree[0]:
        out = []
        for d in tree:
            f = int(d.get("field"))
            t = d.get("type", "varint")
            v = d.get("value")
            if t == "msg" and isinstance(v, (list,)):
                v = _normalize_tree(v) or []
            out.append((f, t, v))
        return out
    # dict {campo: valor}  (ex: {"3": {...}} ou {3: 5})
    if isinstance(tree, dict):
        out = []
        for k, v in tree.items():
            try:
                f = int(k)
            except (TypeError, ValueError):
                continue
            if isinstance(v, dict):
                out.append((f, "msg", _normalize_tree(v) or []))
            elif isinstance(v, (bytes, bytearray)):
                out.append((f, "bytes", bytes(v)))
            elif isinstance(v, str):
                out.append((f, "str", v))
            elif isinstance(v, bool):
                out.append((f, "varint", int(v)))
            elif isinstance(v, int):
                out.append((f, "varint", v))
            elif isinstance(v, list):
                # lista de sub-msgs ou repetido
                for item in v:
                    if isinstance(item, dict):
                        out.append((f, "msg", _normalize_tree(item) or []))
                    elif isinstance(item, int):
                        out.append((f, "varint", item))
            # floats/None ignorados (nao sao numero da roleta)
        return out
    return None


# ============================================================================
# 2) FLATTEN  (campo aninhado -> "3.1.7": valor)
# ============================================================================
def flatten_fields(tree, path: str = "", acc: dict | None = None) -> dict:
    """
    Achata a arvore para { "caminho.de.campo": valor_inteiro }.
    So coletamos valores escalares numericos (varint / i32 / i64), pois sao
    os unicos candidatos plausiveis a "numero sorteado".
    Caminhos repetidos (campo repetido no protobuf) viram listas.
    """
    if acc is None:
        acc = {}
    for field, typ, val in tree:
        p = f"{path}.{field}".lstrip(".")
        if typ == "msg":
            flatten_fields(val, p, acc)
        elif typ in ("varint", "i32", "i64"):
            if p in acc:
                if isinstance(acc[p], list):
                    acc[p].append(val)
                else:
                    acc[p] = [acc[p], val]
            else:
                acc[p] = val
        # str/bytes ignorados de proposito
    return acc


def _envelope_msgtype(tree) -> str:
    """
    Nome do tipo de msg = campo #1 string do envelope (ex 'pt.live.game/...').
    """
    for field, typ, val in tree:
        if field == 1 and typ == "str":
            return val
    return "?"


# ============================================================================
# 3) LOADER DE FRAMES (.jsonl, tolerante a formato de payload)
# ============================================================================
def _repr_to_bytes(s: str) -> bytes:
    """
    Converte um repr de bytes ("b'\\x0a...'") de volta para bytes, tolerante
    a truncamento. Mesma logica do prototipo (manual_repr_to_bytes).
    """
    s = s.strip()
    if s[:2] in ("b'", 'b"'):
        s = s[2:]
    out = bytearray()
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c in ("'", '"') and i == n - 1:
            break
        if c == "\\":
            if i + 1 >= n:
                break
            nxt = s[i + 1]
            if nxt == "x" and i + 3 < n:
                try:
                    out.append(int(s[i + 2:i + 4], 16))
                    i += 4
                    continue
                except ValueError:
                    break
            mp = {"n": 10, "r": 13, "t": 9, "\\": 92, "'": 39, '"': 34,
                  "0": 0, "a": 7, "b": 8, "f": 12, "v": 11}
            if nxt in mp:
                out.append(mp[nxt])
                i += 2
                continue
            out.append(ord(nxt))
            i += 2
            continue
        out.append(ord(c) & 0xFF)
        i += 1
    return bytes(out)


def _payload_to_bytes(rec: dict) -> bytes | None:
    """Extrai bytes crus de um registro do jsonl, na ordem de preferencia."""
    if "payload_b64" in rec and rec["payload_b64"]:
        try:
            return base64.b64decode(rec["payload_b64"])
        except (binascii.Error, ValueError):
            pass
    if "payload_hex" in rec and rec["payload_hex"]:
        try:
            return bytes.fromhex(rec["payload_hex"].replace(" ", ""))
        except ValueError:
            pass
    for key in ("payload_bytes", "payload", "payload_start"):
        if key in rec and isinstance(rec[key], str) and rec[key]:
            s = rec[key]
            if s[:2] in ("b'", 'b"'):
                return _repr_to_bytes(s)
            # talvez seja base64 ou hex "pelado"
            try:
                return base64.b64decode(s, validate=True)
            except (binascii.Error, ValueError):
                pass
            try:
                return bytes.fromhex(s.replace(" ", ""))
            except ValueError:
                pass
    return None


def load_frames(path: str, only_ptielive: bool = True) -> list[dict]:
    """
    Le o .jsonl e devolve uma lista de frames decodificados:
      { "ts": int|None, "url": str, "direction": str,
        "msgtype": str, "flat": {caminho: valor}, "raw_len": int }
    Mantem a ORDEM do arquivo (cronologica de captura).
    """
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Arquivo de frames nao encontrado: {path}\n"
            f"   Rode uma sessao com a captura ligada para gerar o .jsonl."
        )

    frames = []
    skipped = 0
    with open(path, "r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                continue

            url = rec.get("url", "") or ""
            if only_ptielive and "ptielive" not in url and url:
                continue

            raw = _payload_to_bytes(rec)
            if not raw:
                skipped += 1
                continue

            try:
                tree = decode_frame(raw)
            except Exception:
                skipped += 1
                continue

            ts = rec.get("ts") or rec.get("timestamp")
            try:
                ts = int(ts) if ts is not None else None
            except (TypeError, ValueError):
                ts = None

            frames.append({
                "ts": ts,
                "url": url,
                "direction": rec.get("direction", "received"),
                "msgtype": _envelope_msgtype(tree),
                "flat": flatten_fields(tree),
                "raw_len": len(raw),
            })

    if skipped:
        print(f"   (aviso: {skipped} linhas/frames ignorados por erro de parse)")
    return frames


# ============================================================================
# 4) GROUND-TRUTH
# ============================================================================
def load_ground_truth(args) -> list[int]:
    """Le os numeros reais de --truth, argv solto, ou --truth-file."""
    nums: list[int] = []

    raw = None
    if args.truth:
        raw = args.truth
    elif args.positionals:
        raw = " ".join(args.positionals)

    if raw:
        for tok in raw.replace(",", " ").split():
            tok = tok.strip()
            if tok.lstrip("-").isdigit():
                nums.append(int(tok))
    else:
        path = args.truth_file
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line and line.lstrip("-").isdigit():
                        nums.append(int(line))

    # so numeros validos de roleta
    nums = [n for n in nums if 0 <= n <= 36]
    return nums


# ============================================================================
# 5) CORRELACAO
# ============================================================================
def extract_candidate_sequences(frames: list[dict]) -> dict:
    """
    Para cada (msgtype, caminho), monta a sequencia ORDENADA de valores 0-36
    vistos naquele campo ao longo dos frames (na ordem cronologica).

    Retorna:
      seqs[(msgtype, path)] = [v0, v1, v2, ...]
    Apenas valores que cabem como numero (0-36) OU como indice-na-roda (0-36)
    entram; o teste de qual interpretacao vale acontece depois.
    """
    seqs: dict = defaultdict(list)
    for fr in frames:
        mt = fr["msgtype"]
        for path, val in fr["flat"].items():
            vals = val if isinstance(val, list) else [val]
            for v in vals:
                if isinstance(v, int) and 0 <= v <= 36:
                    seqs[(mt, path)].append(v)
    return seqs


def _score_against_truth(seq: list[int], truth: list[int]) -> tuple[int, int, str, int]:
    """
    Compara uma sequencia candidata com o ground-truth, testando 2 leituras:
      - DIRETO        : o valor JA E o numero;
      - INDICE-NA-RODA: o valor e a posicao -> WHEEL_LAYOUT[valor].
    Tambem tolera desalinhamento por 1 evento (offset 0 ou 1) no inicio, pois
    o frame de resultado pode chegar ligeiramente fora de fase.

    Retorna (acertos, comparados, modo, offset_aplicado).
    """
    best = (0, 0, "direto", 0)
    if not seq or not truth:
        return best

    for mode in ("direto", "indice"):
        if mode == "indice":
            conv = [POS_TO_NUM.get(v) for v in seq]
        else:
            conv = list(seq)

        # alinha pelo final (eventos mais recentes) e tolera pequeno offset
        for off in (0, 1, 2):
            cand = [c for c in conv if c is not None]
            if off:
                cand = cand[off:]
            m = min(len(cand), len(truth))
            if m == 0:
                continue
            # compara os ULTIMOS m de cada lado (alinhamento cronologico ao fim)
            a = cand[-m:]
            b = truth[-m:]
            hits = sum(1 for x, y in zip(a, b) if x == y)
            if (hits, m) > (best[0], best[1]) or \
               (hits == best[0] and m > best[1]):
                best = (hits, m, mode, off)
    return best


def correlate(frames, truth, only_game=True, min_hits=0.6):
    """
    Roda a correlacao completa e devolve a lista rankeada de candidatos:
      [ {key, msgtype, path, mode, offset, hits, total, rate}, ... ]
    """
    seqs = extract_candidate_sequences(frames)

    results = []
    for (mt, path), seq in seqs.items():
        if only_game and not mt.startswith("pt.live.game"):
            continue
        # ignora o contador de sequencia monotonico (#...100.1) e timestamps:
        # eles "acertariam" por acaso? Nao, valores 839+ ou epoch ms saem do
        # range 0-36, entao ja foram filtrados em extract_candidate_sequences.
        # campos com pouquissima amostra nao sao confiaveis
        if len(seq) < 1:
            continue
        hits, total, mode, off = _score_against_truth(seq, truth)
        if total == 0:
            continue
        rate = hits / total
        if rate < min_hits:
            continue
        results.append({
            "key": f"{mt}/{path}",
            "msgtype": mt,
            "path": path,
            "mode": mode,
            "offset": off,
            "hits": hits,
            "total": total,
            "rate": rate,
            "n_seen": len(seq),
        })

    # ranking: taxa desc, depois nº de comparacoes desc, depois mais amostras
    results.sort(key=lambda r: (r["rate"], r["total"], r["n_seen"]), reverse=True)
    return results


def detect_result_event_type(frames, winner) -> list[tuple[int, int]]:
    """
    Dado o campo vencedor, descobre qual #3.1.7 (event type) acompanha os
    frames que carregam o numero. Retorna [(event_type, contagem), ...] ord.
    """
    if not winner:
        return []
    mt = winner["msgtype"]
    path = winner["path"]
    counter = Counter()
    for fr in frames:
        if fr["msgtype"] != mt:
            continue
        if path not in fr["flat"]:
            continue
        ev = fr["flat"].get("3.1.7")
        if isinstance(ev, list):
            for e in ev:
                counter[e] += 1
        elif ev is not None:
            counter[ev] += 1
    return counter.most_common()


# ============================================================================
# 6) DEBUG: dump do flatten
# ============================================================================
def dump_flatten(frames, n):
    print(f"\n=== FLATTEN DOS PRIMEIROS {n} FRAMES ===")
    for idx, fr in enumerate(frames[:n]):
        print(f"\n[{idx}] msgtype={fr['msgtype']}  dir={fr['direction']}  "
              f"ts={fr['ts']}  raw={fr['raw_len']}b")
        for path, val in sorted(fr["flat"].items()):
            mark = "  <-- 0..36" if (isinstance(val, int) and 0 <= val <= 36) else ""
            print(f"    {path:>12} = {val}{mark}")


# ============================================================================
# MAIN
# ============================================================================
def build_argparser():
    ap = argparse.ArgumentParser(
        description="Crava automaticamente o campo do numero sorteado (Playtech).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("positionals", nargs="*",
                    help="numeros ground-truth soltos (ex: 7 32 0 15)")
    ap.add_argument("--frames", default=DEFAULT_FRAMES,
                    help=f"caminho do .jsonl (default {DEFAULT_FRAMES})")
    ap.add_argument("--truth-file", default=DEFAULT_TRUTH,
                    help=f"arquivo de ground-truth (default {DEFAULT_TRUTH})")
    ap.add_argument("--truth", default=None,
                    help='ground-truth inline, ex: --truth "7,32,0,15"')
    ap.add_argument("--only-game", action="store_true", default=True,
                    help="so tipos pt.live.game/* (default)")
    ap.add_argument("--all-types", action="store_true",
                    help="considera TODOS os tipos de msg")
    ap.add_argument("--min-hits", type=float, default=0.6,
                    help="taxa minima de acerto p/ ranking (default 0.6)")
    ap.add_argument("--top", type=int, default=12,
                    help="quantos candidatos listar (default 12)")
    ap.add_argument("--dump-flatten", type=int, default=0,
                    help="imprime flatten dos primeiros N frames e sai")
    return ap


def main(argv=None):
    args = build_argparser().parse_args(argv)
    only_game = not args.all_types and args.only_game

    print("=" * 70)
    print(" pb_correlate  -  caca ao campo do numero sorteado (Playtech)")
    print("=" * 70)
    print(f" decoder: {'core.playtech_decoder' if _EXT_DECODE else 'parser embutido (wire cru)'}")
    print(f" frames : {args.frames}")

    # carrega frames
    try:
        frames = load_frames(args.frames, only_ptielive=True)
    except FileNotFoundError as e:
        print(f"\nERRO: {e}")
        return 2

    if not frames:
        print("\nNenhum frame ptielive decodificavel encontrado no arquivo.")
        return 2
    print(f" frames ptielive carregados: {len(frames)}")

    # distribuicao de tipos (visao rapida)
    tipos = Counter(fr["msgtype"] for fr in frames)
    print("\n tipos de mensagem vistos:")
    for mt, c in tipos.most_common(15):
        print(f"   {c:>4}x  {mt}")

    # modo debug: so dumpa flatten
    if args.dump_flatten:
        dump_flatten(frames, args.dump_flatten)
        return 0

    # ground-truth
    args_for_truth = args
    truth = load_ground_truth(args_for_truth)
    if not truth:
        print("\nERRO: ground-truth vazio.")
        print("  Passe os numeros reais via:")
        print('    --truth "7,32,0,15"   ou   numeros soltos   ou   logs/ground_truth.txt')
        return 2
    print(f"\n ground-truth ({len(truth)} numeros): {truth}")

    # correlacao
    results = correlate(frames, truth, only_game=only_game, min_hits=args.min_hits)

    print("\n" + "-" * 70)
    if not results:
        print(" Nenhum campo bateu com o ground-truth acima do limiar.")
        print(" Dicas: rode com --all-types, baixe --min-hits 0.4, ou capture")
        print(" mais rodadas. Use --dump-flatten 5 p/ inspecionar os caminhos.")
        return 1

    print(" RANKING DE CANDIDATOS (campo -> bate com numeros reais)")
    print("-" * 70)
    print(f" {'#':>2} {'acertos':>9} {'taxa':>6} {'modo':>7} {'off':>3}  campo")
    for i, r in enumerate(results[:args.top], 1):
        modo = "RODA" if r["mode"] == "indice" else "dir"
        print(f" {i:>2} {r['hits']:>4}/{r['total']:<4} "
              f"{r['rate']*100:>5.0f}% {modo:>7} {r['offset']:>3}  {r['key']}")

    # vencedor
    win = results[0]
    modo_txt = ("INDICE-NA-RODA  (numero = WHEEL_LAYOUT[valor])"
                if win["mode"] == "indice" else "VALOR DIRETO")
    print("\n" + "=" * 70)
    print(f" CAMPO DO NUMERO = {win['key']}  ({win['hits']}/{win['total']} acertos)")
    print(f" interpretacao   = {modo_txt}")
    if win["offset"]:
        print(f" offset aplicado = {win['offset']} (desalinhamento temporal tolerado)")
    print("=" * 70)

    # event-type dos frames de resultado
    ev_dist = detect_result_event_type(frames, win)
    if ev_dist:
        top_ev = ev_dist[0][0]
        print(f"\n EVENT TYPE de resultado (#3.1.7) = {top_ev}")
        print("   distribuicao nos frames que carregam esse campo:")
        for ev, c in ev_dist:
            star = "  <== resultado" if ev == top_ev else ""
            print(f"     #3.1.7 = {ev:>3}  ({c}x){star}")
    else:
        print("\n (nao foi possivel cravar o #3.1.7 de resultado a partir deste campo)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
