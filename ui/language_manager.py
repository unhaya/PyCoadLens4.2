# ui/language_manager.py
"""言語切り替え機能を管理するクラス"""

import tkinter as tk
from tkinter import messagebox, ttk

from utils.i18n import _


class LanguageManager:
    """言語切り替えとUIテキスト更新を管理するクラス"""

    def __init__(self, main_window):
        """
        言語マネージャーを初期化

        Args:
            main_window: MainWindowインスタンス（親ウィンドウへの参照）
        """
        self.main_window = main_window
        self.jp_button = None
        self.en_button = None

    def setup_language_selector(self):
        """言語切り替えボタンを設定"""
        mw = self.main_window

        # 言語ボタンフレームを作成（右上に配置）
        language_frame = ttk.Frame(mw.toolbar_frame)
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

        # MainWindowにボタン参照を保持（互換性のため）
        mw.jp_button = self.jp_button
        mw.en_button = self.en_button

        # 現在の言語に基づいてボタンの状態を更新
        self.update_language_buttons()

    def update_language_buttons(self):
        """現在の言語に基づいてボタンの状態を更新"""
        mw = self.main_window
        current_lang = mw.i18n.get_current_language()

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
        mw = self.main_window
        if mw.i18n.get_current_language() != lang_code:
            if mw.i18n.set_language(lang_code):
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
        mw = self.main_window
        selected_language = mw.language_var.get()
        if mw.i18n.set_language(selected_language):
            messagebox.showinfo(
                _("language.restart_title", "再起動が必要"),
                _("language.restart_message", "言語設定を完全に適用するには、アプリケーションの再起動が必要です。")
            )
            # 一部のUIテキストを即時更新できる場合は、ここでそれを行います
            self.update_ui_texts()

    def update_ui_texts(self):
        """UIテキストを現在の言語に更新"""
        mw = self.main_window

        # タイトル更新
        mw.root.title(_("app.title", "コード解析ツール"))

        # タブ名などの更新
        if hasattr(mw, 'notebook') and mw.notebook:
            for i, tab_name in enumerate(["project", "code", "analysis", "json", "prompt"]):
                mw.notebook.tab(i, text=_("tabs." + tab_name, mw.notebook.tab(i, "text")))

        # ボタンテキスト更新
        if hasattr(mw, 'analyze_button'):
            mw.analyze_button.config(text=_("buttons.analyze", "解析"))
        if hasattr(mw, 'copy_button'):
            mw.copy_button.config(text=_("buttons.copy", "コピー"))
        if hasattr(mw, 'clear_button'):
            mw.clear_button.config(text=_("buttons.clear", "クリア"))

        # 再分析ボタン更新（追加）
        if hasattr(mw, 'reanalyze_text_label'):
            mw.reanalyze_text_label.config(text=_("buttons.reanalyze", "再分析"))

        # ステータスバー更新
        if hasattr(mw, 'file_status'):
            current_text = mw.file_status.cget("text")
            if current_text.strip() == "":
                mw.file_status.config(text=_("status.ready", "準備完了"))

        # チェックボックスとラベル更新
        for widget in mw.root.winfo_children():
            self._update_widget_texts(widget)

        # メニュー更新（オプション）
        if hasattr(mw, 'menu'):
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
        mw = self.main_window
        if not hasattr(mw, 'menu'):
            return

        menu_items = {
            "file": ["open", "save", "exit"],
            "edit": ["copy", "paste", "select_all"],
            "tools": ["analyze", "settings", "reanalyze"],
            "help": ["about", "documentation"]
        }

        for menu_name, items in menu_items.items():
            if hasattr(mw.menu, menu_name):
                menu_obj = getattr(mw.menu, menu_name)
                menu_obj.entryconfig(0, label=_(f"menu.{menu_name}", menu_name.capitalize()))

                for i, item in enumerate(items):
                    try:
                        current_label = menu_obj.entrycget(i, "label")
                        menu_obj.entryconfig(i, label=_(f"menu.{menu_name}.{item}", current_label))
                    except Exception:
                        pass  # エントリが存在しない場合はスキップ
