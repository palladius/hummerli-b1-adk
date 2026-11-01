"""Oktoberfest 'Karaoke B2' Engine (Pre-Computed CEFR Color-Coding)
and Cross-App Duolingo-Style Silent/No-Mic 'Piano B' Modality (Track 5).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from hummerli.gender import annotate_german_text


CEFRLevel = Literal["A1", "A2", "B1", "B2"]
CEFRColorBand = Literal["green_a1_a2", "blue_b1", "red_b2"]
KaraokeMode = Literal["stop_and_fill", "flow_and_translate"]


CEFR_COLOR_BANDS: dict[CEFRColorBand, dict[str, str]] = {
    "green_a1_a2": {
        "band": "green_a1_a2",
        "levels": "A1-A2",
        "color_hex": "#22c55e",
        "label_it": "Verde (A1-A2 Base)",
    },
    "blue_b1": {
        "band": "blue_b1",
        "levels": "B1",
        "color_hex": "#3b82f6",
        "label_it": "Blu (Goethe B1)",
    },
    "red_b2": {
        "band": "red_b2",
        "levels": "B2+",
        "color_hex": "#ef4444",
        "label_it": "Rosso (B2 / Schlager Idiom)",
    },
}


class KaraokeToken(BaseModel):
    """Pre-computed lyric token with scientific Goethe CEFR level and color band."""

    surface: str
    lemma: str
    cefr: CEFRLevel
    cefr_color_band: CEFRColorBand


class KaraokeLine(BaseModel):
    """Synchronized lyric line with target B1/B2 challenge word and 4 Italian distractors."""

    line_index: int
    start_ms: int
    end_ms: int
    lyrics_de: str
    translation_it: str
    target_word: str
    target_lemma: str
    target_cefr: CEFRLevel
    target_translation_it: str
    distractors_it: list[str] = Field(default_factory=list)
    tokens: list[KaraokeToken] = Field(default_factory=list)


class KaraokeSong(BaseModel):
    """Pre-computed Oktoberfest / Schlager song for Karaoke B2."""

    song_id: str
    title: str
    artist: str
    bpm: int = 128
    vibe_it: str
    melody_notes_hz: list[float] = Field(default_factory=list)
    lines: list[KaraokeLine] = Field(default_factory=list)


class ModalityPreferences(BaseModel):
    """Cross-App Duolingo-Style 'Piano B' state ('🔇 Non posso ascoltare' / '🙊 Non posso parlare')."""

    profile_id: str = "riccardo"
    can_listen: bool = True
    can_speak: bool = True
    active_audio_channel: Literal["webaudio_and_tts", "silent_visual_beat"] = "webaudio_and_tts"
    active_input_channel: Literal["voice_or_text", "text_or_chips_only"] = "voice_or_text"
    banner_it: str = "🔊🎙️ Audio & Voce attivi (Modalità Immersione Completa)"


def verify_karaoke_cefr_integrity(songs: list[KaraokeSong]) -> dict[str, Any]:
    """Deterministically verifies that all pre-computed karaoke tokens adhere to the Goethe CEFR band rules."""
    errors: list[str] = []
    total_tokens = 0

    expected_band_for_cefr: dict[str, CEFRColorBand] = {
        "A1": "green_a1_a2",
        "A2": "green_a1_a2",
        "B1": "blue_b1",
        "B2": "red_b2",
    }

    for song in songs:
        if not song.lines:
            errors.append(f"Song '{song.song_id}' has no lines.")
        for line in song.lines:
            if len(line.distractors_it) != 4:
                errors.append(
                    f"Song '{song.song_id}' line {line.line_index} must have exactly 4 distractors_it (5 options total)."
                )
            if line.target_translation_it in line.distractors_it:
                errors.append(
                    f"Song '{song.song_id}' line {line.line_index} duplicates target_translation_it in distractors_it."
                )
            found_target = False
            for tok in line.tokens:
                total_tokens += 1
                expected_band = expected_band_for_cefr.get(tok.cefr)
                if tok.cefr_color_band != expected_band:
                    errors.append(
                        f"Token '{tok.surface}' in '{song.song_id}' has cefr={tok.cefr} "
                        f"but band={tok.cefr_color_band} (expected {expected_band})."
                    )
                if tok.surface.lower() == line.target_word.lower():
                    found_target = True
            if not found_target:
                errors.append(
                    f"Target word '{line.target_word}' not found in tokens of '{song.song_id}' line {line.line_index}."
                )

    return {
        "valid": len(errors) == 0,
        "total_songs": len(songs),
        "total_tokens": total_tokens,
        "errors": errors,
    }


class KaraokeEngine:
    """Manages Oktoberfest Karaoke B2 sessions and Cross-App Silent/No-Mic Modality ('Piano B')."""

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        catalog_path: Optional[Path] = None,
    ) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        self.data_dir = data_dir or (repo_root / "data")
        self.catalog_path = catalog_path or (repo_root / "data" / "karaoke" / "oktoberfest_b2.json")
        self.songs: list[KaraokeSong] = self._load_catalog()
        self._modality_by_profile: dict[str, ModalityPreferences] = {}

    def _load_catalog(self) -> list[KaraokeSong]:
        raw = json.loads(self.catalog_path.read_text(encoding="utf-8"))
        return [KaraokeSong.model_validate(item) for item in raw]

    def list_songs(self) -> list[KaraokeSong]:
        return list(self.songs)

    def get_song(self, song_id: str) -> KaraokeSong:
        for s in self.songs:
            if s.song_id == song_id:
                return s
        return self.songs[0]

    def get_modality_preferences(self, profile_id: str = "riccardo") -> ModalityPreferences:
        return self._modality_by_profile.get(
            profile_id, ModalityPreferences(profile_id=profile_id)
        )

    def set_modality_preferences(
        self,
        profile_id: str = "riccardo",
        can_listen: bool = True,
        can_speak: bool = True,
    ) -> ModalityPreferences:
        audio_ch: Literal["webaudio_and_tts", "silent_visual_beat"] = (
            "webaudio_and_tts" if can_listen else "silent_visual_beat"
        )
        input_ch: Literal["voice_or_text", "text_or_chips_only"] = (
            "voice_or_text" if can_speak else "text_or_chips_only"
        )

        if not can_listen and not can_speak:
            banner = "🔇🙊 Piano B Attivo (Zona Silenziosa): Beat visivo + Risposte scritte/tattili"
        elif not can_listen:
            banner = "🔇 Piano B Senza Audio: Sottotitoli sincronizzati & Beat visivo attivi"
        elif not can_speak:
            banner = "🙊 Piano B Senza Microfono: Ascolto attivo + Risposte scritte/scelta multipla"
        else:
            banner = "🔊🎙️ Audio & Voce attivi (Modalità Immersione Completa)"

        prefs = ModalityPreferences(
            profile_id=profile_id,
            can_listen=can_listen,
            can_speak=can_speak,
            active_audio_channel=audio_ch,
            active_input_channel=input_ch,
            banner_it=banner,
        )
        self._modality_by_profile[profile_id] = prefs
        return prefs

    def start_session(
        self,
        profile_id: str = "riccardo",
        song_id: str = "fliegerlied",
        mode: KaraokeMode = "stop_and_fill",
        can_listen: Optional[bool] = None,
        can_speak: Optional[bool] = None,
    ) -> dict[str, Any]:
        """Builds a complete karaoke stage payload with CEFR color spans, Mode 1/2 challenges, and Piano B fallbacks."""
        prefs = self.get_modality_preferences(profile_id)
        if can_listen is not None or can_speak is not None:
            prefs = self.set_modality_preferences(
                profile_id=profile_id,
                can_listen=prefs.can_listen if can_listen is None else can_listen,
                can_speak=prefs.can_speak if can_speak is None else can_speak,
            )

        song = self.get_song(song_id)
        rendered_lines: list[dict[str, Any]] = []

        for line in song.lines:
            masked_lyrics = line.lyrics_de.replace(line.target_word, "[_____]", 1)
            options_it = [line.target_translation_it, *line.distractors_it]

            # Build pre-colored CEFR HTML spans + integrate Track 4 Noun Gender X-Ray attributes
            token_spans: list[str] = []
            for tok in line.tokens:
                band_info = CEFR_COLOR_BANDS[tok.cefr_color_band]
                is_target = tok.surface.lower() == line.target_word.lower()
                ann = annotate_german_text(tok.surface)
                noun_attrs = ""
                noun_cls = ""
                if ann["nouns"]:
                    n0 = ann["nouns"][0]
                    noun_cls = f" de-noun {n0['css_class']}"
                    noun_attrs = (
                        f' data-gender="{n0["gender"]}" '
                        f'data-article="{n0["article"]}" '
                        f'data-lemma="{n0["lemma"]}"'
                    )
                display_surf = "[_____]" if (mode == "stop_and_fill" and is_target) else tok.surface
                token_spans.append(
                    f'<span class="karaoke-tok {tok.cefr_color_band}{noun_cls}'
                    f'{" karaoke-target-gap" if is_target else ""}" '
                    f'data-cefr="{tok.cefr}" data-color="{band_info["color_hex"]}"'
                    f"{noun_attrs}>{display_surf}</span>"
                )

            rendered_lines.append(
                {
                    "line_index": line.line_index,
                    "start_ms": line.start_ms,
                    "end_ms": line.end_ms,
                    "lyrics_de": line.lyrics_de,
                    "masked_lyrics_de": masked_lyrics,
                    "colored_html": " ".join(token_spans),
                    "translation_it": line.translation_it,
                    "target_word": line.target_word,
                    "target_lemma": line.target_lemma,
                    "target_cefr": line.target_cefr,
                    "target_translation_it": line.target_translation_it,
                    "MultipleChoiceOptions_it": options_it,
                    "tokens": [t.model_dump() for t in line.tokens],
                }
            )

        return {
            "song_id": song.song_id,
            "title": song.title,
            "artist": song.artist,
            "bpm": song.bpm,
            "vibe_it": song.vibe_it,
            "melody_notes_hz": song.melody_notes_hz,
            "mode": mode,
            "audio_strategy": prefs.active_audio_channel,
            "input_strategy": prefs.active_input_channel,
            "modality_banner_it": prefs.banner_it,
            "cefr_legend": CEFR_COLOR_BANDS,
            "lines": rendered_lines,
        }

    def submit_answer(
        self,
        profile_id: str,
        song_id: str,
        line_index: int,
        user_answer: str,
        mode: KaraokeMode = "stop_and_fill",
    ) -> dict[str, Any]:
        """Evaluates the learner's Karaoke B2 answer in either Mode 1 (gap fill/pronounce) or Mode 2 (5-choice translation)."""
        song = self.get_song(song_id)
        line = song.lines[min(max(0, line_index), len(song.lines) - 1)]
        ans_clean = user_answer.strip().lower()

        if mode == "stop_and_fill":
            expected = line.target_word.lower()
            correct = (
                ans_clean == expected
                or expected in ans_clean
                or line.target_lemma.lower() in ans_clean
            )
            feedback_it = (
                f"🍻 Prost! Hai completato '{line.target_word}' ({line.target_cefr}: '{line.target_translation_it}') a tempo di musica!"
                if correct
                else f"Quasi! La parola mancante nella canzone era '{line.target_word}' ({line.target_cefr}, significa '{line.target_translation_it}')."
            )
        else:
            expected_it = line.target_translation_it.lower()
            correct = ans_clean == expected_it or expected_it in ans_clean
            feedback_it = (
                f"🎯 Esatto! '{line.target_word}' ({line.target_cefr}) significa proprio '{line.target_translation_it}'!"
                if correct
                else f"Attenzione ai falsi amici! '{line.target_word}' ({line.target_cefr}) significa '{line.target_translation_it}'."
            )

        return {
            "profile_id": profile_id,
            "song_id": song.song_id,
            "line_index": line.line_index,
            "mode": mode,
            "user_answer": user_answer,
            "target_word": line.target_word,
            "target_cefr": line.target_cefr,
            "target_translation_it": line.target_translation_it,
            "correct": correct,
            "score_delta": 100 if correct else 0,
            "feedback_it": feedback_it,
            "full_line_de": line.lyrics_de,
        }
