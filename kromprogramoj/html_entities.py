# -*- coding: utf-8 -*-
"""Konvertas HTML-entojn al UTF-8-signoj per ekstera vortaro."""

import monato_common as mc
import re

CATEGORY = "Konvertiloj"
NAME = "HTML-kodoj → UTF8"

VORTARO_PATH = mc.vortaro_path("html_entoj.txt")   # vortaroj/ apud la programo

# Entoj kaj signoj kiuj ne estu konvertataj, alie la XML rompiĝus
PROTEKTITAJ = {"&amp;", "&lt;", "&gt;"}
PROTEKTITAJ_SIGNOJ = {"&", "<", ">"}
PROTEKTITAJ_KODOJ = {38, 60, 62}

_UNICODE_RE = re.compile(r"\\U([0-9a-fA-F]{8})|\\u([0-9a-fA-F]{4})")


def _dekodi_signon(valoro):
    """Dekodas \\uXXXX kaj \\UXXXXXXXX en la valoro."""
    def rep(m):
        kodo = int(m.group(1) or m.group(2), 16)
        try:
            return chr(kodo)
        except (ValueError, OverflowError):
            return m.group(0)
    return _UNICODE_RE.sub(rep, valoro)


def legi_vortaron():
    vortaro = {}

    with open(VORTARO_PATH, encoding="utf-8") as f:
        for linio in f:
            linio = linio.rstrip("\r\n").strip()

            if not linio or linio.startswith("#"):
                continue

            if "=" not in linio:
                continue

            ento, signo = linio.split("=", 1)
            ento = ento.strip()

            # Nur entoj kun fina «;» (ignoras malnovajn variantojn
            # sen punktokomo, kiel &copy aŭ &para)
            if not (ento.startswith("&") and ento.endswith(";")):
                continue

            if ento in PROTEKTITAJ:
                continue

            signo = _dekodi_signon(signo)

            if not signo or signo in PROTEKTITAJ_SIGNOJ:
                continue

            vortaro[ento] = signo

    return vortaro


def konverti_entojn(teksto):
    vortaro = legi_vortaron()

    if not vortaro:
        return teksto

    # Unue la plej longaj entoj
    entoj = sorted(vortaro, key=len, reverse=True)

    pattern = re.compile(
        "|".join(re.escape(ento) for ento in entoj)
        + r"|&#(?:[0-9]+|[xX][0-9a-fA-F]+);"
    )

    def anstataŭigi(match):
        ento = match.group(0)

        if ento in vortaro:
            return vortaro[ento]

        # Numeraj entoj: dekumaj kaj deksesumaj
        if ento.startswith("&#"):
            valoro = ento[2:-1]

            try:
                if valoro.startswith(("x", "X")):
                    kodo = int(valoro[1:], 16)
                else:
                    kodo = int(valoro, 10)

                if (
                    0 <= kodo <= 0x10FFFF
                    and not 0xD800 <= kodo <= 0xDFFF
                    and kodo not in PROTEKTITAJ_KODOJ
                ):
                    return chr(kodo)

            except ValueError:
                pass

        return ento

    return pattern.sub(anstataŭigi, teksto)


def run(ctx):
    erari = getattr(ctx, "error", None) or ctx.warn
    try:
        ctx.apply(konverti_entojn)
    except FileNotFoundError:
        erari("La vortaro html_entoj.txt ne estis trovita.")
    except Exception as e:
        erari(f"Eraro dum konvertado: {e}")
