---
speck_version: "0.1"
mode: reverse-engineered
source_urls:
  - https://finnishit.ulusoyapps.com/
  - https://finnishit.ulusoyapps.com/about.html
  - https://ulusoyapps.com/
  - https://play.google.com/store/apps/details?id=com.sopuacademy.finnishit
  - https://apps.apple.com/us/app/finnish-it-yki-test-practice/id6742380858
created_at: 2026-10-30
---

# Reverse-Engineered SPEC: "Finnish It!" / "Finish it: YKI & German Exam Prep"

## 1. Executive Summary & Identity
* **App Name**: **Finnish it** (recently rebranded on stores as **Finish it: YKI & Learn Finnish / German** to expand from Finland into the German citizenship exam market).
* **Creators**: **Cagatay Ulusoy** (`@ulusoyca`, Google Developer Expert for Flutter & Dart, ex-Wolt, Helsinki) & **Dilara Akcakoca** (Head of Product / UX Designer).
* **Company**: Originally **Sopu Academy Oy**, now **Ulusoy Apps Oy** (Espoo, Finland, Business ID `FI35811655`).
* **Traction & Monetization**: **14,000+ learners**, **~€2,000/month MRR**, Freemium with daily quota + Premium Subscription (monthly/annual).
* **Core Thesis (Outcome-Based Language Prep)**:
  Unlike generalist gamified apps (Duolingo teaching *"You're quite a wizard"*), **Finnish It** is strictly **outcome-based**: every single activity exists to make an immigrant pass the **state language exam required for citizenship/residence**:
  * 🇫🇮 **Finland**: **YKI Test** (*Yleinen kielitutkinto*, Level 3–4 = CEFR B1–B2 required by *Migri* for Finnish citizenship).
  * 🇩🇪 **Germany / DACH**: **DTZ** (*Deutsch-Test für Zuwanderer*), **Goethe B1/B2**, and **telc B1/B2**.

---

## 2. Reverse-Engineered Product Architecture & Feature Matrix

From scraping `finnishit.ulusoyapps.com`, `ulusoyapps.com`, the Google Play / App Store manifests (`com.sopuacademy.finnishit`), and Cagatay's public Flutter/Firebase repositories (`@ulusoyca`), here is the exact product specification:

| Module | Finnish (YKI) | German (Goethe / telc / DTZ) | How It Works Under the Hood |
| :--- | :---: | :---: | :--- |
| **1. Timed Exam Speaking Simulator** | ✅ | ✅ | Replicates official oral exam tasks with a preparation countdown timer + speaking recording timer (**Exam Mode** vs **Study Mode**). |
| **2. Real-Life AI Roleplay Dialogues** | ✅ | ✅ | Contextual bureaucratic & survival scenarios (*Kela / Behörde / Gemeinde*, booking a doctor, workplace, complaints) spoken out loud or in chat. |
| **3. Picture Description Speaking** | ✅ | ✅ | Shows an everyday scene photo; user describes it out loud (classic Goethe B1 / DTZ / YKI task); AI scores it and provides a native sample answer + tied vocabulary. |
| **4. Outcome-Based AI Scoring Rubric** | ✅ | ✅ | Instant post-turn breakdown on **Fluency, Grammar, Pronunciation, Wording**, mapped directly to the **YKI 1–6 scale** or **CEFR A1–B2 scale** (*"Your level on the scale, and what it takes to reach the next one"*). |
| **5. Register Switcher (`Kirjakieli` vs `Puhekieli`)** | ✅ | ➖ | Lets learners toggle between formal textbook Finnish (*Minä olen*) and spoken street Finnish (*Mä oon*) before starting a speaking scenario. |
| **6. Exam Writing Lab** | ✅ | ✅ | Formal letters, emails, complaints, and forum posts with inline AI diff corrections and vocabulary upgrades. |
| **7. Listening & Reading Exam Drills** | ✅ | ✅ | Heading matching, gap-fill, and audio comprehension modeled on official YKI/telc/Goethe papers. |
| **8. "What Do You Say?" (Pragmatic Audio MCQ)** | ✅ | 🔜 | User hears a situational prompt and 3 spoken replies, and picks the culturally/pragmatically appropriate response. |
| **9. Inflection & Conjugation Inspector** | ✅ | ✅ | Instant lookup of any verb, noun, or adjective showing full declension/conjugation tables + example sentences. |
| **10. Daily News at 3 Levels** | ✅ | 🔜 | Current local news rewritten at 3 proficiency tiers with tap-to-translate vocabulary and comprehension quizzes. |
| **11. 12 Native Support Languages** | ✅ | ✅ | Explanations and feedback delivered in the learner's native language (**Italian**, English, Turkish, Ukrainian, Arabic, etc.) while practicing Finnish/German. |

---

## 3. Reverse-Engineered Tech Stack

Based on `@ulusoyca`'s open-source footprint and public workshops:
1. **Mobile & Multi-Platform Client**: **Flutter & Dart** (`com.sopuacademy.finnishit` on Android, `id6742380858` on iOS).
   * UI built with Cagatay's own [`wolt_modal_sheet`](https://github.com/ulusoyca/wolt_modal_sheet) (multi-page bottom sheets for task setup -> recording -> AI feedback breakdown), `flex_color_scheme`, and `audioplayers`.
2. **AI & Backend Infrastructure**:
   * **Firebase** (Auth, Firestore, Cloud Storage, Remote Config) + **Firebase AI Logic / Gemini API** (as demonstrated in `ulusoyca/hive-flutter-workshop`).
   * Turn-based audio/text evaluation prompts returning structured JSON rubrics (Grammar correction, Vocabulary upgrade, Native rewrite, Predicted YKI/CEFR grade).
3. **Monetization Engine (Why It Makes ~€2k/mo)**:
   * **High Willingness-To-Pay (WTP) Niche**: An immigrant applying for citizenship in Finland or Switzerland/Germany pays €150–€300+ for the official exam and waits months for a slot; failing costs months of delay. Paying €10–€20/month for an app that guarantees passing the oral exam is a no-brainer.
   * **Daily Free Taste + Hard Paywall on AI Feedback**: Users can do 1–2 short exercises per day for free; unlocking unlimited AI speaking/writing evaluations and full timed mock exams requires **Premium**.

---

## 4. Head-to-Head: *Finnish It* vs *Hummerli B1 ADK* (Cosa abbiamo già in più e cosa possiamo rubargli!)

### 🏆 Dove **Hummerli** è GIÀ più avanzato di *Finnish It*:
1. **True Bidirectional Barge-In & Dual-Voice Persona (`Frau Leonie Blücher 🐎` + `Rijckard 🇮🇹`)**:
   * *Finnish It* è quasi interamente **turn-based** (registri il vocale → aspetti la scheda di feedback).
   * *Hummerli* ha il **Pallino Vocale con Barge-In** e il doppio agente ADK con switch istantaneo tedesco/italiano quando dici *"Non ho capito"*.
2. **Motore Spaced Repetition (SM-2) ancorato alla Wortliste Ufficiale Goethe B1**:
   * *Hummerli* traccia scientificamente ogni singolo lemma (`1d → 7d → 15d → 30d → 90d` e reset `🔴 struggling`) e costringe Frau Blücher a incastonare le tue 3 parole in scadenza nella conversazione.
3. **Two-Level Trajectory Evals & Closed-Loop Judge**:
   * Nessuna app consumer ha un harness ADK `.test.json` + LLM-as-Judge che separa bug di harness da bug pedagogici.

### 💡 Cosa possiamo "rubare" subito da *Finnish It* per rendere **Hummerli** una killer app (anche monetizzabile per la Svizzera — **FIDE / KDE / Einbürgerung Zürich**!):
1. **Modalità "Simulazione Esame FIDE / Goethe B1 Cronometrata" (Exam Mode vs Study Mode)**:
   * Aggiungere i 3 task classici dell'orale FIDE / Goethe B1:
     * **Task 1**: *Sich vorstellen & Rückfragen* (Presentazione + domande dell'esaminatore su Zurigo/Comune).
     * **Task 2**: *Bildbeschreibung / Situazione illustrata* (Descrivere un'immagine di vita quotidiana svizzera — es. *Gemeinde*, *SBB*, *Krankenkasse* — generata con NanoBanana!).
     * **Task 3**: *Gemeinsam etwas planen / Problem risolvere* (es. organizzare un evento di quartiere o prendere un appuntamento in Comune).
2. **"Il tuo livello FIDE oggi" (Outcome Score Bar: A1 → A2 → B1 Pass Bar)**:
   * Come fa *Finnish It* con la scala YKI, mostrare dopo ogni sessione un indicatore chiaro: **`Livello stimato: A2+ (mancano +0.3 punti su Wortschatz per il B1 FIDE)`** + **"Come l'avrebbe detto un madrelingua"** (*Native Rewrite*).
3. **5-Minute Daily Local News (Zürich / SRF Easy B1)**:
   * Una notizia del giorno su Zurigo/Svizzera riscritta a livello B1 usando le tue parole `due` dello Spaced Repetition, con 2 domande orali di comprensione (*Hören & Sprechen*)!
