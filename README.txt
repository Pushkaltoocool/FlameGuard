W19 Endicott – walkthrough editor (offline copy)
================================================

HOW TO RUN
1. Unzip this folder anywhere on your computer. Keep the 3 files together:
     index.html, three.min.js, OrbitControls.js
2. Double-click index.html. It opens in your browser (Chrome or Edge recommended).
   No internet or installation needed.

   If your browser blocks it, run a tiny local server instead:
     - open a terminal in this folder
     - run:  python -m http.server 8000
     - visit http://localhost:8000 in your browser

SAVING YOUR CHANGES
- "Save layout" downloads a new index.html that contains your current layout.
  Move it into this folder, replacing the old index.html, to keep your changes.
- The browser also keeps an unsaved draft automatically; next time you open the page
  it offers "Restore" or "Discard".
- View tab > "Export JSON" saves w19-layout.json (all devices and cables);
  "Import JSON" loads one back in.

CONTROLS
- Overview: drag to rotate, scroll/pinch to zoom, drag a device to move it,
  tap a device to edit it, Add tab to place new devices or furniture.
- Walk mode: W A S D to move (Shift = run), drag to look, walk up/down stairs,
  V = third person, R = rotate the selected item, minimap tap = jump there.
