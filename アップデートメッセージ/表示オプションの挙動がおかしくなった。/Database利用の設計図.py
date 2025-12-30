---

# 📐PycoadLens 用コードスニペット管理システム設計図

## 🧭 コンセプト概要

### 🎯 目的

Pythonファイルから**関数・クラス定義を抽出**しブロックごとに、**SQLiteに保存**。
PycoadLens上でコードを**ツリービューから表示・コピー（複数ブロック）**可能にすることで、LLMに明確かつ正確なコードスニペットを渡せるUXを提供。

---

## 🧱 技術スタック

| 要素     | 技術候補                       | 備考             |
| ------ | -------------------------- | -------------- |
| データ保存  | `sqlite3`（標準ライブラリ）         | 軽量・単一ファイルで完結   |
| GUI    | `PyQt5` または `PySide2`      | Qtベース、高機能なUI構築 |
| コード解析  | `ast`, `parso`, `lib2to3`等 | Pythonコードの構文解析 |
| ハイライト  | `QSyntaxHighlighter`       | Pythonシンタックス表示 |
| コードコピー | `QClipboard`               | PyQt組み込み       |

---

## 🧰 推奨ライブラリ（補足）

| ライブラリ                    | 用途                        |
| ------------------------ | ------------------------- |
| `pygments`               | コードの色分け（Syntax Highlight） |
| `watchdog`               | ファイルの更新監視（再解析トリガー）        |
| `python-lsp-server`（将来案） | LLM連携・補完支援                |

---

## 🗂️ データベース設計（SQLite）

```sql
CREATE TABLE code_snippets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL,
    dir_path TEXT,
    name TEXT NOT NULL,
    type TEXT CHECK(type IN ('class', 'function', 'import')) NOT NULL,
    description TEXT,
    code TEXT NOT NULL,
    line_start INTEGER,
    line_end INTEGER,
    tags TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 補足

* `file_path`, `dir_path`: コピー時コメント付与に必要（LLM用データラベル）
* `line_start`, `line_end`: 抽出コードの原位置管理
* `tags`: 機能分類（例: math, i/o, gui）

---

## 📑 コメント構造（コピー時挿入）

```
## ディレクトリ: D:\Project\MyApp\core
### ファイル: config_manager.py
# クラス
class ConfigManager:
    def _ensure_required_keys():
        ...
```

> LLMへの送信を考慮した**位置情報の明示フォーマット**

---

## 🖼️ GUI設計（PycoadLens内 Code View）

* **左側: ツリービュー**

  * ディレクトリ構造 → ファイル → クラス/関数（Node単位）
* **右側: コード表示ウィンドウ**

  * 該当コード（QPlainTextEdit＋シンタックスハイライト）
* **機能ボタン**

  * `表示`: 詳細ウィンドウに反映
  * `コピー`: コメント付きコードをクリップボードへコピー

---

## 🔄 処理フローと更新最適化

### 初回起動時

1. 全コード読み込み → `code_snippets`に挿入
2. 各ファイルの `modified_time` を `code_files` テーブルに記録

### 再起動時（差分読み込み）

```sql
CREATE TABLE code_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT UNIQUE,
    last_parsed_time TIMESTAMP
);
```

→ タイムスタンプを比較し、差分のあるファイルのみ再解析。

---

## 🧪 パフォーマンス対策

* 読み込み中は `QProgressBar` によりステータス表示
* 非同期スレッドでパース処理（UIスレッドをブロックしない）

---
