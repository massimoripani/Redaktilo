"""Testoj por la morfologia kaj silaba Esperanto-vortdividilo."""
import importlib.util
import pathlib
import unittest

PLUGIN = (
    pathlib.Path(__file__).resolve().parents[1]
    / "kromprogramoj"
    / "esperanto_hyphenation.py"
)
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
            "virinoj", "viro", "subŝtato", "ŝtato", "lingvon",
            "publikigita", "publika", "vortaro", "libro",
        })

    def check(self, text):
        return hyphenation.find_suspect_breaks(text, self.dictionary)

    def test_valid_syllabic_breaks_are_not_reported(self):
        self.assertEqual(self.check("espe-\nranto"), [])
        self.assertEqual(self.check("es-pe-\nranto"), [])
        self.assertEqual(self.check("pa-\ntro"), [])
        self.assertEqual(self.check("aŭ-\nto"), [])
        self.assertEqual(self.check("ŝi-\npo"), [])

    def test_invalid_syllabic_break_reports_location_and_suggestion(self):
        findings = self.check("Unua linio.\nesper-\nanto")
        self.assertEqual(len(findings), 1)
        line, message = findings[0]
        self.assertEqual(line, 2)
        self.assertIn("Originalo «esper-anto»", message)
        self.assertIn("detektita divido esper|anto", message)
        self.assertIn("es-pe-ran-to", message)

    def test_morphological_boundaries_are_accepted(self):
        self.assertFalse(
            self.check("vir-\ninoj"),
            "vir-inoj should be accepted as vir + in + oj",
        )
        self.assertFalse(
            self.check("sub-\nŝtato"),
            "sub-ŝtato should be accepted as prefix + root",
        )
        self.assertFalse(
            self.check("publik-\nigita"),
            "publik-igita should be accepted as root + suffix chain",
        )

    def test_lingvon_syllabic_boundary(self):
        self.assertIn(4, hyphenation.syllable_boundaries("lingvon"))
        self.assertEqual(self.check("ling-\nvon"), [])

    def test_incorrect_break_with_esperanto_diacritics(self):
        findings = self.check("ŝip-\no")
        self.assertEqual(len(findings), 1)
        self.assertIn("ŝi-po", findings[0][1])

    def test_prefix_suffix_and_unknown_words(self):
        self.assertEqual(self.check("re-\nverki"), [])
        self.assertEqual(self.check("libr-\nejo"), [])
        self.assertEqual(self.check("Xyz-\nabc"), [])
        self.assertEqual(self.check("vort-\naro"), [])

    def test_markup_is_ignored_and_line_numbers_preserved(self):
        self.assertEqual(self.check("<!-- ignoru --> <b>espe-</b>\nranto"), [])
        findings = self.check("<p>esper-\nanto</p>")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0][0], 1)

    def test_line_endings_and_punctuation(self):
        self.assertEqual(self.check("pa-\r\ntro"), [])
        findings = self.check("Teksto:\r\nesper-\r\nanto")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0][0], 2)

    def test_hyphen_without_following_word_is_ignored(self):
        self.assertEqual(self.check("esper-\n"), [])
        self.assertEqual(self.check("vort-aro"), [])

    def test_dictionary_unknown_words_are_ignored(self):
        self.assertEqual(self.check("nekonata-\nvorto"), [])


if __name__ == "__main__":
    unittest.main()
