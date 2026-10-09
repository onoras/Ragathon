# RAG Against the Machine — 7-Day Work Plan

**Start:** Monday
**Pace:** 8 focused hours/day
**Total budget:** ~50–55 hours (with Sunday as buffer, not a guaranteed bonus day)

## Guiding Rules (read before you start)

1. **Do not touch the LLM until retrieval is solid.** A perfect prompt cannot fix retrieval that never surfaces the right chunk. If Thursday's recall numbers are short of target, Friday morning is still retrieval-tuning time — not LLM time.
2. **Character-offset correctness on Tuesday is non-negotiable.** If chunk offsets are wrong, every recall number from Wednesday onward is meaningless, and you'll debug the wrong layer for days.
3. **Build your own `evaluate` command early (Wednesday, not later).** Never wait for an external grader to tell you if retrieval is working. You need a fast, local feedback loop before you can tune anything.
4. **Every day ends with a concrete, testable checkpoint** — not "made progress," but "this command runs and produces this correct output."
5. **Timebox tuning.** Recall tuning and prompt tuning are open-ended by nature. If a tuning session isn't producing gains after ~90 minutes, step back and check for a structural bug (path mismatch, offset error) before assuming it's a parameter problem.

---

## Day 1 — FoundationsCan

**Goal:** Environment is solid, data contracts are locked in, raw file access works.

| Time | Task |
|---|---|
| 09:00–09:30 | Re-read the assignment once, fully. Then close it and explain the full pipeline (indexing → retrieving → augmenting → generating) out loud or in writing, from memory. If you can't, re-read the weak section before moving on. |
| 09:30–10:30 | Project skeleton: `uv init`, `pyproject.toml`, folder structure (`src/`), `.gitignore` |
| 10:30–12:00 | Makefile: `install`, `run`, `debug`, `clean`, `lint`, `lint-strict` — confirm `flake8`/`mypy` run clean on the empty skeleton |
| 13:00–15:00 | Implement all Pydantic models (`MinimalSource`, `UnansweredQuestion`, `AnsweredQuestion`, `RagDataset`, `MinimalSearchResults`, `MinimalAnswer`, `StudentSearchResults`, `StudentSearchResultsAndAnswer`) |
| 15:00–16:00 | Round-trip test: load the provided public datasets into `RagDataset`, confirm validation passes, dump back to JSON and diff against the original |
| 16:00–17:30 | File ingestion: recursively walk the vLLM repo, decide inclusion rules (which extensions/dirs actually matter — probably `.py` and `.md`, exclude tests/binaries/caches), read raw file contents with correct encoding handling |

**End-of-day checkpoint:** Every provided dataset JSON parses cleanly into your Pydantic models. You can list every file you intend to index and read its raw content faithfully.

---

## Day 2 — Chunking (highest-risk day — do not rush)

**Goal:** Character-offset-correct chunking for both file types.

| Time | Task |
|---|---|
| 09:00–11:00 | Text/Markdown chunker: split by headings/paragraphs, respect max chunk size (default 2000, CLI-configurable via `--max_chunk_size`) |
| 11:00–12:00 | Offset sanity test: for a real `.md` file, verify `raw_file_content[first:last] == chunk_text` for **every** chunk produced |
| 13:00–16:00 | Python code chunker using `ast` — split by logical unit (function/class). If a unit exceeds `max_chunk_size`, recursively split it further (don't just truncate) |
| 16:00–17:00 | Same offset sanity test on 3–4 real `.py` files, including at least one unusually large one from the repo |
| 17:00–17:30 | Build a `debug_chunks.json` dump so you can visually eyeball whether splits look logical, not just offset-correct |

**Landmines to check before moving on:**
- [ ] Chunk length never exceeds `max_chunk_size` — add a defensive assertion on this. If the moulinette sees any oversized `MinimalSource`, it can reject the whole output file.
- [ ] `first_character_index`/`last_character_index` are computed against the **raw, unmodified file content** — not a stripped, re-joined, or otherwise transformed string.

**End-of-day checkpoint:** For any chunk of any file, slicing the original file content at `[first:last]` reproduces the chunk exactly. Chunk count for the full repo is roughly in the thousands (order of magnitude: low thousands to ~10k+), not dozens or hundreds of thousands.

---

## Day 3 — Indexing, Retrieval, and Your Own Evaluator

**Goal:** Working `index`, `search`, `search_dataset`, **and `evaluate`** — all in one day.

| Time | Task |
|---|---|
| 09:00–10:30 | Tokenizer v1: whitespace + punctuation splitting. Build vocabulary and document frequencies across all chunks |
| 10:30–12:00 | Implement BM25 (via `bm25s` or hand-rolled), persist index to `data/processed/`, wire into `index` CLI command. Time it — must finish well under 5 minutes |
| 13:00–14:00 | Implement `search` (single query → top-k `MinimalSource`s) |
| 14:00–15:30 | Implement `search_dataset` (batch over `RagDataset` → `StudentSearchResults` JSON, with a `tqdm` progress bar) |
| 15:30–17:00 | Implement your own `evaluate` command: same-file overlap check (≥5% overlap = "found"), recall@k aggregation. **Do this today, not later** — you need this feedback loop before Thursday's tuning work even starts. |
| 17:00–17:30 | Hand-verify the recall math on 2–3 toy examples you construct yourself, before trusting it on real data |

**Landmine to check now, before it silently zeroes out your recall tomorrow:**
- [ ] The `file_path` your `index`/`search` commands write into output JSON **exactly matches** the format used in the ground-truth dataset (e.g., don't include a `data/raw/` prefix if the dataset expects paths relative to the repo root). Test this explicitly — a mismatch here looks exactly like a retrieval-quality problem but is actually a string-formatting bug, and it can cost you an entire day if you don't catch it now.

**End-of-day checkpoint:** `index`, `search`, `search_dataset`, and `evaluate` all run end-to-end against the real repo and produce a recall number — even if that number isn't good yet.

---

## Day 4 — Retrieval Quality (LLM stays off)

**Goal:** Recall@5 ≥ 80% (docs) / ≥ 50% (code). If you don't hit it today, Friday morning continues this — do not move to the LLM until this is at or near threshold.

| Time | Task |
|---|---|
| 09:00–10:30 | Run baseline eval on both docs and code datasets. Record the starting numbers. |
| 10:30–12:00 | **Manual gut-check**, alongside the numeric eval: pick 5 questions, retrieve top-5 chunks, open those files yourself, and ask "could I answer this using only these chunks?" This catches problems the numeric score alone might mask (e.g., generous overlap counting hiding chunks that wouldn't actually help a human). |
| 13:00–14:00 | If code recall lags docs recall (likely, since the target itself is lower for code): fix the tokenizer to split identifiers — `camelCase` → `camel Case`, `snake_case` → `snake case`. Re-run eval. |
| 14:00–15:30 | If still short: sweep BM25 `k1`/`b` parameters (try `b=0.5` to reduce long-document penalty, try `k1=1.0` and `k1=1.5`). Re-run eval after each change — don't change multiple parameters at once, you won't know which one helped. |
| 15:30–17:00 | If still short: try overlapping/sliding-window chunking (e.g., 2000-char chunks sliding by 500 chars) to catch content that fell on a chunk boundary. This raises recall but also raises indexing time — make sure you're still under the 5-minute budget. |
| 17:00–17:30 | Record final numbers and what's left, if anything, for tomorrow morning. |

**End-of-day checkpoint:** Recall@5 hits or is close to 80%/50%. If not, you know exactly what's still missing and have a specific next experiment queued, not a vague "keep tuning."

---

## Day 5 — LLM Integration

**Gate before starting:** Thursday's recall is at or near threshold. If not, spend the first 1–2 hours of today closing that gap before writing any generation code.

**Goal:** Working `answer` and `answer_dataset`, with grounded, faithful, non-hallucinating output.

| Time | Task |
|---|---|
| 09:00–10:00 | *(Gate check — see above)* |
| 10:00–11:00 | Load Qwen/Qwen3-0.6B via `transformers`. Load the model **once** (singleton pattern), not per-call — this matters for your cold-start and throughput budgets later. |
| 11:00–12:00 | Build the prompt template: context block from retrieved chunks + question + explicit grounding instructions ("answer only from the provided context, cite sources, say so if the answer isn't present") |
| 13:00–15:00 | Implement `answer`. Iterate on the prompt until answers are self-contained, cite their source, and don't hallucinate outside the given context. Test against a handful of questions where you already know the right answer. |
| 15:00–16:30 | Implement `answer_dataset`. Add **defensive JSON parsing** on the model's raw output — a 0.6B model asked for structured output will sometimes wrap it in extra prose; extract just the answer field rather than assuming clean output. |
| 16:30–17:30 | Test throughput: run `answer_dataset` on a real dataset and check it's within the 90-second/1000-question budget. If it's too slow, look at batching or reducing redundant model calls before Saturday. |

**End-of-day checkpoint:** `answer_dataset` completes a full run within the performance budget, and spot-checked answers look reasonably grounded.

---

## Day 6 — Batch Hardening, Edge Cases, and Landmine Sweep

**Goal:** Nothing crashes, all CLI commands are robust, repo is evaluator-ready.

| Time | Task |
|---|---|
| 09:00–10:30 | Error handling pass: wrap risky I/O and model calls in try/except with clear messages. Test degenerate CLI inputs deliberately: `k=0`, negative `k`, empty query string, missing dataset file, malformed JSON. |
| 10:30–11:00 | **Landmine sweep** (see checklist below) — go through each item explicitly. |
| 11:00–12:00 | Full `flake8` + `mypy`/`mypy --strict` cleanup — read and actually fix the type issues, don't just silence them |
| 13:00–15:00 | Full clean-environment run-through: delete all generated data (`data/processed/`, `data/output/`), re-run `index` → `search_dataset` → `evaluate` → `answer_dataset` from scratch, exactly as an evaluator would |
| 15:00–17:00 | Write README.md: italicized first line with logins, Description, Instructions, Resources (+ AI usage disclosure — be specific about which tasks AI helped with), System architecture (ASCII diagram recommended), Chunking strategy, Retrieval method + chosen hyperparameters, Performance analysis (your actual recall@k numbers), Design decisions, Challenges faced, Example usage |
| 17:00–17:30 | Final repo check: confirm no large data/model files committed, `uv.lock` present, `src/` structure matches requirements, Makefile only uses `uv` (no stray `pip install`) |

**Landmine checklist (go through explicitly, don't just trust memory):**
- [ ] `file_path` output format matches the dataset's expected format exactly (re-verify, don't just trust Wednesday's fix still holds after later changes)
- [ ] No `MinimalSource` in any output JSON has `last_character_index - first_character_index > max_chunk_size` — add a defensive clamp/assertion in the retriever if needed
- [ ] Model output is parsed defensively — stray prose around the JSON doesn't break `answer`/`answer_dataset`
- [ ] Makefile uses only `uv` for `install` — an evaluator running `uv sync` should get everything needed, nothing silently installed via `pip`
- [ ] CLI never produces an unhandled traceback on bad input — this will be deliberately tested
- [ ] Indexing still completes in <5 minutes after all your tuning changes (sliding windows, larger tokenizer vocab, etc. can slow this down — re-time it)

**End-of-day checkpoint:** A stranger cloning your repo fresh could run the whole pipeline from the README alone, with no crashes, and get recall numbers at or above threshold.

---

## Day 7 — Buffer (use conditionally, don't assume it's free)

Priority order:
1. **If Thursday/Friday overran** (most likely candidates: recall tuning, throughput budget) — close that gap first. This is not optional buffer time if something is still broken.
2. If everything above is solid: attempt **one** bonus feature — semantic embeddings or hybrid retrieval are probably the best return on the time you have left, since they build directly on the BM25 pipeline you already have rather than requiring a new architecture.
3. If truly ahead of schedule: rest. You'll be sharper for the defense than if you spend the day still fiddling with parameters at midnight.

---

## Quick-Reference: What Must Be True Before Moving to the Next Day

| End of... | Must be true |
|---|---|
| Monday | All datasets validate against your Pydantic models; raw file reading works |
| Tuesday | `raw_content[first:last] == chunk_text` holds for every chunk, every file type |
| Wednesday | `index`, `search`, `search_dataset`, `evaluate` all run end-to-end; `file_path` format matches ground truth |
| Thursday | Recall@5 at or near 80% (docs) / 50% (code) |
| Friday | `answer_dataset` completes within throughput budget; answers are grounded on spot-check |
| Saturday | Full pipeline runs clean from scratch; lint/mypy clean; README complete |
| Sunday | Buffer spent closing real gaps, not new feature work, unless genuinely ahead |


---

## Reworked Work Plan

### Week 1 — New Monday (today): Chunking

**Goal:** Character-offset-correct chunking for both file types, `file_path` already in final `data/raw/vllm-0.10.1/...` form.

| Time | Task |
|---|---|
| 10:00–11:00 | Markdown chunker: heading-boundary detection + code-fence masking |
| 11:00–11:45 | Lunch |
| 11:45–13:00 | Markdown chunker: paragraph-level fallback (greedy packing) + line-aligned last resort |
| 13:00–14:00 | Offset sanity test on real `.md` files — `raw_content[first:last] == chunk_text` for every chunk, plus `file_path` format check |
| 14:00–16:30 | Python code chunker via `ast` — function/class-level split, line→offset lookup table |
| 16:30–17:30 | Offset sanity test on 3–4 real `.py` files, including one large one |
| 17:30–18:00 | `debug_chunks.json` dump for visual sanity check |

**Landmines:** chunk length never exceeds `max_chunk_size`; offsets always against raw untouched content; `file_path` exact-match format from the start.

**Checkpoint:** every chunk round-trips via slicing; chunk count in the low-thousands range, not dozens or hundreds of thousands.

---

### New Tuesday: Indexing, Retrieval, Your Own Evaluator

**Goal:** Working `index`, `search`, `search_dataset`, and `evaluate` — all today.

| Time | Task |
|---|---|
| 10:00–11:00 | Tokenizer v1 (whitespace/punctuation split), build vocabulary + doc frequencies |
| 11:00–11:45 | Lunch |
| 11:45–13:00 | BM25 implementation, persist index under `data/processed/`, wire into `index` command — time it against the 5-minute budget |
| 13:00–14:00 | `search`: single query → top-k `MinimalSource`s |
| 14:00–15:30 | `search_dataset`: batch mode, `tqdm` progress bar, `--save_directory` scoped by dataset |
| 15:30–17:00 | Your own `evaluate` command: same-file + ≥5% overlap check, recall@k aggregation |
| 17:00–18:00 | Hand-verify recall math on 2–3 toy examples before trusting it on real data; run once end-to-end on the real repo |

**Landmine:** verify `file_path` output matches ground truth verbatim — test this explicitly today, don't assume yesterday's convention survived unchanged into the index.

**Checkpoint:** all four commands run end-to-end on the real repo, producing a recall number — even a bad one.

---

### New Wednesday: Retrieval Quality Tuning (LLM stays off)

**Goal:** Recall@5 ≥ 80% (docs) / ≥ 50% (code), or as close as possible.

| Time | Task |
|---|---|
| 10:00–11:00 | Baseline eval on both datasets, record starting numbers |
| 11:00–11:45 | Lunch |
| 11:45–13:00 | Manual gut-check: 5 questions, top-5 chunks, "could a human answer this from just these?" |
| 13:00–14:00 | If code recall lags: tokenizer fix for identifier splitting (`camelCase`/`snake_case`); re-run eval |
| 14:00–16:00 | If still short: BM25 `k1`/`b` sweep — one parameter at a time, re-eval after each |
| 16:00–17:30 | If still short: sliding-window chunking experiment; re-check the 5-minute indexing budget still holds |
| 17:30–18:00 | Record final numbers + exact next experiment if not yet at threshold |

**Checkpoint:** recall at or near threshold, with a specific next step queued if not — not a vague "keep tuning."

---

### New Thursday (short day — ~4.5 net hours, 10:00–13:00 + 16:00–18:00)

**Goal:** Low-risk prep work for LLM integration. Nothing here should be on the critical path if it runs long — this is deliberately the lightest day.

| Time | Task |
|---|---|
| 10:00–11:00 | Gate check: is Wednesday's recall at/near threshold? If not, this becomes recall-tuning continuation instead of moving on. |
| 11:00–11:30 | Lunch |
| 11:30–13:00 | Load Qwen/Qwen3-0.6B via `transformers` as a singleton (load once, not per-call) |
| *13:00–16:00 blocked* | |
| 16:00–18:00 | Draft the grounding prompt template (context block + question + explicit "answer only from context, cite sources, say if absent" instructions). Sketch only — don't need working `answer` yet. |

**Checkpoint:** model loads successfully in isolation; you have a first-draft prompt template written down, even if untested end-to-end.

---

### New Friday: LLM Integration

**Goal:** Working `answer` and `answer_dataset`, grounded and within budget.

| Time | Task |
|---|---|
| 10:00–11:00 | Implement `answer`: wire prompt template + model into single-query flow |
| 11:00–11:45 | Lunch |
| 11:45–13:30 | Iterate on prompt against a handful of known-answer questions until grounded/non-hallucinating |
| 13:30–15:00 | Implement `answer_dataset` with defensive JSON parsing (model may wrap output in stray prose) |
| 15:00–16:30 | Throughput test: 200 questions within 90s (v2.0's actual budget — lighter than the old 1000q/90s target) |
| 16:30–18:00 | Buffer for prompt/throughput fixes if needed |

**Checkpoint:** `answer_dataset` completes within budget; spot-checked answers look reasonably grounded.

---

### Week 2 — New Monday: Hardening

**Goal:** Nothing crashes, all CLI commands robust.

| Time | Task |
|---|---|
| 10:00–11:00 | Error handling pass: try/except with clear messages on risky I/O and model calls |
| 11:00–11:45 | Lunch |
| 11:45–13:00 | Deliberate degenerate-input testing: `k=0`, negative `k`, empty query, missing files, malformed JSON |
| 13:00–14:00 | Landmine sweep (see checklist below) |
| 14:00–16:00 | Full `flake8` + `mypy`/`mypy --strict` cleanup — fix, don't silence |
| 16:00–18:00 | Full clean-environment run-through: delete generated data, re-run `index → search_dataset → evaluate → answer_dataset` from scratch |

**Landmine checklist:**
- [ ] `file_path` format still matches ground truth exactly (re-verify — don't trust it just because it worked Tuesday)
- [ ] No `MinimalSource` exceeds `max_chunk_size`/`max_context_length`
- [ ] Model output parsed defensively against stray prose
- [ ] Makefile `install` uses only `uv`
- [ ] No unhandled traceback on any bad CLI input
- [ ] Indexing still under 5 minutes after all tuning changes

---

### Week 2 — New Tuesday: README + Final Checks

| Time | Task |
|---|---|
| 10:00–11:00 | README: italicized first line, Description, Instructions |
| 11:00–11:45 | Lunch |
| 11:45–13:30 | README: Resources (+ AI usage disclosure), System architecture (diagram), Chunking strategy, Retrieval method + hyperparameters |
| 13:30–15:00 | README: Performance analysis (real recall@k numbers), Design decisions, Challenges faced, Example usage |
| 15:00–16:00 | Final repo check: no large files/model weights committed, `uv.lock` present, `src/` layout matches v2.0's expected structure exactly |
| 16:00–18:00 | Re-run the full pipeline one more time from a genuinely clean clone if possible |

**Checkpoint:** a stranger cloning your repo fresh could run the whole pipeline from the README alone, with no crashes, recall at/above threshold.

---

### Week 2 — New Wednesday: Buffer

Priority order, same logic as before:
1. Close any real gap from Wednesday/Friday (recall or throughput) first — not optional.
2. If solid: attempt one bonus (hybrid retrieval or semantic embeddings — best return given they build directly on your existing BM25 pipeline).
3. If genuinely ahead: stop and rest rather than fiddling with parameters.

---

## Quick Reference

| End of... | Must be true |
|---|---|
| New Mon | Every chunk round-trips via offsets; `file_path` format locked in |
| New Tue | `index/search/search_dataset/evaluate` all run end-to-end |
| New Wed | Recall@5 at/near 80% docs / 50% code |
| New Thu | Model loads as singleton; prompt draft exists |
| New Fri | `answer_dataset` within 200q/90s budget, grounded on spot-check |
| Wk2 Mon | Full pipeline clean-run, lint/mypy clean |
| Wk2 Tue | README complete, repo matches expected layout |
| Wk2 Wed | Buffer spent on real gaps or one bonus, not new scope |

Want to jump straight into today's Markdown heading-detection code, or is there anything about this retiming you'd want adjusted first?
