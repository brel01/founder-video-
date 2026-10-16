# Projects & status

Update this file whenever a deliverable changes state.

## 1. Founder film: "Why I'm building Urbn"
- **Output:** `output/Urbn_Founder_Film.mp4`, 1080×1920, 83 s, −14 LUFS
- **Code:** `edit/render.py` (visuals), `edit/audio.py` (voice and score), `edit/track_face.py`
- **Status:** v2 delivered after the creative director's review. The reviewer said it "could fly like this".
- **Story beats:** see the table in `edit/README.md` (source times; output = source − 0.85 s)
- **Open items:**
  - [ ] Swap in Creato Display Bold when the font file is supplied
  - [ ] Optional lower-third with the founder's name and title (name not yet provided)
  - [ ] Product-being-built screenshots, if the founder supplies them (brief asked for them)
  - [ ] Human listening check of the v2 score

## 2. Thumbnails
- **Output:** `output/thumbnail_9x16.png`, `output/thumbnail_16x9.png`
- **Code:** `edit/thumbnail.py` (cutouts in `edit/assets/*_cutout.png`)
- **Status:** delivered

## 3. "Ibadan is Urbn": animated campaign teaser
- **Output:** `output/Ibadan_is_Urbn.mp4`, 1080×1920, 31.2 s, about −13.2 LUFS
- **Code:** `ibadan/animate.py`, `ibadan/audio_ibadan.py`; voice script in `ibadan/VOICE_SCRIPT.md`
- **Status:** v2 with real voices and recorded foley, awaiting review
- **Beat sheet:** `ibadan/README.md`
- **Open items:**
  - [ ] Confirm take choices by ear (R2 first vs second "turbo")
  - [ ] Confirm copy: Pidgin lines, end-card call to action ("Find, rent and manage homes in Ibadan."), #IbadanIsUrbn, any waitlist or app link
  - [ ] App screen is a **mock-up** (city card edited to Ibadan). Confirm it's OK to show before the Ibadan card ships
  - [ ] Bring loudness to −14 LUFS (two-pass loudnorm)
  - [ ] Creato Display swap (shared fonts)

## Ideas backlog
- A "chain" UGC follow-up: people across Ibadan shout it on (#IbadanIsUrbn), reusing the teaser's end beat
- Other city variants with the same card format (the app already has "Lagos is Urbn.", "Port Harcourt is Urbn.")
