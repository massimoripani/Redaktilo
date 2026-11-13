#!/bin/sh
# Konstruo por Linux/macOS (la sama, sen .bat). Rezulto: dist/Redaktilo/
cd "$(dirname "$0")"
PY=${PYTHON:-python3}
$PY -m pip install $PIP_FLAGS --upgrade pyinstaller spylls || exit 1
HID="--hidden-import htmlumilo --hidden-import monato_common"
while read -r M; do
  [ -n "$M" ] && HID="$HID --hidden-import $M"
done < moduloj.txt
$PY -m PyInstaller --noconfirm --clean --windowed --name Redaktilo --collect-submodules spylls $HID editor.py || exit 1
cp -r kromprogramoj vortaroj lingvoj licencoj dist/Redaktilo/ && cp LEGUMIN.txt LICENCO.txt dist/Redaktilo/
echo "FINITE: dist/Redaktilo/"
