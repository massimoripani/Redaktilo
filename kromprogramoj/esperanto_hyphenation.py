# -*- coding: utf-8 -*-
"""Kontrolilo de vortdivido ĉe linifinoj en Esperanto.

La modulo silabigas laŭ literumaj fonemaj bazoj: a/e/i/o/u estas vokaloj,
la ses Esperantaj diakritaj literoj estas unuopaj konsonantoj/vokaloj, kaj
aŭ/eŭ/aj/ej/oj/uj estas diftongoj. Inter nukleoj la plej longa permesita
silabkomenca konsonantaro restas kune; alie la lasta konsonanto komencas
la sekvan silabon. La regulo estas konscia ortografia modelo, ne vortara
sistemo de tipografiaj esceptoj.

La plugin nur raportas. Ĝi bezonas la jam uzatan dependaĵon spylls kaj la
Hunspell-vortaron de la projekto por eviti konjektadon pri nekonataj vortoj.
"""
import os
import re

CATEGORY = "Kontroliloj"
NAME = "Kontroli esperantajn vortdividojn"

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DIC_PATH = os.path.join(_BASE, "vortaroj", "eo", "eo")

VOWELS = frozenset("aeiou")
DIPHTHONGS = frozenset(("aŭ", "eŭ", "aj", "ej", "oj", "uj"))
# Oftaj ortografie permesataj komencoj. La listo estas intence konservativa:
# ĉiu alia konsonantaro dividiĝas antaŭ sia lasta konsonanto.
ONSETS = frozenset((
    "bl", "br", " ĝis", "dr", "fl", "fr", "gl", "gr", "kl", "kr",
    "pl", "pr", "tr", "vr", "kv", "gv", "sc", "sk", "sl", "sm",
    "sn", "sp", "st", "sv", "ŝv",
)) - {" ĝis"}  # evitu hazardan whitespace en literaj konstantoj

# Unicode-literoj inkluzivas ĉ ĝ ĥ ĵ ŝ ŭ sen specialaj ASCII-konvertoj.
_LETTER = r"[^\W\d_]"
_SPLIT_RE = re.compile(
    rf"(?P<left>{_LETTER}{{2,}})-[ \t]*\r?\n[ \t]*(?P<right>{_LETTER}{{2,}})",
    re.UNICODE,
)
_TAG_OR_COMMENT = re.compile(r"<!--.*?-->|<[^>]*>", re.DOTALL)
_ENTITY = re.compile(r"&(?:[A-Za-z][A-Za-z0-9]+|\#[0-9]+|\#x[0-9A-Fa-f]+);")


def _mask_markup(text):
    """Blankigu markigon konservante signolokojn kaj linionumerojn."""
    def blank(match):
        return "".join("\n" if ch == "\n" else " " for ch in match.group(0))

    text = _TAG_OR_COMMENT.sub(blank, text)
    return _ENTITY.sub(blank, text)


def _is_vowel(ch):
    return ch.lower() in VOWELS


def syllable_boundaries(word):
    """Redonu 0-bazitajn poziciojn kie la silaboj de *word* estu dividitaj.

    Vokalaj sinsekvoj estas unu nukleo nur kiam ili estas unu el la ses
    diftongoj. Hiatoj (ekz. a-e) do donas apartajn nukleojn. Inter du nukleoj,
    oni elektas la plej longan konsonantan sufikson en ONSETS; se neniu
    permesita komenco ekzistas, oni dividas antaŭ la lasta konsonanto.
    Vorto sen almenaŭ du vokalaj nukleoj ne havas internan silablimon.
    """
    w = word.lower()
    nuclei = []
    i = 0
    while i < len(w):
        if not _is_vowel(w[i]):
            i += 1
            continue
        start = i
        i += 1
        while i < len(w) and _is_vowel(w[i]):
            pair = w[i - 1:i + 1]
            if pair in DIPHTHONGS:
                i += 1
            else:
                break
        nuclei.append((start, i))

    boundaries = []
    for (prev_start, prev_end), (next_start, next_end) in zip(nuclei, nuclei[1:]):
        consonants = w[prev_end:next_start]
        if not consonants:
            boundary = next_start
        else:
            onset_len = next((n for n in range(len(consonants), 0, -1)
                              if consonants[-n:] in ONSETS), 1)
            boundary = next_start - onset_len
        if 0 < boundary < len(w):
            boundaries.append(boundary)
    return tuple(boundaries)


def syllabify(word):
    """Redonu *word* kun punktoj ĉe la kalkulitaj silabaj limoj."""
    cuts = set(syllable_boundaries(word))
    return "".join(("-" if i in cuts else "") + ch for i, ch in enumerate(word))


def _dictionary_has(dictionary, word):
    """Kontrolu literuman rekonon per spylls/Hunspell Dictionary."""
    return any(dictionary.lookup(candidate) for candidate in {word, word.lower(), word.capitalize()})


def find_suspect_breaks(text, dictionary):
    """Listo de (unua_lin, mesaĝo) por vortdividoj ne kongruaj kun silabigo.

    La vortara kontrolo estas intenca sekurigilo kontraŭ nomoj, fremdaj vortoj,
    kaj necerte rekonstrueblaj kunmetaĵoj. Ne rekonitaj vortoj estas preterlasitaj.
    """
    visible = _mask_markup(text)
    findings = []
    for match in _SPLIT_RE.finditer(visible):
        left, right = match.group("left"), match.group("right")
        # Ne rekaptu nur la finan elementon de kunmetaĵo kun ordinara streketo.
        if match.start("left") and visible[match.start("left") - 1] == "-":
            continue
        word = left + right
        if not _dictionary_has(dictionary, word):
            continue
        cut = len(left)
        if cut in syllable_boundaries(word):
            continue
        first_line = visible.count("\n", 0, match.start()) + 1
        second_line = first_line + 1
        suggested = syllabify(word)
        message = (
            f"Originalo «{left}-{right}»; linioj {first_line}–{second_line}; "
            f"detektita divido {left}|{right}; propono {suggested}; "
            "la linifina divido ne kongruas kun la kalkulitaj silabaj limoj."
        )
        findings.append((first_line, message))
    return findings


def _load_dictionary(ctx):
    try:
        from spylls.hunspell import Dictionary
        return Dictionary.from_files(_DIC_PATH)
    except ImportError:
        ctx.warn("Mankas la pakaĵo «spylls». Instalu ĝin per: pip install spylls")
    except Exception as error:
        ctx.warn(f"Ne eblas ŝargi la Esperanto-vortaron ({_DIC_PATH}.dic):\n{error}")
    return None


def run(ctx):
    """Redaktilo-plugin: nur kontrolas kaj raportas, neniam ŝanĝas la tekston."""
    dictionary = _load_dictionary(ctx)
    if dictionary is None:
        return
    findings = find_suspect_breaks(ctx.text, dictionary)
    if not findings:
        ctx.info("Neniu suspektinda Esperanto-vortdivido trovita.")
        return
    ctx.report(f"Esperantaj vortdividoj: {len(findings)} suspektinda(j)", findings)
