import re
import os
import html
import xml.etree.ElementTree as ET
from html import escape

# Se True, i tag di servizio (inf, n-ro, kod, loko, lig, mend, retfoto)
# compaiono in grigio nell'anteprima; se False vengono nascosti.
SHOW_META = True

# =========================
# MAPPA TAG MONATO -> HTML
# (tag: (tag html, classe css))
# Fonte: "Teknikaj konvencioj: la XML-etikedoj"
# =========================
TAG_HTML = {
    # titoli
    "t":   ("h1", None),           # titolo principale
    "tt":  ("h2", "tt"),           # titolo tematico
    "it":  ("h3", None),           # intertitolo
    "p":   ("p", None),            # paragrafo

    # formattazione del testo
    "d":   ("strong", None),       # grassetto
    "k":   ("em", None),           # corsivo
    "r":   ("span", "red"),        # testo rosso
    "mm":  ("span", "mm"),         # maiuscoletto (maiuscole all'80%)
    "sub": ("sub", None),          # pedice
    "sup": ("sup", None),          # apice

    # intestazione e chiusura dell'articolo
    "aut": ("div", "author"),
    "rub": ("div", "rubric"),
    "sv":  ("div", "keywords"),
    "land": ("div", "land"),

    # recensioni
    "bib":    ("div", "bib"),
    "bibaut": ("span", "bibaut"),
    "bibt":   ("em", "bibt"),
    "prez":   ("div", "prez"),

    # elementi vari
    "foto": ("div", "foto"),       # didascalia
    "noto": ("div", "noto"),       # nota sotto l'articolo
    "cit":  ("blockquote", "cit"), # citazione di riempimento
    "sinp": ("div", "sinp"),       # autopresentazione

    # tabelle
    "tab": ("table", "tab"),
    "lin": ("tr", None),
    "td":  ("td", None),
}

# Tag di servizio: non fanno parte del testo stampato
META_TAGS = {"inf", "n-ro", "kod", "loko", "lig", "mend", "retfoto"}

# Tag vuoti (self-closing)
VOID_HTML = {
    "hs": "—",        # trattino lungo (gli spazi sono già nel testo)
    "nl": "<br>\n",   # a capo
    "ss": "_",        # trattino basso
}

_warned = set()


# =========================
# ESPERANTO NORMALIZZAZIONE
# =========================
REPLACEMENTS = {
    "Cx": "Ĉ", "cx": "ĉ",
    "Gx": "Ĝ", "gx": "ĝ",
    "Hx": "Ĥ", "hx": "ĥ",
    "Jx": "Ĵ", "jx": "ĵ",
    "Sx": "Ŝ", "sx": "ŝ",
    "Ux": "Ŭ", "ux": "ŭ",
}


def fix_esperanto(text):
    # Non tocca i tag né il contenuto di <ret> (indirizzi web ed email)
    parts = re.split(r"(<ret>.*?</ret>|<[^>]*>)", text, flags=re.DOTALL)
    for i in range(0, len(parts), 2):
        for k, v in REPLACEMENTS.items():
            parts[i] = parts[i].replace(k, v)
    return "".join(parts)


def unescape_entities(text):
    # Converte entità HTML (&Uuml; ecc.) ma lascia quelle XML di base,
    # altrimenti &amp; e &lt; romperebbero il parsing.
    keep = {"amp", "lt", "gt", "quot", "apos"}

    def rep(m):
        return m.group(0) if m.group(1) in keep else html.unescape(m.group(0))

    return re.sub(r"&([A-Za-z][A-Za-z0-9]*);", rep, text)


# =========================
# ESTRAZIONE TESTO COMPLETO
# =========================
def extract_plain_text(elem):
    text = elem.text or ""
    for child in elem:
        text += extract_plain_text(child)
        if child.tail:
            text += child.tail
    return text


# =========================
# TESTO SOLO DA <tt> IN POI
# =========================
def extract_plain_text_from_tt(root):
    text = ""
    start = False
    for elem in root:
        if elem.tag == "tt":
            start = True
        if not start:
            continue
        text += extract_plain_text(elem)
    return text


# =========================
# CONVERSIONE XML → HTML
# =========================
def inner_html(elem, cdepth):
    content = escape(elem.text or "", quote=False)
    for child in elem:
        content += convert_element(child, cdepth)
        if child.tail:
            content += escape(child.tail, quote=False)
    return content


def convert_element(elem, cdepth=0):
    tag = elem.tag

    # tag vuoti
    if tag in VOID_HTML:
        return VOID_HTML[tag]

    # virgolette: <c> è la virgoletta, non il grassetto
    if tag == "c":
        op, cl = ("„", "“") if cdepth % 2 == 0 else ("‚", "‘")
        return op + inner_html(elem, cdepth + 1) + cl

    # indirizzi web / email
    if tag == "ret":
        target = (elem.text or "").strip()
        href = target
        if "@" in target and not re.match(r"^(https?:|mailto:)", target):
            href = "mailto:" + target
        return f'<a href="{escape(href)}">{escape(target, quote=False)}</a>'

    # tag di servizio
    if tag in META_TAGS:
        if not SHOW_META:
            return ""
        if tag == "mend":
            content = elem.get("id", "")
        else:
            content = inner_html(elem, cdepth)
        return (f'<span class="meta">[{tag}: {escape(content, quote=False)}]</span>'
                if tag == "mend"
                else f'<span class="meta">[{tag}: {content}]</span>')

    # tag con corrispondenza HTML
    if tag in TAG_HTML:
        html_tag, cls = TAG_HTML[tag]
    else:
        if tag not in _warned:
            print(f"⚠️  Tag senza corrispondenza HTML: <{tag}>")
            _warned.add(tag)
        html_tag, cls = "div", f"xml-{tag}"

    class_attr = f' class="{cls}"' if cls else ""
    return f"<{html_tag}{class_attr}>{inner_html(elem, cdepth)}</{html_tag}>"


# =========================
# CONVERSIONE PRINCIPALE
# =========================
def convert_xml_to_html(input_file, output_file):

    with open(input_file, "r", encoding="utf-8") as f:
        raw_xml = f.read()

    raw_xml = unescape_entities(raw_xml)
    raw_xml = fix_esperanto(raw_xml)

    try:
        root = ET.fromstring(raw_xml)
    except Exception as e:
        print("❌ Errore nel parsing XML:", e)
        return

    # I commenti <!-- --> vengono scartati automaticamente dal parser,
    # come previsto dalle convenzioni.

    plain_text = extract_plain_text_from_tt(root)
    char_count = len(plain_text)

    body = ""
    for child in root:
        body += convert_element(child) + "\n"

    html_output = f"""<!DOCTYPE html>
<html lang="eo">
<head>
<meta charset="UTF-8">
<title>Artikolo</title>
<style>
body {{
    font-family: Arial, sans-serif;
    max-width: 800px;
    margin: auto;
    line-height: 1.6;
}}
.rubric {{ font-weight: bold; color: gray; margin-bottom: 10px; }}
.author {{ margin-top: 20px; font-style: italic; }}
.keywords {{ font-size: 0.9em; color: #666; }}
.land {{ font-size: 0.9em; }}
.mm {{ text-transform: uppercase; font-size: 80%; }}
.red {{ color: #c00000; }}
.bib {{ margin: 1em 0 0.3em; }}
.prez {{ margin-bottom: 1em; }}
.foto {{ font-size: 0.85em; color: #444; margin: 0.5em 0; }}
.noto {{ font-size: 0.85em; border-top: 1px solid #ccc; margin-top: 1em; padding-top: 0.3em; }}
.cit {{ font-size: 1.1em; color: #444; border-left: 3px solid #ccc; margin-left: 0; padding-left: 1em; }}
.sinp {{ font-size: 0.9em; background: #f4f4f4; padding: 0.5em; }}
.tab {{ border-collapse: collapse; }}
.tab td {{ border: 1px solid #bbb; padding: 3px 8px; }}
.meta {{ font-size: 0.75em; color: #999; background: #f0f0f0; padding: 0 4px; }}
[class^="xml-"] {{ outline: 1px dashed orange; }}
</style>
</head>
<body>

<p><strong>Lunghezza dell’articolo: {char_count} caratteri</strong></p>

{body}

</body>
</html>
"""

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_output)

    print(f"✅ File HTML creato: {output_file}")


# =========================
# INPUT INTERATTIVO
# =========================
if __name__ == "__main__":

    input_file = input("📄 Inserisci il nome del file XML: ").strip()

    if not os.path.exists(input_file):
        print("❌ File non trovato!")
        exit()

    base = os.path.splitext(input_file)[0]
    output_file = base + ".html"

    convert_xml_to_html(input_file, output_file)
