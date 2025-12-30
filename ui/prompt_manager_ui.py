# ui/prompt_manager_ui.py

import sys
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import uuid
from utils.i18n import _ 
   
class PromptManagerUI:
    """プロンプト管理関連のUIコンポーネント"""
    
    def __init__(self, parent, prompt_manager, config_manager):
        self.parent = parent
        self.prompt_manager = prompt_manager
        self.config_manager = config_manager
        
        # プロンプト関連の状態管理
        self.current_prompt_id = None
        self.prompt_modified = False
        
        # UI要素の初期化
        self.setup_prompt_tab()
    
    def setup_prompt_tab(self):
        """プロンプト入力タブのUIを構築する"""
        # プロンプトタブを左右に分割
        self.prompt_paned = ttk.PanedWindow(self.parent, orient=tk.HORIZONTAL)
        self.prompt_paned.pack(expand=True, fill="both")

        # 左側フレーム（プロンプト一覧）を設定
        self.setup_prompt_list_frame()
        
        # 右側フレーム（プロンプト編集）を設定
        self.setup_prompt_edit_frame()
        
        # 下部のボタンエリアを設定
        self.setup_prompt_button_frame()
        
        # プロンプト一覧を更新
        self.update_prompt_list()

        # 最初のプロンプトを選択
        if self.prompt_tree.get_children():
            self.current_prompt_id = self.prompt_tree.get_children()[0]
            self.prompt_tree.selection_set(self.current_prompt_id)
            self.prompt_tree.focus(self.current_prompt_id)
            self.on_prompt_selected(None)

        # ショートカットの設定
        self.bind_prompt_shortcuts()
    
    def setup_prompt_list_frame(self):
        """プロンプト一覧フレームを設定"""
        # 左側フレーム
        self.prompt_list_frame = ttk.Frame(self.prompt_paned, width=220)
        self.prompt_paned.add(self.prompt_list_frame, weight=1)
        
        # 一覧上部のヘッダーフレーム
        list_header_frame = ttk.Frame(self.prompt_list_frame)
        list_header_frame.pack(fill="x", padx=5, pady=(5, 0))
        
        # 「プロンプト一覧」ラベル
        list_label = ttk.Label(list_header_frame, text=_("prompt_list", "プロンプト一覧"), font=('Helvetica', 10, 'bold'))
        list_label.pack(side="left", padx=5)
        
        # プロンプト操作ボタン（+と-）をヘッダーの右側に配置
        button_frame = ttk.Frame(list_header_frame)
        button_frame.pack(side="right", padx=2)
        
        # コンパクトなボタン用のスタイル設定
        style = ttk.Style()
        style.configure("Compact.TButton", 
                       padding=0,       # パディングを0に設定
                       font=('Helvetica', 8),  # フォントサイズ縮小
                       width=1)         # 幅を最小限に設定
        
        # 新規作成ボタン（+）- コンパクトスタイル適用
        self.add_prompt_btn = ttk.Button(button_frame, text="+", style="Compact.TButton",
                                       command=self.create_new_prompt)
        self.add_prompt_btn.pack(side="left", padx=1)
        self.add_tooltip(self.add_prompt_btn, _("new_prompt_tooltip", "新規プロンプト作成"))
        
        # 削除ボタン（-）- コンパクトスタイル適用
        self.remove_prompt_btn = ttk.Button(button_frame, text="-", style="Compact.TButton",
                                          command=self.delete_current_prompt)
        self.remove_prompt_btn.pack(side="left", padx=1)
        self.add_tooltip(self.remove_prompt_btn, _("delete_prompt_tooltip", "選択したプロンプトを削除"))
        
        # 区切り線
        separator = ttk.Separator(self.prompt_list_frame, orient="horizontal")
        separator.pack(fill="x", padx=5, pady=5)
        
        # プロンプト一覧（ツリービュー）
        self.prompt_tree = ttk.Treeview(self.prompt_list_frame, columns=("name",), show="headings", height=15)
        self.prompt_tree.heading("name", text=_("prompt_name_column", "プロンプト名"))
        self.prompt_tree.column("name", width=200, anchor="w")
        
        # スクロールバー - より細く設定
        tree_scroll = ttk.Scrollbar(self.prompt_list_frame, orient="vertical", command=self.prompt_tree.yview)
        self.prompt_tree.configure(yscrollcommand=tree_scroll.set)
        
        # ツリービューとスクロールバーを配置 - スクロールバーを右端に完全に寄せる
        self.prompt_tree.pack(side="left", expand=True, fill="both", padx=(5, 0), pady=5)
        tree_scroll.pack(side="right", fill="y", pady=5)
        
        # プロンプトツリーの選択イベント
        self.prompt_tree.bind("<<TreeviewSelect>>", self.on_prompt_selected)
        
        # 右クリックメニューの追加
        self.setup_prompt_context_menu()
    
    def setup_prompt_context_menu(self):
        """プロンプト一覧の右クリックメニューを設定"""
        self.prompt_context_menu = tk.Menu(self.prompt_tree, tearoff=0)
        self.prompt_context_menu.add_command(label=_("ui.context_menu.new_prompt", "新規作成"), command=self.create_new_prompt)
        self.prompt_context_menu.add_command(label=_("ui.context_menu.duplicate_prompt", "複製"), command=self.duplicate_current_prompt)
        self.prompt_context_menu.add_command(label=_("ui.context_menu.delete_prompt", "削除"), command=self.delete_current_prompt)
        
        # 右クリックイベントをバインド
        if sys.platform == 'darwin':  # macOS
            self.prompt_tree.bind("<Button-2>", self.show_prompt_context_menu)
        else:  # Windows/Linux
            self.prompt_tree.bind("<Button-3>", self.show_prompt_context_menu)
    
    def show_prompt_context_menu(self, event):
        """プロンプト一覧の右クリックメニューを表示"""
        try:
            # クリックした位置の項目を特定
            item = self.prompt_tree.identify_row(event.y)
            if item:
                # 項目を選択
                self.prompt_tree.selection_set(item)
                self.prompt_tree.focus(item)
                self.on_prompt_selected(None)
                
                # メニューを表示
                self.prompt_context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.prompt_context_menu.grab_release()
    
    def setup_prompt_edit_frame(self):
        """プロンプト編集フレームを設定"""
        # 右側フレーム
        self.prompt_edit_frame = ttk.Frame(self.prompt_paned)
        self.prompt_paned.add(self.prompt_edit_frame, weight=3)
        
        # プロンプト名入力エリア
        name_frame = ttk.Frame(self.prompt_edit_frame)
        name_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        self.prompt_name_label = ttk.Label(name_frame, text=_("prompt_name_label", "プロンプト名:"), font=('Helvetica', 10))
        self.prompt_name_label.pack(side="left", padx=(0, 5))
        
        self.prompt_name_var = tk.StringVar()
        self.prompt_name_entry = ttk.Entry(name_frame, textvariable=self.prompt_name_var, font=('Helvetica', 10))
        self.prompt_name_entry.pack(side="left", fill="x", expand=True)
        
        # 区切り線
        separator = ttk.Separator(self.prompt_edit_frame, orient="horizontal")
        separator.pack(fill="x", padx=10, pady=5)
        
        # エディタラベル
        editor_label_frame = ttk.Frame(self.prompt_edit_frame)
        editor_label_frame.pack(fill="x", padx=10, pady=(0, 5))
        
        editor_label = ttk.Label(editor_label_frame, text=_("prompt_content_label", "プロンプト内容:"), font=('Helvetica', 10))
        editor_label.pack(side="left")
        
        # 編集ステータス
        self.edit_status_var = tk.StringVar(value=_("status_unchanged", "未変更"))
        self.edit_status_label = ttk.Label(editor_label_frame, textvariable=self.edit_status_var,
                                         font=('Helvetica', 9), foreground="#999999")
        self.edit_status_label.pack(side="right")
        
        # プロンプト編集エリア（エディタ）
        from tkinter import scrolledtext
        self.prompt_text = scrolledtext.ScrolledText(
            self.prompt_edit_frame, 
            font=('Consolas', 10),
            wrap=tk.WORD,
            undo=True
        )
        self.prompt_text.pack(expand=True, fill="both", padx=10, pady=(0, 10))
        
        # テキスト変更時のイベント設定
        self.prompt_text.bind("<<Modified>>", self.on_prompt_text_modified)
    
    def setup_prompt_button_frame(self):
        """プロンプト操作ボタンフレームの設定"""
        # ボタンエリア（ステータスバー的なフレーム）
        self.prompt_button_frame = ttk.Frame(self.parent)
        self.prompt_button_frame.pack(fill="x", side="bottom", padx=0, pady=0)
        
        # 区切り線
        separator = ttk.Separator(self.prompt_button_frame, orient="horizontal")
        separator.pack(fill="x")
        
        # ボタン配置用の内部フレーム
        button_container = ttk.Frame(self.prompt_button_frame)
        button_container.pack(fill="x", padx=10, pady=8)
        
        # 新規ボタン
        self.new_prompt_button = ttk.Button(
            button_container, 
            text=_("new_prompt_button", "新規作成"), 
            command=self.create_new_prompt,
            style="Accent.TButton"
        )
        self.new_prompt_button.pack(side="left", padx=(0, 5))
        
        # 名前を付けて保存ボタン
        self.save_as_prompt_button = ttk.Button(
            button_container, 
            text=_("save_as_button", "名前を付けて保存"), 
            command=self.save_prompt_as
        )
        self.save_as_prompt_button.pack(side="left", padx=5)
        
        # 保存ボタン
        self.save_prompt_button = ttk.Button(
            button_container, 
            text=_("save_button_with_shortcut", "保存 (Ctrl+S)"), 
            command=self.save_current_prompt
        )
        self.save_prompt_button.pack(side="left", padx=5)
        
        # 削除ボタン - 右端に配置
        self.delete_prompt_button = ttk.Button(
            button_container, 
            text=_("delete_button", "削除"), 
            command=self.delete_current_prompt
        )
        self.delete_prompt_button.pack(side="right")
        
        # 文字数カウンタ
        self.prompt_char_count_var = tk.StringVar(value=_("char_count", "文字数: {0}").format(0))
        char_count_label = ttk.Label(
            button_container, 
            textvariable=self.prompt_char_count_var,
            font=('Helvetica', 9),
            foreground="#666666"
        )
        char_count_label.pack(side="right", padx=10)
    
    def bind_prompt_shortcuts(self):
        """プロンプト編集関連のショートカットキーをバインド"""
        # Ctrl+S で保存
        self.prompt_text.bind("<Control-s>", lambda event: self.save_current_prompt())
        # Ctrl+N で新規作成
        self.prompt_text.bind("<Control-n>", lambda event: self.create_new_prompt())
        # Ctrl+Shift+S で名前を付けて保存
        self.prompt_text.bind("<Control-Shift-S>", lambda event: self.save_prompt_as())
        # エスケープキーでフォーカスをプロンプトリストに移動
        self.prompt_text.bind("<Escape>", lambda event: self.prompt_tree.focus_set())
    
    def add_tooltip(self, widget, text):
        """ウィジェットにツールチップを追加"""
        # シンプルなツールチップ実装
        def enter(event):
            if not hasattr(self, 'tooltip'):
                self.tooltip = tk.Toplevel(widget)
                self.tooltip.wm_overrideredirect(True)
                self.tooltip.wm_geometry(f"+{event.x_root+15}+{event.y_root+10}")
                label = ttk.Label(self.tooltip, text=text, background="#FFFFCC", 
                                 relief="solid", borderwidth=1, padding=2)
                label.pack()
        
        def leave(event):
            if hasattr(self, 'tooltip'):
                self.tooltip.destroy()
                del self.tooltip
        
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)
    
    def on_prompt_selected(self, event):
        """プロンプトが選択されたときの処理"""
        selected_items = self.prompt_tree.selection()
        if not selected_items:
            return
        
        # 選択された新しいプロンプトID
        new_prompt_id = selected_items[0]
        
        # 選択が変わっていない場合は何もしない
        if new_prompt_id == self.current_prompt_id:
            return
        
        # 未保存の変更があれば確認
        if hasattr(self, 'prompt_modified') and self.prompt_modified:
            if not messagebox.askyesno(_("confirm_title", "確認"), _("confirm_discard_changes", "現在のプロンプトに未保存の変更があります。\n変更を破棄しますか？")):
                # 選択を元に戻す（現在の選択を維持）
                self.prompt_tree.selection_remove(new_prompt_id)  # 新しい選択を解除
                if self.current_prompt_id:
                    self.prompt_tree.selection_set(self.current_prompt_id)
                    self.prompt_tree.focus(self.current_prompt_id)
                return
        
        # ここから先は変更を破棄するか、変更がない場合の処理
        self.current_prompt_id = new_prompt_id
        
        # プロンプト名と内容を表示
        prompt_name = self.prompt_manager.get_prompt_name(new_prompt_id)
        prompt_content = self.prompt_manager.get_prompt(new_prompt_id)
        
        self.prompt_name_var.set(prompt_name)
        
        # テキスト変更イベントが発生しないように一時的にバインドを解除
        self.prompt_text.bind("<<Modified>>", lambda e: None)
        
        self.prompt_text.delete(1.0, tk.END)
        self.prompt_text.insert(tk.END, prompt_content)
        
        # 変更フラグをリセット
        self.prompt_modified = False
        self.edit_status_var.set(_("status_unchanged", "未変更"))
        
        # テキスト変更イベントを再バインド
        self.prompt_text.bind("<<Modified>>", self.on_prompt_text_modified)
        self.prompt_text.edit_modified(False)  # 変更フラグをリセット
        
        # 文字数を更新
        char_count = len(prompt_content)
        self.prompt_char_count_var.set(_("char_count", "文字数: {0}").format(char_count))

    def on_prompt_text_modified(self, event):
        """プロンプトテキストが変更されたときの処理"""
        # Modifiedフラグがセットされている場合のみ処理
        if self.prompt_text.edit_modified():
            try:
                # テキスト内容を取得して文字数をカウント
                text_content = self.prompt_text.get(1.0, tk.END)
                char_count = len(text_content) - 1  # 最後の改行文字を除く
                
                # 文字数表示を更新
                self.prompt_char_count_var.set(_("char_count", "文字数: {0}").format(char_count))
                
                # メインウィンドウのステータスバーも更新
                # メインウィンドウを検索して文字数表示を更新
                main_window = self.parent.winfo_toplevel()
                if hasattr(main_window, 'char_count_label'):
                    main_window.char_count_label.config(text=_("char_count", "文字数: {0}").format(char_count))
                
                # 変更フラグを設定
                self.prompt_modified = True
                self.edit_status_var.set(_("status_modified", "変更あり*"))
            except Exception as e:
                print(f"プロンプトテキスト変更エラー: {e}")
            
            # Modifiedフラグをリセット（次の変更を検知するため）
            self.prompt_text.edit_modified(False)

    def create_new_prompt(self):
        """新規プロンプトを作成"""
        # 未保存の変更があれば確認
        if hasattr(self, 'prompt_modified') and self.prompt_modified:
            if not messagebox.askyesno(_("confirm_title", "確認"), _("confirm_discard_changes", "現在のプロンプトに未保存の変更があります。\n変更を破棄しますか？")):
                return
        
        # デフォルトの新規プロンプトテンプレート
        template = _("""# [ファイル/ディレクトリ名]の解析プロンプト

    以下のコード構造を分析して：
    [解析結果]

    ## 質問/指示
    [ここに質問や指示を入力してください]

    ## 特記事項
    [特記事項があれば記入してください]
    """, "prompt_template")
        
        # 新しいプロンプトIDを取得
        prompt_id = self.prompt_manager.add_prompt(_("new_prompt_name", "新規プロンプト"), template)
        
        # プロンプト一覧を更新して新しいプロンプトを選択
        self.update_prompt_list()
        self.prompt_tree.selection_set(prompt_id)
        self.prompt_tree.focus(prompt_id)
        self.prompt_tree.see(prompt_id)  # 選択項目が見えるようにスクロール
        self.on_prompt_selected(None)
        
        # 名前入力フィールドにフォーカス
        self.prompt_name_entry.focus_set()
        self.prompt_name_entry.select_range(0, tk.END)
    
    def duplicate_current_prompt(self):
        """現在のプロンプトを複製"""
        if not self.current_prompt_id:
            return
        
        # 現在のプロンプトの名前と内容を取得
        current_name = self.prompt_name_var.get()
        current_content = self.prompt_text.get(1.0, tk.END).strip()
        
        # 複製名を生成
        copy_name = f"{current_name} のコピー"
        
        # 新しいプロンプトを追加
        new_id = self.prompt_manager.add_prompt(copy_name, current_content)
        
        # プロンプト一覧を更新して新しいプロンプトを選択
        self.update_prompt_list()
        self.prompt_tree.selection_set(new_id)
        self.prompt_tree.focus(new_id)
        self.prompt_tree.see(new_id)
        self.on_prompt_selected(None)
        
        # 名前入力フィールドにフォーカス
        self.prompt_name_entry.focus_set()
        self.prompt_name_entry.select_range(0, tk.END)
    
    def save_current_prompt(self, event=None):
        """現在のプロンプトを保存"""
        if not self.current_prompt_id:
            return
        
        prompt_name = self.prompt_name_var.get().strip()
        prompt_content = self.prompt_text.get(1.0, tk.END).strip()
        
        if not prompt_name:
            messagebox.showwarning(_("warning_title", "警告"), _("warning_empty_name", "プロンプト名を入力してください。"))
            self.prompt_name_entry.focus_set()
            return
        
        if self.prompt_manager.update_prompt(self.current_prompt_id, name=prompt_name, content=prompt_content):
            # 保存成功
            self.update_prompt_list()
            
            # 変更フラグをリセット
            self.prompt_modified = False
            self.edit_status_var.set(_("status_saved", "保存済み"))
            
            # 一定時間後に「未変更」に戻す
            self.parent.after(2000, lambda: self.edit_status_var.set(_("status_unchanged", "未変更")))
            
            # ツリービュー内の選択項目を保存済みの名前で表示
            item_index = self.prompt_tree.index(self.current_prompt_id)
            self.prompt_tree.item(self.current_prompt_id, values=(prompt_name,))
            
            return True
        else:
            messagebox.showerror(_("error_title", "エラー"), _("error_save_failed", "プロンプトの保存に失敗しました。"))
            return False
    
    def save_prompt_as(self, event=None):
        """名前を付けて保存"""
        prompt_name = self.prompt_name_var.get().strip()
        prompt_content = self.prompt_text.get(1.0, tk.END).strip()
        
        # 名前入力ダイアログ
        new_name = simpledialog.askstring(
            _("save_as_title", "名前を付けて保存"), 
            _("save_as_message", "新しいプロンプト名を入力してください:"),
            initialvalue=f"{prompt_name} のコピー" if prompt_name else _("new_prompt_name", "新規プロンプト")
        )
        
        if not new_name:
            return False  # キャンセルされた
        
        # 新しいプロンプトとして保存
        new_id = self.prompt_manager.add_prompt(new_name, prompt_content)

        # プロンプト一覧を更新して新しいプロンプトを選択
        self.update_prompt_list()
        self.prompt_tree.selection_set(new_id)
        self.prompt_tree.focus(new_id)
        self.prompt_tree.see(new_id)
        self.on_prompt_selected(None)
        
        return True
    
    def delete_current_prompt(self):
        """選択されているプロンプトを削除"""
        if not self.current_prompt_id:
            return
        
        prompt_name = self.prompt_manager.get_prompt_name(self.current_prompt_id)
        
        # 確認ダイアログにプロンプト名を表示
        if messagebox.askyesno(_("confirm_title", "確認"), _("confirm_delete_prompt", "プロンプト '{0}' を削除しますか？\nこの操作は元に戻せません。").format(prompt_name)):
            if self.prompt_manager.delete_prompt(self.current_prompt_id):
                # 削除成功
                all_prompts = self.prompt_manager.get_all_prompts()
                if all_prompts:
                    # 他のプロンプトがある場合は最初のプロンプトを選択
                    self.current_prompt_id = next(iter(all_prompts))
                else:
                    # 全てのプロンプトが削除された場合はデフォルトプロンプトを作成
                    self.prompt_manager.create_default_prompt()
                    self.current_prompt_id = next(iter(self.prompt_manager.get_all_prompts()))
                
                self.update_prompt_list()
                self.prompt_tree.selection_set(self.current_prompt_id)
                self.prompt_tree.focus(self.current_prompt_id)
                self.on_prompt_selected(None)
            else:
                messagebox.showinfo(_("info_title", "情報"), _("info_cannot_delete_last", "最後のプロンプトは削除できません。"))
    
    def update_prompt_list(self):
        """プロンプト一覧を更新"""
        # ツリービューをクリア
        for item in self.prompt_tree.get_children():
            self.prompt_tree.delete(item)
        
        # プロンプト一覧を追加
        for prompt_id, prompt in self.prompt_manager.get_all_prompts().items():
            self.prompt_tree.insert("", "end", iid=prompt_id, text="", values=(prompt["name"],))
        
        # 現在のプロンプトIDが設定されていて、そのプロンプトが存在する場合に選択
        if hasattr(self, 'current_prompt_id') and self.current_prompt_id:
            if self.current_prompt_id in self.prompt_manager.get_all_prompts():
                self.prompt_tree.selection_set(self.current_prompt_id)
                self.prompt_tree.focus(self.current_prompt_id)
                self.prompt_tree.see(self.current_prompt_id)  # 選択項目が見えるようにスクロール
    
    def save_current_prompt_without_confirm(self):
        """現在のプロンプトを確認なしで保存（終了時などに使用）"""
        if hasattr(self, 'prompt_modified') and self.prompt_modified and self.current_prompt_id:
            prompt_name = self.prompt_name_var.get().strip()
            prompt_content = self.prompt_text.get(1.0, tk.END).strip()
            
            if not prompt_name:
                prompt_name = _("untitled_prompt", "無題のプロンプト")
            
            self.prompt_manager.update_prompt(self.current_prompt_id, name=prompt_name, content=prompt_content)