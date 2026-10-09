from dataclasses import dataclass
from typing import List
import re


@dataclass(frozen=True)
class Chunk:
    text: str
    first_char_index: int
    last_char_index: int
    file_path: str


@dataclass
class Section:
    heading_path: List[str]
    content: str
    start: int
    end: int


class MarkdownChunker:
    def __init__(self, max_chunk_size: int = 2000, overlap: int = 200):
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap

    def chunk(self, text: str, file_path: str) -> List[Chunk]:
        blocks = self._split_into_blocks(text)
        sections = self._build_section_tree(blocks)
        chunks = []
        for section in sections:
            chunks.extend(self._chunk_section(section, file_path))
        return chunks

    def _split_into_blocks(self, text: str) -> List[dict]:
        pattern = re.compile(r'^#{1,6} .*$', re.MULTILINE)
        matches = list(pattern.finditer(text))
        if not matches:
            return [{'content': text, 'start': 0, 'end': len(text)}]
        blocks = []
        if matches[0].start() > 0:
            blocks.append({
                'content': text[:matches[0].start()],
                'start': 0,
                'end': matches[0].start(),
            })
        for i, m in enumerate(matches):
            start = m.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            blocks.append({'content': text[start:end],
                           'start': start, 'end': end})
        return blocks

    def _chunk_section(self, section: dict, file_path: str) -> List[Chunk]:
        content = section['content']
        if len(content) <= self.max_chunk_size:
            return [Chunk(content, section['start'], section['end'],
                          file_path)]
        return self._split_long_text(content, section['start'], file_path)

    def _split_long_text(self, text: str, base_start: int,
                         file_path: str) -> List[Chunk]:
        paragraphs = self._split_into_paragraphs(text)
        chunks = []
        chunk_start = None
        chunk_end = None
        for p_start, p_end in paragraphs:
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
        if chunks >= self.max_chunk_size:
            return KeyError
        return chunks

    def _split_into_paragraphs(self, text: str) -> List[tuple]:
        paragraphs = []
        for m in re.finditer(r'[^\n]+(?:\n[^\n]+)*', text):
            if m.group(0).strip():
                paragraphs.append((m.start(), m.end()))
        return paragraphs
