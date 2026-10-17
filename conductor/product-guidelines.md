# Product Guidelines — Hummerli

## Tone & Voice

### Frau Leonie Blücher 🐎 (German Tutor Persona)
- **Language**: Standard High German (Hochdeutsch B1). Never Schweizerdeutsch.
- **Tone**: Patient, encouraging, clear. Like a friendly Volkshochschule teacher.
- **Pace**: Measured — slightly slower than native speed. Never condescending.
- **Error Handling**: Gently correct grammar/vocabulary mistakes mid-conversation; never interrupt for minor errors. Focus on fluency, not perfection.
- **Vocabulary**: Stays within B1 Goethe Wortliste scope. Avoids idioms or dialect.

### Rijckard (Coach Persona — Italian)
- **Language**: Italian (it-IT), intervenes ONLY when the user signals confusion.
  - Triggers: `"Non ho capito"`, switching to Italian/English, explicit grammar questions.
- **Tone**: Warm, concise, like a patient older sibling. Gets out of the way quickly so Frau Blücher resumes.
- **Role**: Translator + grammar explainer. Never leads conversations.

### CLI / Dashboard / System Messages
- **Language**: English (technical logs, code, CLI) and Italian (user-facing messages where appropriate).
- **Tone**: Direct, no-nonsense, developer-friendly.

## UX Principles

1. **Zero Artificial Turn-Taking**: Barge-in must work fluidly. The user should never feel they are "waiting for the bot to finish" before speaking. VAD is non-negotiable.
2. **Low-Latency First**: Prefer streaming responses over complete synthesis. Buffer UX is acceptable only on Telegram (async mode).
3. **Organic Learning**: Vocabulary (SRS lemmata) must be woven naturally into conversation — never delivered as a quiz or flashcard. Hummerli asks, doesn't test.
4. **Privacy by Default**: All audio is stored encrypted on GCS. No third-party TTS (e.g., no Microsoft Edge TTS). Only Google Cloud TTS Neural2 and Gemini native audio.
5. **Failure Resilience**: Network drops, GCS timeouts, or eval failures MUST NOT interrupt the live conversation. All non-conversational tasks (eval, upload) are async and non-blocking.
6. **Transparency**: The dashboard must show the user exactly what Hummerli knows about them — SRS intervals, scores, audio history — without hidden state.

## Branding

- **Name**: Hummerli (Swiss German diminutive of "Hummer" 🦞 — nod to the Lobster theme)
- **Icon**: Small blue lobster 🦞 or Swiss cowbell 🐮 (tbd)
- **Color Palette**:
  - Primary: Swiss red (#D52B1E)
  - Secondary: Midnight blue (#1A2B5F)
  - Accent: Warm gold (#F5C842)
  - Success/Mastered: Green (#2E7D32)
  - Struggling: Red (#C62828)
  - In Progress: Amber (#F57C00)
- **Dashboard style**: Dense, data-rich — GitHub contribution heatmap aesthetic. Not cutesy, not gamified. Professional tutoring tool.

## Code & API Style

- Python code follows **PEP 8** + Google Python Style Guide.
- All public functions must have **docstrings**.
- Config via **environment variables** (`.env`) — no hardcoded API keys.
- GCS paths must be parameterized, never hardcoded bucket names.
- CLI commands follow `hummerli <verb> [--flags]` pattern (e.g., `hummerli session`, `hummerli replay`).

## Safety (Kid Profiles)

- `allow_swear_words: false` for all profiles (including `riccardo`).
- Profiles `ale` and `sebi` have additional guardrails: no violence, no adult themes, always encouraging.
- Kid profiles always respond with `kid_friendly: true` tone — simpler vocabulary, enthusiastic, short sentences.

## Accessibility

- Web client must support keyboard-only navigation (for barge-in button).
- Audio controls must have ARIA labels.
- Dashboard color coding (🟢🟡🔴) must also use text labels/icons for colorblind users.
