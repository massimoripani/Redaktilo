"""Testoj por Esperanto-silabigo kaj vortara morfologia analizo."""
import importlib.util
import pathlib
import unittest

PLUGIN = pathlib.Path(__file__).resolve().parents[1] / "kromprogramoj" / "esperanto_hyphenation.py"
spec = importlib.util.spec_from_file_location("esperanto_hyphenation", PLUGIN)
hyphenation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hyphenation)


class FakeDictionary:
    def __init__(self, words):
        self.words = {word.lower() for word in words}

    def lookup(self, word):
        return word.lower() in self.words


class SyllabificationTests(unittest.TestCase):
    def test_basic_vowel_nuclei_and_clusters(self):
        self.assertEqual(hyphenation.syllabify("esperanto"), "es-pe-ran-to")
        self.assertEqual(hyphenation.syllabify("patro"), "pa-tro")
        self.assertEqual(hyphenation.syllabify("akvo"), "a-kvo")
        self.assertEqual(hyphenation.syllabify("instruisto"), "ins-tru-is-to")

    def test_esperanto_letters_and_diphthongs(self):
        self.assertEqual(hyphenation.syllabify("aŭto"), "aŭ-to")
        self.assertEqual(hyphenation.syllabify("ŝipo"), "ŝi-po")
        self.assertEqual(hyphenation.syllabify("ĝardeno"), "ĝar-de-no")
        self.assertEqual(hyphenation.syllabify("eŭropo"), "eŭ-ro-po")
        self.assertEqual(hyphenation.syllabify("familio"), "fa-mi-li-o")

    def test_hiatus_and_single_vowel(self):
        self.assertEqual(hyphenation.syllabify("a"), "a")
        self.assertEqual(hyphenation.syllabify("poeto"), "po-e-to")

    def test_diphthong_letters_are_part_of_the_nucleus(self):
        self.assertEqual(hyphenation._syllable_nuclei("aŭto"), ((0, 2), (3, 4)))
        self.assertEqual(hyphenation._syllable_nuclei("ajna"), ((0, 2), (3, 4)))


class DetectionTests(unittest.TestCase):
    def setUp(self):
        self.dictionary = FakeDictionary({
            "esperanto", "patro", "akvo", "aŭto", "ŝipo", "ĝardeno",
            "instruisto", "familio", "poeto", "reverki", "librejo",
            "virinoj", "viro", "vir", "subŝtato", "ŝtato", "lingvon",
            "publikigita", "publika", "publik", "vortaro", "libro",
            "libera", "libero", "lumo", "liberejo", "kulp", "kulpo",
            "kulpigis", "aplik", "apliko", "aplikata", "frot", "froto",
            "frotataj", "mort", "morto", "mortintoj", "griz", "griza",
            "griziĝo", "griziĝantan", "ĉefa", "ĉef", "strato", "ĉefstrato",
            "naskiĝo", "naskiĝurbo", "urbo", "alta", "alto", "rang", "ranga",
            "altrangaj", "organizajn", "organiza", "organiz", "malnovajn",
            "malnova", "malnov", "internaciajn", "internacia", "internaci",
            "pikiletojn", "pikileto", "helbluajn", "helblua", "orajn", "ora",
            "mallumo", "mal", "xyzabc",
        })

    def check(self, text):
        return hyphenation.find_suspect_breaks(text, self.dictionary)

    def test_valid_syllabic_breaks_are_not_reported(self):
        self.assertEqual(self.check("es-pe-\nranto"), [])
        self.assertEqual(self.check("pa-\ntro"), [])
        self.assertEqual(self.check("aŭ-\nto"), [])
        self.assertEqual(self.check("ŝi-\npo"), [])

    def test_non_syllabic_invalid_break_is_reported(self):
        findings = self.check("Unua linio.\nesper-\nanto")
        self.assertEqual(len(findings), 1)
        line, message = findings[0]
        self.assertEqual(line, 2)
        self.assertIn("Originalo «esper-anto»", message)
        self.assertIn("detektita divido esper|anto", message)
        self.assertIn("es-pe-ran-to", message)

    def test_morphological_roots_suffixes_endings_and_participles(self):
        examples = (
            "vir-\ninoj", "publik-\nigita", "kulp-\nigis",
            "aplik-\nata", "frot-\nataj", "mort-\nintoj",
            "griziĝ-\nantan",
        )
        for text in examples:
            with self.subTest(text=text):
                self.assertEqual(self.check(text), [])

    def test_compound_root_boundaries_need_not_be_syllabic(self):
        for text in ("ĉef-\nstrato", "naskiĝ-\nurbo", "alt-\nrangaj"):
            with self.subTest(text=text):
                self.assertEqual(self.check(text), [])

    def test_prefixes_include_doubled_consonants(self):
        self.assertEqual(self.check("mal-\nliberejo"), [])
        self.assertEqual(self.check("mal-\nlumo"), [])
        self.assertEqual(self.check("sub-\nŝtato"), [])

    def test_grammatical_endings_are_kept_with_their_word(self):
        for text in (
            "organiz-\najn", "malnov-\najn", "internaci-\najn",
            "pikileto-\njn", "helblu-\najn", "or-\najn",
        ):
            with self.subTest(text=text):
                self.assertEqual(self.check(text), [])

    def test_existing_syllabic_hyphens_are_removed_before_analysis(self):
        self.assertEqual(self.check("es-pe-\nranto"), [])
        self.assertEqual(self.check("esperanto-vort-\naro"), [])

    def test_unknown_words_and_ambiguous_forms_are_ignored(self):
        self.assertEqual(self.check("Xyz-\nabc"), [])
        self.assertEqual(self.check("nekonata-\nvorto"), [])

    def test_esperanto_special_letters_and_incorrect_break(self):
        findings = self.check("ŝip-\no")
        self.assertEqual(len(findings), 1)
        self.assertIn("ŝi-po", findings[0][1])

    def test_lingvon_syllabic_boundary(self):
        self.assertIn(4, hyphenation.syllable_boundaries("lingvon"))
        self.assertEqual(self.check("ling-\nvon"), [])

    def test_markup_is_ignored_and_line_numbers_preserved(self):
        self.assertEqual(self.check("<!-- ignoru --> <b>espe-</b>\nranto"), [])
        findings = self.check("<p>esper-\nanto</p>")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0][0], 1)

    def test_lf_and_windows_line_endings(self):
        self.assertEqual(self.check("pa-\r\ntro"), [])
        findings = self.check("Teksto:\r\nesper-\r\nanto")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0][0], 2)

    def test_non_line_end_hyphens_and_missing_right_fragment_are_ignored(self):
        self.assertEqual(self.check("vort-aro"), [])
        self.assertEqual(self.check("esper-\n"), [])


if __name__ == "__main__":
    unittest.main()
