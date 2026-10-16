# Motion & editing

## Storytelling spine
1. **The narration is the backbone.** Cut visuals to what is being said. Whenever the speaker mentions the problem, the journey, the product, the build, housing, technology or the vision, show a supporting visual instead of holding on the talking head.
2. The founder-film arc to preserve in any recut: **the problem with housing → the founder lived it → Urbn exists because of it → Urbn is digital infrastructure for housing → this is only the beginning.**
3. Give important statements **stronger emphasis**: a full-screen statement card, a punch-in, or a highlight box.

## Hooks (binding after review)
- **Open on a human face from frame 1.** The reviewer said a motion-graphic opening "took some seconds for us to know what the video was about."
- Put a **topic kicker on screen from frame 1** (e.g. `■ WHY I'M BUILDING URBN`).
- **No dead air.** Trim silence before the first word. The founder film trims 0.85 s (`OFFSET`).
- After the face is established, quick brand cards (≈1.3–2.3 s each) can carry the hook's rhythm.

## Pacing
- Alternate between founder footage, product screens, full-screen statements, punch-ins, brand frames and motion graphics. Aim for a visual change every **2–4 s**.
- Cut on speech boundaries: phrase starts, or just after a key word.
- Punch-ins change framing between **MED** and **CLOSE** only (LAYOUT.md). Use CLOSE for emotional or turning-point lines.
- When a real performance runs long, **stretch the beat** with a time-warp rather than cutting the performance short (see `WARP` in `ibadan/`).

## Text animation (house style)
- **Masked rise-in:** each line slides up from inside its own box while fading in. Duration 0.45–0.5 s, `ease_out` cubic. Stagger lines by 0.12–0.6 s, timed to the words being spoken (`put_text(..., t0=…)` in `edit/render.py`).
- Highlight boxes appear with their line (no separate pop).
- **Syllable or word reveals** for chanted or slogan lines, synced to the voice ("I- / I-BA- / I-BA-DAN / IBADAN IS URBN!").
- **Strike-through** (blue bar, 0.25 s) for a wrong word or mishearing ("TURBO??").
- Captions fade or rise in over 0.12 s. No bouncing, typewriter or per-letter jitter.

## Graphic devices that worked
- An animated map of street-to-street searching, with "?" markers that go unanswered.
- A word that **splits** to show "disconnected".
- **Floating chips** (Tenants, Managers…) that drift apart on "different places".
- A **network graphic**: the Urbn U at the centre, connecting to each stakeholder exactly when it's named, then satellites bloom.
- **Real app UI** in phone mockups and property cards. Highlight the meaningful bit (e.g. DPI code `MNY-0001-Z`, "Digital Property Identity").
- **Sound rings** (Ibadan teaser): jagged and broken when the message is unclear, clean concentric circles when it's clear. Visualise clarity, not volume.
- A **brand slam** on the brand name: full Urbn-blue frame, white wordmark settling from 1.06× to 1.0×, hairlines drawing in.

## Transitions
- Mostly **hard cuts on the beat**, supported by sound (whoosh, tick, impact).
- A "settle" on new cards: the content eases from slight offset or scale. No spins, zoom blurs, glitch, light leaks or 3D flips.
- Camera moves are slow pushes or gentle tracking. Drift on watermarks is about 14 px/s.

## Avoid (reviewed and rejected, or off-brand)
- A non-face cold open, or silence at the start.
- Inconsistent framing or headroom between cuts.
- Captions that change position or style, or run into the IG UI.
- Random effects, stock-ad flash, emoji overload.
- Logo misuse of any kind (BRAND.md).

## End cards
Black background, header bar, wordmark or tagline headline with the key word on a blue box, a short call-to-action line, hashtag where relevant, bottom rule. Fade to black over the last 0.8–1.1 s.
