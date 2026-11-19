
#!/bin/sh
# Konstruo por Linux. Rezulto: dist/Redaktilo/

cd "$(dirname "$0")" || exit 1

PY=${PYTHON:-python3}

$PY -m pip install $PIP_FLAGS --upgrade pyinstaller spylls || exit 1

HID="--hidden-import htmlumilo --hidden-import monato_common"

while read -r M; do
  [ -n "$M" ] && HID="$HID --hidden-import $M"
done < moduloj.txt

$PY -m PyInstaller --noconfirm --clean --windowed \
  --name Redaktilo --collect-submodules spylls $HID editor.py || exit 1

# Kopias la kromprogramojn, vortarojn, lingvojn, licencojn kaj gvidlibron.
cp -r kromprogramoj vortaroj lingvoj licencoj doc dist/Redaktilo/ || exit 1

# Kopias la informajn dosierojn.
cp LEGUMIN.txt LICENCO.txt dist/Redaktilo/ || exit 1

# Kontrolas la ĉeeston de la integra gvidlibro.
if [ ! -f dist/Redaktilo/doc/gvidilo.html ]; then
  echo "ERARO: doc/gvidlibro.html ne trovita en la pakaĵo." >&2
  exit 1
fi

echo "FINITE: dist/Redaktilo/"
echo "La gvidlibro troviĝas en dist/Redaktilo/doc/gvidlibro.html"
