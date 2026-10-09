## Description
<!-- Provide a concise summary of the change and its rationale -->

## Type of Change
- [ ] `feat`: New feature
- [ ] `fix`: Bug fix
- [ ] `docs`: Documentation update
- [ ] `refactor`: Code refactoring

## Verification & Guardrails Checklist
- [ ] **Branch Workflow**: Follows `feat/*`, `fix/*`, `docs/*`, or `refactor/*` per [WORKFLOW.md](file:///home/yien/Projects/panataanph/WORKFLOW.md).
- [ ] **Offline / Local-First**: No external AI APIs called (runs with local Ollama + PaddleOCR).
- [ ] **Privacy**: Sensitive documents remain in private `storage/` directory; never exposed to public static URLs.
- [ ] **Deterministic Scoring**: Evidence completeness score remains deterministic application code, not LLM output.
- [ ] **Tests & Quality**: Backend tests (`pytest tests/`) and frontend lint/tests pass locally.
