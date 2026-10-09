"""
Tests for the Pydantic data models (models.py).

Run with:
    uv run pytest tests/test_models.py -v

Adjust the import below to match your actual project structure
(e.g. `from src.models import ...` if models.py lives in src/).
"""
import json
import uuid
from pathlib import Path

import pytest
from pydantic import ValidationError

from models import (
    AnsweredQuestion,
    MinimalAnswer,
    MinimalSearchResults,
    MinimalSource,
    RagDataset,
    StudentSearchResults,
    StudentSearchResultsAndAnswer,
    UnansweredQuestion,
)


# ---------------------------------------------------------------------------
# 1. Basic construction / validation
# ---------------------------------------------------------------------------

def test_minimal_source_valid() -> None:
    src = MinimalSource(
        file_path="vllm/entrypoints/openai/api_server.py",
        first_character_index=267,
        last_character_index=400,
    )
    assert src.last_character_index > src.first_character_index


def test_minimal_source_rejects_wrong_types() -> None:
    with pytest.raises(ValidationError):
        MinimalSource(
            file_path="some/file.py",
            first_character_index="not_an_int",  # type: ignore[arg-type]
            last_character_index=400,
        )


def test_unanswered_question_autogenerates_id() -> None:
    q1 = UnansweredQuestion(question="What is vLLM?")
    q2 = UnansweredQuestion(question="What is vLLM?")
    # Each instance should get its own UUID, not share one / not be empty.
    assert q1.question_id != q2.question_id
    assert uuid.UUID(q1.question_id)  # raises if not a valid UUID string


def test_unanswered_question_preserves_provided_id() -> None:
    q = UnansweredQuestion(question_id="q1", question="What is vLLM?")
    assert q.question_id == "q1"


# ---------------------------------------------------------------------------
# 2. The tricky part: Union discrimination in RagDataset
# ---------------------------------------------------------------------------

def test_rag_dataset_distinguishes_answered_vs_unanswered() -> None:
    raw = {
        "rag_questions": [
            {
                "question_id": "q1",
                "question": "What is vLLM?",
                "sources": [
                    {
                        "file_path": "README.md",
                        "first_character_index": 0,
                        "last_character_index": 50,
                    }
                ],
                "answer": "vLLM is an inference engine.",
            },
            {
                "question_id": "q2",
                "question": "How do I install it?",
            },
        ]
    }
    dataset = RagDataset.model_validate(raw)

    q1, q2 = dataset.rag_questions
    # q1 has sources/answer -> must be parsed as AnsweredQuestion, not
    # silently downgraded to UnansweredQuestion (which would just drop
    # the extra fields).
    assert isinstance(q1, AnsweredQuestion)
    assert q1.answer == "vLLM is an inference engine."
    assert len(q1.sources) == 1

    assert isinstance(q2, UnansweredQuestion)
    assert not isinstance(q2, AnsweredQuestion)


def test_rag_dataset_rejects_missing_required_fields() -> None:
    # "question" is the required field for even the minimal UnansweredQuestion
    # omitting it should fail validation rather than silently produce a
    # half-populated object.
    bad = {"rag_questions": [{"not_question": "oops"}]}
    with pytest.raises(ValidationError):
        RagDataset.model_validate(bad)


# ---------------------------------------------------------------------------
# 3. Round-trip: parse real provided dataset files, dump, and diff
# ---------------------------------------------------------------------------

# Point this at your actual downloaded dataset files.
DATASET_PATHS = [
    Path("data/datasets/AnsweredQuestions/dataset_docs_public.json"),
    Path("data/datasets/AnsweredQuestions/dataset_code_public.json"),
    Path("data/datasets/UnansweredQuestions/dataset_docs_public.json"),
    Path("data/datasets/UnansweredQuestions/dataset_code_public.json"),
]


@pytest.mark.parametrize("path", DATASET_PATHS)
def test_real_dataset_round_trip(path: Path) -> None:
    if not path.exists():
        pytest.skip(f"{path} not found locally - skipping round-trip test")

    original_raw = json.loads(path.read_text(encoding="utf-8"))

    # Parse into our model.
    dataset = RagDataset.model_validate(original_raw)

    # Dump back out. `by_alias=False` since we're not using aliases here;
    # `exclude_none=False` to make sure optional-looking fields aren't
    # silently dropped.
    round_tripped = json.loads(dataset.model_dump_json())

    # Question count must match exactly - nothing silently lost.
    assert len(round_tripped["rag_questions"]) == len(original_raw
                                                      ["rag_questions"])

    # Spot-check every question_id from the original survives the round trip.
    original_ids = {q["question_id"] for q in original_raw["rag_questions"] if
                    "question_id" in q}
    round_tripped_ids = {q["question_id"] for q in
                         round_tripped["rag_questions"]}
    assert original_ids.issubset(round_tripped_ids)


# ---------------------------------------------------------------------------
# 4. Search-results / answer models
# ---------------------------------------------------------------------------

def test_student_search_results_shape() -> None:
    result = StudentSearchResults(
        search_results=[
            MinimalSearchResults(
                question_id="q1",
                question="How to configure OpenAI server?",
                retrieved_sources=[
                    MinimalSource(
                        file_path="docs/serving/openai_compatible_server.md",
                        first_character_index=9867,
                        last_character_index=10100,
                    )
                ],
            )
        ],
        k=10,
    )
    dumped = json.loads(result.model_dump_json())
    assert dumped["k"] == 10
    assert dumped["search_results"][0]["question_id"] == "q1"
    assert "answer" not in dumped["search_results"][0]


def test_student_search_results_and_answer_shape() -> None:
    result = StudentSearchResultsAndAnswer(
        search_results=[
            MinimalAnswer(
                question_id="q1",
                question="How to configure OpenAI server?",
                retrieved_sources=[
                    MinimalSource(
                        file_path="docs/serving/openai_compatible_server.md",
                        first_character_index=9867,
                        last_character_index=10100,
                    )
                ],
                answer="To configure the OpenAI compatible server in vLLM...",
            )
        ],
        k=10,
    )
    dumped = json.loads(result.model_dump_json())
    assert dumped["search_results"][0]["answer"].startswith("To configure")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
