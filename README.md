# Timberborn Save Tool — Community Edition

**FR · EN · DE · ES** | Windows | Python 3.10+ | No third-party runtime dependencies

An **unofficial**, community-made GUI for editing local `.timber` save files from Timberborn. Inspired by a wood-and-nature aesthetic; not affiliated with Mechanistry. No copyrighted game files included.

> **Beta software:** saves are valid ZIP/JSON archives after editing, but not every feature has been independently verified by loading edited saves in the game. Keep original backups. The tool *never permits overwriting the opened save*.

## Features

| Tool | What it does |
|---|---|
| Stockpiles | Fill every completed and assigned storage to its capacity, or choose goods individually |
| Population | Add adult beavers, choose their age; duplicate bots **only if a compatible bot already exists in the save** |
| Needs | Restore hunger and thirst **once**; the game's natural progression continues afterward. Also includes a heal-all option |
| Science | Set the exact number of science points (0–2,000,000,000) |
| Weather | Modify min/max durations of temperate seasons, droughts and badtides where present in the save |
| Map | Add/remove sources, draw a line of water sources |
| Forest | Select a rectangular area (two clicks), choose birch/pine/oak/maple, set density, place trees in vacant tiles |
| Languages | French, English, German, Spanish. Includes many resource names. Unknown resource identifiers fall back to the game's internal ID |
| Export | Saves a new `.timber` with `_modifie` appended to the name |

### FR — Installation et utilisation

1. Télécharger le ZIP du projet puis le décompresser.
2. Installer **Python 3.10+** sur Windows en cochant « Add Python to PATH ».
3. Lancer `LANCER.bat` ou `python src/Timberborn_Save_Tool.py`.
4. Ouvrir une sauvegarde `.timber` (dossier habituel : `Documents/Timberborn/Saves/<nom-colonie>/`).
5. Faire les modifications puis **Enregistrer une copie**.
6. Charger cette nouvelle sauvegarde dans Timberborn et contrôler le résultat avant de poursuivre la partie.

Pour créer un exécutable, lancer `CONSTRUIRE_EXE.bat` (nécessite PyInstaller, téléchargé automatiquement par ce script). Une GitHub Action peut aussi compiler le programme sur Windows.

### EN — Quick start

Install Python 3.10+ on Windows. Run `LANCER.bat` or `python src/Timberborn_Save_Tool.py`. Open a `.timber` save, make edits, and save a copy. Load and verify the copy in-game.

### DE — Kurzanleitung

Python 3.10+ unter Windows installieren. `LANCER.bat` starten. `.timber`-Spielstand öffnen, Änderungen vornehmen und eine Kopie speichern. Die Kopie im Spiel prüfen.

### ES — Inicio rápido

Instala Python 3.10+ en Windows. Ejecuta `LANCER.bat`. Abre una partida `.timber`, edítala y guarda una copia. Comprueba la copia dentro del juego.

## Notes and limitations

- Trees are cloned from **living native trees** already represented in the loaded save. Trees placed in bad soil, flooding or polluted areas may die. Occupancy checks are conservative and do not fully model every multi-tile building, so use care.
- Adding bots without a native bot model is not yet supported. Inventing bot components can crash Timberborn. A future import-from-compatible-save workflow could address this.
- The difficulty editor modifies supported **future weather durations**, not every parameter in the new-game difficulty dialog and not an already active season.
- The hunger and thirst buttons restore needs **only once**. They do not disable future consumption.
- The map includes experimental natural resource editing, and game updates may change the save format.
- Never upload personal save files or Steam account information to this repository.

## Repository structure

```text
src/                  Python/Tkinter GUI, editing engine, localization and map tools
tests/                Offline tests using generated fixtures (no user saves)
.github/workflows/    Optional Windows build + tests
LANCER.bat             Launches the GUI with Python
CONSTRUIRE_EXE.bat     Builds a standalone Windows EXE
LICENSE                MIT
```

## Contributing

Pull requests are welcome for translations, additional resource names, safe map placement checks, and compatibility fixes. Report an issue with the **Timberborn game version**, exact reproduction steps and a sanitized traceback. Avoid uploading personal colony saves without checking their contents.

## License

MIT. Timberborn is a trademark of its respective owner; this is a fan-made, unofficial utility.
