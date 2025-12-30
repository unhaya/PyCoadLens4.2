# ui/main_window.py

import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import traceback
import uuid
import pyperclip

# PIL (Pillow) - 画像処理用
from PIL import Image, ImageTk

# UIコンポーネント（絶対インポートパス）
from ui.tree_view import DirectoryTreeView
from ui.syntax_highlighter import SyntaxHighlighter
from ui.error_display import ErrorDisplayWindow

# 他のモジュール（絶対インポートパス）
from utils.config import ConfigManager
from utils.file_utils import open_in_explorer, open_with_default_app, create_temp_error_log, run_python_file
from utils.json_converter import text_to_json_structure, extract_llm_structured_data
from core.analyzer import CodeAnalyzer
from core.astroid_analyzer import AstroidAnalyzer
from core.dependency import generate_call_graph
from utils.i18n import _, init_i18n, get_i18n
from core.language_registry import LanguageRegistry
from core.database import CodeDatabase
from utils.code_extractor import CodeExtractor

class MainWindow:
    """アプリケーションのメインウィンドウを管理するクラス"""
    
    def __init__(self, root, config_manager=None):
        self.root = root
        self.root.title("PyCodeLens")
        
        # 設定マネージャーを初期化（渡されなければ新規作成）
        self.config_manager = config_manager or ConfigManager()
        
        # I18n初期化（ConfigManagerの初期化後に行う）
        self.i18n = init_i18n(self.config_manager) if not get_i18n() else get_i18n()

        window_size = self.config_manager.get_window_size()
        window_size["width"] = 1000
        window_size["height"] = 720
        self.root.geometry(f"{window_size['width']}x{window_size['height']}")
        
        # データベース初期化
        self.code_database = CodeDatabase()
        
        # 分析オブジェクトの初期化
        self.analyzer = CodeAnalyzer()
        self.astroid_analyzer = AstroidAnalyzer()

        # 言語レジストリを初期化
        self.registry = LanguageRegistry.get_instance()
        # Flutterアナライザー関連の登録を削除
        
        # UI構築
        self.setup_ui()
        
        # ウィンドウを中央に配置
        self.center_window()
        
        # ウィンドウのリサイズイベントをバインド
        self.root.bind("<Configure>", self.on_window_resize)
        
        # ウィンドウが閉じられる前のイベントをバインド
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 前回のディレクトリまたはファイルを読み込む
        self.load_last_session()

    def setup_ui(self):
        """UIコンポーネントをセットアップする"""
        # メインスタイルの設定
        style = ttk.Style()
        style.configure("TFrame", background="#f0f0f0")
        style.configure("TButton", font=('Helvetica', 10), padding=5)
        style.configure("TLabel", font=('Helvetica', 11), background="#f0f0f0")
        style.configure("Stats.TLabel", font=('Helvetica', 9), foreground="#666666")

        # プロンプト用のアクセントボタンスタイル
        style.configure("Accent.TButton", font=('Helvetica', 10, 'bold'))

        # スタイルマップの設定
        style.map("Treeview", foreground=[("disabled", "#a0a0a0")], 
                background=[("disabled", "#f0f0f0")])
        
        # ツリービューのカスタムスタイル
        style.configure("Treeview", 
                        background="#ffffff", 
                        foreground="#000000", 
                        rowheight=26,
                        fieldbackground="#ffffff")
        
        # 選択項目のハイライトスタイル - 選択状態をより明確に
        style.map("Treeview", 
                  background=[("selected", "#e0e0ff")],
                  foreground=[("selected", "#000000")])
        
        # ツリービューヘッダーのスタイル
        style.configure("Treeview.Heading", 
                        font=('Helvetica', 10, 'bold'),
                        background="#e0e0e0")
        
        # 含む/除外の視覚的なスタイル
        style.configure("Include.TLabel", foreground="green", font=('Helvetica', 10))
        style.configure("Exclude.TLabel", foreground="red", font=('Helvetica', 10))
        
        # メインフレーム
        self.main_frame = ttk.Frame(self.root, padding=10)
        self.main_frame.pack(expand=True, fill="both")
        
        # ツールバーフレーム
        self.toolbar_frame = ttk.Frame(self.main_frame)
        self.toolbar_frame.pack(fill="x", pady=(0, 10))
       
        # 言語切り替えボタン  
        self.setup_language_selector() 
        
        # カスタムボタンをセットアップ（標準のボタン作成コードを置き換え）
        self.setup_custom_buttons()

        # ステータスバー
        self.status_frame = ttk.Frame(self.main_frame)
        self.status_frame.pack(fill="x", side="bottom", pady=(5, 0))

        # 左側ステータス（現在のファイル情報）
        self.file_status = ttk.Label(self.status_frame, text=_("ui.status.ready", "準備完了"), style="Stats.TLabel")
        self.file_status.pack(side="left")

        # 右側ステータス（文字数表示）
        self.char_count_label = ttk.Label(self.status_frame, text=_("ui.status.char_count", "文字数: 0"), style="Stats.TLabel")
        self.char_count_label.pack(side="right")

        # 表示オプションフレーム - ステータスバーの右側に配置
        self.option_frame = ttk.Frame(self.status_frame)
        self.option_frame.pack(side="right", padx=20)

        # インポート文を含めるかどうかのチェックボックス変数
        self.show_imports = tk.BooleanVar(value=True)
        # docstringを表示するかどうかのチェックボックス変数
        self.show_docstrings = tk.BooleanVar(value=True)
        # EXEフォルダスキップチェックボックスは削除（デフォルトでTrueに設定）

        # オプションラベル
        option_label = ttk.Label(self.option_frame, text=_("ui.options.label", "表示オプション:"), style="Stats.TLabel")
        option_label.pack(side="left", padx=5)

        # インポート文を表示するチェックボックス
        self.imports_check = ttk.Checkbutton(
            self.option_frame, 
            text=_("ui.options.imports", "インポート文"), 
            variable=self.show_imports,
            command=self.toggle_display_options
        )
        self.imports_check.pack(side="left", padx=5)

        # docstringを表示するチェックボックス
        self.docstrings_check = ttk.Checkbutton(
            self.option_frame, 
            text=_("ui.options.docstrings", "説明文"), 
            variable=self.show_docstrings,
            command=self.toggle_display_options
        )
        self.docstrings_check.pack(side="left", padx=5)

        # EXEを含むフォルダスキップチェックボックスは削除

        # ペイン分割（左右に分割）- 比率を30:70に
        self.paned_window = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        self.paned_window.pack(expand=True, fill="both")
        
        # 左側フレーム（ディレクトリツリー用）- 30%
        window_width = self.config_manager.get_window_size()["width"]
        self.left_frame = ttk.Frame(self.paned_window, width=int(window_width * 0.3))
        self.left_frame.pack_propagate(False)  # サイズを固定
        self.paned_window.add(self.left_frame, weight=1)
        
        # 右側フレーム（結果表示用）- 70%
        self.right_frame = ttk.Frame(self.paned_window, width=int(window_width * 0.7))
        self.paned_window.add(self.right_frame, weight=4)
        
        # ディレクトリツリービュー - 設定マネージャーを渡す
        self.dir_tree_view = DirectoryTreeView(self.left_frame, self.config_manager)
        self.dir_tree_view.set_file_selected_callback(self.on_file_selected)
        self.dir_tree_view.set_dir_selected_callback(self.on_dir_selected)

        # タブコントロールの作成
        self.tab_control = ttk.Notebook(self.right_frame)

        # タブ選択パネルの作成
        self.tab_selection_panel = self.create_tab_selection_panel()
        self.tab_selection_panel.pack(fill="x", pady=(0, 5))

        # 解析結果タブの作成
        self.result_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.result_tab, text=f" {_('ui.tabs.analysis', '解析結果')} ")

        # 拡張解析タブの作成
        self.extended_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.extended_tab, text=f" {_('ui.tabs.extended', '拡張解析')} ")
        
        # JSONタブの作成
        self.json_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.json_tab, text=f" {_('ui.tabs.json', 'JSON出力')} ")

        # JSONテキストエリアのラベル
        self.json_label = ttk.Label(self.json_tab, text=_("ui.labels.json", "JSON形式のコード構造:"))
        self.json_label.pack(anchor="w", pady=(0, 5))

        # JSONテキストエリア
        self.json_text = scrolledtext.ScrolledText(self.json_tab, font=('Consolas', 10))
        self.json_text.pack(expand=True, fill="both")

        # JSONテキストにもシンタックスハイライターを適用
        self.json_highlighter = SyntaxHighlighter(self.json_text)
        
        # マーメードタブ
        self.mermaid_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.mermaid_tab, text=f" {_('ui.tabs.mermaid', 'マーメード')} ")

        # マーメードタブのラベル
        self.mermaid_label = ttk.Label(self.mermaid_tab, text=_("ui.labels.mermaid", "マーメードダイアグラム:"))
        self.mermaid_label.pack(anchor="w", pady=(0, 5))

        # マーメードテキストエリア
        self.mermaid_text = scrolledtext.ScrolledText(self.mermaid_tab, font=('Consolas', 10))
        self.mermaid_text.pack(expand=True, fill="both")

        # マーメードテキストにもシンタックスハイライターを適用
        self.mermaid_highlighter = SyntaxHighlighter(self.mermaid_text)
        
        # プロンプト入力タブは削除

        # タブコントロールをpack
        self.tab_control.pack(expand=True, fill="both")

        # タブ切り替えイベントをバインド
        self.tab_control.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        # 結果テキストエリアのラベル
        self.result_label = ttk.Label(self.result_tab, text=_("ui.labels.analysis", "解析結果:"))
        self.result_label.pack(anchor="w", pady=(0, 5))

        # 結果テキストエリア - result_tabに配置
        self.result_text = scrolledtext.ScrolledText(self.result_tab, font=('Consolas', 10))
        self.result_text.pack(expand=True, fill="both")
        
        # 拡張解析テキストエリアのラベル
        self.extended_label = ttk.Label(self.extended_tab, text=_("ui.labels.extended", "astroidによる拡張解析結果:"))
        self.extended_label.pack(anchor="w", pady=(0, 5))

        # 拡張解析テキストエリア
        self.extended_text = scrolledtext.ScrolledText(self.extended_tab, font=('Consolas', 10))
        self.extended_text.pack(expand=True, fill="both")

        # プロンプトマネージャーとプロンプト入力タブ関連のコードは削除

        # 結果テキストエリアにシンタックスハイライターを適用
        self.result_highlighter = SyntaxHighlighter(self.result_text)
        
        # 拡張解析テキストエリアにもハイライターを適用
        self.extended_highlighter = SyntaxHighlighter(self.extended_text)

        # 現在のディレクトリパス
        self.current_dir = None
        
        # 選択されたファイル
        self.selected_file = None
        
        # テキストエディタのショートカットとコンテキストメニューを設定
        self.setup_text_editor_shortcuts()
        
        # コード関連のコンテキストメニューをセットアップ
        self.setup_code_context_menus()
        
        # 解析結果テキストのコンテキストメニュー設定
        self.setup_analysis_result_context_menu()

    def generate_advanced_mermaid_for_llm(self):
        """LLM向けに詳細なコード情報をマーメードダイアグラムで生成する"""
        try:
            mermaid_text = ""
            
            # 1. 拡張クラス図（docstring情報付き）
            mermaid_text += "```mermaid\n"
            mermaid_text += "classDiagram\n"
            
            # サブシステム境界の定義
            modules = set()
            for cls in self.astroid_analyzer.classes:
                module = cls.get("module", "unknown")
                modules.add(module)
                
            # サブグラフでモジュール/サブシステムを表現
            for module in modules:
                mermaid_text += f"  namespace {module} {{\n"
                # モジュール内のクラスを追加
                for cls in [c for c in self.astroid_analyzer.classes if c.get("module") == module]:
                    cls_name = cls["name"]
                    
                    # クラスの責任範囲をコメントとして追加
                    docstring = cls.get("docstring", "").replace("\n", "<br>")
                    if docstring:
                        mermaid_text += f"    %% {cls_name}: {docstring[:50]}...\n"
                        
                    # 継承関係
                    for base in cls.get("base_classes", []):
                        if base and base != "object":
                            mermaid_text += f"    {base} <|-- {cls_name}\n"
                            
                    # 複雑さ指標を含んだクラス定義
                    methods_count = len(cls.get("methods", []))
                    attrs_count = len(cls.get("attributes", []))
                    complexity = methods_count * 2 + attrs_count
                    
                    mermaid_text += f"    class {cls_name} {{\n"
                    mermaid_text += f"      %% 複雑さ: {complexity}\n"
                    
                    # 主要メソッドとその説明
                    for method in cls.get("methods", []):
                        method_name = method["name"]
                        params = ", ".join([p.get("name", "") for p in method.get("parameters", []) if p.get("name") != "self"])
                        ret_type = method.get("return_type", "")
                        return_str = f" : {ret_type}" if ret_type and ret_type != "unknown" else ""
                        
                        # メソッドの目的をコメントとして追加
                        doc = method.get("docstring", "")
                        if doc:
                            short_doc = doc.split("\n")[0][:40] + "..."
                            mermaid_text += f"      %% {method_name}: {short_doc}\n"
                            
                        visibility = "+" if not method_name.startswith("_") else "-"
                        mermaid_text += f"      {visibility}{method_name}({params}){return_str}\n"
                    
                    mermaid_text += "    }\n"
                mermaid_text += "  }\n"
                
            mermaid_text += "```\n\n"
            
            # 2. データフロー図
            mermaid_text += "```mermaid\n"
            mermaid_text += "flowchart TD\n"
            
            # データフローの視覚化
            processed_flows = set()
            
            # 関数間のデータ依存関係を解析
            for func in self.astroid_analyzer.functions:
                func_name = func["name"]
                
                # 入力パラメータと出力(戻り値)の分析
                params = [p.get("name") for p in func.get("parameters", [])]
                ret_type = func.get("return_type", "")
                
                # 関数の呼び出し関係を検証
                if func_name in self.astroid_analyzer.dependencies:
                    for callee in self.astroid_analyzer.dependencies[func_name]:
                        flow_key = f"{func_name}_{callee}"
                        if flow_key not in processed_flows:
                            # データの流れを示す（パラメータを使用して）
                            data_passed = ""
                            # このシンプルな例では一部の推測になる
                            if params:
                                data_passed = f"|{params[0]}|"
                            
                            mermaid_text += f"  {func_name} -->|{data_passed}| {callee}\n"
                            processed_flows.add(flow_key)
            
            # 重要な関数に対して、複雑さと責任を示す
            for func in self.astroid_analyzer.functions:
                func_name = func["name"]
                # 関数の複雑さを推定
                lines = func.get("source_lines", 0)
                calls = len(self.astroid_analyzer.dependencies.get(func_name, []))
                complexity = lines + calls * 2
                
                # スタイル設定（複雑さに基づく）
                if complexity > 20:
                    mermaid_text += f"  style {func_name} fill:#f96,stroke:#333,stroke-width:2px\n"
                elif complexity > 10:
                    mermaid_text += f"  style {func_name} fill:#ff9,stroke:#333,stroke-width:1px\n"
            
            mermaid_text += "```\n\n"
            
            # 3. コンテキスト概要図（主要コンポーネントとその責任）
            mermaid_text += "```mermaid\n"
            mermaid_text += "mindmap\n"
            mermaid_text += "  root((コードマップ))\n"
            
            # 主要なモジュールとその責任
            for module in modules:
                mermaid_text += f"    {module}\n"
                
                # モジュール内の主要クラス
                module_classes = [c for c in self.astroid_analyzer.classes if c.get("module") == module]
                for cls in module_classes:
                    cls_name = cls["name"]
                    mermaid_text += f"      {cls_name}\n"
                    
                    # 主な責任（簡潔に）
                    docstring = cls.get("docstring", "")
                    if docstring:
                        first_line = docstring.split("\n")[0][:50]
                        mermaid_text += f"        {first_line}\n"
                        
                    # 主要メソッド（最大3つ）
                    methods = cls.get("methods", [])
                    important_methods = sorted(methods, key=lambda m: len(m.get("docstring", "")), reverse=True)[:3]
                    for method in important_methods:
                        method_name = method["name"]
                        if not method_name.startswith("_"):  # 公開メソッドのみ
                            mermaid_text += f"        {method_name}()\n"
            
            mermaid_text += "```\n"
            
            return mermaid_text
            
        except Exception as e:
            traceback.print_exc()
            return f"マーメードダイアグラム生成中にエラーが発生しました: {str(e)}"

    def generate_mermaid_output(self):
        """現在の解析結果からマーメードダイアグラムを生成してマーメードタブに表示する"""
        # 既存の解析結果を取得
        if not hasattr(self, 'astroid_analyzer') or not self.astroid_analyzer.dependencies:
            self.mermaid_text.delete(1.0, tk.END)
            self.mermaid_text.insert(tk.END, "マーメードダイアグラム生成に必要な解析データがありません。")
            return

        try:
            # マーメードテキスト初期化
            mermaid_text = ""
            
            # 1. クラス図
            if self.astroid_analyzer.classes:
                mermaid_text += "```mermaid\n%% クラス図\nclassDiagram\n"
                
                # クラス定義と継承関係
                for cls in self.astroid_analyzer.classes:
                    cls_name = cls["name"]
                    
                    # 継承関係
                    for base in cls.get("base_classes", []):
                        if base and base != "object":
                            mermaid_text += f"  {base} <|-- {cls_name}\n"
                    
                    # クラスの内容
                    mermaid_text += f"  class {cls_name} {{\n"
                    
                    # メソッド (最大10個まで表示)
                    methods = cls.get("methods", [])[:10]
                    for method in methods:
                        method_name = method["name"]
                        params = ", ".join([p.get("name", "") for p in method.get("parameters", []) 
                                         if p.get("name") != "self"])
                        mermaid_text += f"    +{method_name}({params})\n"
                    
                    mermaid_text += "  }\n"
                
                mermaid_text += "```\n\n"
            
            # 2. 関数呼び出し図
            mermaid_text += "```mermaid\n%% 関数呼び出し図\nflowchart TD\n"
            
            # ノードスタイル
            mermaid_text += "  %% ノードスタイル\n"
            mermaid_text += "  classDef main fill:#f96,stroke:#333,stroke-width:2px;\n"
            mermaid_text += "  classDef method fill:#9cf,stroke:#333,stroke-width:1px;\n"
            mermaid_text += "  classDef func fill:#cfc,stroke:#333,stroke-width:1px;\n"
            
            # 主要な依存関係をフロー図に変換
            added_nodes = set()
            added_relations = set()
            
            # 重要度でソート (呼び出し数が多い順)
            sorted_callers = sorted(self.astroid_analyzer.dependencies.items(), 
                                 key=lambda x: len(x[1]), reverse=True)
            # 最大20の関数を表示
            for caller, callees in sorted_callers[:20]:
                caller_id = caller.replace('.', '_').replace('()', '')
                
                # ノード追加
                if caller not in added_nodes:
                    if caller == "main" or caller.endswith(".main"):
                        mermaid_text += f"  {caller_id}[\"🚀 {caller}\"]:::main\n"
                    elif "." in caller:  # クラスメソッド
                        mermaid_text += f"  {caller_id}[\"{caller}\"]:::method\n"
                    else:  # 通常関数
                        mermaid_text += f"  {caller_id}[\"{caller}\"]:::func\n"
                    added_nodes.add(caller)
                
                # 依存関係を追加 (最大5つの依存を表示)
                for callee in list(callees)[:5]:
                    callee_id = callee.replace('.', '_').replace('()', '')
                    relation = f"{caller_id}-->{callee_id}"
                    
                    # 標準ライブラリ関数などはスキップ
                    if callee not in added_nodes and not any(callee.startswith(lib) for lib in 
                                                        ['print', 'len', 'os.', 'sys.', 'tk.']):
                        # ノード追加
                        if "." in callee:  # クラスメソッド
                            mermaid_text += f"  {callee_id}[\"{callee}\"]:::method\n"
                        else:  # 通常関数
                            mermaid_text += f"  {callee_id}[\"{callee}\"]:::func\n"
                        added_nodes.add(callee)
                    
                    # 関係を追加
                    if relation not in added_relations:
                        mermaid_text += f"  {caller_id}-->{callee_id}\n"
                        added_relations.add(relation)
            
            mermaid_text += "```\n\n"
            
            # 3. モジュール関係図の部分を完全に書き換え
            mermaid_text += "```mermaid\n%% モジュール構造\nflowchart LR\n"

            try:
                # ディレクトリ情報からのみモジュール構造を構築
                if self.current_dir:
                    python_files = self.dir_tree_view.get_included_files(include_python_only=True)
                    modules = {}
                    
                    # モジュールをディレクトリでグループ化
                    for file_path in python_files:
                        dir_name = os.path.basename(os.path.dirname(file_path))
                        file_name = os.path.basename(file_path).replace('.py', '')
                        
                        # モジュール名を安全な形式に変換
                        safe_dir_name = dir_name.replace(' ', '_').replace('-', '_')
                        safe_file_name = file_name.replace('.', '_').replace('-', '_').replace(' ', '_')
                        
                        if safe_dir_name not in modules:
                            modules[safe_dir_name] = []
                        modules[safe_dir_name].append((file_name, safe_file_name))
                    
                    # サブグラフでディレクトリ構造を表現
                    for dir_name, files in modules.items():
                        mermaid_text += f"  subgraph {dir_name}[{dir_name.replace('_', ' ')}]\n"
                        
                        # ディレクトリ内のモジュール
                        for original_name, safe_name in files:
                            mermaid_text += f"    {safe_name}[\"{original_name}\"]\n"
                        
                        mermaid_text += "  end\n"
                    
                    # ディレクトリ間の関係（単純な例として親子関係を示す）
                    if len(modules) > 1:
                        mermaid_text += "  %% ディレクトリ間の関係\n"
                        dirs = list(modules.keys())
                        for i in range(1, len(dirs)):
                            mermaid_text += f"  {dirs[0]}-->{dirs[i]}\n"
                    
                    # メイン関数等の特別な関係を追加（ある場合）
                    if hasattr(self, 'astroid_analyzer') and hasattr(self.astroid_analyzer, 'functions'):
                        # main関数を探す
                        main_functions = [f for f in self.astroid_analyzer.functions if f.get('name') == 'main']
                        if main_functions:
                            # main関数がどのファイルにあるか推測
                            for original_name, safe_name in sum(modules.values(), []):
                                mermaid_text += f"  {safe_name}:::mainModule\n"
                                break
                            
                            mermaid_text += "  classDef mainModule fill:#f96,stroke:#333,stroke-width:2px;\n"

            except Exception as e:
                # モジュール図生成中のエラーをキャッチして続行
                mermaid_text += f"  error[\"エラー: {str(e)}\"]\n"

            mermaid_text += "```\n"
            
            # マーメードタブに表示
            self.mermaid_text.delete(1.0, tk.END)
            self.mermaid_text.insert(tk.END, mermaid_text)
            
            # シンタックスハイライト適用
            if hasattr(self, 'mermaid_highlighter'):
                self.mermaid_highlighter.highlight()
            
            # 文字数更新
            current_tab_index = self.tab_control.index(self.tab_control.select())
            if current_tab_index == 3:  # マーメードタブ
                char_count = len(mermaid_text)
                self.char_count_label.config(text=_("ui.status.char_count_value", "文字数: {0}").format(char_count))
            
        except Exception as e:
            traceback.print_exc()
            self.mermaid_text.delete(1.0, tk.END)
            self.mermaid_text.insert(tk.END, f"マーメードダイアグラム生成中にエラーが発生しました: {str(e)}")

    def setup_language_selector(self):
        """言語切り替えボタンを設定"""
        # 言語ボタンフレームを作成（右上に配置）
        language_frame = ttk.Frame(self.toolbar_frame)
        language_frame.pack(side="right", padx=10)
        
        # 日本語ボタン
        self.jp_button = ttk.Button(
            language_frame, 
            text=_("ui.language.japanese", "日本語"), 
            width=8,
            command=lambda: self.change_language("ja")
        )
        self.jp_button.pack(side="left", padx=2)

        # 英語ボタン
        self.en_button = ttk.Button(
            language_frame, 
            text=_("ui.language.english", "English"), 
            width=8,
            command=lambda: self.change_language("en")
        )
        self.en_button.pack(side="left", padx=2)
        
        # 現在の言語に基づいてボタンの状態を更新
        self.update_language_buttons()

    def update_language_buttons(self):
        """現在の言語に基づいてボタンの状態を更新"""
        current_lang = self.i18n.get_current_language()
        
        # すべてのボタンを通常状態にリセット
        self.jp_button.state(["!disabled"])
        self.en_button.state(["!disabled"])
        
        # 現在の言語のボタンを無効化（選択状態を示す）
        if current_lang == "ja":
            self.jp_button.state(["disabled"])
        elif current_lang == "en":
            self.en_button.state(["disabled"])

    def change_language(self, lang_code):
        """言語を変更する"""
        if self.i18n.get_current_language() != lang_code:
            if self.i18n.set_language(lang_code):
                self.update_language_buttons()
                
                # 確認メッセージ（変更した言語で表示）
                messagebox.showinfo(
                    _("language.changed_title", "言語変更"),
                    _("language.changed_message", "言語を変更しました。一部の変更はアプリケーションの再起動後に適用されます。")
                )
                
                # 即時更新可能なUI要素を更新
                self.update_ui_texts()

    def on_language_change(self, event=None):
        """言語変更時の処理"""
        selected_language = self.language_var.get()
        if self.i18n.set_language(selected_language):
            messagebox.showinfo(
                _("language.restart_title", "再起動が必要"),
                _("language.restart_message", "言語設定を完全に適用するには、アプリケーションの再起動が必要です。")
            )
            # 一部のUIテキストを即時更新できる場合は、ここでそれを行います
            self.update_ui_texts()
            
    def update_ui_texts(self):
        """UIテキストを現在の言語に更新"""
        # タイトル更新
        self.root.title(_("app.title", "コード解析ツール"))
        
        # タブ名などの更新
        if hasattr(self, 'notebook') and self.notebook:
            for i, tab_name in enumerate(["project", "code", "analysis", "json", "prompt"]):
                self.notebook.tab(i, text=_("tabs." + tab_name, self.notebook.tab(i, "text")))
        
        # ボタンテキスト更新
        if hasattr(self, 'analyze_button'):
            self.analyze_button.config(text=_("buttons.analyze", "解析"))
        if hasattr(self, 'copy_button'):
            self.copy_button.config(text=_("buttons.copy", "コピー"))
        if hasattr(self, 'clear_button'):
            self.clear_button.config(text=_("buttons.clear", "クリア"))
        
        # 再分析ボタン更新（追加）
        if hasattr(self, 'reanalyze_text_label'):
            self.reanalyze_text_label.config(text=_("buttons.reanalyze", "再分析"))
        
        # ステータスバー更新
        if hasattr(self, 'file_status'):
            current_text = self.file_status.cget("text")
            if current_text.strip() == "":
                self.file_status.config(text=_("status.ready", "準備完了"))
        
        # チェックボックスとラベル更新
        for widget in self.root.winfo_children():
            self._update_widget_texts(widget)
        
        # メニュー更新（オプション）
        if hasattr(self, 'menu'):
            self._update_menu_texts()

    def _update_widget_texts(self, parent):
        """ウィジェット内のテキストを再帰的に更新"""
        for widget in parent.winfo_children():
            if isinstance(widget, ttk.Checkbutton) or isinstance(widget, tk.Checkbutton):
                # チェックボックスのテキスト更新
                text = widget.cget("text")
                if text:
                    widget_name = widget.winfo_name()
                    widget.config(text=_(f"widget.{widget_name}", text))
            elif isinstance(widget, ttk.Label) or isinstance(widget, tk.Label):
                # ラベルのテキスト更新
                text = widget.cget("text")
                if text and not text.startswith(("http://", "https://", "/", "C:", "D:")):
                    widget_name = widget.winfo_name()
                    widget.config(text=_(f"widget.{widget_name}", text))
            
            # 子ウィジェットも処理
            if widget.winfo_children():
                self._update_widget_texts(widget)

    def _update_menu_texts(self):
        """メニューテキストを更新"""
        if not hasattr(self, 'menu'):
            return
            
        menu_items = {
            "file": ["open", "save", "exit"],
            "edit": ["copy", "paste", "select_all"],
            "tools": ["analyze", "settings", "reanalyze"],
            "help": ["about", "documentation"]
        }
        
        for menu_name, items in menu_items.items():
            if hasattr(self.menu, menu_name):
                menu_obj = getattr(self.menu, menu_name)
                menu_obj.entryconfig(0, label=_(f"menu.{menu_name}", menu_name.capitalize()))
                
                for i, item in enumerate(items):
                    try:
                        current_label = menu_obj.entrycget(i, "label")
                        menu_obj.entryconfig(i, label=_(f"menu.{menu_name}.{item}", current_label))
                    except Exception:
                        pass  # エントリが存在しない場合はスキップ
                        
    def setup_custom_buttons(self):
        """カスタムボタンをセットアップ（PNG画像を使用）"""
        # アイコンディレクトリのパスを定義
        self.icon_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icon")
        
        # 再分析ボタン
        reanalyze_btn_frame = ttk.Frame(self.toolbar_frame)
        reanalyze_btn_frame.pack(side="left", padx=5)

        # アイコン画像
        with Image.open(os.path.join(self.icon_dir, "refresh.png")) as reanalyze_icon:
            reanalyze_icon_image = ImageTk.PhotoImage(reanalyze_icon.resize((24, 24)))

        # アイコンラベル
        reanalyze_icon_label = tk.Label(reanalyze_btn_frame, image=reanalyze_icon_image, bg="#f0f0f0")
        reanalyze_icon_label.image = reanalyze_icon_image  # 参照を保持
        reanalyze_icon_label.pack(side="left")

        # テキストラベル
        self.reanalyze_text_label = tk.Label(reanalyze_btn_frame, 
                                          text=_("buttons.reanalyze", "再分析"), 
                                          bg="#f0f0f0",
                                          name="reanalyze_label")
        self.reanalyze_text_label.pack(side="left", padx=2)

        # ボタン機能
        reanalyze_btn_frame.bind("<Button-1>", lambda e: self.reanalyze_project())
        reanalyze_icon_label.bind("<Button-1>", lambda e: self.reanalyze_project())
        self.reanalyze_text_label.bind("<Button-1>", lambda e: self.reanalyze_project())

        # ホバーエフェクト
        enter_func = self.create_enter_function(reanalyze_btn_frame, "#e0e0e0")
        leave_func = self.create_leave_function(reanalyze_btn_frame, "#f0f0f0")

        reanalyze_btn_frame.bind("<Enter>", enter_func)
        reanalyze_btn_frame.bind("<Leave>", leave_func)
        reanalyze_icon_label.bind("<Enter>", enter_func)
        reanalyze_icon_label.bind("<Leave>", leave_func)
        self.reanalyze_text_label.bind("<Enter>", enter_func)
        self.reanalyze_text_label.bind("<Leave>", leave_func)

        # 画像パスのベースディレクトリを相対パスで指定
        icon_dir = os.path.join(os.path.dirname(__file__), "icon")
        
        # ボタン設定
        button_configs = [
            {'icon': "folder.png", 'label': "Import", 'command': self.import_directory},
            {'icon': "analyze.png", 'label': "Analysis", 'command': self.analyze_selected},
            {'icon': "copy.png", 'label': "Copy", 'command': self.copy_to_clipboard},
            {'icon': "cleaner.png", 'label': "Clear", 'command': self.clear_workspace},
            {'icon': "run.png", 'label': "Run", 'command': self.run_python_file}
        ]
        
        # ボタンリストを保持
        self.custom_buttons = []
        
        # 画像オブジェクトへの参照を保持（ガベージコレクションを防ぐため）
        self.button_images = []
        
        # ツールバーにカスタムボタンを作成
        for config in button_configs:
            # アイコン画像のパス
            icon_path = os.path.join(icon_dir, config['icon'])
            
            # 画像をロード
            try:
                with Image.open(icon_path) as icon_image:
                    # サイズを24x24ピクセルに変更
                    resized_icon = icon_image.resize((24, 24), Image.LANCZOS)
                    icon_photo = ImageTk.PhotoImage(resized_icon)
                    # 画像への参照を保持
                    self.button_images.append(icon_photo)
            except Exception as e:
                print(f"アイコン画像の読み込みエラー: {e}")
                # エラー時はデフォルトテキストを設定
                icon_photo = None
            
            # フレームを作成
            btn_frame = ttk.Frame(self.toolbar_frame)
            btn_frame.pack(side="left", padx=5)
            
            # アイコンラベル
            if icon_photo:
                icon_label = tk.Label(btn_frame, image=icon_photo, background="#f0f0f0")
            else:
                # フォールバックとして文字を表示
                icon_label = tk.Label(btn_frame, text="■", font=('Helvetica', 14), background="#f0f0f0")
            icon_label.pack(side="left")
            
            # テキストラベル
            text_label = tk.Label(btn_frame, text=" " + config['label'], 
                                  font=('Helvetica', 10), background="#f0f0f0")
            text_label.pack(side="left")
            
            # クリックイベント
            cmd = config['command']
            icon_label.bind("<Button-1>", lambda e, cmd=cmd: cmd())
            text_label.bind("<Button-1>", lambda e, cmd=cmd: cmd())
            
            # ホバー効果用の関数 - ローカル関数を削除し、クラスメソッドを使用するように変更
            enter_func = self.create_enter_function(btn_frame, "#e0e0e0")
            leave_func = self.create_leave_function(btn_frame, "#f0f0f0")
            
            btn_frame.bind("<Enter>", enter_func)
            btn_frame.bind("<Leave>", leave_func)
            icon_label.bind("<Enter>", enter_func)
            icon_label.bind("<Leave>", leave_func)
            text_label.bind("<Enter>", enter_func)
            text_label.bind("<Leave>", leave_func)
            
            # ボタンリストに追加
            self.custom_buttons.append({
                'frame': btn_frame,
                'icon': icon_label,
                'text': text_label,
                'command': cmd
            })

    def create_enter_function(self, frame, color):
        """ホバー時の色変更関数を生成"""
        return lambda e: [w.configure(background=color) for w in frame.winfo_children()]

    def create_leave_function(self, frame, color):
        """ホバー終了時の色変更関数を生成"""
        return lambda e: [w.configure(background=color) for w in frame.winfo_children()]

    def create_tab_selection_panel(self):
        """タブ選択パネルを作成"""
        tab_selection_frame = ttk.Frame(self.right_frame)

        # タイトルラベル
        title_label = ttk.Label(tab_selection_frame, text=_("ui.tab_selection.label", "コピーするタブ:"))
        title_label.pack(side="left", padx=5)
        
        # チェックボックスの変数と保存場所
        self.tab_checkboxes = {}
        self.tab_checkbox_vars = {}
        
        # 設定から前回のタブ選択状態を取得
        saved_tab_selection = self.config_manager.get_tab_selection()
        
        # タブ名の翻訳キーとデフォルト値のマッピング - プロンプトタブを削除
        tab_name_keys = [
            ("ui.tabs.analysis", "解析結果"), 
            ("ui.tabs.extended", "拡張解析"), 
            ("ui.tabs.json", "JSON出力"),
            ("ui.tabs.mermaid", "マーメード")
            # プロンプト入力タブを削除
        ]

        # 指定されたタブの並びに合わせてチェックボックスを追加
        for key, default_name in tab_name_keys:
            tab_name = _(key, default_name)
            # 保存された選択状態を使用、なければデフォルトでFalse
            is_selected = saved_tab_selection.get(tab_name, False)
            var = tk.BooleanVar(value=is_selected)
            self.tab_checkbox_vars[tab_name] = var
            
            # チェックボックスを作成
            checkbox = ttk.Checkbutton(tab_selection_frame, text=tab_name, variable=var, 
                                      command=lambda tn=tab_name: self.on_tab_checkbox_changed(tn))
            checkbox.pack(side="left", padx=5)
            self.tab_checkboxes[tab_name] = checkbox
        
        return tab_selection_frame

    def on_tab_checkbox_changed(self, tab_name):
        """タブ選択チェックボックスが変更されたときの処理"""
        # 設定に保存
        self.save_tab_selection_state()
        
        # 文字数表示を更新
        self.update_char_count()

    def save_tab_selection_state(self):
        """タブ選択状態を保存"""
        # 現在の選択状態を取得
        current_selection = {}
        for tab_name, var in self.tab_checkbox_vars.items():
            current_selection[tab_name] = var.get()
        
        # 設定に保存
        self.config_manager.set_tab_selection(current_selection)
        
        # 文字数表示を更新
        self.update_char_count()

    def copy_selected_tabs(self):
        """選択されたタブの内容をクリップボードにコピー"""
        # 指定されたタブの並びに合わせる
        tab_names = ["解析結果", "拡張解析", "プロンプト入力"]
        selected_content = []
        
        # 各タブのチェック状態を確認
        for tab_name in tab_names:
            if self.tab_checkbox_vars[tab_name].get():
                content = self.get_tab_content(tab_name)
                if content:
                    selected_content.append(f"## {tab_name}\n{content}\n\n")
        
        if selected_content:
            # コンテンツを結合してクリップボードにコピー
            
            clipboard_text = "".join(selected_content)
            pyperclip.copy(clipboard_text)
            messagebox.showinfo(_("ui.dialogs.info_title", "情報"), _("ui.messages.copy_success", "選択したタブの内容をクリップボードにコピーしました。"))
        else:
            messagebox.showinfo("情報", "コピーするタブが選択されていません。")
    
    def get_tab_content(self, tab_name):
        """タブ名に対応する内容を取得"""
        if tab_name == _("ui.tabs.analysis", "解析結果"):
            return self.result_text.get(1.0, tk.END).strip()
        elif tab_name == _("ui.tabs.extended", "拡張解析"):
            return self.extended_text.get(1.0, tk.END).strip()
        elif tab_name == _("ui.tabs.json", "JSON出力"):
            return self.json_text.get(1.0, tk.END).strip()
        elif tab_name == _("ui.tabs.mermaid", "マーメード"):
            return self.mermaid_text.get(1.0, tk.END).strip()
        elif tab_name == _("ui.tabs.prompt", "プロンプト入力"):
            return self.prompt_ui.prompt_text.get(1.0, tk.END).strip()
        return ""
    
    def toggle_exe_folder_skip(self):
        """EXEを含むフォルダのスキップ設定を変更"""
        skip_exe = self.skip_exe_folders.get()
        
        # ディレクトリツリービューの設定を更新
        if hasattr(self.dir_tree_view, 'skip_exe_folders'):
            self.dir_tree_view.skip_exe_folders = skip_exe
            
            # 現在のディレクトリが読み込まれている場合は再読み込み
            if self.current_dir:
                # 確認ダイアログを表示
                if messagebox.askyesno(_("ui.dialogs.confirm_title", "確認"), _("ui.messages.reload_directory", "設定を適用するには、現在のディレクトリを再読み込みする必要があります。続行しますか？")):
                    self.dir_tree_view.load_directory(self.current_dir)
    
    def setup_text_editor_shortcuts(self):
        """テキストエディタのショートカットとコンテキストメニューを設定"""
        # 各テキストエリアにショートカットを設定
        self.setup_editor_shortcuts(self.result_text)
        self.setup_editor_shortcuts(self.extended_text)
        self.setup_editor_shortcuts(self.json_text)
        self.setup_editor_shortcuts(self.mermaid_text)  # マーメードテキストエリアを追加
        
        # プロンプトテキストエリアのショートカット設定（別途実装）
        # if hasattr(self.prompt_ui, 'prompt_text'):
            # self.setup_editor_shortcuts(self.prompt_ui.prompt_text)    

    def setup_editor_shortcuts(self, text_widget):
        """テキストウィジェットにショートカットとコンテキストメニューを設定"""
        # ショートカットキーのバインド
        text_widget.bind("<Control-a>", lambda event: self.select_all(event, text_widget))
        text_widget.bind("<Control-c>", lambda event: self.copy_text(event, text_widget))
        
        # コンテキストメニュー作成
        context_menu = tk.Menu(text_widget, tearoff=0)
        context_menu.add_command(label=_("ui.context_menu.copy", "コピー"), command=lambda: self.copy_text(None, text_widget), accelerator="Ctrl+C")
        context_menu.add_separator()
        context_menu.add_command(label=_("ui.context_menu.select_all", "すべて選択"), command=lambda: self.select_all(None, text_widget), accelerator="Ctrl+A")
        
        # 右クリックでコンテキストメニュー表示
        if sys.platform == 'darwin':  # macOS
            text_widget.bind("<Button-2>", lambda event: self.show_context_menu(event, context_menu))
        else:  # Windows/Linux
            text_widget.bind("<Button-3>", lambda event: self.show_context_menu(event, context_menu))
    
    def show_context_menu(self, event, menu):
        """コンテキストメニューを表示"""
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
        return "break"  # イベントの伝播を停止
    
    def select_all(self, event, text_widget):
        """テキストをすべて選択"""
        text_widget.tag_add(tk.SEL, "1.0", tk.END)
        text_widget.mark_set(tk.INSERT, tk.END)
        text_widget.see(tk.INSERT)
        return "break"  # イベントの伝播を停止
    
    def copy_text(self, event, text_widget):
        """選択テキストをコピー"""
        try:
            selection = text_widget.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.root.clipboard_clear()
            self.root.clipboard_append(selection)
        except tk.TclError:
            pass  # 選択されていない場合は何もしない
        return "break"  # イベントの伝播を停止

    def on_tab_changed(self, event=None):
        """タブが切り替わったときに文字数を更新する"""
        try:
            # 現在のタブインデックスを取得
            current_tab_index = self.tab_control.index(self.tab_control.select())
            
            # タブに応じてテキストウィジェットを選択
            if current_tab_index == 0:  # 解析結果タブ
                text_widget = self.result_text
            elif current_tab_index == 1:  # 拡張解析タブ
                text_widget = self.extended_text
            elif current_tab_index == 2:  # JSONタブ
                text_widget = self.json_text
            elif current_tab_index == 3:  # マーメードタブ
                text_widget = self.mermaid_text
            elif current_tab_index == 4:  # プロンプト入力タブ
                # プロンプトタブの特別処理
                if hasattr(self, 'prompt_ui') and hasattr(self.prompt_ui, 'prompt_text'):
                    text_widget = self.prompt_ui.prompt_text
                else:
                    self.char_count_label.config(text=_("ui.status.char_count_value", "文字数: {0}").format(0))
                    return
            
            # 選択されているタブがプロンプト以外の場合は通常処理
            text_content = text_widget.get(1.0, tk.END)
            char_count = len(text_content) - 1  # 最後の改行を除く
            
            # 文字数更新
            self.char_count_label.config(text=_("ui.status.char_count_value", "文字数: {0}").format(char_count))
            
            # プロンプトタブの場合は専用の文字数表示も更新
            if current_tab_index == 4 and hasattr(self.prompt_ui, 'prompt_char_count_var'):
                self.prompt_ui.prompt_char_count_var.set(_("ui.prompt.char_count", "文字数: {0}").format(char_count))
                
        except Exception as e:
            print(f"タブ切り替え時のエラー: {e}")
            traceback.print_exc()
            # エラー発生時は文字数表示をリセット
            self.char_count_label.config(text=_("ui.status.char_count_value", "文字数: {0}").format(0))

    def update_char_count(self, event=None):
        """選択されたタブに基づいて文字数を更新する"""
        try:
            # 選択されたタブを取得
            selected_tabs = []
            for tab_name, var in self.tab_checkbox_vars.items():
                if var.get():
                    selected_tabs.append(tab_name)
            
            # 選択されたタブがない場合は、現在のタブの文字数のみ表示
            if not selected_tabs:
                current_tab_index = self.tab_control.index(self.tab_control.select())
                self.on_tab_changed()  # 現在のタブの文字数を更新
                return
            
            # 選択されたタブのコンテンツを結合したときの文字数を計算
            total_chars = 0
            for tab_name in selected_tabs:
                content = self.get_tab_content(tab_name)
                total_chars += len(content)
                
                # 複数タブ選択時は見出し追加分も計算
                if len(selected_tabs) > 1:
                    total_chars += len(f"## {tab_name}\n\n\n")
            
            # 文字数表示を更新
            self.char_count_label.config(text=_("ui.status.selected_char_count", "選択タブの文字数: {0}").format(total_chars))
            
        except Exception as e:
            print(f"文字数更新時のエラー: {e}")
            traceback.print_exc()
            # エラー発生時は文字数表示をリセット
            self.char_count_label.config(text=_("ui.status.char_count_value", "文字数: {0}").format(0))

    def toggle_display_options(self):
        """表示オプションの切り替え処理"""
        # アナライザーの設定を更新
        self.analyzer.include_imports = self.show_imports.get()
        self.analyzer.include_docstrings = self.show_docstrings.get()
        
        # 現在の選択に応じて再解析を実行
        if self.selected_file and os.path.isfile(self.selected_file):
            # 単一ファイルモード
            self.analyze_file(self.selected_file)
        elif self.current_dir:
            # ディレクトリモード
            self.analyze_selected()
    
    def load_last_session(self):
        """前回のセッション情報を読み込む"""
        # 各タブをクリア (プロンプト以外)
        self.result_text.delete(1.0, tk.END)
        self.extended_text.delete(1.0, tk.END)
        self.json_text.delete(1.0, tk.END)
        self.mermaid_text.delete(1.0, tk.END)
        
        # 前回のディレクトリとファイルを取得
        last_file = self.config_manager.get_last_file()
        last_directory = self.config_manager.get_last_directory()
        
        # 前回のファイルが存在する場合はそれを開く
        if last_file and os.path.exists(last_file):
            self.selected_file = last_file
            dir_path = os.path.dirname(last_file)
            self.current_dir = dir_path
            self.file_status.config(text=_("ui.status.file", "ファイル: {0}").format(os.path.basename(last_file)))
            
            # ディレクトリツリーを読み込み
            self.dir_tree_view.load_directory(dir_path)
            
            # ファイル内容を解析
            self.analyze_file(last_file)
        # 前回のディレクトリが存在する場合はそれを開く
        elif last_directory and os.path.exists(last_directory):
            self.import_directory_path(last_directory)
    
    def on_window_resize(self, event):
        """ウィンドウサイズ変更時のイベントハンドラ"""
        # イベントがルートウィンドウからのものかチェック
        if event.widget == self.root:
            # 一定間隔でサイズ保存（タイマーをリセット）
            if hasattr(self, '_resize_timer'):
                self.root.after_cancel(self._resize_timer)
            self._resize_timer = self.root.after(500, self.save_window_size)
    
    def save_window_size(self):
        """現在のウィンドウサイズを設定に保存する"""
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        if width > 100 and height > 100:  # 最小サイズ以上の場合のみ保存
            self.config_manager.set_window_size(width, height)
    
    def on_closing(self):
        # プロンプト保存確認 - 属性確認が必要
        if hasattr(self, 'prompt_ui') and hasattr(self.prompt_ui, 'prompt_modified') and self.prompt_ui.prompt_modified:
            response = messagebox.askyesnocancel(_("ui.dialogs.confirm_title", "確認"), _("ui.messages.save_changes", "未保存の変更があります。\n保存しますか？"))
            if response is None:
                return
            elif response:
                if not self.prompt_ui.save_current_prompt():
                    return
                else:
                    self.prompt_ui.prompt_modified = False

        # ウィンドウサイズ保存
        self.save_window_size()

        # タブ選択保存
        if hasattr(self, 'save_tab_selection_state'):
            self.save_tab_selection_state()

        # ディレクトリ保存（ファイルがあれば優先的にそこから取得）
        if hasattr(self, 'selected_file') and self.selected_file and os.path.exists(self.selected_file):
            self.config_manager.set_last_file(self.selected_file)
            # ファイルからディレクトリを導出
            self.config_manager.set_last_directory(os.path.dirname(self.selected_file))
        elif hasattr(self, 'current_dir') and self.current_dir and os.path.exists(self.current_dir):
            self.config_manager.set_last_directory(self.current_dir)

        # データベース接続をクローズ
        if hasattr(self, 'code_database'):
            try:
                self.code_database.close()
            except Exception as e:
                print(f"データベース接続クローズエラー: {str(e)}")

        # アプリ終了
        self.root.destroy()

    def center_window(self):
        """ウィンドウを画面の中央に配置する"""
        self.root.update_idletasks()
        
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        window_width = self.root.winfo_width()
        window_height = self.root.winfo_height()
        
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.root.geometry(f"+{x}+{y}")
    
    def import_directory(self):
        """ディレクトリを選択してツリービューに表示"""
        dir_path = filedialog.askdirectory(title="Pythonファイルを含むディレクトリを選択")
        
        if dir_path:
            self.import_directory_path(dir_path)
    
    def import_directory_path(self, dir_path):
        """指定されたパスのディレクトリを読み込む"""
        # 選択されたファイルをリセット
        self.selected_file = None
        self.current_dir = dir_path
        self.dir_tree_view.load_directory(dir_path)
        self.file_status.config(text=_("ui.status.directory", "ディレクトリ: {0}").format(os.path.basename(dir_path)))
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, _("ui.messages.directory_loaded", "ディレクトリ '{0}' を読み込みました。").format(dir_path) + "\n" +
                              _("ui.messages.select_file", "解析したいPythonファイルを選択して、[解析]ボタンをクリックしてください。") + "\n\n" +
                              _("ui.messages.hint", "ヒント: Ctrl+クリックでファイルやディレクトリを解析から除外できます。\nダブルクリックでファイルを選択できます。"))
    
    def on_file_selected(self, file_path):
        # 現在のファイルパスを保存
        self.selected_file = file_path
        self.config_manager.set_last_file(file_path)
        
        # ファイル拡張子の取得
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == '.dart':
            # Dartファイルを処理
            self.file_status.config(text=f"Dartファイル: {os.path.basename(file_path)}")
            try:
                # FlutterAnalyzerを取得
                analyzer = self.registry.get_analyzer("flutter")
                if analyzer:
                    # ファイルを解析
                    analyzer.analyze_file(file_path)
                    
                    # 解析結果を表示
                    flutter_data = {
                        "language": "Flutter/Dart",
                        "components": analyzer.components if hasattr(analyzer, "components") else {},
                        "connections": analyzer.find_connections(self.astroid_analyzer)
                    }
                    
                    # UIに表示（自動でFlutterタブを選択）
                    if hasattr(self, 'language_connection_view'):
                        self.language_connection_view.update_data(flutter_data)
                        
                        # Flutterタブを選択
                        for i in range(self.tab_control.index("end")):
                            tab_text = self.tab_control.tab(i, "text")
                            if "Flutter" in tab_text:
                                self.tab_control.select(i)
                                break
            except Exception as e:
                traceback.print_exc()
                messagebox.showerror("エラー", f"Dartファイルの解析エラー: {str(e)}")
        else:
            # 通常のPythonファイル解析（既存コード）
            self.analyze_file(file_path)

    def on_dir_selected(self, dir_path):
        """ツリービューでディレクトリが選択されたときのコールバック"""
        # 個別ファイル選択をクリアしてディレクトリ解析モードに切り替え
        self.selected_file = None
        self.current_dir = dir_path
        
        # 設定に保存
        self.config_manager.set_last_directory(dir_path)
        
        # ステータス更新
        self.file_status.config(text=_("ui.status.directory", "ディレクトリ: {0}").format(os.path.basename(dir_path)))
        
        # 解析結果タブに切り替え
        self.tab_control.select(0)  # 最初のタブ（解析結果タブ）を選択
        
        # ディレクトリ内のファイルを解析
        self.analyze_directory(dir_path)
        
        # プロンプトテンプレートを更新
        self.update_prompt_template(os.path.basename(dir_path))
    
    def update_prompt_template(self, name):
        """選択されたファイル/ディレクトリ名に基づいてプロンプトテンプレートを更新"""
        # デバッグ情報を追加
        print(f"プロンプトテンプレートの更新が呼び出されました。名前: {name}")
        print(f"現在のモード: {'ファイルモード' if self.selected_file else 'ディレクトリモード'}")
        
        # プロンプトUIオブジェクトの存在確認
        if not hasattr(self, 'prompt_ui') or not hasattr(self.prompt_ui, 'prompt_text'):
            return
        
        # 現在のプロンプトテキストを取得
        current_prompt = self.prompt_ui.prompt_text.get(1.0, tk.END)
        
        # 更新フラグ（変更があったかどうか）
        updated = False
        
        # 解析結果とJSON出力を取得
        analysis_result = self.result_text.get(1.0, tk.END) if hasattr(self, 'result_text') else ""
        json_output = self.json_text.get(1.0, tk.END) if hasattr(self, 'json_text') else ""
        
        # 置換処理を開始（複数のプレースホルダーを処理）
        updated_prompt = current_prompt
        
        # ファイル/ディレクトリ名の置換
        if "[ファイル/ディレクトリ名]" in updated_prompt:
            updated_prompt = updated_prompt.replace("[ファイル/ディレクトリ名]", name)
            updated = True
        elif "# main.pyの解析プロンプト" in updated_prompt and not self.selected_file:
            # ディレクトリモードなのに main.py が入っている場合は修正
            updated_prompt = updated_prompt.replace("main.py", name)
            updated = True
        
        # 解析結果の置換
        if "[解析結果]" in updated_prompt and analysis_result:
            updated_prompt = updated_prompt.replace("[解析結果]", analysis_result)
            updated = True
        
        # JSON出力の置換
        if "[json出力]" in updated_prompt and json_output:
            updated_prompt = updated_prompt.replace("[json出力]", json_output)
            updated = True
        
        # 変更があった場合のみテキストを更新
        if updated:
            # テキストを更新
            self.prompt_text.delete(1.0, tk.END)
            self.prompt_text.insert(tk.END, updated_prompt)
            
            # 文字数も更新
            char_count = len(updated_prompt) - 1  # 最後の改行文字を除く
            
            # 文字数表示を更新（プロンプトUIの専用変数と全体の文字数ラベル）
            if hasattr(self, 'prompt_char_count_var'):
                self.prompt_char_count_var.set(f"文字数: {char_count}")
            
            # 現在表示されているタブがプロンプト入力タブの場合のみメインの文字数ラベルも更新
            current_tab_index = self.tab_control.index(self.tab_control.select())
            if current_tab_index == 3:  # プロンプト入力タブ
                self.char_count_label.config(text=_("ui.status.char_count_value", "文字数: {0}").format(char_count))
    
    def analyze_directory(self, dir_path):
        """指定されたディレクトリ内のPythonファイルを解析"""
        try:
            # ディレクトリ内のファイルを取得
            python_files = []
            
            # ツリービューから解析対象ファイルを取得
            all_files = self.dir_tree_view.get_included_files(include_python_only=True)
            
            # Pythonファイルのみを保存
            for file_path in all_files:
                ext = os.path.splitext(file_path)[1].lower()
                if ext == '.py':
                    python_files.append(file_path)
            
            # Pythonファイルの解析
            if python_files:
                self.perform_extended_analysis(python_files)
                return True
            else:
                messagebox.showinfo(_("info_title", "情報"), 
                                  _("info_no_python_files", "解析対象のPythonファイルがありません。"))
                return False
                
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("エラー", f"ディレクトリ解析エラー: {str(e)}")
            return False

    def get_directory_structure(self, python_files):
        """ファイルリストからディレクトリ構造を生成する"""
        # ファイルのディレクトリを取得する
        if not python_files:
            return "ファイルがありません"
        
        # 共通のルートディレクトリを見つける
        file_dirs = [os.path.dirname(f) for f in python_files]
        common_root = os.path.commonpath(file_dirs) if file_dirs else ""
        
        # ディレクトリツリーを構築
        tree = {}
        for file_path in python_files:
            # ルートからの相対パスを取得
            rel_path = os.path.relpath(file_path, common_root)
            parts = rel_path.split(os.sep)
            
            # ツリー構造に追加
            current = tree
            for i, part in enumerate(parts):
                if i == len(parts) - 1:  # ファイル
                    if "_files" not in current:
                        current["_files"] = []
                    current["_files"].append(part)
                else:  # ディレクトリ
                    if part not in current:
                        current[part] = {}
                    current = current[part]
        
        # ツリー構造を文字列に変換
        result = []
        
        def print_tree(node, prefix="", is_last=True, indent=""):
            # ディレクトリ内のファイルとサブディレクトリを取得
            dirs = sorted([k for k in node.keys() if k != "_files"])
            files = sorted(node.get("_files", []))
            
            # 現在のディレクトリのファイルを出力
            for i, f in enumerate(files):
                is_last_file = (i == len(files) - 1) and not dirs
                result.append(f"{indent}{'└── ' if is_last_file else '├── '}{f}")
            
            # サブディレクトリを出力
            for i, d in enumerate(dirs):
                is_last_dir = (i == len(dirs) - 1)
                result.append(f"{indent}{'└── ' if is_last_dir else '├── '}{d}/")
                # 次のレベルのインデント
                next_indent = indent + ("    " if is_last_dir else "│   ")
                print_tree(node[d], prefix + d + "/", is_last_dir, next_indent)
        
        # ルートディレクトリ名を出力
        root_name = os.path.basename(common_root) or "root"
        result.append(f"{root_name}/")
        # ルート以下のツリーを出力
        print_tree(tree, indent="")
        
        return "\n".join(result)
    
    def analyze_selected(self):
        """選択されたファイルまたはディレクトリを解析"""
        # ファイルモードかディレクトリモードかを明示的に確認
        file_mode = self.selected_file and os.path.isfile(self.selected_file)
        
        # ファイルモードの場合は、そのファイルだけを解析
        if file_mode:
            self.analyze_file(self.selected_file)
            return
        
        # ディレクトリモードの場合は、含まれるPythonファイルのみを解析
        included_files = self.dir_tree_view.get_included_files(include_python_only=True)
        
        if not included_files:
            messagebox.showinfo("情報", "解析対象のPythonファイルがありません。\n"
                               "ディレクトリを選択し、Pythonファイルが含まれていることを確認してください。\n"
                               "または、Pythonファイルがすべて「除外」状態になっていないか確認してください。")
            return
        
        # 解析実行
        result, char_count = self.analyzer.analyze_files(included_files)
        
        # 結果表示
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, result)
        self.result_highlighter.highlight()
        self.char_count_label.config(text=_("ui.status.char_count_value", "文字数: {0}").format(char_count))
        
        # ステータス更新
        self.file_status.config(text=f"{len(included_files)} 個のPythonファイルを解析しました")
        
        # 拡張解析を実行
        self.perform_extended_analysis(included_files)

    def copy_to_clipboard(self):
        """解析結果とプロンプトをクリップボードにコピーする（選択されたタブに基づく）"""
        # 選択されたタブのチェック状態を取得
        selected_tabs = []
        for tab_name, var in self.tab_checkbox_vars.items():
            if var.get():
                selected_tabs.append(tab_name)
        
        # 選択されたタブがない場合は、現在表示されているタブを選択
        if not selected_tabs:
            current_tab_index = self.tab_control.index(self.tab_control.select())
            tab_indices = {
                0: _("ui.tabs.analysis", "解析結果"),
                1: _("ui.tabs.extended", "拡張解析"),
                2: _("ui.tabs.json", "JSON出力"),
                3: _("ui.tabs.mermaid", "マーメード"),
                4: _("ui.tabs.prompt", "プロンプト入力")
            }
            if current_tab_index in tab_indices:
                selected_tabs.append(tab_indices[current_tab_index])
        
        # 選択されたタブの内容を結合
        combined_content = []
        for tab_name in selected_tabs:
            content = self.get_tab_content(tab_name)
            if content:
                if len(selected_tabs) > 1:  # 複数のタブが選択されている場合のみ見出しを追加
                    combined_content.append(f"## {tab_name}\n{content}\n\n")
                else:
                    combined_content.append(content)
        
        if combined_content:
            # コンテンツを結合してクリップボードにコピー
            clipboard_text = "".join(combined_content)
            
            # pyperclipを使用してクリップボードにコピー (Tkinterのクリップボードより信頼性が高い)
            try:
                pyperclip.copy(clipboard_text)
                messagebox.showinfo(
                    _("ui.dialogs.info_title", "情報"), 
                    _("ui.messages.copy_success", "選択したタブの内容をクリップボードにコピーしました。")
                )
            except Exception as e:
                # 代替手段としてTkinterのクリップボードを使用
                self.root.clipboard_clear()
                self.root.clipboard_append(clipboard_text)
                messagebox.showinfo(
                    _("ui.dialogs.info_title", "情報"), 
                    _("ui.messages.copy_success", "選択したタブの内容をクリップボードにコピーしました。")
                )
        else:
            messagebox.showinfo(
                _("ui.dialogs.info_title", "情報"), 
                _("ui.messages.no_tabs_selected", "コピーするタブが選択されていません。")
            )    

    def analyze_file(self, file_path):
        """単一のファイルを解析"""
        try:
            # 通常の解析（UI表示用）
            result, char_count = self.analyzer.analyze_file(file_path)
            
            # ファイル文字数を取得して表示に組み込む
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
                file_char_count = len(code)
            
            # 文字数表示を追加
            file_name = os.path.basename(file_path)
            dir_path = os.path.dirname(file_path)
            formatted_result = f"## ディレクトリ: {dir_path}\n### ファイル: {file_name}\n"
            formatted_result += f"文字数: {file_char_count:,}\n\n"
            formatted_result += result
            
            # 結果表示
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, formatted_result)
            self.result_highlighter.highlight()
            
            # コード抽出モジュールを使用してデータベースに保存
            from utils.code_extractor import CodeExtractor
            extractor = CodeExtractor(self.code_database)
            
            try:
                # コード抽出と保存を実行
                snippet_count = extractor.extract_from_file(file_path)
                self.current_file = file_path  # 現在のファイルパスを保存
                
                # ステータス表示を更新
                self.file_status.config(
                    text=_("ui.status.file_extracted", "ファイル: {0}（{1}個のスニペットを抽出）")
                    .format(os.path.basename(file_path), snippet_count)
                )
            except Exception as ex:
                print(f"コード抽出エラー: {str(ex)}")
                traceback.print_exc()
                # エラーは表示するが処理は続行
            
            # 現在表示されているタブが解析結果タブの場合のみ文字数を更新
            current_tab_index = self.tab_control.index(self.tab_control.select())
            if current_tab_index == 0:
                self.char_count_label.config(text=_("ui.status.char_count_value", "文字数: {0}").format(file_char_count))
            
            # 拡張解析を実行
            self.perform_extended_analysis([file_path])
            
            # JSON出力を生成
            self.generate_json_output()
            
            # マーメードダイアグラムを生成
            self.generate_mermaid_output()
            
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror(
                _("ui.dialogs.error_title", "エラー"), 
                _("ui.messages.analysis_error", "ファイルの解析中にエラーが発生しました:\n{0}").format(str(e))
            )

    def load_code_snippets(self, file_path):
        """データベースからファイルのコードスニペットを読み込む"""
        try:
            snippets = self.code_database.get_snippets_by_file(file_path)
            return snippets
        except Exception as e:
            messagebox.showerror("データベースエラー", f"スニペット読み込みエラー: {str(e)}")
            return []

    def perform_extended_analysis(self, python_files):
        """astroidによる拡張解析を実行する"""
        try:
            import astroid
            
            if not python_files:
                self.extended_text.delete(1.0, tk.END)
                self.extended_text.insert(tk.END, "拡張解析対象のPythonファイルがありません。")
                return
                    
            # 解析結果を保存する辞書
            analysis_results = {}
            module_nodes = {}
            
            # プログレスウィンドウを表示
            progress_window = tk.Toplevel(self.root)
            progress_window.title("拡張解析中")
            progress_window.geometry("400x100")
            progress_window.transient(self.root)
                
            progress_label = ttk.Label(progress_window, text=f"ファイルを解析中... (0/{len(python_files)})")
            progress_label.pack(pady=10)
                
            progress_bar = ttk.Progressbar(progress_window, mode="determinate", maximum=100)
            progress_bar.pack(fill="x", padx=20)
                
            # ウィンドウを中央に配置
            progress_window.update_idletasks()
            x = self.root.winfo_rootx() + (self.root.winfo_width() - progress_window.winfo_width()) // 2
            y = self.root.winfo_rooty() + (self.root.winfo_height() - progress_window.winfo_height()) // 2
            progress_window.geometry(f"+{x}+{y}")
                
            # 統合解析レポート用の情報
            all_classes = []
            all_functions = []
            all_dependencies = {}
            all_inheritance = {}
            
            # ディレクトリ構造を取得
            directory_structure = self.get_directory_structure(python_files)
                
            # Step 1: 各ファイルを個別に解析する
            for i, file_path in enumerate(python_files):
                try:
                    # プログレス更新
                    progress_pct = (i / len(python_files)) * 100
                    progress_bar["value"] = progress_pct
                    progress_label.config(text=f"ファイルを解析中... ({i+1}/{len(python_files)}): {os.path.basename(file_path)}")
                    progress_window.update()
                    
                    # ファイルを読み込む（BOM除去対応）
                    with open(file_path, 'r', encoding='utf-8-sig') as file:
                        code = file.read()

                    # 有効なPythonコードかどうか事前チェック（日本語メモファイル等を除外）
                    try:
                        compile(code, file_path, 'exec')
                    except SyntaxError:
                        print(f"スキップ（構文エラー）: {file_path}")
                        continue

                    # ファイル文字数を取得
                    file_char_count = len(code)

                    # astroidでモジュールをパース
                    module = astroid.parse(code)
                    module_name = os.path.basename(file_path).replace('.py', '')
                    module_nodes[module_name] = module
                    
                    # ファイル個別の解析結果を取得
                    self.astroid_analyzer.reset()
                    file_result, _ = self.astroid_analyzer.analyze_code(code, os.path.basename(file_path))
                    
                    # 結果を蓄積
                    analysis_results[file_path] = {
                        'name': os.path.basename(file_path),
                        'classes': self.astroid_analyzer.classes.copy(),
                        'functions': self.astroid_analyzer.functions.copy(),
                        'dependencies': self.astroid_analyzer.dependencies.copy(),
                        'inheritance': self.astroid_analyzer.inheritance.copy(),
                        'char_count': file_char_count  # 文字数を追加
                    }
                    
                    # データベースにタイムスタンプを更新
                    self.code_database.update_file_timestamp(file_path)
                    
                    # 全体のリストに追加
                    all_classes.extend(self.astroid_analyzer.classes)
                    all_functions.extend(self.astroid_analyzer.functions)
                    all_dependencies.update(self.astroid_analyzer.dependencies)
                    all_inheritance.update(self.astroid_analyzer.inheritance)
                    
                except Exception as e:
                    print(f"ファイル {file_path} の解析中にエラー: {e}")
                    traceback.print_exc()
            
            # プログレスウィンドウを閉じる
            progress_window.destroy()
            
            # 依存関係をフィルタリング
            SKIP_DEPENDENCIES = {
                'print', 'len', 'str', 'int', 'float', 'list', 'dict', 'set', 'tuple',
                'open', 'range', 'enumerate', 'zip', 'map', 'filter',
                'os.path.join', 'os.path.exists', 'os.path.basename', 'os.path.dirname',
                'logging.info', 'logging.debug', 'logging.warning', 'logging.error'
            }
            
            # 依存関係をフィルタリング
            filtered_dependencies = {}
            for caller, callees in all_dependencies.items():
                filtered_callees = {callee for callee in callees if callee not in SKIP_DEPENDENCIES}
                if filtered_callees:  # 空でない場合のみ追加
                    filtered_dependencies[caller] = filtered_callees
            
            # フィルタリングした依存関係を使用
            all_dependencies = filtered_dependencies
            
            # 統合レポートの生成 - ファイル文字数情報を含める
            report = "# プロジェクト全体の拡張解析レポート\n\n"
            
            # LLM向け構造化データの出力
            report += "## LLM向け構造化データ\n"
            report += "```\n"
            
            # ディレクトリ構造を冒頭に挿入
            report += "# ディレクトリ構造\n"
            report += directory_structure
            report += "\n"
            
            # ファイル文字数情報を追加
            report += "# ファイル文字数\n"
            for file_path, result in analysis_results.items():
                file_name = os.path.basename(file_path)
                char_count = result.get('char_count', 0)
                report += f"{file_name}: {char_count:,} 文字\n"
            report += "\n"
            
            # コンパクトなフォーマットでデータを出力
            compact_data = "# クラス一覧\n"
            for cls in all_classes:
                base_info = f" <- {', '.join(cls['base_classes'])}" if cls['base_classes'] else ""
                file_info = next((os.path.basename(f) for f, r in analysis_results.items() 
                              if any(c["name"] == cls["name"] for c in r["classes"])), "unknown")
                compact_data += f"{cls['name']}{base_info} ({file_info})\n"
                
                if cls['methods']:
                    compact_data += "  メソッド:\n"
                    for m in cls['methods']:
                        params = ", ".join(p['name'] for p in m['parameters'])
                        ret_type = f" -> {m['return_type']}" if m['return_type'] and m['return_type'] != "unknown" else ""
                        compact_data += f"    {m['name']}({params}){ret_type}\n"
                compact_data += "\n"

            compact_data += "# 関数一覧\n"
            for func in all_functions:
                params = ", ".join(p['name'] for p in func['parameters'])
                ret_type = f" -> {func['return_type']}" if func['return_type'] and func['return_type'] != "unknown" else ""
                file_info = next((os.path.basename(f) for f, r in analysis_results.items() 
                              if any(fn["name"] == func["name"] for fn in r["functions"])), "unknown")
                compact_data += f"{func['name']}({params}){ret_type} ({file_info})\n"
            compact_data += "\n"

            # 主要な関数の依存関係を表示
            if all_dependencies:
                compact_data += "# 主要な関数依存関係\n"
                # 依存の多いもの順に表示
                important_dependencies = sorted([(k, v) for k, v in all_dependencies.items() if v], 
                                            key=lambda x: len(x[1]), reverse=True)[:10]
                for caller, callees in important_dependencies:
                    compact_data += f"{caller} -> {', '.join(callees)}\n"
                compact_data += "\n"
            
            # コールグラフの生成と追加
            call_graph_text = generate_call_graph(python_files)
            compact_data += call_graph_text
            
            report += compact_data
            report += "```\n"
            
            # 拡張解析の結果を表示
            self.extended_text.delete(1.0, tk.END)
            self.extended_text.insert(tk.END, report)
            self.extended_highlighter.highlight()
            
            # 現在表示されているタブが拡張解析タブの場合のみ文字数を更新
            current_tab_index = self.tab_control.index(self.tab_control.select())
            if current_tab_index == 1:  # 拡張解析タブ
                char_count = len(report)
                self.char_count_label.config(text=_("ui.status.char_count_value", "文字数: {0}").format(char_count))
            
            # JSON出力を生成（拡張解析の後に呼び出し）
            self.generate_json_output()
            
            # マーメードダイアグラムを生成
            self.generate_mermaid_output()
            
        except ImportError:
            self.extended_text.delete(1.0, tk.END)
            self.extended_text.insert(tk.END, "astroidライブラリがインストールされていません。\n"
                                    "pip install astroid でインストールしてください。")
        except Exception as e:
            self.extended_text.delete(1.0, tk.END)
            error_msg = f"拡張解析中にエラーが発生しました:\n{str(e)}"
            print(error_msg)
            traceback.print_exc()
            self.extended_text.insert(tk.END, error_msg)

    def generate_json_output(self):
        """現在の解析結果からJSON出力を生成してJSONタブに表示する"""
        # 現在の解析結果を取得
        result_text = self.result_text.get(1.0, "end-1c")
        extended_text = self.extended_text.get(1.0, "end-1c")
        
        if not result_text.strip():
            self.json_text.delete(1.0, tk.END)
            self.json_text.insert(tk.END, "JSONに変換する解析結果がありません。")
            return
        
        try:
            # テキストをJSON構造に変換
            json_data = text_to_json_structure(result_text)
            
            # ディレクトリ構造をJSONの冒頭に追加
            if self.selected_file:
                # ファイルモードの場合は、そのファイルを含むディレクトリを取得
                python_files = [self.selected_file]
            else:
                # ディレクトリモードの場合は含まれるPythonファイルを取得
                python_files = self.dir_tree_view.get_included_files(include_python_only=True)
            
            # ディレクトリ構造を取得して行ごとの配列に変換
            if python_files:
                dir_structure_text = self.get_directory_structure(python_files)
                dir_structure_lines = dir_structure_text.split('\n')
                
                # 既存のディレクトリ構造を上書き
                json_data["directory_structure"] = dir_structure_lines
            
            # 拡張解析テキストがあれば追加
            if extended_text.strip():
                # LLM構造化データ部分を抽出して構造化
                extended_data = extract_llm_structured_data(extended_text)
                if extended_data:
                    json_data["extended_analysis"] = extended_data
            
            # JSON形式の文字列に変換して整形
            import json
            json_string = json.dumps(json_data, indent=2, ensure_ascii=False)
            
            # JSONタブに表示
            self.json_text.delete(1.0, tk.END)
            self.json_text.insert(tk.END, json_string)
            
            # シンタックスハイライトを適用
            self.json_highlighter.highlight()
            
            # 現在表示されているタブがJSONタブの場合のみ文字数を更新
            current_tab_index = self.tab_control.index(self.tab_control.select())
            if current_tab_index == 2:  # JSONタブ (JSONタブが3番目)
                char_count = len(json_string)
                self.char_count_label.config(text=_("ui.status.char_count_value", "文字数: {0}").format(char_count))
            
        except Exception as e:
            traceback.print_exc()
            self.json_text.delete(1.0, tk.END)
            self.json_text.insert(tk.END, f"JSON変換中にエラーが発生しました: {str(e)}")
    
    def clear_workspace(self):
        """ワークスペースをクリアして初期状態に戻す"""
        # テキストエリアのクリア
        self.result_text.delete(1.0, tk.END)
        self.extended_text.delete(1.0, tk.END)
        self.json_text.delete(1.0, tk.END)
        self.mermaid_text.delete(1.0, tk.END)
        
        # ステータスメッセージをリセット
        self.file_status.config(text=_("ui.status.ready", "準備完了"))
        self.char_count_label.config(text=_("ui.status.char_count_value", "文字数: {0}").format(0))
        
        # 選択状態をリセット
        self.selected_file = None
        
        # メッセージを表示
        self.result_text.insert(tk.END, _("ui.messages.workspace_cleared", "ワークスペースをクリアしました。\n新しいファイルまたはディレクトリを選択してください。"))    

    def run_python_file(self):
        """Pythonファイルを実行する (コマンドライン方式)"""
        import subprocess
        
        if not self.current_dir:
            messagebox.showinfo("情報", "まずディレクトリを開いてください。")
            return
        
        # 実行するファイルを選択させる
        file_path = self.selected_file
        if not file_path or not os.path.isfile(file_path):
            file_path = filedialog.askopenfilename(
                title="実行するPythonファイルを選択",
                initialdir=self.current_dir,
                filetypes=[("Pythonファイル", "*.py"), ("すべてのファイル", "*.*")]
            )
            if not file_path:
                return  # キャンセルされた場合
        
        try:
            # コマンドラインウィンドウを開いてPythonスクリプトを実行
            # shell=True でコンソールウィンドウを表示
            # cwd でスクリプトのあるディレクトリに移動してから実行
            process = subprocess.Popen(
                f'python "{file_path}"', 
                shell=True,
                cwd=os.path.dirname(file_path)
            )
            
            # 設定ファイルに実行ファイルを保存
            self.config_manager.set_run_file(file_path)
            messagebox.showinfo("実行", f"{os.path.basename(file_path)} をコマンドラインで実行しています。")
            
        except Exception as e:
            messagebox.showerror("エラー", f"実行エラー: {str(e)}")
            
    def setup_analysis_result_context_menu(self):
        """解析結果タブのコンテキストメニューをセットアップ"""
        # コンテキストメニュー
        self.result_context_menu = tk.Menu(self.result_text, tearoff=0)
        self.result_context_menu.add_command(label="コピー", command=self.copy_selected_text)
        self.result_context_menu.add_separator()
        self.result_context_menu.add_command(label="選択された要素のコード全体をコピー", command=self.copy_code)
        
        # 右クリックイベント
        self.result_text.bind("<Button-3>", self.show_result_context_menu)

    def show_result_context_menu(self, event):
        """解析結果のコンテキストメニューを表示"""
        self.result_text.focus_set()
        self.result_context_menu.tk_popup(event.x_root, event.y_root)
        return "break"

    def copy_selected_text(self):
        """選択されたテキストをコピー"""
        try:
            selected_text = self.result_text.get("sel.first", "sel.last")
            if selected_text:
                pyperclip.copy(selected_text)
                self.file_status.config(text="選択テキストをコピーしました")
        except tk.TclError:
            pass  # 選択がない場合

    # MainWindowクラスに追加するメソッド
    def setup_snippet_context_menu(self):
        """解析結果やテキストエリアのコンテキストメニューをセットアップ"""
        # コンテキストメニュー作成
        self.snippet_menu = tk.Menu(self.root, tearoff=0)
        self.snippet_menu.add_command(label=_("ui.menu.copy", "コピー"), 
                                   command=self.copy_selection)
        self.snippet_menu.add_separator()
        self.snippet_menu.add_command(label=_("ui.menu.copy_code", "完全なコードをコピー"), 
                                   command=self.copy_full_code)
        
        # 各テキストエリアにバインド
        for text_widget in [self.result_text, self.extended_text]:
            text_widget.bind("<Button-3>", self.show_context_menu)
        
    def show_context_menu(self, event):
        """コンテキストメニュー表示"""
        widget = event.widget
        widget.focus_set()
        try:
            # 選択テキストがあるか確認
            has_selection = len(widget.tag_ranges("sel")) > 0
            
            # 選択に応じてメニュー項目の有効/無効を設定
            self.snippet_menu.entryconfig(_("ui.menu.copy", "コピー"), 
                                        state="normal" if has_selection else "disabled")
            
            # 完全なコード取得が可能かどうか判断
            can_get_code = self._can_get_full_code(widget)
            self.snippet_menu.entryconfig(_("ui.menu.copy_code", "完全なコードをコピー"), 
                                        state="normal" if can_get_code else "disabled")
            
            # メニュー表示
            self.snippet_menu.tk_popup(event.x_root, event.y_root)
        finally:
            # grab_releaseは必ず呼び出す
            self.snippet_menu.grab_release()
        
        return "break"  # イベント伝播を停止

    def show_snippet_context_menu(self, event):  # メソッド名変更
        """コンテキストメニュー表示"""
        widget = event.widget
        widget.focus_set()
        try:
            # 選択テキストがあるか確認
            has_selection = len(widget.tag_ranges("sel")) > 0
            
            # 選択に応じてメニュー項目の有効/無効を設定
            self.snippet_menu.entryconfig(_("ui.menu.copy", "コピー"), 
                                        state="normal" if has_selection else "disabled")
            
            # 完全なコード取得が可能かどうか判断
            can_get_code = self._can_get_full_code(widget)
            self.snippet_menu.entryconfig(_("ui.menu.copy_code", "完全なコードをコピー"), 
                                        state="normal" if can_get_code else "disabled")
            
            # メニュー表示
            self.snippet_menu.tk_popup(event.x_root, event.y_root)
        finally:
            # grab_releaseは必ず呼び出す
            self.snippet_menu.grab_release()
        
        return "break"  # イベント伝播を停止

    def _can_get_full_code(self, widget):
        """選択されたテキストに対して完全なコードが取得可能か判定"""
        try:
            if len(widget.tag_ranges("sel")) == 0:
                return False
                
            # 選択テキストを取得
            sel_text = widget.get("sel.first", "sel.last").strip()
            
            # 行全体を取得して分析
            line_start = widget.index("sel.first linestart")
            line_end = widget.index("sel.last lineend")
            full_line = widget.get(line_start, line_end).strip()
            
            # クラスまたは関数の定義行かどうかを柔軟にチェック
            if sel_text.startswith("class ") or sel_text.startswith("def "):
                return True
            
            # 装飾子を含む場合や、選択範囲が名前だけの場合も対応
            import re
            if re.search(r'(^|\s)(class|def)\s+\w+', full_line):
                return True
                
            return False
        except Exception as e:
            print(f"コード確認エラー: {str(e)}")
            return False

    def copy_code(self, widget=None):
        """選択された関数/クラスの完全なコードをコピー（詳細デバッグ版）"""
        try:
            # ウィジェットが指定されていない場合はフォーカスを持つウィジェットを使用
            if widget is None:
                widget = self.root.focus_get()
                print(f"ウィジェット自動検出: {widget.__class__.__name__}")
                    
            if not hasattr(widget, "get") or not hasattr(widget, "tag_ranges"):
                self.file_status.config(text="選択可能なテキストがありません")
                print(f"無効なウィジェット: {widget.__class__.__name__}, get={hasattr(widget, 'get')}, tag_ranges={hasattr(widget, 'tag_ranges')}")
                return
                    
            # 選択範囲が存在するか確認
            try:
                sel_ranges = widget.tag_ranges("sel")
                if not sel_ranges or len(sel_ranges) < 2:
                    self.file_status.config(text="テキストが選択されていません")
                    print(f"選択範囲なし: {sel_ranges}")
                    return
                
                # 選択範囲の詳細情報
                start_index = str(sel_ranges[0])
                end_index = str(sel_ranges[1])
                print(f"選択範囲: {start_index} から {end_index}")
            except Exception as e:
                print(f"選択範囲確認エラー: {str(e)}")
                traceback.print_exc()
                self.file_status.config(text="テキストが選択されていません")
                return
                    
            # 選択テキストを取得
            try:
                # 選択テキストとその前後のコンテキスト
                full_text = widget.get("1.0", "end")
                sel_text = widget.get("sel.first", "sel.last").strip()
                
                # 行全体の情報取得
                line_start = widget.index("sel.first linestart")
                line_end = widget.index("sel.last lineend")
                full_line = widget.get(line_start, line_end).strip()
                
                sel_line = sel_text.split("\n")[0] if "\n" in sel_text else sel_text
                print(f"選択テキスト: '{sel_text[:50]}{'...' if len(sel_text) > 50 else ''}'")
                print(f"選択行: '{sel_line}'")
                print(f"行全体: '{full_line[:100]}{'...' if len(full_line) > 100 else ''}'")
            except Exception as e:
                print(f"選択テキスト取得エラー: {str(e)}")
                traceback.print_exc()
                self.file_status.config(text="選択テキストの取得に失敗しました")
                return
            
            # 関数かクラスの名前を抽出
            element_name = None
            element_type = None
            
            # 正規表現で詳細に解析
            import re
            
            if "def " in sel_line:
                # 関数の場合
                element_name = sel_line.split("def ")[1].split("(")[0].strip()
                element_type = "function"
                print(f"関数検出: '{element_name}'")
            elif "class " in sel_line:
                # クラスの場合
                class_decl = sel_line.split("class ")[1]
                element_name = class_decl.split("(")[0].split(":")[0].strip()
                element_type = "class"
                print(f"クラス検出: '{element_name}'")
            else:
                # より高度な検出を試みる
                # クラスか関数の名前のパターン
                func_pattern = r'def\s+(\w+)'
                class_pattern = r'class\s+(\w+)'
                
                # 行内で検索
                func_match = re.search(func_pattern, full_line)
                class_match = re.search(class_pattern, full_line)
                
                if func_match:
                    element_name = func_match.group(1)
                    element_type = "function"
                    print(f"正規表現で関数検出: '{element_name}'")
                elif class_match:
                    element_name = class_match.group(1)
                    element_type = "class"
                    print(f"正規表現でクラス検出: '{element_name}'")
                else:
                    # 単語をそのまま使用
                    words = sel_line.split()
                    if words:
                        element_name = words[0].strip()
                        if element_name.endswith(":"):
                            element_name = element_name[:-1]
                        print(f"単語として検出: '{element_name}'")
                        # 型は判断できないのでどちらも検索
                        element_type = None
                    else:
                        self.file_status.config(text="関数またはクラスの名前を特定できませんでした")
                        print("名前検出失敗: 選択テキストから名前を抽出できません")
                        return
            
            if not element_name:
                self.file_status.config(text="関数名またはクラス名を特定できませんでした")
                print("名前検出失敗: 空の名前")
                return
                
            if not hasattr(self, "current_file") or not self.current_file:
                self.file_status.config(text="ファイルが選択されていません")
                print("ファイル未選択")
                return
                
            # 詳細なデバッグ情報
            print(f"検索対象: type={element_type}, name={element_name}, file={self.current_file}")
            print(f"ファイル存在確認: {os.path.exists(self.current_file)}")
                
            # データベースから完全なコードを検索
            try:
                db_connection = self.code_database.connection
                if not db_connection:
                    print("データベース接続がありません")
                    self.file_status.config(text="データベース接続がありません")
                    return
                    
                cursor = db_connection.cursor()
                
                # すべてのスニペット情報を表示（デバッグ用）
                cursor.execute("""
                    SELECT id, name, type, line_start, line_end FROM code_snippets 
                    WHERE file_path = ?
                    ORDER BY line_start
                    """, (self.current_file,))
                all_snippets = cursor.fetchall()
                print(f"データベース内のスニペット数: {len(all_snippets)}")
                for i, snippet in enumerate(all_snippets[:10]):  # 最初の10件だけ表示
                    print(f"  スニペット[{i}]: id={snippet[0]}, name={snippet[1]}, type={snippet[2]}, lines={snippet[3]}-{snippet[4]}")
                if len(all_snippets) > 10:
                    print(f"  ...他 {len(all_snippets) - 10} 件")
                
                # 検索ステップ1: 完全一致検索
                query = """
                    SELECT id, name, code, description, type, line_start, line_end FROM code_snippets 
                    WHERE file_path = ? AND name = ?
                    """
                cursor.execute(query, (self.current_file, element_name))
                results = cursor.fetchall()
                print(f"完全一致検索結果: {len(results)} 件")
                
                # 検索ステップ2: 型による条件付き検索
                if not results and element_type:
                    query = """
                        SELECT id, name, code, description, type, line_start, line_end FROM code_snippets 
                        WHERE file_path = ? AND type = ? AND name = ?
                        """
                    cursor.execute(query, (self.current_file, element_type, element_name))
                    results = cursor.fetchall()
                    print(f"型指定検索結果: {len(results)} 件")
                
                # 検索ステップ3: 部分一致検索（拡張版）
                if not results:
                    query = """
                        SELECT id, name, code, description, type, line_start, line_end FROM code_snippets 
                        WHERE file_path = ? AND 
                        (name = ? OR name LIKE ? OR name LIKE ? OR name LIKE ? OR 
                         name LIKE ? OR name LIKE ? OR name LIKE ?)
                        ORDER BY 
                            CASE 
                                WHEN name = ? THEN 0
                                WHEN name LIKE ? THEN 1
                                WHEN name LIKE ? THEN 2
                                ELSE 3
                            END,
                            line_start
                        """
                    
                    # 検索パラメータ（拡張）
                    params = (
                        self.current_file,
                        element_name,                # 完全一致
                        f"{element_name}.%",         # プレフィックス一致
                        f"%.{element_name}",         # サフィックス一致
                        f"%.{element_name}.%",       # 内部一致
                        f"%def {element_name}(%",    # 関数定義パターン
                        f"%class {element_name}%",   # クラス定義パターン
                        f"{element_name}(%",         # メソッド名パターン
                        element_name,                # ソート用
                        f"{element_name}.%",         # ソート用
                        f"%.{element_name}"          # ソート用
                    )
                    
                    cursor.execute(query, params)
                    results = cursor.fetchall()
                    print(f"部分一致検索結果: {len(results)} 件")
                    
                    # 部分一致結果の詳細ログ
                    for i, r in enumerate(results[:5]):  # 最初の5件だけ表示
                        print(f"  結果[{i}]: id={r[0]}, name={r[1]}, type={r[4]}, lines={r[5]}-{r[6]}")
                    if len(results) > 5:
                        print(f"  ...他 {len(results) - 5} 件")
                
                # 結果処理
                if results:
                    # 最も関連性の高い結果を選択
                    best_match = None
                    
                    # 完全一致を優先
                    exact_matches = [r for r in results if r[1] == element_name]
                    if exact_matches:
                        best_match = exact_matches[0]
                        print(f"完全一致を選択: {best_match[1]}")
                    else:
                        # 名前の長さでソート（最も短いものを選択）
                        results_sorted = sorted(results, key=lambda x: len(x[1]))
                        best_match = results_sorted[0]
                        print(f"部分一致で最適なものを選択: {best_match[1]}")
                    
                    id, name, code, description, result_type, line_start, line_end = best_match
                    
                    # ヘッダー情報
                    header = f"## ディレクトリ: {os.path.dirname(self.current_file)}\n"
                    header += f"### ファイル: {os.path.basename(self.current_file)}\n"
                    header += f"### 行番号: {line_start}-{line_end}\n"
                    
                    # Type表示を調整
                    type_display = "Method" if "." in name and result_type == "function" else result_type.capitalize()
                    
                    # docstringがあれば追加
                    if description:
                        header += f"# {type_display}: {name}\n"
                        header += f"\"{description}\"\n\n"
                    else:
                        header += f"# {type_display}: {name}\n\n"
                    
                    # コード全体をクリップボードにコピー
                    full_code = header + code
                    pyperclip.copy(full_code)
                    self.file_status.config(text=f"{type_display} '{name}' のコードをコピーしました")
                    print(f"コピー成功: {type_display} '{name}', {len(code)} 文字")
                else:
                    # コードが見つからない場合、全ファイル検索を実行
                    result = self.find_function_in_all_files(element_name)
                    
                    if result:
                        file_path, (name, code, description, result_type) = result
                        
                        # ユーザーに通知
                        message = f"'{element_name}'はこのファイルではなく '{os.path.basename(file_path)}' に存在します"
                        self.file_status.config(text=message)
                        
                        # 正しいファイルを開くか確認
                        if messagebox.askyesno(_("ファイル検索結果"), 
                            _(f"関数 '{element_name}' は別のファイルに存在します:\n{file_path}\n\nこのファイルを開きますか？")):
                            # ファイルを切り替え
                            self.current_file = file_path
                            # ファイルを表示
                            if hasattr(self, "on_file_selected"):
                                self.on_file_selected(file_path)
                            
                            # コードをコピー
                            header = f"## ディレクトリ: {os.path.dirname(file_path)}\n"
                            header += f"### ファイル: {os.path.basename(file_path)}\n"
                            
                            # Type表示を調整
                            type_display = "Method" if "." in name and result_type == "function" else result_type.capitalize()
                            
                            # docstringがあれば追加
                            if description:
                                header += f"# {type_display}: {name}\n"
                                header += f"\"{description}\"\n\n"
                            else:
                                header += f"# {type_display}: {name}\n\n"
                            
                            # コード全体をクリップボードにコピー
                            full_code = header + code
                            pyperclip.copy(full_code)
                            self.file_status.config(text=f"{type_display} '{name}' のコードをコピーしました")
                    else:
                        # 再同期を試みる
                        success, count = self.resync_file_to_database(self.current_file)
                        if success:
                            # 再検索のためのパラメータを用意
                            search_params = (
                                self.current_file, 
                                element_name,
                                f"{element_name}.%",
                                f"%.{element_name}",
                                f"%.{element_name}.%",
                                f"%def {element_name}(%",
                                f"%class {element_name}%", 
                                f"{element_name}(%", 
                                element_name,
                                f"{element_name}.%",
                                f"%.{element_name}"
                            )
                            # 再度検索
                            cursor.execute(query, search_params)
                            results = cursor.fetchall()
                            
                            if results:
                                # 同期により問題が解決
                                self.file_status.config(text=f"再同期後にコードが見つかりました。もう一度試してください。")
                            else:
                                # 再分析を提案
                                self.file_status.config(text=f"'{element_name}' が見つかりません。プロジェクト再分析を試してください")
                                
                                # 再分析するか確認
                                if messagebox.askyesno(_("再分析"), 
                                    _(f"'{element_name}' が見つかりませんでした。プロジェクト全体を再分析しますか？")):
                                    self.reanalyze_project()
                        else:
                            self.file_status.config(text=f"'{element_name}' が見つかりません。プロジェクト再分析を試してください")
                    
            except Exception as ex:
                print(f"コード検索エラー: {str(ex)}")
                traceback.print_exc()
                self.file_status.config(text="コードの検索中にエラーが発生しました")
        except Exception as e:
            print(f"コードコピーエラー: {str(e)}")
            traceback.print_exc()
            self.file_status.config(text="コードのコピー中にエラーが発生しました")

    def setup_code_context_menus(self):
        """コード関連のコンテキストメニューをセットアップ"""
        # 解析結果用のコンテキストメニュー
        self.code_context_menu = tk.Menu(self.root, tearoff=0)
        self.code_context_menu.add_command(label="選択テキストをコピー", command=self.copy_selection)
        self.code_context_menu.add_separator()
        self.code_context_menu.add_command(label="完全なコードをコピー", command=self.copy_code)
        
        # 各テキストエリアにバインド
        for text_widget in [self.result_text, self.extended_text]:
            text_widget.bind("<Button-3>", self.show_code_context_menu)

    def show_code_context_menu(self, event):
        """コードコンテキストメニューを表示"""
        widget = event.widget
        widget.focus_set()
        
        try:
            # 選択テキストがあるか確認
            has_selection = False
            try:
                sel_ranges = widget.tag_ranges("sel")
                has_selection = sel_ranges and len(sel_ranges) >= 2
            except Exception:
                has_selection = False
            
            # 選択に応じてメニュー項目の有効/無効を設定
            self.code_context_menu.entryconfig("選択テキストをコピー", 
                                            state="normal" if has_selection else "disabled")
            
            # 完全なコード取得が可能かどうか判断
            can_get_code = False
            if has_selection:
                try:
                    # 選択テキストが関数またはクラス定義行かチェック
                    sel_line = widget.get("sel.first linestart", "sel.first lineend").strip()
                    can_get_code = sel_line.startswith("def ") or sel_line.startswith("class ")
                except Exception:
                    can_get_code = False
            
            self.code_context_menu.entryconfig("完全なコードをコピー", 
                                            state="normal" if can_get_code else "disabled")
            
            # メニュー表示
            self.code_context_menu.tk_popup(event.x_root, event.y_root)
        except Exception as e:
            print(f"コンテキストメニュー表示エラー: {str(e)}")
            traceback.print_exc()
        finally:
            # grab_releaseは必ず呼び出す
            self.code_context_menu.grab_release()
        
        return "break"  # イベント伝播を停止

    def copy_selection(self):
        """選択テキストをコピー"""
        try:
            widget = self.root.focus_get()
            if hasattr(widget, "get") and hasattr(widget, "tag_ranges"):
                try:
                    selected_text = widget.get("sel.first", "sel.last")
                    if selected_text:
                        pyperclip.copy(selected_text)
                        self.file_status.config(text="選択テキストをコピーしました")
                except tk.TclError:
                    self.file_status.config(text="テキストが選択されていません")
        except Exception as e:
            print(f"テキストコピーエラー: {str(e)}")
            self.file_status.config(text="コピー中にエラーが発生しました")
                        
    def handle_missing_code(self, element_name):
        """コードが見つからない場合の処理"""
        # 現在のファイルを再同期
        success, count = self.resync_file_to_database(self.current_file)
        
        if success:
            # 再度検索
            cursor = self.code_database.connection.cursor()
            cursor.execute("""
                SELECT name, code, description, type FROM code_snippets 
                WHERE file_path = ? AND name = ?
            """, (self.current_file, element_name))
            results = cursor.fetchall()
            
            if results:
                # 同期により問題が解決
                return results[0]
            else:
                # 全ファイル検索
                cursor.execute("""
                    SELECT file_path, name, code, description, type FROM code_snippets 
                    WHERE name = ?
                """, (element_name,))
                all_results = cursor.fetchall()
                
                if all_results:
                    file_path, name, code, description, result_type = all_results[0]
                    # 重複関数の存在を通知
                    if file_path != self.current_file:
                        message = f"注意: '{element_name}'はこのファイルに存在していますが、" + \
                                  f"データベースには別のファイル({os.path.basename(file_path)})の同名関数が登録されています。\n" + \
                                  f"コード変更または複製された可能性があります。再分析をお勧めします。"
                        self.file_status.config(text=message)
                    return name, code, description, result_type
        
        return None
                
    def find_function_in_all_files(self, function_name):
        """すべてのファイルから関数定義を検索"""
        try:
            # データベース接続確認
            if not hasattr(self, "code_database") or not self.code_database.connection:
                print("データベース接続がありません")
                return None
                
            cursor = self.code_database.connection.cursor()
            
            # すべてのファイルから検索
            query = """
                SELECT file_path, name, code, description, type FROM code_snippets 
                WHERE name = ? AND type = 'function'
                """
            cursor.execute(query, (function_name,))
            results = cursor.fetchall()
            
            if results:
                # 最初に見つかった結果を返す
                file_path, name, code, description, result_type = results[0]
                print(f"検索結果: ファイル={file_path}, 名前={name}")
                return file_path, (name, code, description, result_type)
            
            # クラスでも検索
            query = """
                SELECT file_path, name, code, description, type FROM code_snippets 
                WHERE name = ? AND type = 'class'
                """
            cursor.execute(query, (function_name,))
            results = cursor.fetchall()
            
            if results:
                file_path, name, code, description, result_type = results[0]
                print(f"クラス検索結果: ファイル={file_path}, 名前={name}")
                return file_path, (name, code, description, result_type)
            
            # 部分一致検索も試す
            query = """
                SELECT file_path, name, code, description, type FROM code_snippets 
                WHERE name LIKE ? AND (type = 'function' OR type = 'class')
                """
            cursor.execute(query, (f"%{function_name}%",))
            results = cursor.fetchall()
            
            if results:
                file_path, name, code, description, result_type = results[0]
                print(f"部分一致検索結果: ファイル={file_path}, 名前={name}")
                return file_path, (name, code, description, result_type)
                
            return None
        except Exception as e:
            print(f"グローバル検索エラー: {str(e)}")
            traceback.print_exc()
            return None

    def resync_file_to_database(self, file_path):
        """ファイルの内容を再分析してデータベースを同期"""
        try:
            # 既存のスニペットをクリア
            self.code_database.clear_file_snippets(file_path)
            
            # ファイルを再分析
            extractor = CodeExtractor(self.code_database)
            extractor.extract_from_file(file_path)
            
            # 確認
            cursor = self.code_database.connection.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM code_snippets WHERE file_path = ?
            """, (file_path,))
            count = cursor.fetchone()[0]
            
            return True, count
        except Exception as e:
            print(f"再同期エラー: {str(e)}")
            traceback.print_exc()
            return False, 0

    def reanalyze_project(self):
        """プロジェクト全体を再分析"""
        try:
            # 確認ダイアログ
            if not messagebox.askyesno(_("確認"), 
                _("プロジェクト全体を再分析します。この処理には時間がかかる場合があります。続行しますか？")):
                return
            
            # 進捗ダイアログ
            progress_window = tk.Toplevel(self.root)
            progress_window.title(_("プロジェクト再分析"))
            progress_window.transient(self.root)
            progress_window.geometry("400x150")
            progress_window.resizable(False, False)
            
            progress_label = ttk.Label(progress_window, text=_("データベースをリセットしています..."))
            progress_label.pack(pady=10)
            
            progress_bar = ttk.Progressbar(progress_window, mode="determinate")
            progress_bar.pack(fill="x", padx=20, pady=10)
            
            # データベースをリセット
            self.code_database.connection.execute("DELETE FROM code_snippets")
            self.code_database.connection.commit()
            
            # プロジェクトファイルの一覧取得
            files = []
            if hasattr(self, "directory_tree") and self.directory_tree:
                files = self.directory_tree.get_included_files()
            
            # 進捗計算
            total_files = len(files)
            progress_bar["maximum"] = total_files
            
            # ファイルを再分析
            file_count = 0
            extractor = CodeExtractor(self.code_database)
            
            for file_path in files:
                file_count += 1
                progress_label.config(text=f"分析中: {os.path.basename(file_path)}")
                progress_bar["value"] = file_count
                progress_window.update()
                
                extractor.extract_from_file(file_path)
                
            progress_window.destroy()
            messagebox.showinfo(_("完了"), 
                _(f"プロジェクト再分析が完了しました。\n処理されたファイル: {file_count}個"))
            
            # 現在のファイルを再分析
            if hasattr(self, "current_file") and self.current_file:
                self.analyze_file(self.current_file)
                
        except Exception as e:
            print(f"プロジェクト再分析エラー: {str(e)}")
            traceback.print_exc()
            messagebox.showerror(_("エラー"), 
                _(f"再分析中にエラーが発生しました:\n{str(e)}"))