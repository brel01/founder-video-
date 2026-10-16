# Asset inventory

## Brand
| Path | What | Notes |
|---|---|---|
| `URBN — Visual Identity Guide (2) (1) copy.pdf` | Brand guide (8 pp.) | Source of truth. Summarised in `docs/design/BRAND.md` |
| `urbn logos/Urbn logo black.png` / `Urbn logo White.png` | Wordmark | Transparent; white = `#E6E6E6`. Crop to the alpha bounding box (alpha > 8) |
| `urbn logos/Urbn logo Icon black.png` / `Icon white.png` | "U" icon | Also used as a watermark and container shape |
| `edit/fonts/` | Inter, Inter Display (OFL) | Stand-in for Creato Display (headlines) |

## Founder
| Path | What | Notes |
|---|---|---|
| `1001.mp4` | Founder's narration take | 1080×1920 HEVC, 30 fps, 78.7 s, AAC. Has headroom; framing is handled by face tracking. The first word is at 1.04 s |
| `founder pictures/DSC00718.jpg` | Founder in a black **urbn** T-shirt, tie over shoulder, warm brown background | Most on-brand. Used for "I've gone through it" and the 9:16 thumbnail |
| `founder pictures/DSC00562.jpg` | Navy double-breasted suit, brown background | Premium; used for the 16:9 thumbnail |
| `founder pictures/DSC00527.jpg`, `DSC00537.jpg` | Red plaid suit, light background | Unused so far |
| `edit/assets/DSC00718_cutout.png`, `DSC00562_cutout.png` | Background-removed cutouts (2200 px tall) | Made with ISNet (rembg model) |
| `edit/assets/face_track.json` | Per-frame face centre x and eye-line y for `1001.mp4` | Regenerate with `edit/track_face.py` |

**Transcript (founder film), corrected:** "You can order food from your phone, send money in seconds, book a flight without talking to anyone. But when it comes to renting a house in Nigeria, suddenly you are walking street to street asking the security man if there is any vacant house around the area. I know this because I have gone through it. And that is when I started asking the bigger question: why is housing still disconnected? Renting is difficult. Tenancy is fragmented. Agents are managing properties through WhatsApp and notebooks. Property owners are juggling tenants, managers, records and payments across different places. And we keep trying to fix each problem separately. At Urbn, we think there is a bigger problem to solve first. We are giving physical properties a digital presence, connecting them to owners, renters, agents, records, services and everything happening around them. So finding a home becomes easier, managing one becomes simpler, and eventually your property is no longer just a building. It has history, identity, and can interact with the digital world. That's what we are building at Urbn: the digital infrastructure for housing."

## Product (app) screens: `app screens/`
⚠️ Two filenames contain a macOS **narrow no-break space** (U+202F) before "AM". Resolve them by glob (`asset()` in `edit/render.py` does this).

| File | Screen |
|---|---|
| `Screenshot 2026-10-03 at 12.04.45 AM.png` | Dark home: "Good morning", city card **"Lagos is Urbn."** ("Now in your city") |
| `Screenshot 2026-10-03 at 12.05.00 AM.png` | Phone-number / OTP login |
| `Simulator Screenshot … 23.38.38.png` | Light home: "Port Harcourt is Urbn.", portfolio, property "Muse" |
| `Simulator Screenshot … 23.43.13.png` | **Property Dashboard**: Muse, Verified, **DPI code MNY-0001-Z**, Listings, Management, Documents & Ownership |
| `Simulator Screenshot … 23.43.20.png` | **Listings**: pool property, ₦100/day |
| `ibadan/app_ibadan.png` | Mock-up: the dark home screen with the city card edited to **"Ibadan is Urbn."** (circles rebuilt analytically) |

Useful crops (dashboard screenshot, 1290×2796): property card `(40, 390, 1250, 1034)`; DPI black card `(94, 692, 1196, 982)`.

## Ibadan teaser audio
| Path | What |
|---|---|
| `ibadan/voice/shouter.m4a` | Shouter takes with slates (warm-up, S1, S2, S3 syllable read, S4) |
| `ibadan/voice/runner.m4a` | Runner takes with slates (R1–R6; two "turbo" takes; extra "Ah-ah" line). Has a noise floor of about −37 dB, so it gets denoised |
| `ibadan/voice/*.segs.json` | Detected speech segments plus ASR text (helper output) |
| `ibadan/sfx/grass.m4a` | 8 s grass swish. Clean section 0.2–5.9 s; handling bump at about 6.6 s |
| `ibadan/sfx/street2.m4a` | 29 s city street bed (traffic, voices, a horn at about 13.5 s) |
| `ibadan/sfx/street3_crickets.m4a` | 9 s street plus crickets; high-pass about 2.5 kHz to isolate the crickets |
Cut points for each take are in `TAKES` in `ibadan/audio_ibadan.py`.

## Outputs: `output/`
`Urbn_Founder_Film.mp4`, `thumbnail_9x16.png`, `thumbnail_16x9.png`, `Ibadan_is_Urbn.mp4`. These are generated; rebuild, don't edit.
