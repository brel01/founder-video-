# Pipeline: render, QA, ship

## Dependencies
```bash
pip install pillow numpy scipy soundfile "opencv-python-headless<5" onnxruntime sherpa-onnx
# system: ffmpeg, ffprobe
```
- **OpenCV must be < 5.** OpenCV 5 has no `cv2.CascadeClassifier`.
- Fonts are vendored in `edit/fonts/`. Nothing to install.

## Environment gotchas (cloud sessions)
- **HuggingFace is blocked** by the proxy, so `faster-whisper`, `rembg` auto-download and similar fail. **GitHub releases work:**
  - ASR: `https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-whisper-small.en.tar.bz2` (fast) and `…/sherpa-onnx-whisper-medium.tar.bz2` (multilingual, better on Nigerian English and Pidgin; use `language="yo"` for Pidgin lines).
  - Background removal: `https://github.com/danielgatis/rembg/releases/download/v0.0.0/isnet-general-use.onnx` (input 1024², `(x/255 − 0.5)`, min-max normalise the output).
- Google Fonts and Font Squirrel are unreachable, which is why **Creato Display isn't installed**. Ask the user for the file.
- Download models into your scratchpad, not the repo.
- You can't listen to audio. See `docs/design/AUDIO.md → Working without ears`.

## Founder film
```bash
python3 edit/track_face.py                       # only if 1001.mp4 changes
python3 edit/render.py  edit/video_only.mp4      # ~6 min; frames run from OFFSET (0.85 s) to the end
python3 edit/audio.py   edit/mix.wav             # voice clean-up + score + SFX (already trimmed by OFFSET)
python3 edit/thumbnail.py                        # thumbnails -> output/
```
Stills: `python3 edit/render.py --still <source_seconds> out.png` (source time = output time + 0.85).

## Ibadan teaser
```bash
python3 ibadan/animate.py      ibadan/video_only.mp4   # ~4 min, 31.2 s at 30 fps
python3 ibadan/audio_ibadan.py ibadan/mix.wav          # also writes mix_voices.wav
```
Stills: `python3 ibadan/animate.py --still <output_seconds> out.png`.
**Story time vs output time:** `WARP` (identical in both files) maps output → story time. Scene and dialogue tables are in story time. Recorded voices are placed in output time. If you change `WARP`, change it in **both** files.

## Mux & master (both projects)
```bash
ffmpeg -y -i video_only.mp4 -i mix.wav -map 0:v -map 1:a \
  -c:v libx264 -preset slow -crf 19 -maxrate 9M -bufsize 18M -pix_fmt yuv420p -profile:v high -movflags +faststart \
  -af "alimiter=limit=0.89:attack=3:release=60:level=disabled,loudnorm=I=-14:TP=-1.0:LRA=9,aresample=48000" \
  -c:a aac -b:a 256k -shortest output/<Name>.mp4
```

## QA checklist (do all before shipping)
1. **Contact sheet with the safe-zone overlay.** No text, logo, chip or face in the red areas:
   ```bash
   ffmpeg -i out.mp4 -vf "fps=1/2,scale=180:320,drawbox=x=0:y=0:w=180:h=41:color=red@0.35:t=fill,drawbox=x=0:y=256:w=180:h=64:color=red@0.35:t=fill,drawbox=x=148:y=143:w=32:h=113:color=red@0.35:t=fill,tile=14x3" -frames:v 1 qa.png
   ```
2. **Framing:** the eyes sit at the same height across founder shots.
3. **Captions:** same position and style everywhere; no dangling words; nothing over the T-shirt logo.
4. **Loudness:** `ebur128` reads −14 LUFS ±0.5 and peak ≤ −1 dBTP.
5. **A/V sync:** speech onset matches the captions (check the first word and a mid-video line).
6. **Voice above the bed:** per-section RMS of voice vs (mix − voice) ≥ 5 dB.
7. Update `docs/memory/PROJECTS.md` and add a `FEEDBACK_LOG.md` entry for any decision.

## Git
- Work on the session's designated branch and commit with clear messages.
- Large binaries in `output/` are committed deliberately: deliverables under 100 MB.
- Ignored: `*/video_only.mp4`, `*/mix*.wav`, `__pycache__/`.
