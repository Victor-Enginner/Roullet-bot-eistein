"""
playtech_decoder.py — Decodificador STANDALONE do WebSocket binário da Playtech.

Objetivo
--------
Extrair, em tempo real, o NÚMERO SORTEADO da roleta a partir dos frames
Protocol-Buffers (wire format CRU, sem .proto) do gateway:
    wss://ielive-gateway.ptielive.com/ws

O protocolo NÃO é criptografado nem ofuscado: é 100% decodificável com um
parser wire genérico. Esta biblioteca não tem dependências externas (só
stdlib) e foi pensada para ser plugada no monitor (core/monitor.py) que já
mantém a conexão autenticada e intercepta os frames via
    page.on("websocket") -> ws.on("framereceived").

Estrutura do envelope (protobuf, confirmada nos logs)
-----------------------------------------------------
    #1 (string)  = nome do tipo de mensagem  (ex.: "pt.live.game/TableEventRequest")
    #3 (msg)     = payload da mensagem
    #4 (string)  = token de sessão
    #6 (varint)  = flags

Tipos de mensagem relevantes (pt.live.game/*)
---------------------------------------------
    gameRoundOver/1.0         -> FIM da rodada; carrega o NÚMERO SORTEADO
        #3.16.3.1.2 = 100 + numero  (offset-100)  <-- RESULTADO CRAVADO
        #3.11       = id da rodada
    GameEventRequest          -> evento de jogo; replica o número sorteado
        #3.118.1    = 100 + numero  (offset-100)  <-- RESULTADO CRAVADO
        #3.4.3.1.2  = 100 + numero  (offset-100)  (mesmo valor)
    TableEventRequest         -> stream de notificações AO VIVO da mesa
        #3.1.6  = timestamp epoch ms
        #3.1.7  = TIPO DE EVENTO (enum)  -> NÃO é o número
        #3.100.1 = contador de sequência (id de evento)
        (os frames capturados nos logs vieram só como notificação de 76 bytes)
    gameResultStatistics/1.0  -> estatística agregada
        #3.3[].2 = pares {key, count}; key = 100 + numero (offset-100 CONFIRMADO)
    JoinTableResponse         -> estado inicial da mesa (histórico recente)

O NÚMERO SORTEADO foi CRAVADO nos logs reais: em gameRoundOver e
GameEventRequest ele vem como (100 + numero). Confirmado em 2 rodadas:
raw 111 -> número 11, raw 135 -> número 35 (ids de rodada batem entre as
duas mensagens).

Codificações de número observadas
---------------------------------
    1) Valor de face direto         : varint 0..36
    2) Índice de posição na roda     : varint 0..36 -> WHEEL_LAYOUT[idx]
    3) Offset-100 (visto na estat.)  : varint 100..136 -> (valor - 100)

`extract_roulette_number` testa uma lista de CAMINHOS CANDIDATOS
(CANDIDATE_PATHS) e devolve o primeiro número plausível. Os primeiros
caminhos da lista são CONFIRMADOS (gameRoundOver / GameEventRequest); os
demais são hipóteses de reserva para outras variantes de mesa — fácil de
ajustar.
"""

from __future__ import annotations

import base64
import binascii
import json
import os
import struct
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constantes de domínio
# ---------------------------------------------------------------------------

#: Layout da roda europeia (single-zero), no sentido horário a partir do 0.
#: Usado para converter um ÍNDICE de posição na roda em valor de face.
WHEEL_LAYOUT: List[int] = [
    0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23,
    10, 5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26,
]

#: Offset confirmado na mensagem gameResultStatistics: a "key" de cada slot
#: de número vem como (100 + numero). Ex.: key 100 -> número 0, key 136 -> 36.
NUMBER_OFFSET: int = 100

# Tipo de um nó decodificado: (numero_campo, tipo_wire_legivel, valor)
#   tipo_wire_legivel in {"varint","i64","i32","str","bytes","msg"}
#   valor: int para varint/i64/i32; str para str; bytes para bytes;
#          List[DecodedField] para msg.
DecodedField = Tuple[int, str, Any]
Decoded = List[DecodedField]


# ---------------------------------------------------------------------------
# CAMINHOS CANDIDATOS para o número sorteado
# ---------------------------------------------------------------------------
# Cada caminho é uma tupla de números de campo aplicada SOBRE o payload (#3),
# ou seja, NÃO inclui o #3 do envelope — `extract_roulette_number` já entra
# no payload antes de aplicar o caminho.
#
# `encoding` diz como interpretar o varint encontrado:
#   "face"   -> valor é o número de face (0..36) direto
#   "wheel"  -> valor é um índice 0..36 na WHEEL_LAYOUT
#   "offset" -> valor é (NUMBER_OFFSET + numero); subtrai o offset
#   "auto"   -> tenta face; se não couber, tenta offset; (wheel é ambíguo,
#               então só é usado quando explicitamente pedido)
#
# Os primeiros caminhos são CONFIRMADOS (cravados decodificando frames reais
# de gameRoundOver e GameEventRequest nos logs — ver docstring do módulo).
# Os de baixo são HIPÓTESES de reserva para outras variantes de mesa.
# Para adicionar um caminho novo, basta inserir um dict {"path","encoding","note"}.
CANDIDATE_PATHS: List[Dict[str, Any]] = [
    # ====================== CONFIRMADOS (offset-100) ======================
    # gameRoundOver/1.0: o número final vem em #3.16.3.1.2 codificado como
    # (100 + numero). Validado em 2 rodadas: raw 111 -> 11, raw 135 -> 35.
    {"path": (16, 3, 1, 2), "encoding": "offset",
     "note": "[CONFIRMADO] gameRoundOver #3.16.3.1.2 (offset-100)"},
    # GameEventRequest: mesmo número em #3.118.1 (e replicado em #3.4.3.1.2).
    {"path": (118, 1), "encoding": "offset",
     "note": "[CONFIRMADO] GameEventRequest #3.118.1 (offset-100)"},
    {"path": (4, 3, 1, 2), "encoding": "offset",
     "note": "[CONFIRMADO] GameEventRequest #3.4.3.1.2 (offset-100)"},

    # ===================== HIPÓTESES DE RESERVA ==========================
    # --- A: campo dedicado dentro do bloco de evento #3.1 (face direto) ---
    {"path": (1, 8), "encoding": "face", "note": "evento #3.1.8 (logo apos o tipo) como face"},
    {"path": (1, 9), "encoding": "face", "note": "evento #3.1.9 como face"},
    {"path": (1, 10), "encoding": "face", "note": "evento #3.1.10 como face"},
    {"path": (1, 8), "encoding": "wheel", "note": "evento #3.1.8 como indice na roda"},

    # --- B: sub-mensagem de resultado embrulhada (#3.2 / #3.5) ---
    {"path": (2, 1), "encoding": "auto", "note": "result wrapper #3.2.1"},
    {"path": (5, 1), "encoding": "auto", "note": "result wrapper #3.5.1"},
    {"path": (5, 2), "encoding": "auto", "note": "result wrapper #3.5.2"},

    # --- C: offset-100 em outros estados da mesa ---
    {"path": (16, 3), "encoding": "offset", "note": "estado da mesa #3.16.3 (offset-100)"},
]


# ---------------------------------------------------------------------------
# Parser wire CRU
# ---------------------------------------------------------------------------

def read_varint(buf: bytes, i: int) -> Tuple[int, int]:
    """
    Lê um varint (base-128 little-endian) de `buf` a partir do índice `i`.

    Retorna `(valor, novo_indice)`. O bit 0x80 de cada byte indica
    "continua". Levanta IndexError se o buffer terminar no meio do varint.
    """
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
        if shift > 70:  # varint maior que 10 bytes: corrompido
            raise IndexError("varint excede 10 bytes (corrompido)")
    raise IndexError("varint truncado")


def zigzag_decode(n: int) -> int:
    """Decodifica um inteiro zigzag (sint32/sint64): n>>1 ^ -(n & 1)."""
    return (n >> 1) ^ -(n & 1)


def _looks_text(b: bytes) -> bool:
    """
    Heurística: o chunk parece texto imprimível?

    Considera ASCII imprimível (32..126) e whitespace comum (9..13).
    True se >85% dos bytes forem imprimíveis. Usado para distinguir
    string de sub-mensagem/bytes em campos length-delimited.
    """
    if not b:
        return False
    printable = sum(1 for c in b if 9 <= c <= 13 or 32 <= c <= 126)
    return printable / len(b) > 0.85


def _looks_submessage(chunk: bytes) -> bool:
    """
    Heurística: o chunk parece uma sub-mensagem protobuf válida?

    Tenta decodificar e exige que o parse consuma TODO o buffer sem sobra e
    que tenha pelo menos um campo com número de campo plausível (1..536870911).
    Isso reduz falsos positivos (ex.: tratar uma string como msg).
    """
    if not chunk:
        return False
    try:
        fields, consumed = _decode_strict(chunk)
    except Exception:
        return False
    return consumed == len(chunk) and len(fields) >= 1


def _decode_strict(buf: bytes) -> Tuple[Decoded, int]:
    """
    Decodifica `buf` de forma ESTRITA (sem recursão profunda), só para validar
    se é uma sub-mensagem bem-formada. Retorna (campos, bytes_consumidos).

    Diferente de `decode`, não tenta interpretar sub-mensagens recursivamente;
    serve apenas como teste de boa-formação para `_looks_submessage`.
    """
    out: Decoded = []
    i = 0
    n = len(buf)
    while i < n:
        tag, i = read_varint(buf, i)
        field = tag >> 3
        wt = tag & 7
        if field == 0:
            raise ValueError("campo 0 invalido")
        if wt == 0:
            v, i = read_varint(buf, i)
            out.append((field, "varint", v))
        elif wt == 1:
            if i + 8 > n:
                raise IndexError("i64 truncado")
            out.append((field, "i64", struct.unpack("<Q", buf[i:i + 8])[0]))
            i += 8
        elif wt == 2:
            ln, i = read_varint(buf, i)
            if i + ln > n:
                raise IndexError("length-delimited truncado")
            out.append((field, "bytes", buf[i:i + ln]))
            i += ln
        elif wt == 5:
            if i + 4 > n:
                raise IndexError("i32 truncado")
            out.append((field, "i32", struct.unpack("<I", buf[i:i + 4])[0]))
            i += 4
        else:
            raise ValueError(f"wire type {wt} invalido")
    return out, i


def decode(buf: bytes, depth: int = 0, max_depth: int = 12) -> Decoded:
    """
    Decodifica um buffer protobuf wire CRU em uma lista recursiva de campos.

    Cada item é `(numero_campo, tipo, valor)`, cobrindo os quatro wire types:
        0 -> "varint" (int)
        1 -> "i64"    (uint64 little-endian)
        2 -> "str" | "bytes" | "msg"  (length-delimited, com detecção heurística)
        5 -> "i32"    (uint32 little-endian)

    Para campos length-delimited (wire type 2), tenta nesta ordem:
      1. sub-mensagem (se `_looks_submessage` e não parece texto)  -> "msg"
      2. string imprimível (`_looks_text`)                          -> "str"
      3. bytes opacos                                               -> "bytes"

    É TOLERANTE a truncamento: ao encontrar bytes incompletos, devolve o que
    já decodificou em vez de levantar exceção (essencial para os logs cujo
    payload foi cortado em str(payload)[:2000]).
    """
    out: Decoded = []
    i = 0
    n = len(buf)
    while i < n:
        try:
            tag, i = read_varint(buf, i)
        except Exception:
            break
        field = tag >> 3
        wt = tag & 7
        if field == 0:
            break
        try:
            if wt == 0:
                v, i = read_varint(buf, i)
                out.append((field, "varint", v))
            elif wt == 1:
                if i + 8 > n:
                    break
                out.append((field, "i64", struct.unpack("<Q", buf[i:i + 8])[0]))
                i += 8
            elif wt == 2:
                ln, i = read_varint(buf, i)
                chunk = buf[i:i + ln]   # tolera truncamento: fatia o que houver
                i = min(i + ln, n)
                if depth < max_depth and not _looks_text(chunk) and _looks_submessage(chunk):
                    out.append((field, "msg", decode(chunk, depth + 1, max_depth)))
                elif _looks_text(chunk):
                    out.append((field, "str", chunk.decode("latin-1")))
                else:
                    out.append((field, "bytes", chunk))
            elif wt == 5:
                if i + 4 > n:
                    break
                out.append((field, "i32", struct.unpack("<I", buf[i:i + 4])[0]))
                i += 4
            else:
                break
        except Exception:
            break
    return out


# ---------------------------------------------------------------------------
# Frame de alto nível (envelope)
# ---------------------------------------------------------------------------

def parse_frame(raw_bytes: bytes) -> Dict[str, Any]:
    """
    Decodifica um frame WebSocket binário completo (envelope Playtech).

    Retorna um dict:
        {
          "type":    <str | None>,   # nome do tipo de msg (#1)
          "payload": <Decoded>,      # estrutura decodificada do payload (#3)
          "session": <str | None>,   # token de sessão (#4)
          "flags":   <int | None>,   # flags (#6)
          "raw":     <Decoded>,      # estrutura decodificada do envelope inteiro
        }

    Campos ausentes voltam como None / lista vazia. Nunca levanta exceção em
    frame malformado — devolve o que conseguiu extrair.
    """
    env = decode(raw_bytes)
    msg_type: Optional[str] = None
    payload: Decoded = []
    session: Optional[str] = None
    flags: Optional[int] = None

    for field, typ, val in env:
        if field == 1 and typ == "str":
            msg_type = val
        elif field == 3:
            if typ == "msg":
                payload = val
            elif typ == "bytes":
                # payload veio como bytes opacos (truncado p.ex.); decodifica o que der
                payload = decode(val)
        elif field == 4 and typ in ("str", "bytes"):
            session = val if typ == "str" else val.decode("latin-1", "ignore")
        elif field == 6 and typ == "varint":
            flags = val

    return {
        "type": msg_type,
        "payload": payload,
        "session": session,
        "flags": flags,
        "raw": env,
    }


# ---------------------------------------------------------------------------
# Navegação por caminho de campo
# ---------------------------------------------------------------------------

def get_path(decoded: Decoded, path: Iterable[int]) -> List[Any]:
    """
    Resolve um caminho de números de campo sobre uma estrutura decodificada.

    Como protobuf permite campos repetidos, retorna uma LISTA com todos os
    valores que casam o caminho (não apenas o primeiro). Para um caminho
    `(1, 7)`, navega no campo #1 (esperando msg) e coleta todos os #7 dentro.

    Os valores retornados são os "valores brutos" (int/str/bytes/Decoded).
    """
    current: List[Any] = [decoded]
    for key in path:
        nxt: List[Any] = []
        for node in current:
            if not isinstance(node, list):
                continue
            for field, _typ, val in node:
                if field == key:
                    nxt.append(val)
        current = nxt
        if not current:
            return []
    return current


# ---------------------------------------------------------------------------
# Interpretação de número sorteado
# ---------------------------------------------------------------------------

def _interpret_number(value: int, encoding: str) -> Optional[int]:
    """
    Converte um valor bruto em número de roleta (0..36) conforme a codificação.

    encoding:
        "face"   -> aceita 0..36 direto
        "wheel"  -> 0..36 como índice -> WHEEL_LAYOUT[idx]
        "offset" -> NUMBER_OFFSET + numero -> subtrai o offset
        "auto"   -> tenta face; senão tenta offset
    Retorna None se o valor não couber na codificação pedida.
    """
    if encoding == "face":
        return value if 0 <= value <= 36 else None
    if encoding == "wheel":
        return WHEEL_LAYOUT[value] if 0 <= value < len(WHEEL_LAYOUT) else None
    if encoding == "offset":
        n = value - NUMBER_OFFSET
        return n if 0 <= n <= 36 else None
    if encoding == "auto":
        if 0 <= value <= 36:
            return value
        n = value - NUMBER_OFFSET
        return n if 0 <= n <= 36 else None
    return None


def extract_roulette_number(raw_bytes: bytes) -> Optional[int]:
    """
    Tenta extrair o número sorteado (0..36) de um frame de RESULTADO.

    Percorre CANDIDATE_PATHS na ordem definida no topo do módulo e devolve o
    PRIMEIRO valor plausível encontrado. Suporta valor de face direto, índice
    de posição na roda (WHEEL_LAYOUT) e codificação offset-100.

    Retorna None se nenhum caminho candidato render um número válido — o que
    é esperado para frames que não sejam de resultado (ex.: notificações de
    76 bytes do TableEventRequest).

    Para diagnóstico/calibração, veja `extract_roulette_number_debug`, que
    retorna QUAL caminho casou.
    """
    result = extract_roulette_number_debug(raw_bytes)
    return result[0] if result else None


def extract_roulette_number_debug(
    raw_bytes: bytes,
) -> Optional[Tuple[int, Dict[str, Any]]]:
    """
    Igual a `extract_roulette_number`, mas retorna `(numero, candidato)` —
    o dict de CANDIDATE_PATHS que casou, mais o valor bruto encontrado —
    para facilitar a calibração dos caminhos. Retorna None se nada casar.
    """
    frame = parse_frame(raw_bytes)
    payload = frame["payload"]
    if not payload:
        return None

    for cand in CANDIDATE_PATHS:
        path = cand["path"]
        encoding = cand["encoding"]
        for raw_val in get_path(payload, path):
            if not isinstance(raw_val, int):
                continue
            num = _interpret_number(raw_val, encoding)
            if num is not None:
                info = dict(cand)
                info["raw_value"] = raw_val
                info["msg_type"] = frame["type"]
                return num, info
    return None


# ---------------------------------------------------------------------------
# Helpers de entrada (base64 / repr / jsonl)
# ---------------------------------------------------------------------------

def b64_frame_to_bytes(payload: str) -> bytes:
    """
    Converte um frame em base64 (string) para bytes.

    Tolera padding ausente (adiciona '=' até múltiplo de 4) e espaços/quebras
    de linha. Levanta binascii.Error se a string não for base64 válida.
    """
    s = "".join(payload.split())
    pad = (-len(s)) % 4
    s += "=" * pad
    return base64.b64decode(s)


def repr_to_bytes(payload: str) -> bytes:
    """
    Reconstrói bytes a partir de um `str(payload_bytes)` (repr Python b'...'),
    TOLERANTE a truncamento.

    Os logs antigos (logs/debug_*.json -> websocket_frames[].payload_start)
    guardam str(payload)[:2000], que corta o repr no meio. Este parser
    recupera o máximo possível sem depender de ast.literal_eval (que falha em
    repr truncado).
    """
    s = payload.strip()
    if s[:2] in ("b'", 'b"'):
        s = s[2:]
    out = bytearray()
    i = 0
    n = len(s)
    backslash = chr(92)
    simple = {"n": 10, "r": 13, "t": 9, backslash: 92, "'": 39,
              '"': 34, "0": 0, "a": 7, "b": 8, "f": 12, "v": 11}
    while i < n:
        c = s[i]
        if c in ("'", '"') and i == n - 1:
            break
        if c == backslash:
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
            if nxt in simple:
                out.append(simple[nxt])
                i += 2
                continue
            out.append(ord(nxt) & 0xFF)
            i += 2
            continue
        out.append(ord(c) & 0xFF)
        i += 1
    return bytes(out)


def decode_jsonl(path: str) -> Iterator[Dict[str, Any]]:
    """
    Lê um arquivo JSONL de frames (logs/ptielive_frames.jsonl) e itera os
    frames já decodificados.

    Formato esperado de cada linha (flexível — aceita várias chaves):
        {"direction": "...", "url": "...", "data_b64": "<base64>"}
        {"direction": "...", "url": "...", "payload_b64": "<base64>"}
        {"direction": "...", "url": "...", "payload_repr": "b'...'"}
        {"direction": "...", "url": "...", "payload_start": "b'...'"}  (legado)
        {"direction": "...", "url": "...", "hex": "0a1e..."}

    Para cada linha válida, faz yield de:
        {
          "direction": <str | None>,
          "url":       <str | None>,
          "bytes":     <bytes>,        # bytes reconstruídos do frame
          "frame":     <dict>,         # saída de parse_frame
          "number":    <int | None>,   # extract_roulette_number(bytes)
        }

    Linhas que não puderem ser interpretadas como bytes são ignoradas
    silenciosamente (mantém a iteração resiliente a logs sujos).
    """
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            raw = _row_to_bytes(obj)
            if raw is None:
                continue
            yield {
                "direction": obj.get("direction"),
                "url": obj.get("url"),
                "bytes": raw,
                "frame": parse_frame(raw),
                "number": extract_roulette_number(raw),
            }


def _row_to_bytes(obj: Dict[str, Any]) -> Optional[bytes]:
    """Extrai os bytes do frame de uma linha JSONL, testando chaves conhecidas."""
    for key in ("data_b64", "payload_b64", "b64", "base64"):
        if isinstance(obj.get(key), str):
            try:
                return b64_frame_to_bytes(obj[key])
            except (binascii.Error, ValueError):
                continue
    if isinstance(obj.get("hex"), str):
        try:
            return bytes.fromhex(obj["hex"].strip())
        except ValueError:
            pass
    for key in ("payload_repr", "payload_start", "payload"):
        if isinstance(obj.get(key), str):
            return repr_to_bytes(obj[key])
    return None


# ---------------------------------------------------------------------------
# Resumo legível (pretty-print) — útil em debug e no __main__
# ---------------------------------------------------------------------------

def pretty(decoded: Decoded, indent: int = 0) -> str:
    """Renderiza uma estrutura decodificada em texto indentado, legível."""
    lines: List[str] = []
    pad = "  " * indent
    for field, typ, val in decoded:
        if typ == "msg":
            lines.append(f"{pad}#{field} (msg):")
            lines.append(pretty(val, indent + 1))
        elif typ == "bytes":
            head = val[:24].hex()
            tail = "…" if len(val) > 24 else ""
            lines.append(f"{pad}#{field} (bytes, {len(val)}b): {head}{tail}")
        elif typ == "str":
            lines.append(f"{pad}#{field} (str): {val[:80]!r}")
        else:
            lines.append(f"{pad}#{field} ({typ}): {val}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Execução direta: lê o jsonl e imprime um resumo
# ---------------------------------------------------------------------------

DEFAULT_JSONL = os.path.join("logs", "ptielive_frames.jsonl")


def _run_main(path: str) -> None:
    """Lê o JSONL em `path`, decodifica e imprime um resumo agregado."""
    if not os.path.exists(path):
        print(f"[playtech_decoder] arquivo nao encontrado: {path}")
        print("Gere logs/ptielive_frames.jsonl no monitor (ws.on('framereceived'))")
        print("com linhas como: {\"direction\":\"received\",\"data_b64\":\"...\"}")
        return

    from collections import Counter

    total = 0
    by_type: Counter = Counter()
    numbers: List[int] = []
    examples: List[str] = []

    for rec in decode_jsonl(path):
        total += 1
        mtype = rec["frame"]["type"] or "<sem-tipo>"
        by_type[mtype] += 1
        if rec["number"] is not None:
            numbers.append(rec["number"])
            if len(examples) < 10:
                examples.append(
                    f"  -> numero {rec['number']:>2}  ({mtype}, dir={rec['direction']})"
                )

    print(f"[playtech_decoder] arquivo: {path}")
    print(f"frames lidos: {total}")
    print("\ntipos de mensagem:")
    for mtype, cnt in by_type.most_common():
        print(f"  {cnt:>5}  {mtype}")

    print(f"\nnumeros de roleta extraidos: {len(numbers)}")
    if examples:
        print("primeiros resultados:")
        print("\n".join(examples))
    if numbers:
        print(f"\nsequencia (ultimos 30): {numbers[-30:]}")
    else:
        print("(nenhum numero casou os CANDIDATE_PATHS — ajuste-os quando "
              "capturar um frame de resultado limpo)")


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_JSONL
    _run_main(target)
