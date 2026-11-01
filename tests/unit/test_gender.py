"""Unit tests for Cross-Stack German Noun Gender X-Ray (Track 4: Rosa/Azzurrino/Grigio)."""

from hummerli.gender import (
    GENDER_PALETTE,
    GenderResolver,
    annotate_german_text,
)


def test_canonical_gender_palette_rosa_azzurrino_grigio():
    """Verifies that Feminine=Rosa (#f472b6), Masculine=Azzurrino (#38bdf8), Neuter=Grigio (#94a3b8)."""
    assert GENDER_PALETTE["F"]["article"] == "die"
    assert GENDER_PALETTE["F"]["color_hex"] == "#f472b6"
    assert GENDER_PALETTE["F"]["color_name_it"] == "rosa"
    assert GENDER_PALETTE["F"]["css_class"] == "gender-f"

    assert GENDER_PALETTE["M"]["article"] == "der"
    assert GENDER_PALETTE["M"]["color_hex"] == "#38bdf8"
    assert GENDER_PALETTE["M"]["color_name_it"] == "azzurrino"
    assert GENDER_PALETTE["M"]["css_class"] == "gender-m"

    assert GENDER_PALETTE["N"]["article"] == "das"
    assert GENDER_PALETTE["N"]["color_hex"] == "#94a3b8"
    assert GENDER_PALETTE["N"]["color_name_it"] == "grigio"
    assert GENDER_PALETTE["N"]["css_class"] == "gender-n"


def test_tier1_inline_llm_markup_resolution():
    """Tier 1: Resolves explicit inline tags like [Wiese|F], [Hund|M], [Geschäft|N]."""
    resolver = GenderResolver()
    text = "Ich komme jeden Morgen mit meinem [Hund|M] auf diese [Wiese|F], damit er sein [Geschäft|N] machen kann."
    annotated = annotate_german_text(text, resolver=resolver)

    assert "[Hund|M]" not in annotated["clean_text"]
    assert "mit meinem Hund auf diese Wiese" in annotated["clean_text"]

    by_surface = {n["surface"]: n for n in annotated["nouns"]}
    assert by_surface["Hund"]["gender"] == "M"
    assert by_surface["Hund"]["article"] == "der"
    assert by_surface["Hund"]["color_hex"] == "#38bdf8"

    assert by_surface["Wiese"]["gender"] == "F"
    assert by_surface["Wiese"]["article"] == "die"
    assert by_surface["Wiese"]["color_hex"] == "#f472b6"

    assert by_surface["Geschäft"]["gender"] == "N"
    assert by_surface["Geschäft"]["article"] == "das"
    assert by_surface["Geschäft"]["color_hex"] == "#94a3b8"


def test_tier2_curriculum_and_compound_noun_tail_resolution():
    """Tier 2: Resolves curriculum words and German compound nouns (Komposita) from their tail noun."""
    resolver = GenderResolver()

    # Direct curriculum nouns
    antrag = resolver.resolve_word("Antrag")
    assert antrag is not None
    assert antrag.gender == "M"
    assert antrag.article == "der"

    gemeinde = resolver.resolve_word("Gemeinde")
    assert gemeinde is not None
    assert gemeinde.gender == "F"
    assert gemeinde.article == "die"

    # Compound nouns (Komposita): gender comes from the last component
    parkbank = resolver.resolve_word("Parkbank")
    assert parkbank is not None
    assert parkbank.gender == "F"
    assert parkbank.article == "die"
    assert parkbank.resolution_tier in {"compound_tail", "core_lexicon"}

    hundewiese = resolver.resolve_word("Hundewiese")
    assert hundewiese is not None
    assert hundewiese.gender == "F"
    assert hundewiese.article == "die"

    sprachzertifikat = resolver.resolve_word("Sprachzertifikat")
    assert sprachzertifikat is not None
    assert sprachzertifikat.gender == "N"
    assert sprachzertifikat.article == "das"

    rathausplatz = resolver.resolve_word("Rathausplatz")
    assert rathausplatz is not None
    assert rathausplatz.gender == "M"
    assert rathausplatz.article == "der"


def test_tier3_morphological_suffix_heuristics():
    """Tier 3: Resolves German nouns via deterministic suffix rules (-ung/-heit/-keit -> F, -chen/-lein/-ment -> N, -ling/-ismus -> M)."""
    resolver = GenderResolver()

    # Feminine suffixes -> F (die, Rosa)
    for word in ("Entscheidung", "Freiheit", "Möglichkeit", "Freundschaft", "Information", "Universität"):
        res = resolver.resolve_word(word)
        assert res is not None, f"Failed to resolve {word}"
        assert res.gender == "F", f"Expected F for {word}, got {res.gender}"
        assert res.article == "die"
        assert res.color_hex == "#f472b6"

    # Neuter suffixes -> N (das, Grigio)
    for word in ("Brötchen", "Fräulein", "Dokument", "Eigentum", "Zentrum"):
        res = resolver.resolve_word(word)
        assert res is not None, f"Failed to resolve {word}"
        assert res.gender == "N", f"Expected N for {word}, got {res.gender}"
        assert res.article == "das"
        assert res.color_hex == "#94a3b8"

    # Masculine suffixes -> M (der, Azzurrino)
    for word in ("Frühling", "Tourismus", "Honig", "Teppich", "Motor"):
        res = resolver.resolve_word(word)
        assert res is not None, f"Failed to resolve {word}"
        assert res.gender == "M", f"Expected M for {word}, got {res.gender}"
        assert res.article == "der"
        assert res.color_hex == "#38bdf8"


def test_annotate_german_text_wraps_nouns_in_interactive_spans():
    """Verifies that annotate_german_text produces .de-noun spans with data-gender and data-article attributes."""
    res = annotate_german_text("Auf der Parkbank sitzt ein Rentner mit seinem Hund auf der Wiese.")
    html = res["annotated_html"]

    assert 'class="de-noun gender-f"' in html
    assert 'data-article="die"' in html
    assert 'class="de-noun gender-m"' in html
    assert 'data-article="der"' in html
    surfaces = {n["surface"] for n in res["nouns"]}
    assert {"Parkbank", "Rentner", "Hund", "Wiese"}.issubset(surfaces)
