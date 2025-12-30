# ui/snippet_view.py
import os
import tkinter as tk
from tkinter import ttk, messagebox
import pyperclip

class SnippetTreeView:
    """コードスニペットをツリーで表示するクラス"""
    
    def __init__(self, parent_frame, code_database, main_window=None):
        """
        コードスニペットツリービューの初期化
        
        :param parent_frame: 親フレーム
        :param code_database: CodeDatabaseインスタンス
        :param main_window: MainWindowインスタンス（任意）
        """
        self.parent_frame = parent_frame
        self.code_database = code_database
        self.main_window = main_window
        
        # スニペット表示用のメインフレーム
        self.main_frame = ttk.Frame(parent_frame)
        self.main_frame.pack(expand=True, fill="both")
        
        # 左右に分割するペインドウィンドウ
        self.paned_window = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        self.paned_window.pack(expand=True, fill="both")
        
        # 左側: ツリービューのフレーム
        self.tree_frame = ttk.Frame(self.paned_window, width=300)
        self.tree_frame.pack_propagate(False)
        
        # 右側: スニペット表示フレーム
        self.snippet_frame = ttk.Frame(self.paned_window)
        
        # フレームをペインドウィンドウに追加
        self.paned_window.add(self.tree_frame, weight=1)
        self.paned_window.add(self.snippet_frame, weight=2)
        
        # ツリービューのセットアップ
        self.setup_tree_view()
        
        # スニペット表示エリアのセットアップ
        self.setup_snippet_view()
        
        # ステータスバー
        self.status_bar = ttk.Label(self.main_frame, text="準備完了", anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=2)
        
        # 現在選択中のファイル
        self.current_file = None
        
        # 右クリックメニューのセットアップ
        self.setup_context_menu()
    
    def setup_tree_view(self):
        """ツリービューのセットアップ"""
        # ツリービューのラベル
        tree_label = ttk.Label(self.tree_frame, text="コードスニペット")
        tree_label.pack(side=tk.TOP, anchor=tk.W, padx=5, pady=5)
        
        # スクロールバー
        scrollbar = ttk.Scrollbar(self.tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # ツリービュー
        self.tree = ttk.Treeview(
            self.tree_frame,
            columns=("type", "lines"),
            height=20,
            selectmode="browse"
        )
        self.tree.pack(expand=True, fill="both")
        
        # スクロールバーとの連携
        self.tree.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.tree.yview)
        
        # カラム設定
        self.tree.column("#0", width=240, minwidth=200)
        self.tree.column("type", width=80, minwidth=60)
        self.tree.column("lines", width=60, minwidth=40)
        
        # ヘッダー
        self.tree.heading("#0", text="名前")
        self.tree.heading("type", text="種類")
        self.tree.heading("lines", text="行数")
        
        # アイテム選択時のイベント
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        
        # ダブルクリックイベント
        self.tree.bind("<Double-1>", self.on_tree_double_click)
    
    def setup_snippet_view(self):
        """スニペット表示エリアのセットアップ"""
        # スニペットビューのラベルフレーム
        self.snippet_label_frame = ttk.Frame(self.snippet_frame)
        self.snippet_label_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # スニペットラベル
        self.snippet_label = ttk.Label(self.snippet_label_frame, text="選択されたスニペット")
        self.snippet_label.pack(side=tk.LEFT)
        
        # コピーボタン
        self.copy_button = ttk.Button(
            self.snippet_label_frame, 
            text="コピー",
            command=self.copy_snippet
        )
        self.copy_button.pack(side=tk.RIGHT, padx=5)
        
        # スニペットテキストエリア（構文ハイライト対応）
        self.snippet_text = tk.Text(
            self.snippet_frame,
            wrap=tk.NONE,
            font=("Consolas", 10),
            background="#FFFFFF",
            foreground="#000000"
        )
        
        # スクロールバー（水平・垂直）
        h_scrollbar = ttk.Scrollbar(self.snippet_frame, orient=tk.HORIZONTAL)
        v_scrollbar = ttk.Scrollbar(self.snippet_frame)
        
        # テキストエリアとスクロールバーのレイアウト
        self.snippet_text.pack(expand=True, fill=tk.BOTH)
        h_scrollbar.pack(fill=tk.X)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # スクロールバーとの連携
        self.snippet_text.config(
            xscrollcommand=h_scrollbar.set,
            yscrollcommand=v_scrollbar.set
        )
        h_scrollbar.config(command=self.snippet_text.xview)
        v_scrollbar.config(command=self.snippet_text.yview)
        
        # 構文ハイライト用のタグ
        self.setup_syntax_tags()
        
        # 読み取り専用設定
        self.snippet_text.config(state=tk.DISABLED)
    
    def setup_syntax_tags(self):
        """構文ハイライト用のタグ設定"""
        # Pythonの基本キーワードに対するタグ
        self.snippet_text.tag_configure(
            "keyword", 
            foreground="#0000FF"
        )
        
        # 文字列に対するタグ
        self.snippet_text.tag_configure(
            "string", 
            foreground="#008000"
        )
        
        # コメントに対するタグ
        self.snippet_text.tag_configure(
            "comment", 
            foreground="#808080", 
            font=("Consolas", 10, "italic")
        )
        
        # 関数定義に対するタグ
        self.snippet_text.tag_configure(
            "function", 
            foreground="#7F0055", 
            font=("Consolas", 10, "bold")
        )
        
        # クラス定義に対するタグ
        self.snippet_text.tag_configure(
            "class", 
            foreground="#7F0055", 
            font=("Consolas", 10, "bold")
        )
    
    def setup_context_menu(self):
        """右クリックメニューのセットアップ"""
        self.context_menu = tk.Menu(self.tree, tearoff=0)
        self.context_menu.add_command(label="コピー", command=self.copy_snippet)
        self.context_menu.add_command(label="詳細表示", command=self.show_snippet_details)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="LLMに送信...", command=self.send_to_llm)
        
        # 右クリックイベント
        self.tree.bind("<Button-3>", self.show_context_menu)
    
    def show_context_menu(self, event):
        """右クリックメニューを表示"""
        # 選択されたアイテムを取得
        item = self.tree.identify_row(event.y)
        if item:
            # 選択状態にする
            self.tree.selection_set(item)
            # メニューを表示
            try:
                self.context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.context_menu.grab_release()
    
    def load_snippets_from_file(self, file_path):
        """指定されたファイルのスニペットをロード"""
        self.current_file = file_path
        
        # ツリービューをクリア
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        try:
            # ファイルの変更チェック - タイムスタンプが古い場合はスキップ
            if not self.code_database.needs_update(file_path):
                # データベースからスニペットを取得
                snippets = self.code_database.get_snippets_by_file(file_path)
                
                if not snippets:
                    self.status_bar.config(text=f"ファイル '{os.path.basename(file_path)}' にスニペットが見つかりません")
                    return
                
                # ファイルノードを追加
                file_node = self.tree.insert(
                    "", 
                    "end", 
                    text=os.path.basename(file_path),
                    values=("file", "")
                )
                
                # スニペットタイプごとにグループ化
                class_nodes = {}  # class_name -> node_id のマッピング
                
                # すべてのスニペットを処理
                for snippet in snippets:
                    snippet_id, name, type_name, code, line_start, line_end, char_count = snippet
                    
                    # 行数計算
                    line_count = line_end - line_start if line_start and line_end else code.count('\n') + 1
                    
                    if type_name == 'class':
                        # クラスノードを追加
                        class_node = self.tree.insert(
                            file_node,
                            "end",
                            text=name,
                            values=(type_name, line_count),
                            tags=("class",)
                        )
                        class_nodes[name] = class_node
                        
                    elif type_name == 'function':
                        # 親クラスのチェック（メソッドの場合）
                        parent_class = None
                        for cls_name, cls_node in class_nodes.items():
                            if name.startswith(f"{cls_name}."):
                                # クラスメソッド
                                method_name = name.split('.')[1]
                                self.tree.insert(
                                    cls_node,
                                    "end",
                                    text=method_name,
                                    values=("method", line_count),
                                    tags=("method",)
                                )
                                parent_class = cls_name
                                break
                        
                        if not parent_class:
                            # 通常の関数
                            self.tree.insert(
                                file_node,
                                "end",
                                text=name,
                                values=(type_name, line_count),
                                tags=("function",)
                            )
                    
                    elif type_name == 'import':
                        # インポート文
                        self.tree.insert(
                            file_node,
                            "end",
                            text=name[:30] + ('...' if len(name) > 30 else ''),
                            values=(type_name, 1),
                            tags=("import",)
                        )
                
                # 最初のノードを展開
                self.tree.item(file_node, open=True)
                
                # ステータス更新
                self.status_bar.config(text=f"ファイル '{os.path.basename(file_path)}' から {len(snippets)} 個のスニペットを読み込みました")
            else:
                # ファイルが変更されている場合
                if self.main_window:
                    # MainWindowの解析メソッドを呼び出し
                    self.main_window.analyze_file(file_path)
                    # 読み込み直し
                    self.load_snippets_from_file(file_path)
                else:
                    self.status_bar.config(text=f"ファイル '{os.path.basename(file_path)}' は変更されています。再解析が必要です。")
        
        except Exception as e:
            messagebox.showerror("エラー", f"スニペットの読み込み中にエラーが発生しました: {str(e)}")
            self.status_bar.config(text="エラー: スニペットの読み込みに失敗しました")
    
    def on_tree_select(self, event):
        """ツリーアイテム選択イベントのハンドラ"""
        selected_items = self.tree.selection()
        if not selected_items:
            return
        
        # 選択されたアイテムの情報を取得
        item_id = selected_items[0]
        item_type = self.tree.item(item_id, "values")[0]
        
        # ファイル自体が選択された場合はスキップ
        if item_type == "file":
            return
        
        # テキストエリアを更新可能にする
        self.snippet_text.config(state=tk.NORMAL)
        self.snippet_text.delete(1.0, tk.END)
        
        # 選択されたアイテムの完全パスを取得
        full_path = self.get_item_full_path(item_id)
        
        try:
            # データベースから該当スニペットのコードを取得
            cursor = self.code_database.connection.cursor()
            
            # クエリ構築
            query = "SELECT code, description, type FROM code_snippets WHERE file_path = ? AND "
            
            if item_type == "method":
                # メソッドの場合、親クラスと組み合わせる
                parent_id = self.tree.parent(item_id)
                class_name = self.tree.item(parent_id, "text")
                method_name = self.tree.item(item_id, "text")
                full_name = f"{class_name}.{method_name}"
                query += "name = ?"
                params = (self.current_file, full_name)
            else:
                # 通常の関数/クラスの場合
                query += "name = ? AND type = ?"
                params = (self.current_file, full_path, item_type)
            
            # クエリ実行
            cursor.execute(query, params)
            result = cursor.fetchone()
            
            if result:
                code, description, type_name = result
                
                # コード表示
                if self.current_file:
                    # ヘッダー情報を追加
                    header = f"## ディレクトリ: {os.path.dirname(self.current_file)}\n"
                    header += f"### ファイル: {os.path.basename(self.current_file)}\n"
                    
                    # タイプとパス表示
                    header += f"# {item_type.capitalize()}: {full_path}\n\n"
                    
                    # 説明があれば表示
                    if description:
                        header += f"\"{description}\"\n\n"
                    
                    self.snippet_text.insert(tk.END, header)
                
                # コード本体表示
                self.snippet_text.insert(tk.END, code)
                
                # 構文ハイライト適用
                self.apply_syntax_highlight()
                
                # スニペットラベル更新
                self.snippet_label.config(text=f"{item_type.capitalize()}: {full_path}")
                
                # ステータス更新
                lines = code.count('\n') + 1
                self.status_bar.config(text=f"{item_type.capitalize()} '{full_path}' を表示中 ({lines} 行)")
            else:
                self.snippet_text.insert(tk.END, f"スニペット '{full_path}' が見つかりません。")
        
        except Exception as e:
            self.snippet_text.insert(tk.END, f"スニペット読み込みエラー: {str(e)}")
        
        # テキストエリアを読み取り専用に戻す
        self.snippet_text.config(state=tk.DISABLED)
    
    def get_item_full_path(self, item_id):
        """ツリーアイテムの完全パスを取得（階層を含む）"""
        name = self.tree.item(item_id, "text")
        
        # 親ノードをたどる
        parent_id = self.tree.parent(item_id)
        if parent_id:
            parent_type = self.tree.item(parent_id, "values")[0]
            if parent_type == "class":
                # クラスメソッドの場合
                parent_name = self.tree.item(parent_id, "text")
                return f"{parent_name}.{name}"
        
        return name
    
    def on_tree_double_click(self, event):
        """ツリーアイテムのダブルクリックイベントのハンドラ"""
        item = self.tree.identify_row(event.y)
        if item:
            item_type = self.tree.item(item, "values")[0]
            if item_type != "file":
                # スニペットコピー
                self.copy_snippet()
    
    def copy_snippet(self):
        """選択されたスニペットをクリップボードにコピー"""
        selected_items = self.tree.selection()
        if not selected_items:
            return
        
        # 選択されたアイテムのコードを取得
        snippet_text = self.snippet_text.get(1.0, tk.END).strip()
        if snippet_text:
            # クリップボードにコピー
            pyperclip.copy(snippet_text)
            self.status_bar.config(text="スニペットをクリップボードにコピーしました")
    
    def show_snippet_details(self):
        """スニペットの詳細情報を表示"""
        selected_items = self.tree.selection()
        if not selected_items:
            return
        
        # 選択されたアイテムの情報を取得
        item_id = selected_items[0]
        item_type = self.tree.item(item_id, "values")[0]
        
        # ファイル自体が選択された場合はスキップ
        if item_type == "file":
            return
        
        # 選択されたアイテムの完全パスを取得
        full_path = self.get_item_full_path(item_id)
        
        try:
            # データベースから該当スニペットの詳細情報を取得
            cursor = self.code_database.connection.cursor()
            
            # クエリ構築 (詳細情報を取得)
            query = """
            SELECT code, description, line_start, line_end, char_count, updated_at 
            FROM code_snippets WHERE file_path = ? AND 
            """
            
            if item_type == "method":
                # メソッドの場合、親クラスと組み合わせる
                parent_id = self.tree.parent(item_id)
                class_name = self.tree.item(parent_id, "text")
                method_name = self.tree.item(item_id, "text")
                full_name = f"{class_name}.{method_name}"
                query += "name = ?"
                params = (self.current_file, full_name)
            else:
                # 通常の関数/クラスの場合
                query += "name = ? AND type = ?"
                params = (self.current_file, full_path, item_type)
            
            # クエリ実行
            cursor.execute(query, params)
            result = cursor.fetchone()
            
            if result:
                code, description, line_start, line_end, char_count, updated_at = result
                
                # 詳細情報ダイアログを表示
                details = f"名前: {full_path}\n"
                details += f"種類: {item_type}\n"
                if description:
                    details += f"説明: {description}\n"
                if line_start and line_end:
                    details += f"行範囲: {line_start} - {line_end}\n"
                if char_count:
                    details += f"文字数: {char_count}\n"
                if updated_at:
                    details += f"更新日時: {updated_at}\n"
                
                messagebox.showinfo("スニペット詳細", details)
            else:
                messagebox.showinfo("情報", f"スニペット '{full_path}' の詳細が見つかりません。")
        
        except Exception as e:
            messagebox.showerror("エラー", f"詳細情報の取得中にエラーが発生しました: {str(e)}")
    
    def send_to_llm(self):
        """選択されたスニペットをLLMに送信"""
        # LLM連携機能（必要に応じて実装）
        messagebox.showinfo("情報", "この機能は開発中です")
    
    def apply_syntax_highlight(self):
        """簡易的な構文ハイライトを適用"""
        # こちらは実装の一例です。より複雑なハイライトには外部ライブラリの活用を検討してください。
        content = self.snippet_text.get(1.0, tk.END)
        
        # キーワードリスト
        keywords = [
            "def", "class", "import", "from", "return", "if", "else", "elif",
            "try", "except", "finally", "for", "while", "in", "is", "not",
            "and", "or", "True", "False", "None", "self", "pass", "break",
            "continue", "with", "as", "lambda", "global", "nonlocal"
        ]
        
        # すべてのタグをクリア
        for tag in ["keyword", "string", "comment", "function", "class"]:
            self.snippet_text.tag_remove(tag, "1.0", tk.END)
        
        # キーワードのハイライト
        for keyword in keywords:
            start_pos = "1.0"
            while True:
                # キーワードを検索
                start_pos = self.snippet_text.search(
                    rf"\y{keyword}\y",  # 単語境界を考慮
                    start_pos, tk.END,
                    regexp=True
                )
                if not start_pos:
                    break
                    
                end_pos = f"{start_pos}+{len(keyword)}c"
                self.snippet_text.tag_add("keyword", start_pos, end_pos)
                start_pos = end_pos
        
        # コメントのハイライト
        start_pos = "1.0"
        while True:
            # 行コメントを検索
            start_pos = self.snippet_text.search(
                r"#.*$", 
                start_pos, tk.END,
                regexp=True
            )
            if not start_pos:
                break
                
            line_end = self.snippet_text.index(f"{start_pos} lineend")
            self.snippet_text.tag_add("comment", start_pos, line_end)
            start_pos = f"{line_end}+1c"
        
        # 文字列のハイライト (シングルクォート)
        start_pos = "1.0"
        while True:
            # シングルクォート文字列を検索
            start_pos = self.snippet_text.search(
                r"'[^'\\]*(\\.[^'\\]*)*'", 
                start_pos, tk.END,
                regexp=True
            )
            if not start_pos:
                break
                
            content_range = self.snippet_text.get(start_pos, tk.END)
            if not content_range:
                break
                
            # 文字列の終わりを見つける
            match_len = 0
            in_escape = False
            for char in content_range:
                match_len += 1
                if char == "'" and not in_escape:
                    break
                if char == "\\":
                    in_escape = not in_escape
                else:
                    in_escape = False
            
            end_pos = f"{start_pos}+{match_len}c"
            self.snippet_text.tag_add("string", start_pos, end_pos)
            start_pos = end_pos
        
        # 文字列のハイライト (ダブルクォート)
        start_pos = "1.0"
        while True:
            # ダブルクォート文字列を検索
            start_pos = self.snippet_text.search(
                r'"[^"\\]*(\\.[^"\\]*)*"', 
                start_pos, tk.END,
                regexp=True
            )
            if not start_pos:
                break
                
            content_range = self.snippet_text.get(start_pos, tk.END)
            if not content_range:
                break
                
            # 文字列の終わりを見つける
            match_len = 0
            in_escape = False
            for char in content_range:
                match_len += 1
                if char == '"' and not in_escape:
                    break
                if char == "\\":
                    in_escape = not in_escape
                else:
                    in_escape = False
            
            end_pos = f"{start_pos}+{match_len}c"
            self.snippet_text.tag_add("string", start_pos, end_pos)
            start_pos = end_pos
        
        # 関数・クラス定義のハイライト
        start_pos = "1.0"
        while True:
            # 関数定義を検索
            start_pos = self.snippet_text.search(
                r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)", 
                start_pos, tk.END,
                regexp=True
            )
            if not start_pos:
                break
                
            # "def"部分にキーワードタグ
            keyword_end = f"{start_pos}+3c"
            self.snippet_text.tag_add("keyword", start_pos, keyword_end)
            
            # 関数名部分に関数タグ
            name_start = self.snippet_text.search(
                r"[a-zA-Z_][a-zA-Z0-9_]*", 
                keyword_end, tk.END,
                regexp=True
            )
            if name_start:
                content_range = self.snippet_text.get(name_start, tk.END)
                if content_range:
                    name_len = 0
                    for char in content_range:
                        if not (char.isalnum() or char == '_'):
                            break
                        name_len += 1
                    
                    name_end = f"{name_start}+{name_len}c"
                    self.snippet_text.tag_add("function", name_start, name_end)
                    start_pos = name_end
                else:
                    start_pos = f"{keyword_end}+1c"
            else:
                start_pos = f"{keyword_end}+1c"
        
        # クラス定義のハイライト
        start_pos = "1.0"
        while True:
            # クラス定義を検索
            start_pos = self.snippet_text.search(
                r"class\s+([a-zA-Z_][a-zA-Z0-9_]*)", 
                start_pos, tk.END,
                regexp=True
            )
            if not start_pos:
                break
                
            # "class"部分にキーワードタグ
            keyword_end = f"{start_pos}+5c"
            self.snippet_text.tag_add("keyword", start_pos, keyword_end)
            
            # クラス名部分にクラスタグ
            name_start = self.snippet_text.search(
                r"[a-zA-Z_][a-zA-Z0-9_]*", 
                keyword_end, tk.END,
                regexp=True
            )
            if name_start:
                content_range = self.snippet_text.get(name_start, tk.END)
                if content_range:
                    name_len = 0
                    for char in content_range:
                        if not (char.isalnum() or char == '_'):
                            break
                        name_len += 1
                    
                    name_end = f"{name_start}+{name_len}c"
                    self.snippet_text.tag_add("class", name_start, name_end)
                    start_pos = name_end
                else:
                    start_pos = f"{keyword_end}+1c"
            else:
                start_pos = f"{keyword_end}+1c"