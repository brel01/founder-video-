# Urbn — Founder Film

Final cut: `output/Urbn_Founder_Film.mp4` (1080×1920, 30 fps, 84 s, H.264 + AAC, mastered to −14 LUFS / −1 dBTP).

## Story structure

| Time | Founder says | On screen |
|---|---|---|
| 0:00–0:06 | "You can order food… send money… book a flight…" | Hook: three brand cards in black, blue and white, each with a success-state chip and UI sound, over a light, upbeat pluck motif |
| 0:06 | "But when it comes to renting a house in Nigeria…" | Hard cut to a tight punch-in. The music drops out under a low impact |
| 0:09–0:16 | "walking street to street asking the security man…" | Animated city map: a walker's path with "?" markers that go unanswered |
| 0:16 | "I know this because I have gone through it." | Founder portrait (DSC00718) with a slow push |
| 0:21 | "Why is housing still disconnected?" | Full-screen statement. "disconnected?" splits in two |
| 0:25–0:33 | "Renting is difficult. Tenancy is fragmented…" | Founder with numbered problem statements (01–03). Pulse and tension build |
| 0:33–0:40 | "juggling tenants, managers, records and payments…" | Floating chips that drift apart on "different places" |
| 0:40–0:44 | "…fix each problem separately. At Urbn," | Riser, then a brand slam: the Urbn wordmark on brand blue |
| 0:48 | "giving physical properties a digital presence" | Key statement on white, plus the real property card from the app (DPI code `MNY-0001-Z`) |
| 0:51–0:59 | "connecting them to owners, renters, agents, records, services…" | Network graphic: the Urbn "U" node connects to each stakeholder as it is spoken |
| 0:59–1:04 | "finding a home… easier / managing one… simpler" | Listings and Property Dashboard screens in phone mockups |
| 1:04–1:13 | "no longer just a building… history, identity… digital world" | Punch-in, then "It has history. An identity." with a fan of app screens |
| 1:15 | "the digital infrastructure for housing." | Closing statement with the final impact |
| 1:19–1:24 | — | End card: wordmark, "This is only the beginning." |

## Rebuild

```bash
pip install pillow numpy scipy soundfile
python3 edit/render.py edit/video_only.mp4   # graphics + footage (about 6 min on 4 cores)
python3 edit/audio.py  edit/mix.wav          # voice clean-up + score + SFX
ffmpeg -i edit/video_only.mp4 -i edit/mix.wav -map 0:v -map 1:a -c:v libx264 -crf 19 -preset slow \
  -pix_fmt yuv420p -movflags +faststart \
  -af "alimiter=limit=0.89:level=disabled,loudnorm=I=-14:TP=-1.0:LRA=9" -c:a aac -b:a 256k \
  output/Urbn_Founder_Film.mp4
```

`python3 edit/render.py --still 44.3 frame.png` renders single frames for review.
All timings live in `TIMELINE`, `CAPTIONS` and the scene functions in `render.py`. Sound cues are in `sfx()` and `score()` in `audio.py`.

## Notes

- **Typeface:** the guide specifies Creato Display Bold for headlines. It could not be downloaded in the build environment, so headlines use Inter Display Bold with tight tracking, which is the closest neo-grotesk. Inter Semi Bold for body and captions matches the guide. To switch, drop `CreatoDisplay-Bold.otf` into `edit/fonts/` and set `HEAD` in `render.py`.
- **Palette:** black `#000000`, Urbn Blue `#253DE2` and white, with Success `#12B76A` used only for the confirmation chips. The logo is never rotated, flipped or given effects.
- **Music and SFX** are original and synthesized in code (`audio.py`), so there are no licensing issues. Swapping in a licensed track is a one-line change in `main()`.
- **Voice:** high-pass, light FFT denoise, de-box EQ, presence lift, de-esser and gentle compression. The music ducks about 6 dB under speech.

## Thumbnails

`python3 edit/thumbnail.py` writes:

- `output/thumbnail_9x16.png` (1080×1920): cover for Reels, TikTok and Shorts. The headline and the founder stay inside the centre 3:4 crop used by Instagram profile grids. Only the top logo bar falls outside it.
- `output/thumbnail_16x9.png` (1280×720): for YouTube, LinkedIn and X.

Both thumbnails lead with the film's hook question. The founder cutouts in `edit/assets/` were made from the original photos with an ISNet background-removal model.
