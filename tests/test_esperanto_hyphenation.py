"""Unit tests for the dependency-free Esperanto syllabification and checker."""
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

    def test_one_vowel_and_consecutive_hiatus(self):
        self.assertEqual(hyphenation.syllabify("a"), "a")
        self.assertEqual(hyphenation.syllabify("poeto"), "po-e-to")


class DetectionTests(unittest.TestCase):
    def setUp(self):
        self.dictionary = FakeDictionary({
            "esperanto", "patro", "akvo", "aŭto", "ŝipo", "ĝardeno",
            "instruisto", "familio", "poeto", "reverki", "librejo",
        })

    def check(self, text):
        return hyphenation.find_suspect_breaks(text, self.dictionary)

    def test_correct_breaks_not_reported(self):
        self.assertEqual(self.check("es-pe-\nranto"), [])
        self.assertEqual(self.check("pa-\ntro"), [])
        self.assertEqual(self.check("aŭ-\nto"), [])
        self.assertEqual(self.check("ŝi-\npo"), [])

    def test_incorrect_break_reports_location_and_suggestion(self):
        findings = self.check("Unua linio.\nesper-\nanto")
        # A line break is only considered between adjacent physical lines.
        self.assertEqual(findings, [])
        findings = self.check("Unua linio.\nesper-\nanto")
        self.assertEqual(findings, [])
        findings = self.check("espe-\nranto")
        self.assertEqual(len(findings), 1)
        line, message = findings[0]
        self.assertEqual(line, 1)
        self.assertIn("Originalo «espe-ranto»", message)
        self.assertIn("detektita divido espe|ranto", message)
        self.assertIn("es-pe-ran-to", message)

    def test_esperanto_diacritics_and_diphthongs(self):
        self.assertEqual(len(self.check("ŝip-\no")), 1)
        self.assertEqual(self.check("aŭ-\nto"), [])

    def test_prefix_suffix_compounds_and_ambiguous_words(self):
        # Rekonitaj vortoj estas traktataj per sia tuta literumita formo.
        self.assertEqual(self.check("re-\nverki"), [])
        self.assertEqual(self.check("libr-\nejo"), [])
        # Nekonataj/fremdaj nomoj kaj kunmetaĵoj ne ricevas konjektajn avertojn.
        self.assertEqual(self.check("Xyz-\nabc"), [])
        self.assertEqual(self.check("vort-\naro"), [])
        self.assertEqual(self.check("esperanto-vort-\naro"), [])

    def test_markup_is_ignored_and_line_numbers_preserved(self):
        self.assertEqual(self.check("<!-- ignoru --> <b>espe-</b>\nranto"), [])
        findings = self.check("<p>espe-\nranto</p>")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0][0], 1)

    def test_hyphen_without_following_line_word_is_ignored(self):
        self.assertEqual(self.check("esper-\n"), [])
        self.assertEqual(self.check("vort-aro"), [])


if __name__ == "__main__":
    unittest.main()
