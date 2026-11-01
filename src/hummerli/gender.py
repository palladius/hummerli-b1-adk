"""Cross-Stack German Noun Gender Resolver & On-Demand X-Ray Annotator (Track 4).

Canonical Hummerli Gender Palette:
- Feminine ('die' / 'F') -> Rosa (#f472b6)
- Masculine ('der' / 'M') -> Azzurrino (#38bdf8)
- Neuter ('das' / 'N') -> Grigio (#94a3b8)
"""

from __future__ import annotations

import html
import re
from typing import Any, Literal, Optional

from pydantic import BaseModel

from hummerli.curriculum import CurriculumRepository


GenderCode = Literal["F", "M", "N"]
ArticleCode = Literal["die", "der", "das"]


GENDER_PALETTE: dict[GenderCode, dict[str, str]] = {
    "F": {
        "gender": "F",
        "article": "die",
        "color_hex": "#f472b6",
        "color_name_it": "rosa",
        "emoji": "🌸",
        "css_class": "gender-f",
        "rich_style": "bright_magenta",
    },
    "M": {
        "gender": "M",
        "article": "der",
        "color_hex": "#38bdf8",
        "color_name_it": "azzurrino",
        "emoji": "🩵",
        "css_class": "gender-m",
        "rich_style": "bright_cyan",
    },
    "N": {
        "gender": "N",
        "article": "das",
        "color_hex": "#94a3b8",
        "color_name_it": "grigio",
        "emoji": "🩶",
        "css_class": "gender-n",
        "rich_style": "grey70",
    },
}

ARTICLE_TO_GENDER: dict[str, GenderCode] = {
    "die": "F",
    "der": "M",
    "das": "N",
    "f": "F",
    "m": "M",
    "n": "N",
}


# Built-in Core German B1 Noun Lexicon & Compound Tail Roots (lowercase lemma -> GenderCode)
CORE_GERMAN_NOUN_GENDERS: dict[str, GenderCode] = {
    # Park & Daily Life (Track 3 & Track 2)
    "bank": "F",
    "parkbank": "F",
    "baum": "M",
    "rentner": "M",
    "wiese": "F",
    "hund": "M",
    "geschäft": "N",
    "park": "M",
    "wetter": "N",
    "morgen": "M",
    "tag": "M",
    "abend": "M",
    "nacht": "F",
    "sonne": "F",
    "regen": "M",
    "winter": "M",
    "sommer": "M",
    "frühling": "M",
    "herbst": "M",
    "spaziergang": "M",
    "leine": "F",
    "blume": "F",
    "brunnen": "M",
    "weg": "M",
    # Zurich, Civic & Einbürgerung
    "antrag": "M",
    "gemeinde": "F",
    "behörde": "F",
    "einbürgerung": "F",
    "termin": "M",
    "formular": "N",
    "unterlagen": "F",
    "unterlage": "F",
    "nachbar": "M",
    "nachbarin": "F",
    "verein": "M",
    "steuer": "F",
    "steuern": "F",
    "abstimmung": "F",
    "gesetz": "N",
    "pflicht": "F",
    "recht": "N",
    "schalter": "M",
    "kreisbüro": "N",
    "büro": "N",
    "rathaus": "N",
    "haus": "N",
    "platz": "M",
    "straße": "F",
    "strasse": "F",
    "bahnhof": "M",
    "hof": "M",
    "zug": "M",
    "tram": "N",
    "ticket": "N",
    "fahrkarte": "F",
    "karte": "F",
    "zertifikat": "N",
    "sprachzertifikat": "N",
    "prüfung": "F",
    "ausweis": "M",
    "pass": "M",
    "kanton": "M",
    "stadt": "F",
    "land": "N",
    "schweiz": "F",
    "see": "M",
    # Gastronomy, Bakery & Shopping
    "bäckerei": "F",
    "brot": "N",
    "brötchen": "N",
    "gipfeli": "N",
    "kaffee": "M",
    "tee": "M",
    "wasser": "N",
    "bier": "N",
    "wein": "M",
    "restaurant": "N",
    "kellner": "M",
    "kellnerin": "F",
    "bedienung": "F",
    "speisekarte": "F",
    "rechnung": "F",
    "tisch": "M",
    "essen": "N",
    "gericht": "N",
    "preis": "M",
    "geld": "N",
    "franken": "M",
    # Family, School & Health
    "kind": "N",
    "kinder": "N",
    "schule": "F",
    "lehrer": "M",
    "lehrerin": "F",
    "arzt": "M",
    "ärztin": "F",
    "praxis": "F",
    "apotheke": "F",
    "rezept": "N",
    "familie": "F",
    "frau": "F",
    "mann": "M",
    "freund": "M",
    "freundin": "F",
    "zeit": "F",
    "uhr": "F",
    "woche": "F",
    "monat": "M",
    "jahr": "N",
    "frage": "F",
    "antwort": "F",
    "satz": "M",
    "wort": "N",
    "sprache": "F",
    # Oktoberfest & Karaoke B2 nouns
    "flieger": "M",
    "lied": "N",
    "herz": "N",
    "wahnsinn": "M",
    "hölle": "F",
    "himmel": "M",
    "liebe": "F",
    "gefühl": "N",
    "sehnsucht": "F",
    "traum": "M",
    "luftballon": "M",
    "ballon": "M",
    "horizont": "M",
    "welt": "F",
    "leben": "N",
    "feuer": "N",
    "eis": "N",
    "sturm": "M",
    "wind": "M",
    "stern": "M",
}

# Capitalized German non-nouns (pronouns, sentence-initial words, greetings) to skip when scanning plain text
NON_NOUN_CAPITALIZED_STOPWORDS: set[str] = {
    "ich",
    "du",
    "er",
    "sie",
    "es",
    "wir",
    "ihr",
    "mein",
    "meine",
    "meinem",
    "meinen",
    "meiner",
    "dein",
    "deine",
    "sein",
    "seine",
    "ihre",
    "ihren",
    "ihrem",
    "unser",
    "unsere",
    "dieser",
    "diese",
    "dieses",
    "jeder",
    "jede",
    "jedes",
    "jeden",
    "welcher",
    "welche",
    "welches",
    "ein",
    "eine",
    "einen",
    "einem",
    "einer",
    "der",
    "die",
    "das",
    "den",
    "dem",
    "des",
    "und",
    "oder",
    "aber",
    "denn",
    "weil",
    "dass",
    "wenn",
    "als",
    "ob",
    "wie",
    "was",
    "wann",
    "wo",
    "warum",
    "wer",
    "grüezi",
    "hallo",
    "guten",
    "schönes",
    "schöner",
    "ja",
    "nein",
    "bitte",
    "danke",
    "heute",
    "gestern",
    "morgen",  # note: lowercase morgen is adverb; capitalized 'Morgen' after 'jeden/guten' is handled via context
    "hier",
    "dort",
    "oft",
    "immer",
    "nie",
    "sehr",
    "ganz",
    "auch",
    "noch",
    "schon",
    "kommen",
    "gehen",
    "machen",
    "haben",
    "sein",
    "können",
    "müssen",
    "wollen",
    "sollen",
    "mögen",
    "möchte",
    "möchten",
    "versuchen",
    "erzählen",
    "bauen",
    "üben",
    "fangen",
    "ausgezeichnet",
    "guter",
    "frau",
    "herr",
    "leonie",
    "blücher",
    "rijckard",
    "riccardo",
    "zürich",
}


class NounGenderAnnotation(BaseModel):
    """Structured gender resolution result for a German noun."""

    surface: str
    lemma: str
    gender: GenderCode
    article: ArticleCode
    color_hex: str
    color_name_it: str
    css_class: str
    resolution_tier: Literal[
        "inline_tag",
        "curriculum",
        "core_lexicon",
        "compound_tail",
        "suffix_rule",
    ]


class GenderResolver:
    """3-Tier Cross-Stack German Noun Gender Resolver."""

    FEMININE_SUFFIXES: tuple[str, ...] = (
        "ung",
        "heit",
        "keit",
        "schaft",
        "tion",
        "tät",
        "taet",
        "ik",
        "ie",
        "enz",
        "anz",
        "ur",
        "bäckerei",
        "erei",
        "in",
    )

    NEUTER_SUFFIXES: tuple[str, ...] = (
        "chen",
        "lein",
        "ment",
        "tum",
        "um",
        "ma",
    )

    MASCULINE_SUFFIXES: tuple[str, ...] = (
        "ling",
        "ismus",
        "ig",
        "ich",
        "or",
        "ant",
        "ent",
        "ist",
    )

    def __init__(self, curriculum_repo: Optional[CurriculumRepository] = None) -> None:
        self.curriculum_repo = curriculum_repo or CurriculumRepository()
        self._curriculum_nouns: dict[str, tuple[str, GenderCode]] = {}
        self._load_curricula()

    def _load_curricula(self) -> None:
        for curr_name in ("goethe_b1", "tandem_p3", "tandem_p1"):
            try:
                entries = self.curriculum_repo.load_curriculum(curr_name)
            except Exception:
                continue
            for entry in entries:
                if entry.pos == "noun" and entry.article in ARTICLE_TO_GENDER:
                    g = ARTICLE_TO_GENDER[entry.article]
                    self._curriculum_nouns[entry.lemma.lower()] = (entry.lemma, g)

    def _make_annotation(
        self,
        surface: str,
        lemma: str,
        gender: GenderCode,
        tier: Literal[
            "inline_tag",
            "curriculum",
            "core_lexicon",
            "compound_tail",
            "suffix_rule",
        ],
    ) -> NounGenderAnnotation:
        palette = GENDER_PALETTE[gender]
        return NounGenderAnnotation(
            surface=surface,
            lemma=lemma,
            gender=gender,
            article=palette["article"],  # type: ignore[arg-type]
            color_hex=palette["color_hex"],
            color_name_it=palette["color_name_it"],
            css_class=palette["css_class"],
            resolution_tier=tier,
        )

    def resolve_word(
        self,
        word: str,
        explicit_gender_or_article: Optional[str] = None,
    ) -> Optional[NounGenderAnnotation]:
        """Resolves a single German noun token across Tier 1, Tier 2 (Curriculum/Lexicon/Komposita), and Tier 3 (Suffixes)."""
        clean = word.strip(".,!?;:\"'()[]{}")
        if not clean:
            return None

        # Tier 1: Explicit gender/article tag
        if explicit_gender_or_article:
            key = explicit_gender_or_article.strip().lower()
            if key in ARTICLE_TO_GENDER:
                return self._make_annotation(
                    surface=clean,
                    lemma=clean,
                    gender=ARTICLE_TO_GENDER[key],
                    tier="inline_tag",
                )

        # Must start with uppercase to be a German noun candidate
        if not clean[0].isupper():
            return None

        low = clean.lower()

        # Candidate stems (handling basic genitive -s/-es or dative plural -n)
        stem_candidates = [low]
        if len(low) > 4 and low.endswith(("en", "er", "es")):
            stem_candidates.append(low[:-2])
        if len(low) > 4 and low.endswith(("e", "n", "s")):
            stem_candidates.append(low[:-1])

        # Tier 2a: Direct Curriculum Lookup
        for cand in stem_candidates:
            if cand in self._curriculum_nouns:
                lemma, g = self._curriculum_nouns[cand]
                return self._make_annotation(clean, lemma, g, "curriculum")

        # Tier 2b: Core German B1 Noun Lexicon
        for cand in stem_candidates:
            if cand in CORE_GERMAN_NOUN_GENDERS:
                return self._make_annotation(
                    clean, cand.capitalize(), CORE_GERMAN_NOUN_GENDERS[cand], "core_lexicon"
                )

        if low in NON_NOUN_CAPITALIZED_STOPWORDS:
            return None

        # Tier 2c: German Compound Noun (Komposita) Tail Lookup
        # The grammatical gender of a German compound noun is ALWAYS determined by its last noun element!
        all_known_tails: dict[str, GenderCode] = {
            **CORE_GERMAN_NOUN_GENDERS,
            **{k: v[1] for k, v in self._curriculum_nouns.items()},
        }
        best_tail = ""
        best_gender: Optional[GenderCode] = None
        for tail_lemma, tail_g in all_known_tails.items():
            if len(tail_lemma) >= 4 and len(low) > len(tail_lemma) + 2:
                if low.endswith(tail_lemma) and len(tail_lemma) > len(best_tail):
                    best_tail = tail_lemma
                    best_gender = tail_g
        if best_gender is not None:
            return self._make_annotation(clean, clean, best_gender, "compound_tail")

        # Tier 3: Deterministic German Morphological Suffix Heuristics
        # Note: Diminutives (-chen, -lein) and neuter suffixes take precedence over -in (e.g. 'das Fräulein')
        if len(low) >= 4:
            for suf in self.NEUTER_SUFFIXES:
                if low.endswith(suf) and len(low) > len(suf) + 1:
                    return self._make_annotation(clean, clean, "N", "suffix_rule")
            for suf in self.FEMININE_SUFFIXES:
                if low.endswith(suf) and len(low) > len(suf) + 1:
                    return self._make_annotation(clean, clean, "F", "suffix_rule")
            for suf in self.MASCULINE_SUFFIXES:
                if low.endswith(suf) and len(low) > len(suf) + 1:
                    return self._make_annotation(clean, clean, "M", "suffix_rule")

        return None


_INLINE_TAG_RE = re.compile(r"\[([A-Za-zÄÖÜäöüß\-]+)\|(F|M|N|die|der|das)\]", re.IGNORECASE)
_WORD_TOKEN_RE = re.compile(r"([A-Za-zÄÖÜäöüß\-]+)")


def annotate_german_text(
    text_de: str,
    resolver: Optional[GenderResolver] = None,
) -> dict[str, Any]:
    """Annotates German text across all 3 tiers, returning clean_text, annotated_html, and resolved nouns."""
    res = resolver or GenderResolver()
    nouns: list[dict[str, Any]] = []

    # First collect any Tier 1 inline tags `[Word|F/M/N/die/der/das]`
    inline_overrides: dict[str, str] = {}

    def _strip_inline(match: re.Match[str]) -> str:
        word, tag = match.group(1), match.group(2)
        inline_overrides[word] = tag
        return word

    clean_text = _INLINE_TAG_RE.sub(_strip_inline, text_de)

    # Now scan tokens in clean_text and wrap resolved German nouns in `.de-noun` spans
    parts: list[str] = []
    last_idx = 0
    for match in _WORD_TOKEN_RE.finditer(clean_text):
        start, end = match.span()
        if start > last_idx:
            parts.append(html.escape(clean_text[last_idx:start]))

        token = match.group(1)
        explicit_tag = inline_overrides.get(token)
        # Special case: 'Morgen' after 'jeden/guten/diesen/am' is a masculine noun ('der Morgen')
        if token == "Morgen" and not explicit_tag:
            prefix_context = clean_text[max(0, start - 12) : start].lower()
            if any(p in prefix_context for p in ("jeden", "guten", "diesen", "heute", "am")):
                explicit_tag = "M"

        annotation = res.resolve_word(token, explicit_gender_or_article=explicit_tag)
        if annotation is not None:
            nouns.append(annotation.model_dump())
            esc_surface = html.escape(annotation.surface)
            esc_lemma = html.escape(annotation.lemma)
            span = (
                f'<span class="de-noun {annotation.css_class}" '
                f'data-gender="{annotation.gender}" '
                f'data-article="{annotation.article}" '
                f'data-lemma="{esc_lemma}" '
                f'data-color="{annotation.color_hex}" '
                f'title="Doppio tap o Ctrl+G: {annotation.article} {esc_lemma} ({annotation.color_name_it})">'
                f"{esc_surface}</span>"
            )
            parts.append(span)
        else:
            parts.append(html.escape(token))

        last_idx = end

    if last_idx < len(clean_text):
        parts.append(html.escape(clean_text[last_idx:]))

    return {
        "clean_text": clean_text,
        "annotated_html": "".join(parts),
        "nouns": nouns,
        "palette": GENDER_PALETTE,
    }
