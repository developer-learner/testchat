# project-trail/ — the project's running trail (exploratory companion to the frozen specs)

The unauthoritative running record of everything AROUND the system: rejected
alternatives with their reasoning, explorations and benchmarks, incident
writeups, near-misses, scratch thinking, external context (links, quotes,
things read that shaped a prior). The frozen specs and DECISIONS.md are
optimized for the pipeline to consume; this directory is the corpus a model
will later be asked to parse — at milestone or project close — to extract
learnings and produce a CEO summary (blueprint D-84). Write what that future
reader would need that no authoritative artifact captures: the why behind a
choice, the paths not taken, what broke and how it looked from the operator
seat.

Rules:

- **Project-authored, routinely.** The working session (conductor seat)
  writes notes as part of normal doc upkeep — same authorship lane as
  `docs/` and `tasks/CURRENT.md` — and the human adds whatever they like.
  Expected cadence: most working sessions leave a note, not only incidents;
  breadth is the point, the corpus is the product. Pipeline phases (EM/coder)
  remain structurally excluded — this directory is outside every
  `.gate-paths` lane (`build=src/`, `test=tests/`), so INV-2 fails closed on
  any pipeline-phase write.
- **Notes are narrative, never evidence.** An agent-written note is a claim
  by that session. The authoritative record stays in DECISIONS.md, the
  frozen specs, and git history; when a note and the tree disagree, the tree
  wins.
- **Nothing here is authoritative** and nothing in the pipeline reads it.
  References are one-way: a note cites decisions and specs by number/path;
  nothing cites back. No gate may ever depend on a note's presence, absence,
  or content.
- **Keep files committed** — INV-2 counts untracked files repo-wide during
  runs.
- **Flat and dated:** `YYYY-MM-DD-short-slug.md`, grep over hierarchy.
  Incident writeups keep `status: historical`.
- **DECISIONS.md remains the single decision log.** When a note graduates
  into a rule or spec, it travels the normal decision/refreeze flow; the
  note stays behind as the why-trail.

No required fields, no taxonomy, no linter — structure would slow the
capture, and the mining model handles unstructured. The one quality bar:
a note should say something the git history alone cannot.

---

**Provenance.** Imported into testchat 2026-07-25 from the blueprint's
`project-trail/README.md` (blueprint D-84). It did not arrive via
`update-template.sh`: the template sync copies only the executable control
plane listed in `scripts/.manifest-template` (31 files under `scripts/`,
`.githooks/`, `.github/`, `.opencode/`) and carries **no `docs/` entries and
no directories**. Conventions established in blueprint documentation have no
transport to children and must be hand-imported — the same gap that required
hand-porting `docs/TPM-ROLE.md` guidance at `d273012`.
