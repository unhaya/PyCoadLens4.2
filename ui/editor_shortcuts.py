# ui/editor_shortcuts.py
"""テキストエディタのショートカットとコンテキストメニュー管理クラス"""

import sys
import tkinter as tk
import traceback

import pyperclip

from utils.i18n import _


class EditorShortcutsManager:
    """テキストエディタのショートカットとコンテキストメニューを管理するクラス"""

    def __init__(self, main_window):
        """
        エディタショートカットマネージャーを初期化

        Args:
            main_window: MainWindowインスタンス（親ウィンドウへの参照）
        """
        self.main_window = main_window

    def setup_text_editor_shortcuts(self):
        """テキストエディタのショートカットとコンテキストメニューを設定"""
        mw = self.main_window

        # 各テキストエリアにショートカットを設定
        self.setup_editor_shortcuts(mw.result_text)
        self.setup_editor_shortcuts(mw.extended_text)
        self.setup_editor_shortcuts(mw.json_text)
        self.setup_editor_shortcuts(mw.mermaid_text)

    def setup_editor_shortcuts(self, text_widget):
        """テキストウィジェットにショートカットとコンテキストメニューを設定"""
        mw = self.main_window

        # ショートカットキーのバインド
        text_widget.bind("<Control-a>", lambda event: self.select_all(event, text_widget))
        text_widget.bind("<Control-c>", lambda event: self.copy_text(event, text_widget))

        # コンテキストメニュー作成
        context_menu = tk.Menu(text_widget, tearoff=0)
        context_menu.add_command(
            label=_("ui.context_menu.copy", "コピー"),
            command=lambda: self.copy_text(None, text_widget),
            accelerator="Ctrl+C"
        )
        context_menu.add_separator()
        context_menu.add_command(
            label=_("ui.context_menu.select_all", "すべて選択"),
            command=lambda: self.select_all(None, text_widget),
            accelerator="Ctrl+A"
        )

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
        return "break"

    def select_all(self, event, text_widget):
        """テキストをすべて選択"""
        text_widget.tag_add(tk.SEL, "1.0", tk.END)
        text_widget.mark_set(tk.INSERT, tk.END)
        text_widget.see(tk.INSERT)
        return "break"

    def copy_text(self, event, text_widget):
        """選択テキストをコピー"""
        mw = self.main_window
        try:
            selection = text_widget.get(tk.SEL_FIRST, tk.SEL_LAST)
            mw.root.clipboard_clear()
            mw.root.clipboard_append(selection)
        except tk.TclError:
            pass  # 選択されていない場合は何もしない
        return "break"

    def setup_analysis_result_context_menu(self):
        """解析結果タブのコンテキストメニューをセットアップ"""
        mw = self.main_window

        # コンテキストメニュー
        mw.result_context_menu = tk.Menu(mw.result_text, tearoff=0)
        mw.result_context_menu.add_command(label="コピー", command=self.copy_selected_text)
        mw.result_context_menu.add_separator()
        mw.result_context_menu.add_command(label="選択された要素のコード全体をコピー", command=mw.copy_code)

        # 右クリックイベント
        mw.result_text.bind("<Button-3>", self.show_result_context_menu)

    def show_result_context_menu(self, event):
        """解析結果のコンテキストメニューを表示"""
        mw = self.main_window
        mw.result_text.focus_set()
        mw.result_context_menu.tk_popup(event.x_root, event.y_root)
        return "break"

    def copy_selected_text(self):
        """選択されたテキストをコピー"""
        mw = self.main_window
        try:
            selected_text = mw.result_text.get("sel.first", "sel.last")
            if selected_text:
                pyperclip.copy(selected_text)
                mw.file_status.config(text="選択テキストをコピーしました")
        except tk.TclError:
            pass  # 選択がない場合

    def setup_code_context_menus(self):
        """コード関連のコンテキストメニューをセットアップ"""
        mw = self.main_window

        # 解析結果用のコンテキストメニュー
        mw.code_context_menu = tk.Menu(mw.root, tearoff=0)
        mw.code_context_menu.add_command(label="選択テキストをコピー", command=mw.copy_selection)
        mw.code_context_menu.add_separator()
        mw.code_context_menu.add_command(label="完全なコードをコピー", command=mw.copy_code)

        # 各テキストエリアにバインド
        for text_widget in [mw.result_text, mw.extended_text]:
            text_widget.bind("<Button-3>", self.show_code_context_menu)

    def show_code_context_menu(self, event):
        """コードコンテキストメニューを表示"""
        mw = self.main_window
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
            mw.code_context_menu.entryconfig(
                "選択テキストをコピー",
                state="normal" if has_selection else "disabled"
            )

            # 完全なコード取得が可能かどうか判断
            can_get_code = False
            if has_selection:
                try:
                    # 選択テキストが関数またはクラス定義行かチェック
                    sel_line = widget.get("sel.first linestart", "sel.first lineend").strip()
                    can_get_code = sel_line.startswith("def ") or sel_line.startswith("class ")
                except Exception:
                    can_get_code = False

            mw.code_context_menu.entryconfig(
                "完全なコードをコピー",
                state="normal" if can_get_code else "disabled"
            )

            # メニュー表示
            mw.code_context_menu.tk_popup(event.x_root, event.y_root)
        except Exception as e:
            print(f"コンテキストメニュー表示エラー: {str(e)}")
            traceback.print_exc()
        finally:
            # grab_releaseは必ず呼び出す
            mw.code_context_menu.grab_release()

        return "break"
