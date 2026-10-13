# Conversion feasibility: October 13, 2026

Day 1 uses Windows System.Speech for a local synthetic American English baseline.
It saves WAV output with no additional Python model dependencies. This establishes
generation plumbing; a listener must still confirm words and practice sounds.
[Microsoft WAV output API](https://learn.microsoft.com/en-us/dotnet/api/system.speech.synthesis.speechsynthesizer.setoutputtowavefile?view=netframework-4.8.1).

For a neural synthetic-example follow-up, Kokoro-82M exposes American English
voices and Apache-2.0 model licensing. The isolated backend is now installed; its repeatable benchmark and listening review are described in KOKORO_RUNBOOK.md. Keep any new dependencies in this module's environment.
[Kokoro model card](https://huggingface.co/hexgrad/Kokoro-82M).

Conversion candidate: **Seed-VC v2**. Its source documentation offers accent/style
conversion with `--convert-style true`; false performs timbre conversion.
It conditions on a target reference voice, so it does not establish preservation
of the learner's identity. Recommendation: investigate, but keep voice-preserving
conversion as an unproven stretch goal.
[Source and usage](https://github.com/Plachtaa/seed-vc).

Public v2 weights are listed on Hugging Face: `ar_base.pth` (359 MB) and
`cfm_small.pth` (353 MB). These are checkpoint download sizes, not required VRAM;
other encoders/vocoder assets are additional. No conversion weights were downloaded
or executed today. Both the repository and model page identify GPL-3.0; dependencies
and ancillary checkpoints also need a license inventory before distribution.
[v2 weight listing](https://huggingface.co/Plachta/Seed-VC/tree/main/v2),
[model license](https://huggingface.co/Plachta/Seed-VC).

The source suggests Python 3.10 for Windows/Linux/macOS and strongly recommends
a GPU for real-time conversion. Its RTX 3060 laptop timing example is for the
v1 tiny model, so it does not establish v2 memory or latency requirements.
An exact v2 minimum VRAM requirement was not verified. Hardware inventory access
was unavailable in this run; no assertion about this laptop's GPU is made.
The upstream repository is archived, which also increases maintenance uncertainty.

Next experiment: in a separate Python 3.10 environment, pin the upstream revision,
download the public checkpoints, and run consented recordings with and without
style conversion. Evaluate word retention, target-accent pronunciation, source
speaker similarity, peak GPU memory and latency. A familiar listener should compare
identity with the original learner audio. Using the learner as reference may help
timbre preservation but may retain their accent; test that tradeoff explicitly.
Do not expose “Hear my voice in the target accent” until this evaluation succeeds.
