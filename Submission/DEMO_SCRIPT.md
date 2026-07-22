# IndusBrain — Demo Video Script

**Target length:** 3–4 minutes
**Tone:** talk like you're showing a friend something you built and are proud of. Not a sales pitch.

---

## Before you hit record

**Setup checklist:**

- [ ] Docker running, backend running, frontend running
- [ ] Refinery corpus loaded (13 documents indexed)
- [ ] Browser at `http://localhost:5173`, **zoom 100%**, window maximised
- [ ] Sidebar role set to **Manager**
- [ ] **Run the PUMP question once before recording** so the model is warm — first inference is
      always slower
- [ ] Close other tabs, silence notifications

**Critical timing decision:**

The local model takes 40–90 seconds per answer. In a 3-minute video you cannot wait for that twice.

**Recommended approach:** use **Retrieval only** mode for the live demo (instant, still fully cited),
then show one pre-generated **AI reasoning** answer that you ran before recording. Say so honestly —
*"I ran this one earlier so we're not sitting here waiting"* — judges respect that far more than an
awkward silence.

---

## [0:00 – 0:25] Opening + the problem

**Screen:** Overview page.

> "Hi, I'm Prem, and this is IndusBrain.
>
> We built this for the oil and gas sector — specifically a refinery's Crude Distillation Unit. A CDU
> runs on documents: OEM equipment manuals, engineering revision notices, maintenance logs, root-cause
> reports, safety standards, standard operating procedures. The problem is they live in seven to
> twelve disconnected systems that don't talk to each other.
>
> McKinsey found engineers spend about thirty-five percent of their time just *looking* for
> information. And there's a worse problem underneath that — around a quarter of India's experienced
> industrial engineers retire in the next decade, and a lot of what they know about this specific unit
> was never written down anywhere.
>
> So we built a knowledge brain for the CDU."

*Transition — gesture at the dashboard:*

> "This is a real refinery unit. Thirteen documents indexed, twenty-two pieces of equipment
> recognised automatically."

---

## [0:25 – 0:50] The hook — it found a contradiction on its own

**Screen:** point at the red banner on Overview.

> "And straight away, notice this. Nobody asked it to do this — while indexing, it found that two of
> our documents *disagree* with each other."

**Click the red banner → Conflicts page.**

> "The OEM manual says pump P-101A has a maximum discharge pressure of 285 PSI. But a later
> engineering revision notice says 340.
>
> On a real plant, that's how people get hurt. One engineer reads the old manual, another reads the
> revision, and they're both convinced they're right.
>
> IndusBrain flags it and — look at this — it recommends applying the *lower* value until an engineer
> formally resolves it. That's the conservative safety default."

---

## [0:50 – 1:35] The centrepiece — ask it about the conflict

**Click "Ask IndusBrain about this conflict".**

> "Now watch — one click. It opens a new conversation, and it's already written the whole question:
> the asset, both values, both source documents. I didn't copy anything."

**As the reasoning panel appears — point at it:**

> "And this is the multi-agent pipeline running. It classifies the question, picks a specialist agent —
> here it's the Knowledge Agent — then searches the documents, walks the knowledge graph, ranks the
> evidence, and composes an answer.
>
> Each stage lights up as it actually happens. That's not a loading animation, those are real pipeline
> stages."

**When the answer lands — read the key part:**

> "So it says 340 PSI *following the impeller change* — but only if four preconditions are met.
> Piping re-rated, relief valve reset, hydrostatic test passed, seal upgraded.
>
> And here's the part I'm actually proud of —"

**Point at the last line:**

> "It checked the maintenance log and found that relief valve PSV-1201 was *never actually reset*.
> It's an open action. So it concludes: keep operating at 285 PSI.
>
> That's three separate documents reasoned over together. No single person had that whole picture."

---

## [1:35 – 2:05] Evidence — the trust layer

**Click "Show evidence".**

> "And nothing here is a black box. Every claim traces back."

**Sources tab:**

> "Four sources, each with the actual passage and a relevance score. See this badge — *graph plus
> vector*? That means this passage was found independently by both the semantic search *and* the
> knowledge graph. That's our strongest evidence class."

**Click Decision replay tab:**

> "And this is the full execution trace — which agent ran, how many passages came from where, what
> the top relevance score was. It's written by the pipeline as it runs, so it's an actual audit trail."

**Click Confidence tab briefly:**

> "The confidence score is computed from measured retrieval quality — and we cap it at 95%, because
> no retrieval system should ever claim it's certain."

---

## [2:05 – 2:30] Honesty — the differentiator

**Type in the chat:** `What is quantum computing?`

> "One thing we were strict about. Watch what happens when I ask something that isn't in the
> documents."

**When it refuses:**

> "Zero percent confidence, zero citations, and it just says it doesn't know.
>
> Most RAG demos will happily hallucinate an answer here. For a plant, a confident wrong number about
> a pressure limit is more dangerous than no answer at all. So we made refusing the correct behaviour."

---

## [2:30 – 3:00] Breadth — the rest of the platform

*Move quickly here, roughly 8 seconds each.*

**Knowledge Explorer:**
> "Every asset it found, and which documentation each one is missing. E-1502 has no procedure
> coverage — that's a real gap it identified."

**Analytics:**
> "Knowledge health scoring, with the formula published right there. No mystery metrics."

**Impact Simulator:**
> "You can test a decision before making it — and if there's no evidence, it refuses rather than
> inventing numbers."

**Documents → click a filename:**
> "And you can open any source document right inside the app, including the extracted text exactly as
> the system indexed it."

---

## [3:00 – 3:20] Roles

**Switch sidebar role to Engineer.**

> "Two roles. Managers curate the corpus — upload, replace, delete. Engineers get full read access but
> can't change the shared knowledge base."

**Point at Documents — upload controls gone:**

> "Same page, different capabilities. And this is enforced on the server — the API returns 403 even if
> you bypass the UI.
>
> One honest note: for this demo we made role switching instant so you can try both without creating
> accounts. Full authentication is built — bcrypt hashing, revocable sessions — it's one config flag
> away. We just prioritised showing you the AI."

---

## [3:20 – 3:45] Close

**Back to Overview.**

> "So that's IndusBrain. Hybrid GraphRAG over a real knowledge graph, a multi-agent reasoning
> pipeline, automatic conflict detection, and organizational memory — all running locally, no cloud,
> no API keys.
>
> The thing we cared about most: every single answer is traceable. If it can't prove it, it says so.
>
> Because the point isn't to build another chatbot. It's to make sure that when an engineer with
> thirty years of experience retires, what they knew doesn't leave with them.
>
> Thanks for watching."

---

## Delivery notes

**Do:**
- Pause after the PSV-1201 discovery — that's your strongest moment, let it land
- Say "I ran this one earlier" if you show a pre-generated answer
- Speak at normal pace; it's better to cut a section than to rush

**Don't:**
- Read this script word for word — use it as a route, not a transcript
- Apologise for anything
- Say "as you can see" repeatedly

**If you overrun:** cut the Analytics and Impact Simulator mentions (section 2:30–3:00) down to a
single sentence. The conflict story is what wins.

**If something breaks live:** say *"one second, let me restart that"* and keep going. Judges have seen
demos break. What they remember is whether you stayed composed.

---

## One-page cue card

| Time | Screen | Key line |
|---|---|---|
| 0:00 | Overview | *"35% of an engineer's time is spent searching"* |
| 0:25 | Conflicts | *"Two documents disagree — 285 vs 340 PSI"* |
| 0:50 | Ask (auto-submitted) | *"One click, question already written"* |
| 1:20 | Answer | *"PSV-1201 was never reset — so use 285"* |
| 1:35 | Evidence panel | *"Graph plus vector — found by both independently"* |
| 2:05 | Off-domain question | *"Zero confidence. It says it doesn't know."* |
| 2:30 | Explorer / Analytics / Simulator | *fast montage* |
| 3:00 | Role switch | *"Enforced server-side, not just hidden"* |
| 3:20 | Overview | *"Knowledge that outlives the people who created it"* |
