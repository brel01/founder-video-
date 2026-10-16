# Feedback & decision log

Newest first. Each entry records **who said it**, **what they said**, and **how it was resolved**. Reviewer notes are binding on future work unless a later entry overrides them.
**Add an entry whenever you receive feedback or make a design decision.**

---

## 2026-10-16: Agent design memory created
- **Source:** founder (repo owner)
- **Ask:** "create md files in this repository so any agents that work on it have the right design memory path."
- **Resolution:** added `AGENTS.md`, `CLAUDE.md`, `docs/design/*`, `docs/memory/*`, `docs/ASSETS.md` and `docs/PIPELINE.md`.

## 2026-10-04: Ibadan teaser, real voices and recorded foley
- **Source:** founder supplied `ibadan/voice/shouter.m4a`, `runner.m4a` and `ibadan/sfx/` (grass, street, street plus crickets).
- **Decisions:**
  - Takes mapped from spoken slates (S1…S4, R1…R6; see `TAKES` in `audio_ibadan.py`).
  - The runner said "Ibadan na turbo" twice back to back, so the first take is used.
  - An extra runner line ("Ah-ah"-like, 26.7–29.3 s) is unused.
  - The shouter's warm-up take became the city's far-off echo (the chain).
  - Two beats were time-stretched (`WARP`) so the performances aren't cut. The clear shout's text is revealed syllable by syllable.
- **Open:** human listening check of the take choices; final loudness was about −13.2 LUFS (target −14).

## 2026-10-04: Ibadan teaser, voicing guidance
- The founder asked how to voice it and whether to record one file. Guidance is in `ibadan/VOICE_SCRIPT.md`: perform physically, project from the belly, don't fake distance, three takes per line, a spoken slate before each, one file per character.

## 2026-10-03: "Ibadan is Urbn" campaign concept
- **Source:** founder's idea: a man on a hill in Ibadan shouts, unclear at first; a runner keeps mishearing; finally "Ibadan is Urbn".
- **Assessment (accepted):**
  - Strong, because the mishearing forces repetition of the brand name and the double meaning ("urban" / Urbn) sparks city-pride debate.
  - Bower's Tower on Oke Aremo is the hero location.
  - Recommendations: funny mishearings in Pidgin ("TURBO??", "URBAN?! Since when?!"), a payoff beyond the final repeat (the phone shows the app's city card), visible spelling (the brand name can't live in audio alone), one line saying what Urbn is, 20–30 s, and a proud tone, not "finally catching up".
- **Format:** animated, because no live shoot was available. The app city card was mocked from the real "Lagos is Urbn." card to read "Ibadan is Urbn."

## 2026-10-03: Founder film v2, creative director review
- **Source:** creative director (relayed by the founder).
- **Notes and resolutions:**
  1. *"The framing isn't consistent… excessive headrooms."* → Face tracking plus two locked framings with the eyes on the upper third (LAYOUT.md).
  2. *"Subtitle alignment needs to be consistent and pushed up… the Instagram UI might cover it"* (safe-zone template supplied) → one caption position, single lines inside the safe zone. Overlays, chips, labels and the header bar moved inside it.
  3. *"The video should start with your face, not the motion animation… it took some seconds to know what the video was about."* → Open on the face with the `WHY I'M BUILDING URBN` kicker; 0.85 s of dead air trimmed.
  4. *"Music needs to be intriguing and spark curiosity. It's too chill for the message."* → New score: Phrygian ostinato, ticking suspense, build, drop at "At Urbn" (AUDIO.md).
  5. *"It could actually fly like this but the hook is important."* → The hook is the priority in all future edits.

## 2026-10-03: Thumbnails
- 9:16 cover plus 16:9, both leading with the hook question "Why is housing still disconnected?", with the founder cut out (ISNet).
- Decision: in the cover, the founder stands *inside* the brand U, with the U's bowl composited in front of him for depth. A faded/ghosted figure was rejected because it looked like a double exposure.

## 2026-10-03: Founder film v1
- **Brief:** a cinematic, Steve-Jobs-clear founder introduction built on the founder's narration, with the brand guide followed closely.
- Transcript corrections (the ASR misheard them, so confirm with the founder if in doubt): "housing" (not "Aosin"), "Urbn" (not "Oban"), "giving" (not "given"), "Tenancy".
- **Known gap:** the brief mentioned screenshots of the product being built, but none were supplied.
- **Font substitution:** Creato Display was unavailable, so Inter Display Bold is used.
