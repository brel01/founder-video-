# Ibadan is Urbn — animated teaser

Output: `output/Ibadan_is_Urbn.mp4` (1080×1920, 31.2 s, about −14 LUFS).

A man shouts from Bower's Tower on Oke Aremo. A runner climbs toward him and mishears him each time ("TURBO??", "URBAN?! Since when?!"), until he's shown the app: **Ibadan is Urbn.** Then they both shout it, and someone in the city below picks it up.

| Time | Beat |
|---|---|
| 0–3 s | Wide shot of Ibadan at dusk. A distant, muffled shout echoes off the hills. Jagged, broken sound rings |
| 3–6 s | Runner: "Oga! Wetin you dey talk?!" |
| 6–9 s | Shouter close-up: the shout is half clear, with the rings smoothing out |
| 9–12 s | "Ibadan na… TURBO??" (struck through) |
| 12–14 s | First clear shout, "IBADAN IS URBN!", with clean rings and an impact |
| 14–17 s | "Ibadan na URBAN?! Since when?!" |
| 17–21 s | Arrival at the top. The phone shows the app's "Ibadan is Urbn." city card |
| 21–25 s | "Ahhh… Ibadan is Urbn!" Both shout it, and the city echoes it back |
| 25–28.5 s | End card with call to action and #IbadanIsUrbn |

## Rebuild

```bash
python3 ibadan/animate.py ibadan/video_only.mp4
python3 ibadan/audio_ibadan.py ibadan/mix.wav
ffmpeg -i ibadan/video_only.mp4 -i ibadan/mix.wav -map 0:v -map 1:a -c:v libx264 -crf 19 -pix_fmt yuv420p \
  -af "alimiter=limit=0.89:level=disabled,loudnorm=I=-14:TP=-1:LRA=9" -c:a aac -b:a 256k output/Ibadan_is_Urbn.mp4
```

## Notes

- **Voices** are the real recordings in `ibadan/voice/` (`shouter.m4a`, `runner.m4a`). Takes were mapped from the spoken slates and are listed in `TAKES` in `audio_ibadan.py`, with their cut points.
  - Each take is high-passed, denoised, EQ'd and compressed, then level-matched.
  - The shouter's three attempts go through `distance(x, q)`, so they move from far, muffled and echoing to close and clear. The warm-up take becomes the far-off echo from the city.
- **Timing:** `WARP` in both scripts stretches two beats to fit the real performances. The slow "I… BA… DAN… IS… URBN!" gets 3.7 s, and its on-screen text reveals syllable by syllable. "Ah!… Ibadan is Urbn!" gets 3.2 s. The music grid stays steady in output time.
- **Recorded effects** in `ibadan/sfx/`:
  - `grass.m4a` loops under the climb.
  - `street2.m4a` is the city bed: close in the wide shots, low-passed and distant up the hill.
  - `street3_crickets.m4a` is high-passed down to the crickets for the hillside.
- **Music:** original, built in code. An Afrobeats/amapiano-style groove at 104 BPM (shaker, log drum, kalimba) is built around a talking drum that plays the rhythm of "Ì-bà-dàn is Ur-bn".
- **App screen:** `app_ibadan.png` is the real home screen, with the city card changed from "Lagos is Urbn." to "Ibadan is Urbn." It's a mock-up until the Ibadan card ships.
- **Copy to confirm:** the Pidgin lines, the call-to-action line ("Find, rent and manage homes in Ibadan.") and the hashtag.
