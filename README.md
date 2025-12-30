# PyCodeLens 4.2

Pythonコード解析ツール - LLM（大規模言語モデル）向けにコード構造を可視化・出力

## 概要

PyCodeLensは、Pythonプロジェクトのコード構造を解析し、LLMに渡しやすい形式で出力するGUIツールです。クラス、関数、依存関係、継承関係などを抽出し、JSON、Mermaidダイアグラム、テキスト形式で出力できます。

## 主な機能

- **コード構造解析**: クラス、関数、メソッド、デコレータを抽出
- **拡張解析（astroid）**: 型推論、継承関係、依存関係の詳細分析
- **複数出力形式**:
  - テキスト形式（解析結果タブ）
  - 拡張解析形式（astroid解析タブ）
  - JSON形式
  - Mermaidダイアグラム
- **ディレクトリツリー**: プロジェクト構造をツリー表示、解析対象を選択可能
- **多言語対応**: 日本語/英語UI切り替え
- **クリップボードコピー**: 選択したタブの内容をワンクリックでコピー

## インストール

### 必須ライブラリ

```bash
pip install pillow pyperclip
```

### 推奨ライブラリ（高度な機能用）

```bash
pip install astroid ttkthemes
```

- `astroid`: 拡張解析機能（型推論、継承関係、依存関係）
- `ttkthemes`: 洗練されたUIテーマ

## 使い方

### 起動

```bash
python PyCodeLens4.2.py
```

### 基本操作

1. **Import**: フォルダを選択してプロジェクトを読み込み
2. **ツリーでファイル/フォルダを選択**: ダブルクリックで選択
3. **Analysis**: 選択したファイル/フォルダを解析
4. **Copy**: 選択したタブの内容をクリップボードにコピー

### ショートカット

- `Ctrl+A`: テキスト全選択
- `Ctrl+C`: 選択テキストをコピー
- 右クリック: コンテキストメニュー

## プロジェクト構造

```
PyCoadLens4.2/
├── PyCodeLens4.2.py    # エントリーポイント
├── core/               # 解析エンジン
│   ├── analyzer.py         # 基本コード解析
│   ├── astroid_analyzer.py # astroid拡張解析
│   ├── database.py         # コードスニペットDB
│   ├── dependency.py       # 依存関係分析
│   ├── language_base.py    # 言語基底クラス
│   └── language_registry.py # 言語レジストリ
├── ui/                 # UIコンポーネント
│   ├── main_window.py      # メインウィンドウ
│   ├── toolbar.py          # ツールバー
│   ├── tree_view.py        # ディレクトリツリー
│   ├── analysis_handler.py # 解析ハンドラー
│   ├── output_generator.py # 出力生成
│   ├── language_manager.py # 言語切り替え
│   ├── editor_shortcuts.py # ショートカット管理
│   ├── syntax_highlighter.py # シンタックスハイライト
│   ├── error_display.py    # エラー表示
│   └── icon/               # アイコン画像
├── utils/              # ユーティリティ
│   ├── config.py          # 設定管理
│   ├── file_utils.py      # ファイル操作
│   ├── i18n.py            # 国際化
│   ├── json_converter.py  # JSON変換
│   └── code_extractor.py  # コード抽出
└── locales/            # 翻訳ファイル
    ├── ja.json
    └── en.json
```

## EXEへのコンパイル

PyInstallerを使用してスタンドアロンEXEを作成できます。

```bash
pip install pyinstaller

pyinstaller --noconfirm --onedir --windowed ^
  --add-data "ui/icon;ui/icon" ^
  --add-data "locales;locales" ^
  --name PyCodeLens4.2 ^
  PyCodeLens4.2.py
```

出力先: `dist/PyCodeLens4.2/`

## ライセンス

MIT License

## 作者

unhaya
