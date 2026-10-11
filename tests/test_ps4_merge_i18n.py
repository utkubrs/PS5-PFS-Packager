import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from ps4_merge_i18n import TRANSLATIONS, merge_text

class MergeLanguagesTest(unittest.TestCase):
    def test_all_15_languages_have_all_labels(self):
        self.assertEqual(len(TRANSLATIONS), 15)
        reference=set(TRANSLATIONS["en"])
        for language,labels in TRANSLATIONS.items():
            self.assertEqual(set(labels),reference,language)
            for key,value in labels.items():
                self.assertTrue(value.strip(),(language,key))
    def test_language_fallback(self):
        self.assertEqual(merge_text("unavailable","submit"),TRANSLATIONS["en"]["submit"])

if __name__=="__main__":
    unittest.main()
