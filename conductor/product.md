# Hummerli — ADK German B1 Oral Tutor & Multi-Eval Datalake

## Vision

Hummerli è un'infrastruttura di tutoring orale AI autonoma, costruita su **Google Agent Development Kit (ADK)** in Python, progettata per preparare Riccardo all'esame **FIDE B1 (Hören & Sprechen)** per la naturalizzazione svizzera nel Canton Zurigo.

Il progetto affronta il fallimento puntuale dell'esame orale (A2 in Hören invece di B1) con un sistema di immersione conversazionale continua, realistico e misurato — non un quiz app statica, ma un tutor vocale paziente, sempre disponibile, che parla vero tedesco.

## Focus Primario (MVP)

**Swiss Naturalization Prep** — Il profilo `riccardo` è prioritario:
- Conversazione orale in tedesco B1 con **barge-in vocale** (interruzione naturale del tutor)
- **SRS Engine** sul Goethe B1 Wortliste (~1,000–1,500 lemmata) per colmare le lacune A2→B1
- Dual-persona vocale: Frau Leonie Blücher 🐎 (tedesco) + Rijckard il Coach (italiano su richiesta)

I profili familiari (`ale` per Alessandro P3, `sebi` per Sebastian P1) sono previsti nell'architettura ma secondari rispetto all'MVP.

## Interfacce Utente (MVP)

1. **Web Client** — Barge-in vocale full-duplex via WebSockets (Gemini Multimodal Live API). Push-to-talk + Voice Activity Detection (VAD). Esperienza desktop-first.
2. **Telegram Bot** — Voice memo asincrono. Push-to-talk → trascrizione → risposta audio. Utilizzabile da mobile senza browser.
3. **CLI** — Sessioni rapide da terminale, senza browser, per pratica durante lo sviluppo o su macchine headless.

## Funzionalità Core

- **Barge-In Engine**: Interrompere Frau Blücher mid-sentence con VAD — nessun turn-taking artificioso.
- **Goethe B1 SRS Engine**: SM-2/Leitner su ~1,000–1,500 lemmata. Parole indovinate → intervallo crescente (7, 15, 30, 90 giorni). Parole difficili → rinforzo frequente. L'agente integra organicamente 1–3 lemmata target per sessione in conversazione naturalistica.
- **Cloud Audio Vault**: 100% degli audio (utente + tutor) archiviati in GCS (`gs://hummerli-audio-vault/{user}/{session_id}/`).
- **Multi-Judge Asincrono**: Valutazione decoupled dalla conversazione live — Flash (real-time), Pro (shadow), benchmark esterno. Replay CLI per rivalutare sessioni storiche.
- **Datalake Telemetry**: Session count, minuti parlati, audio files, target words attempted — in DuckDB/Parquet locale con sync GCS.
- **Astro Dashboard**: Heatmap vocabolario 🟢🟡🔴, drill-down per parola, grafici attività stile OpenClaw/GitHub.

## Persistenza Dati

- **Audio**: GCS `gs://hummerli-audio-vault/` (raw audio, turn metadata JSONL)
- **SRS State**: `data/users/{profile_id}/srs_state.json` + mirror GCS
- **Telemetry**: DuckDB/Parquet locale + sync GCS (`gs://hummerli-audio-vault/telemetry/`)
- **Eval Results**: JSONL per sessione in GCS, consultabili dalla dashboard

## Multi-Profile Architecture

| Profile | Level | Curriculum | Note |
|---|---|---|---|
| `riccardo` | B1 | Goethe B1 Wortliste | **Prioritario MVP** — naturalizzazione Zurigo |
| `ale` | A1-A2 | Tandem P3 (DE/FR/EN) | Alessandro, Primary 3 — post-MVP |
| `sebi` | Early Immersion | Tandem P1 (DE/EN) | Sebastian, Primary 1 — post-MVP |

## Fasi di Implementazione

1. **Fase 1**: Curriculum ingestion + SRS Engine (SM-2, Goethe B1 Wortliste)
2. **Fase 2**: Live Audio Pipeline + Gemini Barge-In (WebSocket ADK)
3. **Fase 3**: Audio Vault GCS + Telemetria Datalake
4. **Fase 4**: Multi-Judge asincrono + Replay CLI
5. **Fase 5**: Telegram Bot + Web Frontend
6. **Fase 6**: Astro Analytics Dashboard

## Successo

Il progetto è riuscito quando Riccardo può:
1. Aprire il web client o Telegram, parlare in tedesco per 10-15 minuti
2. Interrompere Frau Blücher naturalmente senza lag artificioso
3. Vedere nel dashboard che il suo vocabolario B1 cresce settimana su settimana
4. Ripassare l'esame FIDE B1 e superare la soglia orale

## Riferimenti

- [SPEC.md originale](file:///home/riccardo/git/respec/specs/agents/hummerli-b1-adk/SPEC.md) (RESPEC)
- [Input Prompt vocale](file:///home/riccardo/git/respec/specs/agents/hummerli-b1-adk/input_prompt.md) (trascrizione idea originale)
- Skill ADK Python: `adk-python`
- Skill esistente Hermes: `learn-german-hummerli`
