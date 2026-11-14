# -*- coding: utf-8 -*-
"""Kontrolilo de vortdivido ĉe linifinoj en Esperanto.

La kontrolo uzas du apartajn analizojn:
1. morfologian: prefiksoj, sufiksoj kaj gramatikaj finaĵoj;
2. silaban: vokalaj nukleoj, diftongoj kaj konsonantaj grupoj.

La morfologia analizo havas prioritaton. Se la divido estas rekonita kiel
morfologia limo, ĝi estas akceptata eĉ se ĝi ne estas silaba limo.

La modulo estas intence konservativa: nekonataj vortoj kaj dubaj kazoj ne
estas aŭtomate markataj kiel eraroj. La plugin nur raportas kaj neniam
modifas la dokumenton.
"""
import os
import re

CATEGORY = "Kontroliloj"
NAME = "Kontroli esperantajn vortdividojn"

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DIC_PATH = os.path.join(_BASE, "vortaroj", "eo", "eo")

VOWELS = frozenset("aeiou")
DIPHTHONGS = frozenset(("aŭ", "eŭ", "aj", "ej", "oj", "uj"))

# Oftaj komencoj de silabo en Esperanto. La listo estas intence
# konservativa; ne ĉiu komenca konsonantaro estas uzata kiel silabkomenco.
ONSETS = frozenset((
    "bl", "br", "dr", "fl", "fr", "gl", "gr", "kl", "kr",
    "pl", "pr", "tr", "kv",
))

# Oftaj Esperantaj prefiksoj kaj sufiksoj. Ĉi tiuj listoj ne anstataŭas
# plenan morfologian analizilon; ili estas uzataj nur kune kun vortara kontrolo.
PREFIXES = frozenset((
    "bo", "dis", "ek", "eks", "ge", "mal", "mis", "pra",
    "re", "sen", "sub", "super", "trans",
))

SUFFIXES = frozenset((
    "aĉ", "ad", "aĵ", "an", "ar", "ebl", "ec", "eg", "ej",
    "em", "end", "er", "estr", "et", "id", "ig", "iĝ", "il", "it",
    "in", "ind", "ing", "ism", "ist", "obl", "on", "op", "uj",
    "ul", "um",
))

# Unicode-literoj inkluzivas ĉ ĝ ĥ ĵ ŝ ŭ.
_LETTER = r"[^\W\d_]"
_SPLIT_RE = re.compile(
    rf"(?P<left>{_LETTER}+(?:-{_LETTER}+)*)-[ \t]*\r?\n[ \t]*(?P<right>{_LETTER}+)",
    re.UNICODE,
)
_TAG_OR_COMMENT = re.compile(r"<!--.*?-->|<[^>]*>", re.DOTALL)
_ENTITY = re.compile(r"&(?:[A-Za-z][A-Za-z0-9]+|\#[0-9]+|\#x[0-9A-Fa-f]+);")
_ENDING_RE = re.compile(r"[aoeiu](?:j)?n?\Z", re.IGNORECASE)


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
    """Redonu (komenco, fino)-parojn por vokalaj nukleoj.

    La ses diftongoj estas traktataj kiel unu nukleo. La literoj j kaj ŭ
    ne estas mem vokaloj; ili apartenas al la diftongo antaŭa al ili.
    Aliaj apudaj vokaloj formas hiaton.
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

        if i < len(w) and (w[start:i + 1] in DIPHTHONGS):
            i += 1

        nuclei.append((start, i))

    return tuple(nuclei)


def syllable_boundaries(word):
    """Redonu 0-bazitajn silab-limojn laŭ la uzata ortografia modelo.

    Inter du nukleoj:
    - sen konsonanto: limo inter la nukleoj (hiato);
    - unu konsonanto: la konsonanto komencas la sekvan silabon;
    - pluraj konsonantoj: konservu konatan silabkomencan fingrupon;
      alie la lasta konsonanto komencas la sekvan silabon.

    La modelo estas praktika ortografia regulo, ne plena fonetika aŭ
    vortara priskribo de ĉiuj esceptoj.
    """
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
                (
                    n for n in range(len(consonants), 1, -1)
                    if consonants[-n:] in ONSETS
                ),
                1,
            )
            boundary = next_start - onset_len

        if 0 < boundary < len(w):
            boundaries.append(boundary)

    return tuple(boundaries)


def syllabify(word):
    """Redonu la vorton kun streketoj ĉe la kalkulitaj silab-limoj."""
    cuts = set(syllable_boundaries(word))
    return "".join(
        ("-" if i in cuts else "") + ch
        for i, ch in enumerate(word)
    )


def _dictionary_has(dictionary, word):
    """Kontrolu literuman rekonon per spylls/Hunspell aŭ test-stumpo."""
    if not word:
        return False

    candidates = {word, word.lower(), word.capitalize()}
    for candidate in candidates:
        try:
            if dictionary.lookup(candidate):
                return True
        except (KeyError, TypeError, AttributeError):
            continue
    return False


def _suffix_sequence_is_valid(text):
    """Ĉu *text* konsistas el unu aŭ pluraj sufiksoj kaj finaĵo?

    Ekzemploj:
    - in + oj
    - ig + it + a
    - ej + o

    La funkcio kontrolas la formon de la sufiksa ĉeno, ne ĝian semantikan
    taŭgecon; la vortara kontrolo de la radiko estas farata aparte.
    """
    tail = text.lower()

    for ending_start in range(len(tail)):
        ending = tail[ending_start:]
        suffix_part = tail[:ending_start]

        if not suffix_part or not _ENDING_RE.fullmatch(ending):
            continue

        # Dinamika segmentado de la sufiksa parto.
        reachable = {0}
        for position in range(len(suffix_part) + 1):
            if position not in reachable:
                continue
            for suffix in SUFFIXES:
                if suffix_part.startswith(suffix, position):
                    reachable.add(position + len(suffix))

        if len(suffix_part) in reachable:
            return True

    return False


def _known_stem(dictionary, stem):
    """Kontrolu radikon mem aŭ ĝian oftan vortklasan finaĵon."""
    if _dictionary_has(dictionary, stem):
        return True

    return any(
        _dictionary_has(dictionary, stem + ending)
        for ending in ("a", "o", "e", "i")
    )


def is_morphological_boundary(word, cut, dictionary):
    """Ĉu *cut* estas kredinda morfologia limo en *word*?

    Akceptas:
    - konatan prefikson antaŭ vortare rekonita resto;
    - konatan radikon antaŭ rekonita sufiksa ĉeno.

    Ĉi tio estas konservativa heuristiko, ne kompleta morfologia analizilo.
    """
    w = word.lower()
    if cut <= 0 or cut >= len(w):
        return False

    left, right = w[:cut], w[cut:]

    # Prefikso + memstare rekonita vorto/radiko.
    if left in PREFIXES and _dictionary_has(dictionary, right):
        return True

    # Radiko + sufikso(j) + gramatika finaĵo.
    if _suffix_sequence_is_valid(right) and _known_stem(dictionary, left):
        return True

    return False


def _line_number(text, position):
    return text.count("\n", 0, position) + 1


def find_suspect_breaks(text, dictionary):
    """Listo de (unua_lin, mesaĝo) por suspektindaj vortdividoj.

    La teksto antaŭ la fina linifina streketo povas enhavi jam ekzistantajn
    silabajn streketojn, ekzemple ``es-pe-``. Ili estas forigitaj antaŭ la
    kontrolo de la kompleta vorto. La pozicio de la linifina divido estas
    kalkulita laŭ la nombro de literoj, ne laŭ la nombro de signoj.
    """
    visible = _mask_markup(text)
    findings = []

    for match in _SPLIT_RE.finditer(visible):
        left_raw = match.group("left")
        right = match.group("right")

        # Forigu internajn silabajn streketojn el la maldekstra fragmento.
        left = left_raw.replace("-", "")
        word = left + right
        cut = len(left)

        # Ne analizu nekonatajn vortojn aŭ fremdajn nomojn.
        if not _dictionary_has(dictionary, word):
            continue

        # Morfologia limo havas prioritaton super silaba limo.
        if is_morphological_boundary(word, cut, dictionary):
            continue

        # Ordinara silaba limo estas akceptebla.
        if cut in syllable_boundaries(word):
            continue

        first_line = _line_number(visible, match.start())
        second_line = first_line + 1
        suggested = syllabify(word)

        message = (
            f"Originalo «{left_raw}-{right}»; "
            f"linioj {first_line}–{second_line}; "
            f"detektita divido {left}|{right}; "
            f"propono {suggested}; "
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
        ctx.warn(
            f"Ne eblas ŝargi la Esperanto-vortaron ({_DIC_PATH}.dic):\n{error}"
        )
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

    ctx.report(
        f"Esperantaj vortdividoj: {len(findings)} suspektinda(j)",
        findings,
    )
