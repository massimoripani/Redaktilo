# -*- coding: utf-8 -*-
"""Kontrolilo de vortdivido ĉe linifinoj en Esperanto.

La kontrolo unue rekonas morfologiajn limojn (prefiksoj, radikoj,
sufiksoj, finaĵoj kaj kunmetaĵoj), kaj nur poste uzas silabigon. La
analizo estas intence konservativa: ĝi bezonas vortaran subtenon kaj
preterlasas nekonatajn vortojn. La plugin raportas sed neniam ŝanĝas la
originalan dokumenton.
"""
import os
import re

CATEGORY = "Kontroliloj"
NAME = "Kontroli esperantajn vortdividojn"

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DIC_PATH = os.path.join(_BASE, "vortaroj", "eo", "eo")

VOWELS = frozenset("aeiou")
DIPHTHONGS = frozenset(("aŭ", "eŭ", "aj", "ej", "oj", "uj"))
ONSETS = frozenset((
    "bl", "br", "dr", "fl", "fr", "gl", "gr", "kl", "kr",
    "pl", "pr", "tr", "kv", "gv", "sc", "sk", "sl", "sm",
    "sn", "sp", "st", "sv", "ŝv", "vr",
))

PREFIXES = frozenset((
    "bo", "dis", "ek", "eks", "ge", "mal", "mis", "pra",
    "re", "sen", "sub", "super", "trans",
))
SUFFIXES = frozenset((
    "aĉ", "ad", "aĵ", "an", "ar", "ebl", "ec", "eg", "ej",
    "em", "end", "er", "estr", "et", "id", "ig", "iĝ", "il",
    "in", "ind", "ing", "ism", "ist", "obl", "on", "op", "uj",
    "ul", "um",
))
# Participaj formoj estas derivaj morfemoj; ili ne estas gramatikaj finaĵoj.
PARTICIPLES = frozenset(("ant", "int", "ont", "at", "it", "ot"))
# La gramatikaj finaĵoj estas aparte traktataj, post ĉiuj derivaj morfemoj.
ENDINGS = (
    "ojn", "ajn", "oj", "on", "aj", "an",
    "as", "is", "os", "us", "o", "a", "e", "u", "i",
)

_LETTER = r"[^\W\d_]"
_SPLIT_RE = re.compile(
    rf"(?P<left>{_LETTER}+(?:-{_LETTER}+)*)-[ \t]*\r?\n[ \t]*(?P<right>{_LETTER}+)" ,
    re.UNICODE,
)
_TAG_OR_COMMENT = re.compile(r"<!--.*?-->|<[^>]*>", re.DOTALL)
_ENTITY = re.compile(r"&(?:[A-Za-z][A-Za-z0-9]+|\#[0-9]+|\#x[0-9A-Fa-f]+);")


def _blank_match(match):
    """Anstataŭigu markigon per spacoj, konservante linifinojn."""
    return "".join("\n" if ch == "\n" else " " for ch in match.group(0))


def _mask_markup(text):
    """Blankigu HTML-markigon kaj entojn konservante signolokojn."""
    text = _TAG_OR_COMMENT.sub(_blank_match, text)
    return _ENTITY.sub(_blank_match, text)


def _is_vowel(ch):
    return ch.lower() in VOWELS


def _syllable_nuclei(word):
    """Redonu la komencajn kaj finajn poziciojn de vokalaj nukleoj."""
    w = word.lower()
    nuclei = []
    i = 0
    while i < len(w):
        if not _is_vowel(w[i]):
            i += 1
            continue
        start = i
        i += 1
        if i < len(w) and w[start:i + 1] in DIPHTHONGS:
            i += 1
        nuclei.append((start, i))
    return tuple(nuclei)


def syllable_boundaries(word):
    """Redonu 0-bazitajn silab-limojn laŭ praktika ortografia modelo."""
    w = word.lower()
    nuclei = _syllable_nuclei(w)
    boundaries = []
    for (_, prev_end), (next_start, _) in zip(nuclei, nuclei[1:]):
        consonants = w[prev_end:next_start]
        if not consonants:
            boundary = next_start
        elif len(consonants) == 1:
            boundary = prev_end
        else:
            onset_len = next(
                (n for n in range(len(consonants), 1, -1)
                 if consonants[-n:] in ONSETS),
                1,
            )
            boundary = next_start - onset_len
        if 0 < boundary < len(w):
            boundaries.append(boundary)
    return tuple(boundaries)


def syllabify(word):
    """Redonu la vorton kun streketoj ĉe la kalkulitaj silab-limoj."""
    cuts = set(syllable_boundaries(word))
    return "".join(("-" if i in cuts else "") + ch for i, ch in enumerate(word))


def _dictionary_has(dictionary, word):
    """Kontrolu literuman rekonon per spylls/Hunspell aŭ test-stumpo."""
    if not word:
        return False
    for candidate in {word, word.lower(), word.capitalize()}:
        try:
            if dictionary.lookup(candidate):
                return True
        except (KeyError, TypeError, AttributeError):
            continue
    return False


def _known_stem(dictionary, stem):
    """Akceptu radikon nur kun rekta aŭ vortklasa vortara subteno."""
    if not stem:
        return False
    return _dictionary_has(dictionary, stem) or any(
        _dictionary_has(dictionary, stem + ending)
        for ending in ("a", "o", "e", "i")
    )


def _tail_is_suffixes_and_ending(text):
    """Validigu derivajn sufiksojn/participojn sekvatajn de finaĵo.

    La finaĵo estas deviga. Tio malhelpas trakti arbitran literĉenon kiel
    sufikson; la radika parto estas kontrolata aparte per la vortaro.
    """
    tail = text.lower()
    for ending in ENDINGS:
        if not tail.endswith(ending):
            continue
        derivation = tail[:-len(ending)]
        if not derivation:
            continue
        reachable = {0}
        for position in range(len(derivation) + 1):
            if position not in reachable:
                continue
            for morpheme in SUFFIXES | PARTICIPLES:
                if derivation.startswith(morpheme, position):
                    reachable.add(position + len(morpheme))
        if len(derivation) in reachable:
            return True
    return False


def _is_lexical_form(dictionary, form, depth=0):
    """Ĉu formo havas vortare subtenatan radikon kaj laŭleĝan morfologion?"""
    form = form.lower()
    if not form or depth > 4:
        return False
    if _dictionary_has(dictionary, form) or _known_stem(dictionary, form):
        return True

    # Prefiksoj validas nur kiam la posta parto mem estas rekonata.
    for prefix in PREFIXES:
        if form.startswith(prefix) and len(form) > len(prefix):
            if _is_lexical_form(dictionary, form[len(prefix):], depth + 1):
                return True

    # Radiko + derivaj sufiksoj/participa formo + gramatika finaĵo.
    for cut in range(1, len(form)):
        if _tail_is_suffixes_and_ending(form[cut:]) and _known_stem(dictionary, form[:cut]):
            return True

    # Kunmetaĵoj: ambaŭ flankoj devas havi sendependan vortaran subtenon.
    for cut in range(2, len(form) - 1):
        if _known_stem(dictionary, form[:cut]) and _is_lexical_form(
            dictionary, form[cut:], depth + 1
        ):
            return True
    return False


def is_morphological_boundary(word, cut, dictionary):
    """Ĉu *cut* estas vortare subtenata morfologia limo en *word*?

    La kontrolo respektas prefiksojn, radikojn, derivajn sufiksojn,
    participojn, gramatikajn finaĵojn kaj kunmetaĵojn. Ĝi ne uzas nur
    literajn ŝablonojn: la koncernaj radikoj aŭ tutaj vortformoj devas esti
    rekonataj de la Hunspell-vortaro.
    """
    w = word.lower()
    if cut <= 0 or cut >= len(w):
        return False
    left, right = w[:cut], w[cut:]

    # Prefikso + konata radiko aŭ memstare validigita derivita vorto.
    if left in PREFIXES and _is_lexical_form(dictionary, right):
        return True

    # Radiko + sufiksoj/participo + aparta gramatika finaĵo.
    if _tail_is_suffixes_and_ending(right) and _known_stem(dictionary, left):
        return True

    # Radiko (aŭ komponanto) + alia radiko kun ebla finaĵo. Ĉi tiu
    # kontrolo ankaŭ kovras limojn en kunmetaĵoj kiel ĉef-strato kaj
    # naskiĝ-urbo, sen postuli silaban koincidon.
    if _known_stem(dictionary, left) and _is_lexical_form(dictionary, right):
        return True

    return False


def _line_number(text, position):
    return text.count("\n", 0, position) + 1


def find_suspect_breaks(text, dictionary):
    """Listo de (unua_lin, mesaĝo) por suspektindaj vortdividoj.

    Nekonataj kompletaj vortoj kaj streketaj kunmetaĵoj preterlasiĝas.
    Morfologia limo ĉiam estas akceptata antaŭ ol la silaba modelo aplikiĝas.
    """
    visible = _mask_markup(text)
    findings = []
    for match in _SPLIT_RE.finditer(visible):
        left_raw, right = match.group("left"), match.group("right")
        # Ne rekaptu la finan elementon de kunmetaĵo kun ordinara streketo.
        if match.start("left") and visible[match.start("left") - 1] == "-":
            continue
        left = left_raw.replace("-", "")
        word = left + right
        cut = len(left)

        # La tuta formo devas esti konata; nekonataj vortoj restas nedeciditaj.
        if not _dictionary_has(dictionary, word):
            continue
        if is_morphological_boundary(word, cut, dictionary):
            continue
        if cut in syllable_boundaries(word):
            continue

        first_line = _line_number(visible, match.start())
        second_line = first_line + 1
        message = (
            f"Originalo «{left_raw}-{right}»; "
            f"linioj {first_line}–{second_line}; "
            f"detektita divido {left}|{right}; "
            f"propono {syllabify(word)}; "
            "la linifina divido ne estas rekonita kiel morfologia "
            "aŭ silaba limo."
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
