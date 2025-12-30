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
from ui.toolbar import ToolbarManager
from ui.analysis_handler import AnalysisHandler
from ui.output_generator import OutputGenerator
from ui.language_manager import LanguageManager
from ui.editor_shortcuts import EditorShortcutsManager

# 他のモジュール（絶対インポートパス）
from utils.config import ConfigManager
from utils.file_utils import open_in_explorer, open_with_default_app, create_temp_error_log, run_python_file
# json_converterはOutputGeneratorに移動
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

        # 言語マネージャーを初期化（言語ボタン設定より前に）
        self.language_manager = LanguageManager(self)

        # 言語切り替えボタン
        self.setup_language_selector()

        # ツールバーマネージャーを初期化してカスタムボタンをセットアップ
        self.toolbar_manager = ToolbarManager(self)
        self.toolbar_manager.setup_custom_buttons()

        # 解析ハンドラーを初期化
        self.analysis_handler = AnalysisHandler(self)

        # 出力ジェネレーターを初期化
        self.output_generator = OutputGenerator(self)

        # エディタショートカットマネージャーを初期化
        self.editor_shortcuts = EditorShortcutsManager(self)

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
        """LLM向けに詳細なコード情報をマーメードダイアグラムで生成する（OutputGeneratorに委譲）"""
        return self.output_generator.generate_advanced_mermaid_for_llm()

    def generate_mermaid_output(self):
        """マーメードダイアグラム生成（OutputGeneratorに委譲）"""
        self.output_generator.generate_mermaid_output()

    def setup_language_selector(self):
        """言語切り替えボタン設定（LanguageManagerに委譲）"""
        self.language_manager.setup_language_selector()

    def update_language_buttons(self):
        """言語ボタン状態更新（LanguageManagerに委譲）"""
        self.language_manager.update_language_buttons()

    def change_language(self, lang_code):
        """言語変更（LanguageManagerに委譲）"""
        self.language_manager.change_language(lang_code)

    def on_language_change(self, event=None):
        """言語変更処理（LanguageManagerに委譲）"""
        self.language_manager.on_language_change(event)

    def update_ui_texts(self):
        """UIテキスト更新（LanguageManagerに委譲）"""
        self.language_manager.update_ui_texts()

    def _update_widget_texts(self, parent):
        """ウィジェットテキスト更新（LanguageManagerに委譲）"""
        self.language_manager._update_widget_texts(parent)

    def _update_menu_texts(self):
        """メニューテキスト更新（LanguageManagerに委譲）"""
        self.language_manager._update_menu_texts()

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
        """テキストエディタショートカット設定（EditorShortcutsManagerに委譲）"""
        self.editor_shortcuts.setup_text_editor_shortcuts()

    def setup_editor_shortcuts(self, text_widget):
        """エディタショートカット設定（EditorShortcutsManagerに委譲）"""
        self.editor_shortcuts.setup_editor_shortcuts(text_widget)

    def select_all(self, event, text_widget):
        """テキスト全選択（EditorShortcutsManagerに委譲）"""
        return self.editor_shortcuts.select_all(event, text_widget)

    def copy_text(self, event, text_widget):
        """テキストコピー（EditorShortcutsManagerに委譲）"""
        return self.editor_shortcuts.copy_text(event, text_widget)

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
        """ディレクトリ構造を生成（OutputGeneratorに委譲）"""
        return self.output_generator.get_directory_structure(python_files)
    
    def analyze_selected(self):
        """選択されたファイルまたはディレクトリを解析（AnalysisHandlerに委譲）"""
        self.analysis_handler.analyze_selected()

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
        """単一のファイルを解析（AnalysisHandlerに委譲）"""
        self.analysis_handler.analyze_file(file_path)

    def load_code_snippets(self, file_path):
        """データベースからファイルのコードスニペットを読み込む"""
        try:
            snippets = self.code_database.get_snippets_by_file(file_path)
            return snippets
        except Exception as e:
            messagebox.showerror("データベースエラー", f"スニペット読み込みエラー: {str(e)}")
            return []

    def perform_extended_analysis(self, python_files):
        """astroidによる拡張解析を実行する（AnalysisHandlerに委譲）"""
        self.analysis_handler.perform_extended_analysis(python_files)

    def generate_json_output(self):
        """JSON出力生成（OutputGeneratorに委譲）"""
        self.output_generator.generate_json_output()
    
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
        """解析結果コンテキストメニュー設定（EditorShortcutsManagerに委譲）"""
        self.editor_shortcuts.setup_analysis_result_context_menu()

    def show_result_context_menu(self, event):
        """解析結果コンテキストメニュー表示（EditorShortcutsManagerに委譲）"""
        return self.editor_shortcuts.show_result_context_menu(event)

    def copy_selected_text(self):
        """選択テキストコピー（EditorShortcutsManagerに委譲）"""
        self.editor_shortcuts.copy_selected_text()

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
        """コードコンテキストメニュー設定（EditorShortcutsManagerに委譲）"""
        self.editor_shortcuts.setup_code_context_menus()

    def show_code_context_menu(self, event):
        """コードコンテキストメニュー表示（EditorShortcutsManagerに委譲）"""
        return self.editor_shortcuts.show_code_context_menu(event)

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
        """プロジェクト全体を再分析（AnalysisHandlerに委譲）"""
        self.analysis_handler.reanalyze_project()