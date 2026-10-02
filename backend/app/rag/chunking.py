"""Text chunking for the RAG index.

Splits on paragraphs, then lines, sentences and words, and packs the pieces into chunks of up to
CHUNK_SIZE characters with a small overlap between consecutive chunks.
"""

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
_SEPARATORS = ("\n\n", "\n", ". ", " ")


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = text.strip()
    if not text:
        return []
    return _merge(_split(text, chunk_size, _SEPARATORS), chunk_size, overlap)


def _split(text: str, size: int, separators: tuple[str, ...]) -> list[str]:
    if len(text) <= size:
        return [text]
    if not separators:
        return [text[i : i + size] for i in range(0, len(text), size)]

    separator, finer = separators[0], separators[1:]
    parts = text.split(separator)
    if len(parts) == 1:
        return _split(text, size, finer)

    pieces: list[str] = []
    for index, part in enumerate(parts):
        if index < len(parts) - 1:
            part += separator  # keep the boundary so merged chunks read naturally
        if part.strip():
            pieces.extend(_split(part, size, finer))
    return pieces


def _merge(pieces: list[str], size: int, overlap: int) -> list[str]:
    chunks: list[str] = []
    current = ""
    has_new_text = False  # guards against emitting a chunk that is only the previous overlap

    for piece in pieces:
        if has_new_text and len(current) + len(piece) > size:
            chunks.append(current.strip())
            current = _overlap_tail(current, overlap)
            has_new_text = False
        if len(current) + len(piece) > size:
            current = ""  # the overlap doesn't fit alongside this piece
        current += piece
        has_new_text = True

    if has_new_text and current.strip():
        chunks.append(current.strip())
    return chunks


def _overlap_tail(text: str, overlap: int) -> str:
    if overlap <= 0:
        return ""
    tail = text[-overlap:]
    first_space = tail.find(" ")
    # Start the overlap at a word boundary rather than mid-word.
    return tail[first_space + 1 :] if 0 <= first_space < len(tail) - 1 else tail
