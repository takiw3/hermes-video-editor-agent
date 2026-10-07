> **Modified file. Derived from HeyGen HyperFrames v0.8.138 (commit 0ca28db), licensed under Apache-2.0, Copyright 2026 HeyGen, Inc. Changed by TakiGPT AI Inc. for the Hermes video-editor profile. Rules applied: pin-cli, launcher-scripts. See skills/hyperframes-video/MODIFICATIONS.md.**

# TTS → Captions

When no recorded voiceover exists, generate one and obtain word-level caption timing. Two paths depending on which TTS provider is in use:

## Path A — HeyGen (single call, no Whisper)

HeyGen returns word timestamps in the same response as the audio. Use the
bundled REST helper (the `hyperframes tts` command is Kokoro-only):

```bash
python3 "$HERMES_HOME/skills/integrations/editor-hyperframes/scripts/hf.py" script skills/media-use/audio/scripts/heygen-tts.mjs \
  script.txt --output narration.wav --words narration.words.json
```

`narration.words.json` is already in the `[{ id, text, start, end }]` shape the captions pipeline consumes — no separate transcribe pass.

## Path B — Gemini / ElevenLabs / Kokoro (TTS → transcription)

These adapters supply audio without word data. The shared audio engine runs
transcription automatically when timings are absent. For Gemini, use the
request in [Text to speech](tts.md#gemini-narration), then consume
`audio_meta.json` → `voices[].words`.

For a standalone local Kokoro generation, generate the audio, then transcribe:

```bash
python3 "$HERMES_HOME/skills/integrations/editor-hyperframes/scripts/hf.py" tts script.txt --voice af_heart --output narration.wav
python3 "$HERMES_HOME/skills/integrations/editor-hyperframes/scripts/hf.py" transcribe narration.wav --model small.en   # voice af_heart is American English
```

Whisper extracts precise word boundaries from the generated audio, so caption timing matches delivery without hand-tuning. Match `--model` to the voice's language (use `small.en` for `a`/`b` prefixes, `small --language <code>` otherwise). Then consume `transcript.json` via the caption references in `captions/`.

For Gemini, verify that transcription preserved the script, especially names,
numbers, and delivery pauses. If `words` is empty, resolve the transcription
failure before captioning. Generate and align again after changing the read.
