# Audio: voice, music, sound design

## Deliverable targets
- **−14 LUFS integrated, −1 dBTP**, AAC 256 kbps, 48 kHz.
- Final chain (ffmpeg): `alimiter=limit=0.89:level=disabled,loudnorm=I=-14:TP=-1.0:LRA=9`.
- Verify: `ffmpeg -i out.mp4 -af ebur128=peak=true:framelog=quiet -f null -`.

## Voice (always on top)
- Founder dialogue chain (`edit/audio.py → voice()`): highpass 75 Hz, `afftdn` light denoise, −2.5 dB at 280 Hz (de-box), +1.2 dB at 140 Hz (warmth), +2.2 dB at 3.6 kHz (presence), +1 dB at 11 kHz, de-esser, compression 3:1, loudnorm −16 LUFS.
- Recorded character takes (`ibadan/audio_ibadan.py → take()`): high-pass 90 Hz, `afftdn` (stronger on the noisier runner track), de-box and presence EQ, 3:1 compression, each take level-matched to −20 dBFS RMS.
- **Distance is added in post, not at recording.** `distance(x, q)` goes from q = 0 (far: low-pass about 350 Hz, three hill echoes, heavy reverb, quieter) to q = 1 (close and clear).
- **Music ducks under every voice**: about 6 dB in the founder film, about 11 dB (×0.28) under the teaser voices. Keep voice 5–10 dB above the bed in RMS.

## Music direction (binding after review)
The creative director said the first score was **"too chill for the message… it needs to be intriguing and spark curiosity."** Every score since is built for tension and curiosity, with release only at the payoff.
- **Founder film** (`edit/audio.py → score()`, 96 BPM):
  - Hook: D Phrygian string ostinato. The flat second (Eb) stays unresolved, over pulsing bass and ticking hats.
  - "renting a house in Nigeria": a hard stop on an impact, then a ticking clock and a dark drone carry the suspense.
  - Problem section: it builds (ostinato, bass, kick and an opening filter) into a snare roll and riser.
  - "At Urbn": a drop into a driving F-major section with a full kit, plus a high arpeggio for the vision.
  - The end: it resolves on "housing" and under the end card.
- **Ibadan teaser** (`ibadan/audio_ibadan.py → music()`, 104 BPM): an Afrobeats/amapiano palette (shaker, log drum, kalimba). A **talking drum (dùndún) plays the rhythm of "Ì-bà-dàn is Ur-bn"** as a recurring motif. Near-silence for the app reveal, then the full groove for the payoff, and the drum "says" it once more at the end.
- Everything is **synthesized in code**, so there are no licensing issues. A licensed track can replace `score()` or `music()` if it matches this direction.

## Sound design palette
- Transitions: whoosh (band-swept noise), tick (UI text), blip (two-tone UI chime), pop (pitched, for chips and nodes), impact (sub boom plus noise and reverb), riser (swept noise plus a rising tone).
- Use them sparingly and tie them to on-screen events. Audio should **guide attention**, not decorate.
- Recorded foley and ambience (`ibadan/sfx/`): the grass swish under running, a street bed (close in wide shots, low-passed and distant from the hill), crickets (high-passed from the street-plus-crickets clip).

## Working without ears
Agents can't listen. Verify with:
- `ebur128` loudness and per-section RMS (voice vs bed).
- A spectrogram (`showspectrumpic`) to check transients and broadband noise.
- Speech recognition on cut takes: sherpa-onnx Whisper (see PIPELINE.md). Use `language="yo"` for Pidgin and Yoruba-accented lines.

Then ask the human to listen, and log anything they flag.
