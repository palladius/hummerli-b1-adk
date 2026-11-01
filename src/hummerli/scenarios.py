"""Entropic Visual Scenarios, Italian Director Override, FIDE B1 Outcome Rubric (Track 2)
and Interactive Scene Vocabulary Hotspots (SVG Arrows) + Sample Conversations (Track 3).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, Optional
import urllib.parse

from pydantic import BaseModel, Field

from hummerli.curriculum import CurriculumRepository
from hummerli.gender import GENDER_PALETTE, GenderCode, GenderResolver, annotate_german_text
from hummerli.profiles import ProfileManager
from hummerli.srs import SRSEngine


ClientLayout = Literal["mobile_portrait", "desktop_landscape"]
AspectRatio = Literal["1:1", "16:9"]


class SceneVocabHotspot(BaseModel):
    """Interactive vocabulary callout on a scene image with directional SVG arrow coordinates."""

    lemma: str
    display_headword: str
    gender: Literal["F", "M", "N", "verb"]
    article: Literal["die", "der", "das", ""]
    color_hex: str
    color_name_it: str
    css_class: str
    translation_it: str
    phonetic_hint: str = ""
    example_de: str = ""
    # Normalized coordinates (0..100) for pill badge and arrow tip on the scene image
    label_x: float
    label_y: float
    target_x: float
    target_y: float


class DialogueLine(BaseModel):
    """A single line in a scene's Sample Conversation (Track 3)."""

    speaker: str
    role: Literal["interlocutor", "learner"]
    voice: str = "de-DE-Neural2-F"
    text_de: str
    annotated_html: str = ""
    text_it: str
    highlighted_words: list[str] = Field(default_factory=list)


class SampleConversation(BaseModel):
    """4-6 turn realistic B1 dialogue anchored to the visual scene."""

    title_de: str
    title_it: str
    lines: list[DialogueLine] = Field(default_factory=list)


class EntropicScenario(BaseModel):
    """Complete visual situation card with entropy metadata, hotspots, sample dialogue, and SRS target words."""

    scenario_id: str
    title_de: str
    title_it: str
    location_de: str
    time_and_season_de: str
    interlocutor_name: str
    interlocutor_mood_de: str
    situation_summary_de: str
    situation_summary_it: str
    client_layout: ClientLayout = "mobile_portrait"
    aspect_ratio: AspectRatio = "1:1"
    image_data_url: str = ""
    target_words: list[str] = Field(default_factory=list)
    test_questions_de: list[str] = Field(default_factory=list)
    hotspots: list[SceneVocabHotspot] = Field(default_factory=list)
    sample_conversation: SampleConversation
    director_notes_it: str = ""


class FideExamOutcome(BaseModel):
    """Outcome-based FIDE B1 oral evaluation rubric (Stile 'Finnish It!')."""

    fide_level: str
    overall_pct: int
    aufgabenerfuellung_pct: int
    fluessigkeit_pct: int
    wortschatz_pct: int
    strukturen_pct: int
    user_sentence: str
    native_b1_rewrite: str
    rewrite_annotated_html: str
    next_step_advice_it: str
    used_target_words: list[str] = Field(default_factory=list)


def _make_hotspot(
    lemma: str,
    gender: Literal["F", "M", "N", "verb"],
    translation_it: str,
    label_x: float,
    label_y: float,
    target_x: float,
    target_y: float,
    example_de: str = "",
    phonetic_hint: str = "",
) -> SceneVocabHotspot:
    if gender in ("F", "M", "N"):
        pal = GENDER_PALETTE[gender]  # type: ignore[index]
        article = pal["article"]
        headword = f"{article} {lemma}"
        color_hex = pal["color_hex"]
        color_name_it = pal["color_name_it"]
        css_class = pal["css_class"]
    else:
        article = ""
        headword = lemma
        color_hex = "#f59e0b"
        color_name_it = "ambra (verbo)"
        css_class = "gender-verb"

    return SceneVocabHotspot(
        lemma=lemma,
        display_headword=headword,
        gender=gender,
        article=article,  # type: ignore[arg-type]
        color_hex=color_hex,
        color_name_it=color_name_it,
        css_class=css_class,
        translation_it=translation_it,
        phonetic_hint=phonetic_hint or lemma,
        example_de=example_de or f"Können Sie '{headword}' im Satz verwenden?",
        label_x=label_x,
        label_y=label_y,
        target_x=target_x,
        target_y=target_y,
    )


def _build_dialogue_line(
    speaker: str,
    role: Literal["interlocutor", "learner"],
    text_de: str,
    text_it: str,
    highlighted_words: list[str],
    resolver: GenderResolver,
) -> DialogueLine:
    ann = annotate_german_text(text_de, resolver=resolver)
    html_out = ann["annotated_html"]
    # Bold the target highlighted words in the annotated HTML
    for hw in highlighted_words:
        html_out = html_out.replace(f">{hw}<", f"><strong>{hw}</strong><")
    return DialogueLine(
        speaker=speaker,
        role=role,
        voice="de-DE-Neural2-B" if role == "interlocutor" else "de-DE-Neural2-F",
        text_de=ann["clean_text"],
        annotated_html=html_out,
        text_it=text_it,
        highlighted_words=highlighted_words,
    )


def _render_scene_svg_data_url(
    theme: str,
    title_de: str,
    subtitle_de: str,
    aspect_ratio: AspectRatio,
) -> str:
    """Generates a vivid, illustrated SVG scene matching the scenario and aspect ratio (1:1 or 16:9)."""
    width = 600 if aspect_ratio == "1:1" else 800
    height = 600 if aspect_ratio == "1:1" else 450

    if theme == "park":
        # Zürich Park with sun, tree (left-top), lawn (bottom), park bench (left-bottom), elderly man (center), dog & poop/grass (right)
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="{width}" height="{height}" preserveAspectRatio="none">
          <defs>
            <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="#0ea5e9"/>
              <stop offset="62%" stop-color="#bae6fd"/>
            </linearGradient>
            <linearGradient id="grass" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="#22c55e"/>
              <stop offset="100%" stop-color="#15803d"/>
            </linearGradient>
          </defs>
          <!-- Sky & Sun -->
          <rect x="0" y="0" width="100" height="62" fill="url(#sky)"/>
          <circle cx="84" cy="16" r="8" fill="#fde047" opacity="0.92"/>
          <!-- Zürich Alps silhouette -->
          <polygon points="0,62 22,44 42,62" fill="#94a3b8" opacity="0.45"/>
          <polygon points="32,62 58,40 85,62" fill="#64748b" opacity="0.4"/>
          <!-- Wiese (Lawn) at y=60..100 -->
          <rect x="0" y="60" width="100" height="40" fill="url(#grass)"/>
          <!-- Baum (Tree) around x=20, y=35 -->
          <rect x="17" y="40" width="6" height="25" rx="1" fill="#78350f"/>
          <circle cx="20" cy="30" r="14" fill="#16a34a"/>
          <circle cx="13" cy="34" r="10" fill="#15803d"/>
          <circle cx="27" cy="34" r="10" fill="#22c55e"/>
          <!-- Parkbank (Bench) around x=26, y=72 -->
          <rect x="12" y="67" width="26" height="4" rx="1" fill="#b45309"/>
          <rect x="12" y="72" width="26" height="3" rx="1" fill="#92400e"/>
          <rect x="15" y="75" width="2.5" height="7" fill="#451a03"/>
          <rect x="33" y="75" width="2.5" height="7" fill="#451a03"/>
          <!-- Rentner (Elderly Man) around x=52, y=58 -->
          <circle cx="52" cy="47" r="4.5" fill="#fed7aa"/>
          <rect x="48.5" y="52" width="7" height="14" rx="2" fill="#334155"/>
          <line x1="50" y1="66" x2="49" y2="77" stroke="#1e293b" stroke-width="2.5"/>
          <line x1="54" y1="66" x2="55" y2="77" stroke="#1e293b" stroke-width="2.5"/>
          <!-- Walking stick & leash -->
          <line x1="47" y1="58" x2="44" y2="77" stroke="#78350f" stroke-width="1.4"/>
          <path d="M55,57 Q64,65 71,69" stroke="#f43f5e" stroke-width="1.1" fill="none" stroke-dasharray="1.5,1"/>
          <!-- Hund (Dog) around x=74, y=72 -->
          <ellipse cx="74" cy="72" rx="6" ry="3.8" fill="#d97706"/>
          <circle cx="79" cy="69" r="3.2" fill="#b45309"/>
          <line x1="70" y1="75" x2="70" y2="81" stroke="#92400e" stroke-width="1.8"/>
          <line x1="77" y1="75" x2="77" y2="81" stroke="#92400e" stroke-width="1.8"/>
          <!-- Das Geschäft (Dog's business / Robidog spot) around x=86, y=82 -->
          <circle cx="86" cy="82" r="2.6" fill="#713f12"/>
          <circle cx="86" cy="80.2" r="1.8" fill="#854d0e"/>
          <!-- Caption Banner -->
          <rect x="3" y="4" width="66" height="12" rx="3" fill="#0f172a" opacity="0.72"/>
          <text x="6" y="10" fill="#f8fafc" font-family="sans-serif" font-size="3.6" font-weight="bold">{title_de}</text>
          <text x="6" y="14" fill="#cbd5e1" font-family="sans-serif" font-size="2.6">{subtitle_de}</text>
        </svg>"""
    elif theme == "indian_restaurant":
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="{width}" height="{height}" preserveAspectRatio="none">
          <rect x="0" y="0" width="100" height="100" fill="#451a03"/>
          <rect x="0" y="0" width="100" height="65" fill="#7c2d12"/>
          <!-- Decorative Taj arches -->
          <path d="M15,55 Q25,30 35,55 Z" fill="#9a3412" opacity="0.6"/>
          <path d="M65,55 Q75,30 85,55 Z" fill="#9a3412" opacity="0.6"/>
          <!-- Rude Waitress (Kellnerin) at x=35, y=48 -->
          <circle cx="35" cy="36" r="5" fill="#fdba74"/>
          <rect x="30" y="42" width="10" height="20" rx="2" fill="#be123c"/>
          <!-- Speisekarte (Menu) in hand at x=45, y=50 -->
          <rect x="42" y="44" width="8" height="11" rx="1" fill="#fde047"/>
          <!-- Tisch (Table) at x=55, y=75 -->
          <rect x="20" y="68" width="65" height="6" rx="2" fill="#fcd34d"/>
          <rect x="28" y="74" width="4" height="20" fill="#78350f"/>
          <rect x="72" y="74" width="4" height="20" fill="#78350f"/>
          <!-- Curry Gericht (Dish) at x=58, y=64 -->
          <ellipse cx="58" cy="65" rx="8" ry="3.5" fill="#ea580c"/>
          <!-- Rechnung (Bill) at x=75, y=65 -->
          <rect x="72" y="61" width="7" height="6" fill="#f8fafc"/>
          <rect x="3" y="4" width="78" height="12" rx="3" fill="#0f172a" opacity="0.78"/>
          <text x="6" y="10" fill="#fde047" font-family="sans-serif" font-size="3.5" font-weight="bold">{title_de}</text>
          <text x="6" y="14" fill="#fed7aa" font-family="sans-serif" font-size="2.5">{subtitle_de}</text>
        </svg>"""
    elif theme == "baeckerei":
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="{width}" height="{height}" preserveAspectRatio="none">
          <rect x="0" y="0" width="100" height="100" fill="#fef3c7"/>
          <rect x="0" y="58" width="100" height="42" fill="#d97706"/>
          <!-- Counter & Gipfeli / Brot -->
          <rect x="10" y="52" width="80" height="16" rx="2" fill="#f8fafc" stroke="#92400e" stroke-width="1.5"/>
          <ellipse cx="30" cy="60" rx="6" ry="3" fill="#b45309"/>
          <ellipse cx="52" cy="60" rx="5" ry="2.8" fill="#f59e0b"/>
          <rect x="72" y="42" width="12" height="14" rx="2" fill="#334155"/>
          <rect x="3" y="4" width="74" height="12" rx="3" fill="#0f172a" opacity="0.75"/>
          <text x="6" y="10" fill="#f8fafc" font-family="sans-serif" font-size="3.5" font-weight="bold">{title_de}</text>
          <text x="6" y="14" fill="#fde68a" font-family="sans-serif" font-size="2.5">{subtitle_de}</text>
        </svg>"""
    else:
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="{width}" height="{height}" preserveAspectRatio="none">
          <rect x="0" y="0" width="100" height="100" fill="#1e293b"/>
          <rect x="0" y="60" width="100" height="40" fill="#334155"/>
          <!-- Kreisbüro Schalter -->
          <rect x="15" y="25" width="70" height="35" rx="2" fill="#0f172a" stroke="#38bdf8" stroke-width="1.2"/>
          <circle cx="50" cy="44" r="5" fill="#bae6fd"/>
          <rect x="32" y="58" width="12" height="8" fill="#f8fafc"/>
          <rect x="58" y="56" width="10" height="10" rx="1" fill="#ef4444"/>
          <rect x="3" y="4" width="76" height="12" rx="3" fill="#0f172a" opacity="0.82"/>
          <text x="6" y="10" fill="#38bdf8" font-family="sans-serif" font-size="3.5" font-weight="bold">{title_de}</text>
          <text x="6" y="14" fill="#cbd5e1" font-family="sans-serif" font-size="2.5">{subtitle_de}</text>
        </svg>"""

    compact = " ".join(svg.split())
    return "data:image/svg+xml;utf8," + urllib.parse.quote(compact)


class ScenarioEngine:
    """Generates Zero-Click Entropic Visual Scenarios with Hotspots, Sample Conversations, and Italian Director Override."""

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        curriculum_repo: Optional[CurriculumRepository] = None,
        profile_manager: Optional[ProfileManager] = None,
    ) -> None:
        self.curriculum_repo = curriculum_repo or CurriculumRepository()
        self.profile_manager = profile_manager or ProfileManager()
        self.srs_engine = SRSEngine(
            data_dir=data_dir,
            curriculum_repo=self.curriculum_repo,
            profile_manager=self.profile_manager,
        )
        self.gender_resolver = GenderResolver(curriculum_repo=self.curriculum_repo)
        self._custom_scenarios: dict[str, EntropicScenario] = {}

    def _build_curated_templates(
        self,
        due_lemmas: list[str],
        client_layout: ClientLayout,
    ) -> list[EntropicScenario]:
        aspect: AspectRatio = "1:1" if client_layout == "mobile_portrait" else "16:9"
        r = self.gender_resolver

        # 1. Canonical Zürich Park Scene (Track 3 centerpiece: Parkbank, Baum, Rentner, Wiese, Hund, Geschäft)
        park_title = "🌳 Zürcher Park am Morgen — Spaziergang mit dem Hund"
        park_sub = "Sonniger Herbstmorgen · Herr Meier (freundlicher Rentner)"
        park_hotspots = [
            _make_hotspot(
                lemma="Baum",
                gender="M",
                translation_it="albero",
                label_x=18,
                label_y=18,
                target_x=20,
                target_y=30,
                example_de="Der alte Baum im Park spendet im Sommer viel Schatten.",
            ),
            _make_hotspot(
                lemma="Parkbank",
                gender="F",
                translation_it="panchina del parco",
                label_x=16,
                label_y=86,
                target_x=25,
                target_y=71,
                example_de="Wir sitzen gerne auf der sonnigen Parkbank am Zürichsee.",
            ),
            _make_hotspot(
                lemma="Rentner",
                gender="M",
                translation_it="pensionato / vecchietto",
                label_x=50,
                label_y=28,
                target_x=52,
                target_y=49,
                example_de="Der freundliche Rentner geht jeden Tag im Quartier spazieren.",
            ),
            _make_hotspot(
                lemma="Wiese",
                gender="F",
                translation_it="prato",
                label_x=46,
                label_y=88,
                target_x=48,
                target_y=76,
                example_de="Auf dieser grünen Wiese dürfen die Hunde frei spielen.",
            ),
            _make_hotspot(
                lemma="Hund",
                gender="M",
                translation_it="cane",
                label_x=74,
                label_y=52,
                target_x=74,
                target_y=71,
                example_de="Mein Hund freut sich jeden Morgen auf den Spaziergang.",
            ),
            _make_hotspot(
                lemma="Geschäft",
                gender="N",
                translation_it="bisognini (del cane) / commissione",
                label_x=84,
                label_y=91,
                target_x=86,
                target_y=82,
                example_de="Der Hund macht sein Geschäft auf der Wiese, und man nimmt das Säckli.",
            ),
        ]
        park_convo = SampleConversation(
            title_de="Smalltalk im Park über das Wetter und den Hund",
            title_it="Chiacchierata al parco sul bel tempo e i bisognini del cane",
            lines=[
                _build_dialogue_line(
                    speaker="Herr Meier (Rentner)",
                    role="interlocutor",
                    text_de="Grüezi! Schönes Wetter heute hier im Park, oder?",
                    text_it="Buongiorno! Bella giornata oggi qui al parco, vero?",
                    highlighted_words=["Wetter", "Park"],
                    resolver=r,
                ),
                _build_dialogue_line(
                    speaker="Sie (Kandidat B1)",
                    role="learner",
                    text_de="Ja, herrlich! Ich sitze kurz auf der Parkbank unter dem Baum. Kommen Sie oft hierher?",
                    text_it="Sì, splendida! Mi siedo un attimo sulla panchina sotto l'albero. Viene spesso qui?",
                    highlighted_words=["Parkbank", "Baum"],
                    resolver=r,
                ),
                _build_dialogue_line(
                    speaker="Herr Meier (Rentner)",
                    role="interlocutor",
                    text_de="Ich komme jeden Morgen mit meinem Hund auf diese Wiese, damit er sein Geschäft machen kann.",
                    text_it="Vengo ogni mattina col mio cane su questo prato per fargli fare i suoi bisognini.",
                    highlighted_words=["Morgen", "Hund", "Wiese", "Geschäft"],
                    resolver=r,
                ),
                _build_dialogue_line(
                    speaker="Sie (Kandidat B1)",
                    role="learner",
                    text_de="Das ist sehr vorbildlich! In unserer Gemeinde in Zürich gibt es zum Glück überall Robidog-Behälter.",
                    text_it="È molto esemplare! Nel nostro comune a Zurigo per fortuna ci sono i contenitori Robidog ovunque.",
                    highlighted_words=["Gemeinde"],
                    resolver=r,
                ),
            ],
        )
        sc_park = EntropicScenario(
            scenario_id="zuerich_park_hund",
            title_de=park_title,
            title_it="Parco a Zurigo al mattino — Passeggiata col cane",
            location_de="Bäckeranlage / Park in Zürich",
            time_and_season_de="Sonniger Herbstmorgen, 08:30 Uhr",
            interlocutor_name="Herr Meier (Rentner)",
            interlocutor_mood_de="herzlich, gesprächig und entspannt",
            situation_summary_de=(
                "Sie treffen im Zürcher Park einen freundlichen Rentner mit seinem Hund neben einer Parkbank. "
                "Sprechen Sie über den Alltag im Quartier und Ihre Pflichten in der Gemeinde."
            ),
            situation_summary_it=(
                "Incontri al parco un simpatico pensionato col cane vicino a una panchina. "
                "Chiama in causa le parole B1 di oggi parlando della vita di quartiere a Zurigo."
            ),
            client_layout=client_layout,
            aspect_ratio=aspect,
            image_data_url=_render_scene_svg_data_url("park", park_title, park_sub, aspect),
            target_words=due_lemmas[:3] or ["abholen", "Antrag", "Gemeinde"],
            test_questions_de=[
                "Was macht der Rentner jeden Morgen mit seinem Hund auf der Wiese?",
                f"Wie können Sie das Wort '{(due_lemmas or ['Gemeinde'])[0]}' in dieses Gespräch im Park einbauen?",
            ],
            hotspots=park_hotspots,
            sample_conversation=park_convo,
        )

        # 2. Kreisbüro 4 Zürich — Einbürgerungsgespräch
        kb_title = "🏛️ Kreisbüro Zürich — Schalter für Einbürgerung"
        kb_sub = "Montagmorgen im Winter · Frau Keller (streng, aber korrekt)"
        kb_hotspots = [
            _make_hotspot("Schalter", "M", "sportello", 48, 22, 50, 44, "Bitte gehen Sie zum Schalter drei."),
            _make_hotspot("Antrag", "M", "domanda / richiesta", 26, 78, 36, 62, "Ich reiche heute den Antrag ein."),
            _make_hotspot("Formular", "N", "modulo", 42, 86, 40, 64, "Haben Sie das Formular unterschrieben?"),
            _make_hotspot("Ausweis", "M", "documento d'identità", 72, 78, 63, 61, "Hier ist mein Ausweis."),
            _make_hotspot("Behörde", "F", "autorità / ufficio pubblico", 18, 32, 22, 42, "Die Behörde prüft Ihre Unterlagen."),
        ]
        kb_convo = SampleConversation(
            title_de="Am Schalter der Gemeinde den Antrag einreichen",
            title_it="Allo sportello del comune per consegnare la domanda",
            lines=[
                _build_dialogue_line(
                    speaker="Frau Keller (Kreisbüro)",
                    role="interlocutor",
                    text_de="Guten Morgen! Haben Sie heute einen Termin bei unserer Behörde?",
                    text_it="Buongiorno! Ha un appuntamento oggi presso il nostro ufficio?",
                    highlighted_words=["Termin", "Behörde"],
                    resolver=r,
                ),
                _build_dialogue_line(
                    speaker="Sie (Kandidat B1)",
                    role="learner",
                    text_de="Guten Morgen! Ja, ich möchte meinen Antrag auf Einbürgerung und das Formular abgeben.",
                    text_it="Buongiorno! Sì, vorrei consegnare la mia domanda di naturalizzazione e il modulo.",
                    highlighted_words=["Antrag", "Einbürgerung", "Formular"],
                    resolver=r,
                ),
                _build_dialogue_line(
                    speaker="Frau Keller (Kreisbüro)",
                    role="interlocutor",
                    text_de="Sehr gut. Haben Sie auch das Sprachzertifikat B1 und Ihren Ausweis dabei?",
                    text_it="Molto bene. Ha con sé anche il certificato di lingua B1 e il Suo documento?",
                    highlighted_words=["Sprachzertifikat", "Ausweis"],
                    resolver=r,
                ),
                _build_dialogue_line(
                    speaker="Sie (Kandidat B1)",
                    role="learner",
                    text_de="Natürlich, hier sind alle Unterlagen. Wann kann ich den neuen Pass auf der Gemeinde abholen?",
                    text_it="Certamente, ecco tutti i documenti. Quando potrò ritirare il nuovo passaporto in comune?",
                    highlighted_words=["Unterlagen", "Pass", "Gemeinde"],
                    resolver=r,
                ),
            ],
        )
        sc_kb = EntropicScenario(
            scenario_id="kreisbuero_einbuergerung",
            title_de=kb_title,
            title_it="Kreisbüro Zurigo — Sportello Naturalizzazione",
            location_de="Kreisbüro 4, Zürich",
            time_and_season_de="Montagmorgen im Regen, 09:15 Uhr",
            interlocutor_name="Frau Keller (Sachbearbeiterin)",
            interlocutor_mood_de="bürokratisch, präzise und leicht in Eile",
            situation_summary_de=(
                "Sie stehen am Schalter im Kreisbüro Zürich und möchten Ihre Unterlagen für die Einbürgerung einreichen."
            ),
            situation_summary_it=(
                "Sei allo sportello del Kreisbüro di Zurigo per consegnare i documenti della naturalizzazione."
            ),
            client_layout=client_layout,
            aspect_ratio=aspect,
            image_data_url=_render_scene_svg_data_url("kreisbuero", kb_title, kb_sub, aspect),
            target_words=due_lemmas[:3] or ["Antrag", "Einbürgerung", "Gemeinde"],
            test_questions_de=[
                "Welche Unterlagen müssen Sie am Schalter der Gemeinde vorzeigen?",
                "Erklären Sie Frau Keller in einem Satz mit 'weil', warum Sie sich in Zürich einbürgern lassen möchten.",
            ],
            hotspots=kb_hotspots,
            sample_conversation=kb_convo,
        )

        # 3. Bäckerei am Bellevue
        bk_title = "🥐 Bäckerei am Bellevue — Gipfeli & Nachbarschaft"
        bk_sub = "Samstagmorgen im Frühling · Herr Bünzli (Bäckermeister)"
        bk_hotspots = [
            _make_hotspot("Bäckerei", "F", "panetteria", 20, 26, 25, 45, "Die Bäckerei öffnet um sechs Uhr."),
            _make_hotspot("Brot", "N", "pane", 28, 78, 30, 60, "Ich kaufe ein frisches Brot für das Wochenende."),
            _make_hotspot("Brötchen", "N", "panino / rosette", 52, 82, 52, 60, "Zwei knusprige Brötchen, bitte!"),
            _make_hotspot("Kaffee", "M", "caffè", 76, 30, 76, 48, "Einen warmen Kaffee zum Mitnehmen."),
            _make_hotspot("Rechnung", "F", "conto / scontrino", 80, 78, 68, 56, "Kann ich die Rechnung mit Karte bezahlen?"),
        ]
        bk_convo = SampleConversation(
            title_de="Frühstück bestellen und über das Quartierfest sprechen",
            title_it="Ordinare la colazione e parlare della festa di quartiere",
            lines=[
                _build_dialogue_line(
                    speaker="Herr Bünzli (Bäcker)",
                    role="interlocutor",
                    text_de="Grüezi wohl! Was darf es heute Morgen in unserer Bäckerei sein?",
                    text_it="Buongiorno! Cosa posso servirLe stamattina nella nostra panetteria?",
                    highlighted_words=["Morgen", "Bäckerei"],
                    resolver=r,
                ),
                _build_dialogue_line(
                    speaker="Sie (Kandidat B1)",
                    role="learner",
                    text_de="Guten Morgen! Ich hätte gern ein dunkles Brot, zwei Brötchen und einen Kaffee.",
                    text_it="Buongiorno! Vorrei un pane scuro, due panini e un caffè.",
                    highlighted_words=["Brot", "Brötchen", "Kaffee"],
                    resolver=r,
                ),
                _build_dialogue_line(
                    speaker="Herr Bünzli (Bäcker)",
                    role="interlocutor",
                    text_de="Gerne! Kommen Sie heute Nachmittag auch zum Fest von unserem Verein in der Gemeinde?",
                    text_it="Volentieri! Viene anche Lei oggi pomeriggio alla festa della nostra associazione in comune?",
                    highlighted_words=["Verein", "Gemeinde"],
                    resolver=r,
                ),
                _build_dialogue_line(
                    speaker="Sie (Kandidat B1)",
                    role="learner",
                    text_de="Ja, sobald ich meine Kinder von der Schule abhole, kommen wir zusammen vorbei!",
                    text_it="Sì, non appena vado a prendere i miei bambini a scuola, passiamo insieme!",
                    highlighted_words=["Kinder", "Schule"],
                    resolver=r,
                ),
            ],
        )
        sc_bk = EntropicScenario(
            scenario_id="baeckerei_bellevue",
            title_de=bk_title,
            title_it="Panetteria a Bellevue — Colazione & Quartiere",
            location_de="Bäckerei am Bellevue, Zürich",
            time_and_season_de="Samstagmorgen im Frühling, 07:45 Uhr",
            interlocutor_name="Herr Bünzli (Bäckermeister)",
            interlocutor_mood_de="freundlich, neugierig auf Nachbarn",
            situation_summary_de=(
                "Sie kaufen am Samstagmorgen frisches Brot in der Bäckerei und plaudern mit dem Bäcker über Ihre Familie und die Gemeinde."
            ),
            situation_summary_it=(
                "Compri il pane fresco il sabato mattina e chiacchieri col panettiere della famiglia e del comune."
            ),
            client_layout=client_layout,
            aspect_ratio=aspect,
            image_data_url=_render_scene_svg_data_url("baeckerei", bk_title, bk_sub, aspect),
            target_words=due_lemmas[:3] or ["abholen", "Gemeinde", "Verein"],
            test_questions_de=[
                "Bestellen Sie zwei Brötchen und erklären Sie, was Sie heute noch erledigen müssen.",
                "Antworten Sie dem Bäcker auf seine Frage zum Quartierfest.",
            ],
            hotspots=bk_hotspots,
            sample_conversation=bk_convo,
        )

        return [sc_park, sc_kb, sc_bk]

    def generate_entropic_scenarios(
        self,
        profile_id: str = "riccardo",
        count: int = 3,
        client_layout: ClientLayout = "mobile_portrait",
    ) -> list[EntropicScenario]:
        """Produces up to 3 ready-to-play Entropic Scenarios without requiring setup questionnaires."""
        due_entries = self.srs_engine.get_due_words(profile_id=profile_id, limit=3)
        due_lemmas = [e.lemma for e in due_entries]
        templates = self._build_curated_templates(due_lemmas=due_lemmas, client_layout=client_layout)
        return templates[: max(1, min(count, len(templates)))]

    def get_scenario_by_id(
        self,
        scenario_id: str,
        profile_id: str = "riccardo",
        client_layout: ClientLayout = "mobile_portrait",
    ) -> EntropicScenario:
        """Retrieves a curated or director-mutated scenario by ID."""
        if scenario_id in self._custom_scenarios:
            sc = self._custom_scenarios[scenario_id]
            if sc.client_layout != client_layout:
                sc.client_layout = client_layout
                sc.aspect_ratio = "1:1" if client_layout == "mobile_portrait" else "16:9"
            return sc
        for sc in self.generate_entropic_scenarios(
            profile_id=profile_id, count=3, client_layout=client_layout
        ):
            if sc.scenario_id == scenario_id:
                return sc
        return self.generate_entropic_scenarios(
            profile_id=profile_id, count=1, client_layout=client_layout
        )[0]

    def get_scene_vocabulary_and_dialogue(
        self,
        profile_id: str = "riccardo",
        scenario_id: str = "zuerich_park_hund",
    ) -> dict[str, Any]:
        """Track 3 ADK Tool: Returns the interactive SVG arrow hotspots and sample conversation for a scene."""
        sc = self.get_scenario_by_id(scenario_id=scenario_id, profile_id=profile_id)
        return {
            "scenario_id": sc.scenario_id,
            "title_de": sc.title_de,
            "title_it": sc.title_it,
            "aspect_ratio": sc.aspect_ratio,
            "image_data_url": sc.image_data_url,
            "hotspots": [h.model_dump() for h in sc.hotspots],
            "sample_conversation": sc.sample_conversation.model_dump(),
            "target_words": sc.target_words,
        }

    def mutate_scenario_with_director_notes(
        self,
        profile_id: str,
        current_scenario_id: str,
        director_feedback_it: str,
        client_layout: ClientLayout = "mobile_portrait",
    ) -> EntropicScenario:
        """Track 2 ADK Tool ('Regia in Italiano'): Re-spins the scenario setting & interlocutor vibe while preserving SRS target words."""
        base = self.get_scenario_by_id(
            scenario_id=current_scenario_id,
            profile_id=profile_id,
            client_layout=client_layout,
        )
        aspect: AspectRatio = "1:1" if client_layout == "mobile_portrait" else "16:9"
        notes_low = director_feedback_it.lower()
        r = self.gender_resolver

        # Detect Indian restaurant / rude waitress or general custom steering
        is_indian = "indian" in notes_low or "indiano" in notes_low or "curry" in notes_low
        is_rude = any(
            w in notes_low
            for w in ("maleducat", "scortes", "arrabbiat", "antipatic", "fretta", "unhöflich")
        )

        if is_indian or is_rude:
            title_de = "🍛 Indisches Restaurant in Zürich-Wiedikon — Unhöfliche Bedienung"
            sub_de = "Freitagabend · Frau Sharma (sehr unhöflich, genervt und ungeduldig)"
            mood_de = (
                "sehr unhöflich, genervt und ungeduldig"
                if is_rude
                else "hektisch im vollen Restaurant"
            )
            hotspots = [
                _make_hotspot(
                    "Kellnerin",
                    "F",
                    "cameriera (scortese)",
                    24,
                    22,
                    35,
                    38,
                    "Die Kellnerin reagiert heute Abend leider sehr unhöflich.",
                ),
                _make_hotspot(
                    "Speisekarte",
                    "F",
                    "menù",
                    48,
                    32,
                    45,
                    48,
                    "Könnten Sie uns bitte zuerst die Speisekarte bringen?",
                ),
                _make_hotspot(
                    "Tisch",
                    "M",
                    "tavolo",
                    28,
                    84,
                    38,
                    70,
                    "Wir haben vor zwei Tagen einen Tisch am Fenster reserviert.",
                ),
                _make_hotspot(
                    "Gericht",
                    "N",
                    "piatto / portata (curry)",
                    58,
                    50,
                    58,
                    64,
                    "Dieses indische Gericht mit Reis ist mir leider viel zu scharf.",
                ),
                _make_hotspot(
                    "Rechnung",
                    "F",
                    "il conto",
                    78,
                    82,
                    75,
                    64,
                    "Entschuldigung, auf der Rechnung stimmt der Preis nicht.",
                ),
            ]
            convo = SampleConversation(
                title_de="Höflich bleiben trotz unhöflicher Bedienung im indischen Restaurant",
                title_it="Restare educati in tedesco B1 nonostante la cameriera maleducata al ristorante indiano",
                lines=[
                    _build_dialogue_line(
                        speaker="Kellnerin (genervt)",
                        role="interlocutor",
                        text_de="Was wollen Sie? Ich habe keine Zeit! Haben Sie sich endlich entschieden?",
                        text_it="Cosa volete? Non ho tempo! Vi siete finalmente decisi?",
                        highlighted_words=["Zeit"],
                        resolver=r,
                    ),
                    _build_dialogue_line(
                        speaker="Sie (Kandidat B1)",
                        role="learner",
                        text_de="Entschuldigung, wir sitzen erst seit zwei Minuten am Tisch und haben noch keine Speisekarte bekommen.",
                        text_it="Mi scusi, siamo seduti al tavolo solo da due minuti e non abbiamo ancora ricevuto il menù.",
                        highlighted_words=["Tisch", "Speisekarte"],
                        resolver=r,
                    ),
                    _build_dialogue_line(
                        speaker="Kellnerin (unhöflich)",
                        role="interlocutor",
                        text_de="Die Speisekarte liegt doch dort! Nehmen Sie einfach das Tages-Gericht, sonst dauert es eine Stunde.",
                        text_it="Il menù è lì! Prendete semplicemente il piatto del giorno, altrimenti ci vuole un'ora.",
                        highlighted_words=["Speisekarte", "Gericht"],
                        resolver=r,
                    ),
                    _build_dialogue_line(
                        speaker="Sie (Kandidat B1)",
                        role="learner",
                        text_de=(
                            f"Ich bitte Sie um einen freundlichen Ton. Wir möchten heute in Ruhe essen, "
                            f"nachdem wir unseren {(base.target_words or ['Antrag'])[0]} bei der Gemeinde erledigt haben!"
                        ),
                        text_it=(
                            f"Le chiedo gentilmente un tono cortese. Vorremmo mangiare in pace dopo aver sbrigato "
                            f"la nostra pratica ({(base.target_words or ['Antrag'])[0]}) in comune!"
                        ),
                        highlighted_words=["Antrag", "Gemeinde"],
                        resolver=r,
                    ),
                ],
            )
            mutated = EntropicScenario(
                scenario_id=f"{current_scenario_id}_custom",
                title_de=title_de,
                title_it="Ristorante Indiano a Zurigo — Cameriera molto maleducata",
                location_de="Indisches Restaurant Taj Mahal, Zürich-Wiedikon",
                time_and_season_de="Freitagabend, 20:15 Uhr (volles Lokal)",
                interlocutor_name="Frau Sharma (Kellnerin)",
                interlocutor_mood_de=mood_de,
                situation_summary_de=(
                    "Sie sind in einem indischen Restaurant in Zürich. Die Kellnerin ist extrem ungeduldig und unhöflich. "
                    "Beschweren Sie sich sachlich auf B1-Niveau und benutzen Sie trotzdem Ihre SRS-Zielwörter!"
                ),
                situation_summary_it=f"Regia applicata: '{director_feedback_it}'. I 3 vocaboli SRS restano invariati!",
                client_layout=client_layout,
                aspect_ratio=aspect,
                image_data_url=_render_scene_svg_data_url(
                    "indian_restaurant", title_de, sub_de, aspect
                ),
                target_words=list(base.target_words),
                test_questions_de=[
                    "Wie reagieren Sie höflich aber bestimmt auf Deutsch B1, wenn die Kellnerin unhöflich zu Ihnen ist?",
                    f"Bauen Sie die Zielwörter ({', '.join(base.target_words)}) geschickt in Ihre Beschwerde am Tisch ein!",
                ],
                hotspots=hotspots,
                sample_conversation=convo,
                director_notes_it=director_feedback_it,
            )
        else:
            # Generic director mutation preserving target words
            title_de = f"🎬 Custom Szene Zürich — {director_feedback_it[:38]}"
            mutated = base.model_copy(deep=True)
            mutated.scenario_id = f"{current_scenario_id}_custom"
            mutated.title_de = title_de
            mutated.title_it = f"Scena su misura: {director_feedback_it}"
            mutated.interlocutor_mood_de = f"Angepasst nach Regie: {director_feedback_it}"
            mutated.director_notes_it = director_feedback_it
            mutated.target_words = list(base.target_words)

        self._custom_scenarios[mutated.scenario_id] = mutated
        return mutated


def evaluate_fide_turn_outcome(
    user_sentence: str,
    target_words: Optional[list[str]] = None,
) -> FideExamOutcome:
    """Outcome-Based FIDE B1 Exam Rubric Evaluator (Stile 'Finnish It!')."""
    targets = target_words or ["Antrag", "Gemeinde"]
    words = user_sentence.strip().split()
    word_count = len(words)
    low = user_sentence.lower()

    used = [t for t in targets if t.lower() in low]
    has_connector = any(
        c in low for c in ("weil", "dass", "obwohl", "damit", "wenn", "deshalb", "nachdem", "als")
    )

    if word_count >= 10 and (len(used) >= 1 or has_connector):
        fide_level = "B1 Pass ✅" if len(used) < 3 else "B2 🌟"
        aufgabe = 88
        fluessig = 85
        wortschatz = min(98, 78 + len(used) * 7)
        strukturen = 90 if has_connector else 80
        rewrite = user_sentence.strip()
        if not has_connector:
            rewrite = (
                f"{user_sentence.rstrip('.!?')}, weil mir die Integration in unserer Gemeinde sehr wichtig ist."
            )
        advice_it = (
            "Ottimo turno da livello FIDE B1 superato! Hai usato una struttura completa. "
            "Per puntare al B2, aggiungi un connettivo subordinante come 'obwohl' o 'damit'."
        )
    elif word_count >= 5:
        fide_level = "A2+ → Quasi B1"
        aufgabe = 74
        fluessig = 72
        wortschatz = 70 + len(used) * 8
        strukturen = 68
        first_target = targets[0] if targets else "Antrag"
        rewrite = (
            f"Ich möchte heute darüber sprechen, weil ich {first_target} bei der Gemeinde Zürich erledigen muss."
        )
        advice_it = (
            f"Sei a livello A2+ (soglia FIDE vicina!). Per trasformarlo in un B1 pieno, "
            f"allunga la frase con 'weil' o 'damit' e includi '{first_target}'."
        )
    else:
        fide_level = "A2"
        aufgabe = 55
        fluessig = 58
        wortschatz = 54
        strukturen = 52
        first_target = targets[0] if targets else "Antrag"
        rewrite = (
            f"Guten Tag! Ich möchte bitte meinen {first_target} heute Morgen direkt auf der Gemeinde einreichen."
        )
        advice_it = (
            f"Frase troppo breve per l'esame orale FIDE B1 (valutata A2). "
            f"Prova a pronunciare o scrivere una frase completa come nella riscrittura B1 qui sopra!"
        )

    overall = int(round((aufgabe + fluessig + wortschatz + strukturen) / 4))
    ann = annotate_german_text(rewrite)

    return FideExamOutcome(
        fide_level=fide_level,
        overall_pct=overall,
        aufgabenerfuellung_pct=aufgabe,
        fluessigkeit_pct=fluessig,
        wortschatz_pct=wortschatz,
        strukturen_pct=strukturen,
        user_sentence=user_sentence,
        native_b1_rewrite=rewrite,
        rewrite_annotated_html=ann["annotated_html"],
        next_step_advice_it=advice_it,
        used_target_words=used,
    )
