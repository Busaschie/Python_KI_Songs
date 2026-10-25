# Python_KI_Songs

Python-Skript zur KI-gestützten Erzeugung von Songs über Prompts und Stilvorgaben.

## Überblick

`songs.py` kombiniert Prompt-Vorlagen mit Stil-Definitionen, um Songs per KI zu generieren.

## Projektstruktur

```text
├── songs.py     # Hauptskript
├── prompts/     # Prompt-Vorlagen
├── styles/      # Stil-Definitionen (Genres/Stimmungen)
└── .gitignore
```

## Installation

```bash
git clone https://github.com/Busaschie/Python_KI_Songs.git
cd Python_KI_Songs
python -m venv .venv
# Windows: .venv\Scripts\activate | Linux/macOS: source .venv/bin/activate
```

Benötigte Pakete und API-Schlüssel für den verwendeten KI-Dienst installieren bzw. als Umgebungsvariable setzen (keine Schlüssel committen).

## Nutzung

```bash
python songs.py
```

Prompts und Stile lassen sich über die Dateien in `prompts/` und `styles/` anpassen.
