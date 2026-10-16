# Brand: Urbn visual identity

Source of truth: `URBN — Visual Identity Guide (2) (1) copy.pdf` (repo root). This file summarises it and adds the conventions established in our videos.

## Personality
Premium · modern · ambitious · human · technological · cinematic · founder-led.
**Not** a generic startup ad and **not** a flashy social edit. Confident and clear. Think of a founder introducing a company to the market for the first time.

## Palette

| Role | Hex | RGB | Use |
|---|---|---|---|
| Primary | `#000000` | 0,0,0 | Backgrounds, statement cards, text on light |
| Secondary — **Urbn Blue** | `#253DE2` | 37,61,226 | Highlight boxes, accents, brand slams, squares |
| Neutral | `#FFFFFF` | 255,255,255 | Text on dark, light cards |
| Logo white (as shipped) | `#E6E6E6` | 230,230,230 | The "white" logo PNGs are this off-white |
| Header grey square | `#A8A8A8` | 168,168,168 | Guide-style header bar (second square) |
| App accent (in-app light blue) | `#70A3F3` | 112,163,243 | Only when recreating app UI ("Urbn" in the city card) |

Action colours are for **functional UI only** (status chips, alerts). Never use them as decoration:
- Warning `#F79009` · Error `#FF1100` · **Success `#12B76A`** (used for "Order placed ✓" chips)
- Grey scale (from the guide): 25 `#FCFCFD`, 50 `#F9FAFB`, 100 `#F2F4F7`, 200 `#EAECF0`, 300 `#D0D5DD`, 400 `#98A2B3`, 500 `#667085`, 600 `#475467`, 700 `#344054`, 800 `#1D2939`, 900 `#101828`

Proportions: mostly black and white, with blue as the energy and accent. A full-blue frame is reserved for big moments, such as the "At Urbn" brand slam, a card in the hook, or a phone hero.

## Typography

| Role | Guide spec | What we use in code | Notes |
|---|---|---|---|
| Headlines | **Creato Display Bold** | `InterDisplay-Bold.ttf` with tracking −0.035 to −0.05 em | Creato wasn't available in the build environment. When the file is provided, put it in `edit/fonts/` and set `HEAD` in `edit/render.py` (the Ibadan teaser imports it) |
| H2 / body / captions | **Inter Semi Bold** | `Inter-SemiBold.ttf` (also `Inter-Medium.ttf` for secondary lines) | Matches the guide |

- Headlines are **tight, large, left-aligned** at the margin. Sentence case with a full stop for statements ("The digital infrastructure for housing.").
- Kickers are uppercase Inter Semi Bold, about 34 px, tracking +0.12 em, preceded by a small blue square: `■ RENTING IN NIGERIA`.
- Fonts live in `edit/fonts/` (Inter, OFL licence included).

## Logo

Files are in `urbn logos/`: wordmark black, wordmark white, and "U" icon black and white (all transparent PNGs; crop to the alpha bounding box before use).
- Approved: the black wordmark on white, the white wordmark on blue or black, and the icon alone.
- **Never rotate, flip, stretch, outline or add effects** (glow, gradient, shadow on the mark itself).
- Placements from the guide: top-left in the corner, centred, or the icon top-left.
- The "U" icon may be used large as a **background watermark**: cropped off the right edge, upright, low contrast (`#1A1A1A`–`#282828` on black, `#E8E8E8` on white, white at 8–13 % on blue). It may also be used as a container shape: in the 9:16 thumbnail the founder stands *inside* the U.

## Graphic motifs (from the guide, used throughout)
- **Header bar:** wordmark top-left, a thin hairline across, then a blue square and a grey square at the right. In video it sits at y≈272 so it clears the Instagram UI.
- **Bottom rule:** a blue square at the left margin plus a thin line.
- **Highlight box:** a key word set in white on a solid Urbn-blue rectangle (like the guide's "Join the waitlist" treatment). It's our main emphasis device in headlines and captions.
- **Numbered markers:** `■ 01 / 03` for sequences.
- **Rounded cards** (radius about 4.5 % of width) for app UI and property cards; phone mockups with a dark bezel and a soft shadow.

## Copy tone
- Short, declarative, confident: "Find faster. Move smarter.", "Ibadan is Urbn."
- Nigerian voice is welcome. Pidgin and local references (Ibadan, Oke Aremo, security man, WhatsApp and notebooks) make it real.
- Brand name in running text: **Urbn** (capital U). The wordmark is lowercase "urbn". Spoken: **"UR-bun"** (like "urban"); the Ibadan campaign relies on this double meaning.
- Taglines in use: "The digital infrastructure for housing." · "This is only the beginning." · "Ibadan is Urbn." · #IbadanIsUrbn
