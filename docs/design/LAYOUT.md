# Layout: canvas, safe zones, captions, framing

## Canvas
- **9:16, 1080×1920, 30 fps** for all primary video. The thumbnails are 1080×1920 (cover) and 1280×720 (YouTube, LinkedIn, X).
- Outer margin **M = 90 px**. Text is left-aligned at x = 90 unless it's deliberately centred (end card, wordmark).

## Instagram Reels safe zone (binding)
Reviewer-supplied template, mapped to 1080×1920:

| Edge | Keep content… |
|---|---|
| Top | below **y ≈ 250** (Reels header) |
| Bottom | above **y ≈ 1535** (caption, audio and profile UI) |
| Right, from y ≈ 861 down | left of **x ≈ 880** (like, comment and share column) |
| Right, above y ≈ 861 | left of x ≈ 1028 |

The constants live in code: `SAFE_TOP, SAFE_BOTTOM, SAFE_RIGHT = 250, 1535, 880` (`edit/render.py`).
Decorative elements (watermarks, rules, phone bottoms, rings) may bleed outside. **Text, logos, chips, labels and faces may not.**

QA with the red-overlay contact sheet in `docs/PIPELINE.md`.

## Captions (subtitles)
One style and **one position for the whole video**. Reviewers flagged inconsistency before.
- Inter Semi Bold **58 px**, white with a soft dark shadow, **left-aligned at x = 90**.
- Baseline row fixed at **CAP_Y = 1405**, which sits inside the safe zone and clears the logo on the founder's T-shirt.
- **Single lines only.** Max width about 770 px (`SAFE_RIGHT − M − 20`). Break long sentences into phrase chunks **by hand** with `|` in `CAPTIONS`. Never leave a dangling word ("…from").
- Emphasis: key phrase in white on an **Urbn-blue box**.
- Captions appear only over talking-head footage. Full-screen statement cards carry their own type and get no caption.
- Chunk timing is proportional to character count within the phrase's spoken window, with no overlap between chunks.

## Founder framing (binding)
Source `1001.mp4` has too much headroom; reviewers flagged "excessive headroom" and "inconsistent framing".
- The founder is **face-tracked**: `edit/track_face.py` → `edit/assets/face_track.json` (eye-line y and face centre x per frame, smoothed).
- Only **two framings**: `MED = 1.18×` with the eyes at screen y = 640, and `CLOSE = 1.36×` with the eyes at y = 625. That puts the eyes on the upper third in every shot.
- Pushes are slow (+2–4 %) and **anchored on the eyes**, so the framing never drifts.
- Horizontal follow is damped (85 % of face offset).
- Logo on the founder's T-shirt (source y≈1185–1250): keep captions and text off it.

## Type scale (1080-wide canvas)

| Use | Size |
|---|---|
| Full-screen statement | 132–150 px InterDisplay Bold |
| Section headline | 100–120 px |
| On-footage statement (problem stack) | 66–76 px |
| Caption | 58 px Inter Semi Bold |
| Sub/secondary | 40–54 px Inter Medium |
| Kicker | 34 px Inter Semi Bold, +0.12 em, uppercase |

## Composition patterns that worked
- **Statement card:** black (or white) background, header bar, large stacked headline at mid-height, U watermark bleeding off the right, bottom rule.
- **Phone hero:** headline at top (y≈270), phone mockup (≈660 px wide) rising from the bottom, background blue or white.
- **Talking head plus stack:** founder at MED, bottom gradient, numbered statement in the lower third (inside the safe zone).
- **Thumbnails:** hook question as the headline (with the key word highlighted in blue), founder cutout, brand U as a stage or container, header bar. Keep the 3:4 grid crop in mind for the 9:16 cover.
