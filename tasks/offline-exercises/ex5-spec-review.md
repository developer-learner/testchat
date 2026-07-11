EXERCISE 5 of 5 — Adversarial review of the M9 acceptance criteria (no code)

You are a cold, adversarial product-spec reviewer. Below are DRAFT acceptance
criteria for a maintenance milestone of a local chat app (FastAPI backend,
single-page frontend, local LLMs). Your job is to find holes, not to praise.

For each criterion answer three questions:
1. Is it testable exactly as written (could a machine check it)? If not, say
   what measurable wording is missing.
2. What edge case or failure mode does it silently ignore?
3. Could a lazy implementation satisfy the letter of it while betraying its
   intent? How?
Then, at the end: name any MISSING criterion this milestone obviously needs.
Be specific and terse. Verdict format: one block per AC, then "MISSING:".

DRAFT ACCEPTANCE CRITERIA (M9 polish sweep):

AC-39: WHEN the user unloads Nemotron, THE SYSTEM SHALL terminate the model
server process without triggering the operating system's crash reporter.

AC-40: WHEN the app starts with no NEMOTRON_URL environment variable set,
THE SYSTEM SHALL address the nemotron server at http://localhost:8600; WHEN
NEMOTRON_URL is set, THE SYSTEM SHALL use it for all nemotron endpoints.

AC-41: WHEN a chat reply fails (stream error event or network failure), THE
SYSTEM SHALL retain the user's sent message in the thread's stored history
and persist it, while storing no assistant message for the failed reply.

AC-42: WHILE a reply is in flight and no visible answer text has rendered,
THE SYSTEM SHALL display the placeholder "thinking..." in the reply bubble,
removing it as soon as visible answer text renders.
