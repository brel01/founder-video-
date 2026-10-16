# CLAUDE.md

@AGENTS.md

## Claude Code specifics

- Load the design memory before visual or audio work: `docs/memory/FEEDBACK_LOG.md` first, then `docs/design/`.
- Put scratch renders, contact sheets and test stills in your scratchpad, not the repo. Only `output/` holds deliverables.
- When the user relays reviewer feedback, record it in `docs/memory/FEEDBACK_LOG.md` (date, source, note, resolution) in the same change that addresses it.
- Long renders (about 4–7 min): run them in the background and wait on the log. Don't poll with `sleep`. Be careful that `pgrep -f` doesn't match your own waiting shell.
- You can't listen to audio. Verify sound with loudness meters, per-section RMS, spectrograms and speech recognition, and tell the user to give it a listen.
