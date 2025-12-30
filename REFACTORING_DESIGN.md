# main_window.py リファクタリング設計書

## 現状分析

メタデータファイルの呼び出し関係分析に基づく設計

### 完了済み
1. **ToolbarManager** (ui/toolbar.py) - 約125行削減
2. **AnalysisHandler** (ui/analysis_handler.py) - 約356行削減

### 残り削減対象: 約650行

---

## Phase 3: OutputGenerator

### 対象メソッド
| メソッド | 呼び出し元 | 行数(推定) |
|---------|-----------|----------|
| `generate_mermaid_output()` | AnalysisHandler.perform_extended_analysis, analyze_file | ~150 |
| `generate_json_output()` | AnalysisHandler.perform_extended_analysis, analyze_file | ~60 |
| `generate_advanced_mermaid_for_llm()` | 未使用(将来用) | ~130 |
| `get_directory_structure()` | generate_json_output, perform_extended_analysis | ~60 |

### 依存関係
- `self.astroid_analyzer` (読み取りのみ)
- `self.mermaid_text`, `self.json_text` (UI要素)
- `self.dir_tree_view.get_included_files()`
- `self.current_dir`

### 設計
```python
class OutputGenerator:
    def __init__(self, main_window):
        self.main_window = main_window

    def generate_mermaid_output(self):
    def generate_json_output(self):
    def generate_advanced_mermaid_for_llm(self):
    def get_directory_structure(self, python_files):
```

---

## Phase 4: LanguageManager

### 対象メソッド
| メソッド | 呼び出し元 | 行数(推定) |
|---------|-----------|----------|
| `setup_language_selector()` | setup_ui | ~25 |
| `update_language_buttons()` | setup_language_selector, change_language | ~15 |
| `change_language()` | setup_language_selector (ボタンコールバック) | ~15 |
| `on_language_change()` | 未使用 | ~10 |
| `update_ui_texts()` | change_language, on_language_change | ~20 |
| `_update_widget_texts()` | update_ui_texts (再帰) | ~20 |
| `_update_menu_texts()` | update_ui_texts | ~30 |

### 依存関係
- `self.i18n` (言語管理)
- `self.jp_button`, `self.en_button` (UI要素)
- `self.root` (タイトル更新)
- `self.toolbar_frame` (ボタン配置)

### 設計
```python
class LanguageManager:
    def __init__(self, main_window):
        self.main_window = main_window
        self.jp_button = None
        self.en_button = None

    def setup_language_selector(self):
    def update_language_buttons(self):
    def change_language(self, lang_code):
    def update_ui_texts(self):
    def _update_widget_texts(self, parent):
    def _update_menu_texts(self):
```

---

## Phase 5: EditorShortcutsManager

### 対象メソッド
| メソッド | 呼び出し元 | 行数(推定) |
|---------|-----------|----------|
| `setup_text_editor_shortcuts()` | setup_ui | ~10 |
| `setup_editor_shortcuts()` | setup_text_editor_shortcuts | ~20 |
| `show_context_menu()` | setup_editor_shortcuts (bind) | ~10 |
| `select_all()` | setup_editor_shortcuts (bind) | ~5 |
| `copy_text()` | setup_editor_shortcuts (bind) | ~10 |
| `setup_analysis_result_context_menu()` | setup_ui | ~10 |
| `show_result_context_menu()` | setup_analysis_result_context_menu (bind) | ~5 |
| `copy_selected_text()` | コンテキストメニュー | ~10 |
| `setup_code_context_menus()` | setup_ui | ~20 |
| `show_code_context_menu()` | bind | ~30 |

### 依存関係
- 各テキストウィジェット (`result_text`, `extended_text`, `json_text`, `mermaid_text`)
- `self.root` (クリップボード操作)

### 設計
```python
class EditorShortcutsManager:
    def __init__(self, main_window):
        self.main_window = main_window

    def setup_all(self):
        """全てのテキストエディタにショートカットを設定"""
    def setup_editor_shortcuts(self, text_widget):
    def show_context_menu(self, event, menu):
    def select_all(self, event, text_widget):
    def copy_text(self, event, text_widget):
    def setup_analysis_result_context_menu(self):
    def show_result_context_menu(self, event):
    def copy_selected_text(self):
```

---

## 実装優先順位

1. **OutputGenerator** (Phase 3) - AnalysisHandlerとの関連が強く、一緒に切り出すと効果的
2. **LanguageManager** (Phase 4) - 独立性が高く、切り出しやすい
3. **EditorShortcutsManager** (Phase 5) - UI要素への依存が多いが、パターン化されている

## 予想削減効果

| Phase | モジュール | 削減行数 |
|-------|-----------|---------|
| 完了 | ToolbarManager | ~125 |
| 完了 | AnalysisHandler | ~356 |
| 3 | OutputGenerator | ~400 |
| 4 | LanguageManager | ~135 |
| 5 | EditorShortcutsManager | ~130 |
| **合計** | | **~1,146** |

最終的にmain_window.pyは約1,000行程度になる見込み
