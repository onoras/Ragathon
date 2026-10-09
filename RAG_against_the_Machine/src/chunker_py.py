from dataclasses import dataclass
from typing import List
import ast


@dataclass(frozen=True)
class Chunk:
    text: str
    first_char_index: int
    last_char_index: int
    file_path: str


class PythonChunker:
    def __init__(self, max_chunk_size: int = 2000, overlap: int = 200):
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap

    def chunk(self, text: str, file_path: str) -> List[Chunk]:
        blocks = self._split_into_blocks(text)
        chunks = []
        for block in blocks:
            chunks.extend(self._chunk_block(block, file_path))
        return chunks

    def _split_into_blocks(self, text: str) -> List[dict]:
        tree = ast.parse(text)
        line_offsets = self._line_offsets(text)

        blocks = []
        last_end = 0
        for node in tree.body:
            end_lineno = getattr(node, 'end_lineno', node.lineno)
            end = line_offsets[end_lineno]
            blocks.append({'content': text[last_end:end], 'start': last_end,
                           'end': end})
            last_end = end

        if last_end < len(text):
            blocks.append({'content': text[last_end:], 'start': last_end,
                           'end': len(text)})

        return blocks

    def _line_offsets(self, text: str) -> List[int]:
        offsets = [0]
        for line in text.splitlines(keepends=True):
            offsets.append(offsets[-1] + len(line))
        return offsets

    def _chunk_block(self, block: dict, file_path: str) -> List[Chunk]:
        content = block['content']
        if len(content) <= self.max_chunk_size:
            return [Chunk(content, block['start'], block['end'], file_path)]
        return self._split_long_text(content, block['start'], file_path)

    def _split_long_text(self, text: str, base_start: int,
                         file_path: str) -> List[Chunk]:
        pieces = self._split_into_pieces(text)
        chunks = []
        chunk_start = None
        chunk_end = None

        for p_start, p_end in pieces:
            if chunk_start is None:
                chunk_start, chunk_end = p_start, p_end
                continue

            if p_end - chunk_start <= self.max_chunk_size:
                chunk_end = p_end
                continue

            chunks.append(Chunk(text[chunk_start:chunk_end],
                                base_start + chunk_start,
                                base_start + chunk_end,
                                file_path))

            overlap_start = max(chunk_end - self.overlap, chunk_start)
            chunk_start, chunk_end = overlap_start, p_end

        if chunk_start is not None:
            chunks.append(Chunk(text[chunk_start:chunk_end],
                                base_start + chunk_start,
                                base_start + chunk_end,
                                file_path))

        return chunks

    def _split_into_pieces(self, text: str) -> List[tuple]:
        pieces = []
        import re
        for m in re.finditer(r'[^\n]+(?:\n[^\n]+)*', text):
            if m.group(0).strip():
                pieces.append((m.start(), m.end()))
        return pieces
