# PyCodeLens 4.2

Python Code Analysis Tool - Visualize and export code structure for LLMs (Large Language Models)

## Overview

PyCodeLens is a GUI tool that analyzes Python project structures and outputs them in formats optimized for LLMs. It extracts classes, functions, dependencies, inheritance relationships, and exports them in JSON, Mermaid diagrams, or text format.

## Features

- **Code Structure Analysis**: Extract classes, functions, methods, and decorators
- **Extended Analysis (astroid)**: Detailed analysis including type inference, inheritance, and dependencies
- **Multiple Output Formats**:
  - Text format (Analysis tab)
  - Extended analysis (astroid tab)
  - JSON format
  - Mermaid diagrams
- **Directory Tree**: Display project structure with selectable analysis targets
- **Multi-language UI**: Japanese/English toggle
- **Clipboard Copy**: One-click copy of selected tab contents

## Installation

### Required Libraries

```bash
pip install pillow pyperclip
```

### Recommended Libraries (for advanced features)

```bash
pip install astroid ttkthemes
```

- `astroid`: Extended analysis (type inference, inheritance, dependencies)
- `ttkthemes`: Enhanced UI themes

## Usage

### Launch

```bash
python PyCodeLens4.2.py
```

### Basic Operations

1. **Import**: Select a folder to load the project
2. **Select files/folders in tree**: Double-click to select
3. **Analysis**: Analyze selected files/folders
4. **Copy**: Copy selected tab contents to clipboard

### Shortcuts

- `Ctrl+A`: Select all text
- `Ctrl+C`: Copy selected text
- Right-click: Context menu

## Project Structure

```
PyCoadLens4.2/
├── PyCodeLens4.2.py    # Entry point
├── core/               # Analysis engine
│   ├── analyzer.py         # Basic code analysis
│   ├── astroid_analyzer.py # astroid extended analysis
│   ├── database.py         # Code snippet database
│   ├── dependency.py       # Dependency analysis
│   ├── language_base.py    # Language base class
│   └── language_registry.py # Language registry
├── ui/                 # UI components
│   ├── main_window.py      # Main window
│   ├── toolbar.py          # Toolbar
│   ├── tree_view.py        # Directory tree
│   ├── analysis_handler.py # Analysis handler
│   ├── output_generator.py # Output generation
│   ├── language_manager.py # Language switching
│   ├── editor_shortcuts.py # Shortcut management
│   ├── syntax_highlighter.py # Syntax highlighting
│   ├── error_display.py    # Error display
│   └── icon/               # Icon images
├── utils/              # Utilities
│   ├── config.py          # Configuration management
│   ├── file_utils.py      # File operations
│   ├── i18n.py            # Internationalization
│   ├── json_converter.py  # JSON conversion
│   └── code_extractor.py  # Code extraction
└── locales/            # Translation files
    ├── ja.json
    └── en.json
```

## Compiling to EXE

Create a standalone EXE using PyInstaller:

```bash
pip install pyinstaller

pyinstaller --noconfirm --onedir --windowed ^
  --add-data "ui/icon;ui/icon" ^
  --add-data "locales;locales" ^
  --name PyCodeLens4.2 ^
  PyCodeLens4.2.py
```

Output: `dist/PyCodeLens4.2/`

## License

MIT License

## Author

unhaya
