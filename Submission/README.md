# IndusBrain — Submission Package

**ET AI Hackathon 2026 · Problem Statement 8 — AI for Industrial Knowledge Intelligence: Unified Asset & Operations Brain**

Everything needed to submit, present and hand over IndusBrain.

---

## What is in this folder

| File | What it is | Use it for |
|---|---|---|
| **IndusBrain_Submission_Document.pdf** | The formal submission document, 19 pages | **This is the file you upload.** |
| **IndusBrain_Submission_Document.docx** | Same document, editable | Adding team names, screenshots or last-minute edits |
| **DEMO_SCRIPT.md** | Timed 3–4 minute demo script with narration | Recording the demo video |
| **DEMO_PROMPTS.md** | 11 prompts, each executed against the live system with its measured score | Rehearsing, and as a fallback if a prompt underperforms live |
| **COMMIT_MESSAGE.md** | The final Git commit message and pre-push checklist | Committing and pushing the repository |
| **build_submission_doc.js** | The generator that produced the DOCX | Regenerating the document after editing its content |

---

## Documents in the repository root

| File | What it covers |
|---|---|
| [`README.md`](../README.md) | Full project documentation — problem, solution, architecture, features, installation, API reference |
| [`TEAM_SETUP_GUIDE.md`](../TEAM_SETUP_GUIDE.md) | Step-by-step setup for a teammate starting from an empty machine, plus troubleshooting |
| [`ARCHITECTURE.md`](../ARCHITECTURE.md) | Condensed architecture reference |
| [`docs/srs.md`](../docs/srs.md) | Requirements specification with a conformance column |
| [`LICENSE`](../LICENSE) | MIT |

---

## Submission checklist

- [ ] Team member names filled in — `README.md` contributors table, `ARCHITECTURE.md` §7, and the DOCX title page
- [ ] Confirm **Problem Statement 8** is the statement your team registered for
- [ ] Screenshots captured and added to `docs/screenshots/`
- [ ] Repository pushed and, if the submission portal requires it, made public
- [ ] `backend/.env` confirmed **not** tracked by Git
- [ ] Demo video recorded, under the time limit, audio checked
- [ ] `IndusBrain_Submission_Document.pdf` uploaded

---

## Regenerating the submission document

Edit the content inside `build_submission_doc.js`, then:

```bash
cd Submission
node build_submission_doc.js
```

That rewrites the DOCX. To refresh the PDF, open the DOCX in Word and export as PDF, or
use LibreOffice:

```bash
soffice --headless --convert-to pdf IndusBrain_Submission_Document.docx
```

---

## Before you demo — 60-second sanity check

```bash
cd backend
python scripts/smoke_test.py
python scripts/verify_demo_prompts.py
```

Expected: 43 of 43 assertions pass, and all 11 demo prompts behave as expected.

If the knowledge graph looks empty, rebuild it without re-uploading anything:

```bash
curl -X POST http://localhost:8000/api/v1/ingestion/reindex-graph -H "X-IndusBrain-Role: manager"
```
