# 🚀 Autonomous Open Source Contributor Engine

An intelligent scout, sandbox, and pull request engine for contributing to top-tier AI/ML, Vector Database, and RAG ecosystems with deterministic verification.

---

## 🏗️ Architecture

```
┌─────────────────┐       ┌────────────────────┐       ┌─────────────────────┐
│  Scout Engine   │ ───▶  │ Solvability Scorer │ ───▶  │  Isolated Sandbox   │
│  (Target Repos) │       │ (Filter un-PR'd)   │       │  (.sandboxes/)      │
└─────────────────┘       └────────────────────┘       └─────────────────────┘
                                                                  │
                                                                  ▼
┌─────────────────┐       ┌────────────────────┐       ┌─────────────────────┐
│ Pull Request    │ ◀───  │ Human-in-the-Loop  │ ◀───  │  Code & Test Gate   │
│ (gh pr create)  │       │ Verification & QA  │       │  (Pytest / Ruff)    │
└─────────────────┘       └────────────────────┘       └─────────────────────┘
```

---

## ⚡ Quick Start CLI

Run the tool directly using `python -m tools.contributor_engine`:

### 1. Scan for High-Impact, Solvable Issues
Scans all configured repositories in `config.yaml` for unassigned, un-PR'd issues and ranks them by Solvability Score:
```bash
python -m tools.contributor_engine scan
```
Filter for a specific repository:
```bash
python -m tools.contributor_engine scan --repo qdrant/fastembed --limit 5
```

### 2. Inspect an Issue
Fetch the full description, tracebacks, and error details:
```bash
python -m tools.contributor_engine view qdrant/fastembed 752
```

### 3. Fork and Sandbox
Automatically forks the repository to your GitHub account (`MOHITPRADHAN35`), clones it shallowly into `.sandboxes/`, and creates a dedicated branch:
```bash
python -m tools.contributor_engine prepare qdrant/fastembed 752 --branch fix/mean-pooling-dtype
```

### 4. Review Changes (Diff)
Check the git diff in the sandbox:
```bash
python -m tools.contributor_engine diff qdrant/fastembed
```

### 5. Submit Pull Request
Commits, pushes to your fork, and creates the PR on upstream:
```bash
python -m tools.contributor_engine submit qdrant/fastembed \
  --branch fix/mean-pooling-dtype \
  --title "fix(text): keep model dtype in mean pooling embeddings" \
  --body "Resolves #752. Retains float32 output for mean pooling models."
```
*(Add `--dry-run` to validate before opening public PRs)*

### 6. Clean Sandbox
Clean up temporary clone directories:
```bash
python -m tools.contributor_engine clean
```

---

## ⚙️ Configuration (`config.yaml`)
Customize your target repositories and monitored labels in `tools/contributor_engine/config.yaml`:
- Monitored ecosystems: `qdrant/fastembed`, `qdrant/qdrant-client`, `run-llama/llama_index`, `chroma-core/chroma`, `BerriAI/litellm`, `infiniflow/ragflow`, `Arize-ai/phoenix`, etc.
- Monitored labels: `good first issue`, `help wanted`, `bug`, `documentation`.
