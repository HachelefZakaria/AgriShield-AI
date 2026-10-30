"""Languages and the t(ar, fr, en) helper: every UI string carries its three translations inline."""
LANGS = {"ar": "العربية", "fr": "Français", "en": "English"}


def make_t(lang):
    i = {"ar": 0, "fr": 1, "en": 2}[lang]
    t = lambda ar, fr=None, en=None: (ar, fr or ar, en or ar)[i] if fr or en else ar
    t.i, t.rtl, t.lang = i, lang == "ar", lang
    t.p = lambda tup: tup[i]  # pick from a (ar, fr, en) tuple
    return t
