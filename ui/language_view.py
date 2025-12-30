# ui/language_view.py

"""
多言語解析結果の表示と言語間連携の可視化を行うUIモジュール
"""

import tkinter as tk
from tkinter import ttk
import json
from typing import Dict, List, Any, Callable, Optional

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.i18n import _


class LanguageConnectionView:
    """言語間連携の可視化と表示を行うクラス"""
    
    def __init__(self, parent, copy_callback: Callable = None):
        """
        初期化
        
        Args:
            parent: 親ウィジェット
            copy_callback: コピーボタンが押された時のコールバック関数
        """
        self.parent = parent
        self.copy_callback = copy_callback
        self.frame = ttk.Frame(parent)
        
        self.connection_data = {}
        self.current_language = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        """UIコンポーネントの初期化"""
        # メインフレームをグリッドで配置
        self.frame.grid(row=0, column=0, sticky="nsew")
        self.parent.rowconfigure(0, weight=1)
        self.parent.columnconfigure(0, weight=1)
        
        # 左右のペイン
        self.paned_window = ttk.PanedWindow(self.frame, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 左側: 言語リストと連携リスト
        self.left_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.left_frame, weight=1)
        
        # 右側: 詳細表示
        self.right_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.right_frame, weight=2)
        
        # 言語選択ラベルとタブ
        self.lang_label = ttk.Label(self.left_frame, text=_("検出された言語"))
        self.lang_label.pack(anchor=tk.W, padx=5, pady=5)
        
        # 言語タブ
        self.lang_notebook = ttk.Notebook(self.left_frame)
        self.lang_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 言語間連携タブ
        self.connections_tab = ttk.Frame(self.lang_notebook)
        self.lang_notebook.add(self.connections_tab, text=_("言語間連携"))
        
        # 言語間連携リスト
        self.connections_frame = ttk.Frame(self.connections_tab)
        self.connections_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.connections_tree = ttk.Treeview(self.connections_frame, columns=("from", "to", "type"), 
                                            show="headings", selectmode="browse")
        self.connections_tree.heading("from", text=_("元の言語"))
        self.connections_tree.heading("to", text=_("先の言語"))
        self.connections_tree.heading("type", text=_("タイプ"))
        
        self.connections_tree.column("from", width=80)
        self.connections_tree.column("to", width=80)
        self.connections_tree.column("type", width=100)
        
        self.connections_scrollbar = ttk.Scrollbar(self.connections_frame, orient="vertical", 
                                                 command=self.connections_tree.yview)
        self.connections_tree.configure(yscrollcommand=self.connections_scrollbar.set)
        
        self.connections_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.connections_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.connections_tree.bind("<<TreeviewSelect>>", self._on_connection_selected)
        
        # 詳細表示エリア
        self.details_label = ttk.Label(self.right_frame, text=_("詳細情報"))
        self.details_label.pack(anchor=tk.W, padx=5, pady=5)
        
        # 詳細表示テキストエリア
        self.details_frame = ttk.Frame(self.right_frame)
        self.details_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.details_text = tk.Text(self.details_frame, wrap=tk.WORD, width=50, height=20)
        self.details_scrollbar = ttk.Scrollbar(self.details_frame, orient="vertical", 
                                             command=self.details_text.yview)
        self.details_text.configure(yscrollcommand=self.details_scrollbar.set)
        
        self.details_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.details_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # マーメード図表示エリア
        self.mermaid_label = ttk.Label(self.right_frame, text=_("連携図"))
        self.mermaid_label.pack(anchor=tk.W, padx=5, pady=5)
        
        self.mermaid_frame = ttk.Frame(self.right_frame)
        self.mermaid_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.mermaid_text = tk.Text(self.mermaid_frame, wrap=tk.WORD, width=50, height=20)
        self.mermaid_scrollbar = ttk.Scrollbar(self.mermaid_frame, orient="vertical", 
                                             command=self.mermaid_text.yview)
        self.mermaid_text.configure(yscrollcommand=self.mermaid_scrollbar.set)
        
        self.mermaid_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.mermaid_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # コピーボタン
        self.button_frame = ttk.Frame(self.right_frame)
        self.button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.copy_button = ttk.Button(self.button_frame, text=_("マーメードをコピー"), 
                                     command=self._copy_mermaid)
        self.copy_button.pack(side=tk.RIGHT)
        
        self.copy_details_button = ttk.Button(self.button_frame, text=_("詳細情報をコピー"), 
                                            command=self._copy_details)
        self.copy_details_button.pack(side=tk.RIGHT, padx=5)
    
    def update_data(self, connection_data: Dict[str, Any]):
        """
        連携データを更新
        
        Args:
            connection_data: 言語連携データ（言語レジストリからの出力）
        """
        self.connection_data = connection_data
        
        # 既存のタブをクリア（連携タブを除く）
        for tab in self.lang_notebook.tabs():
            tab_id = self.lang_notebook.index(tab)
            tab_text = self.lang_notebook.tab(tab_id, "text")
            if tab_text != _("言語間連携"):
                self.lang_notebook.forget(tab_id)
        
        # 言語別タブを追加
        for language, data in connection_data.items():
            if language != "connections":
                # 言語名を取得
                if isinstance(data, dict) and "language" in data:
                    lang_display = data.get("language", language).capitalize()
                else:
                    lang_display = language.capitalize()
                
                lang_tab = ttk.Frame(self.lang_notebook)
                self.lang_notebook.add(lang_tab, text=lang_display)
                
                # 言語固有のツリービューを作成
                self._create_language_tree(lang_tab, language, data)
        
        # 連携リストを更新
        self._update_connections_tree(connection_data.get("connections", []))
        
        # マーメード図を更新
        self._update_mermaid()
    
    def _create_language_tree(self, parent, language: str, data: Dict[str, Any]):
        """言語ごとのコンポーネントツリービューを作成"""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        tree = ttk.Treeview(frame, columns=("name", "type"), show="headings", selectmode="browse")
        tree.heading("name", text=_("名前"))
        tree.heading("type", text=_("タイプ"))
        
        tree.column("name", width=150)
        tree.column("type", width=100)
        
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # データを挿入
        if isinstance(data, dict) and "components" in data:
            components = data["components"]
            
            # Flutter/Dartの場合
            if language == "flutter":
                for i, cls in enumerate(components.get("classes", [])):
                    tree.insert("", tk.END, values=(cls["name"], cls.get("type", "Class")), 
                               tags=(language, "class", json.dumps(cls)))
                
                for i, func in enumerate(components.get("functions", [])):
                    tree.insert("", tk.END, values=(func["name"], "Function"), 
                               tags=(language, "function", json.dumps(func)))
                
                for i, method in enumerate(components.get("methods", [])):
                    tree.insert("", tk.END, values=(method["name"], "Method"), 
                               tags=(language, "method", json.dumps(method)))
            
            # Python（将来的に他の言語も同様に）
            else:
                if isinstance(components, dict):
                    for comp_type, comps in components.items():
                        if isinstance(comps, list):
                            for comp in comps:
                                if isinstance(comp, dict) and "name" in comp:
                                    tree.insert("", tk.END, values=(comp["name"], comp_type.capitalize()), 
                                              tags=(language, comp_type, json.dumps(comp)))
        
        # ツリー選択イベントの設定
        tree.bind("<<TreeviewSelect>>", lambda e: self._on_component_selected(e, tree, language))
    
    def _update_connections_tree(self, connections: List[Dict[str, Any]]):
        """連携リストを更新"""
        # 現在のアイテムをクリア
        for item in self.connections_tree.get_children():
            self.connections_tree.delete(item)
        
        # 新しい連携を追加
        for i, conn in enumerate(connections):
            from_lang = conn.get("from_language", conn.get("from", "unknown"))
            to_lang = conn.get("to_language", conn.get("to", "unknown"))
            conn_type = conn.get("type", "unknown")
            
            self.connections_tree.insert("", tk.END, values=(from_lang, to_lang, conn_type), 
                                       tags=("connection", str(i)))
    
    def _on_connection_selected(self, event):
        """連携項目が選択された時のイベントハンドラ"""
        selection = self.connections_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        tags = self.connections_tree.item(item, "tags")
        
        if tags and len(tags) > 1:
            conn_index = int(tags[1])
            if "connections" in self.connection_data and conn_index < len(self.connection_data["connections"]):
                conn = self.connection_data["connections"][conn_index]
                self._display_connection_details(conn)
    
    def _on_component_selected(self, event, tree, language):
        """コンポーネント項目が選択された時のイベントハンドラ"""
        selection = tree.selection()
        if not selection:
            return
        
        item = selection[0]
        tags = tree.item(item, "tags")
        
        if tags and len(tags) > 2:
            try:
                comp_data = json.loads(tags[2])
                self._display_component_details(language, tags[1], comp_data)
            except Exception:
                pass
    
    def _display_connection_details(self, connection: Dict[str, Any]):
        """連携の詳細情報を表示"""
        self.details_text.delete(1.0, tk.END)
        
        # 基本情報
        self.details_text.insert(tk.END, f"{_('連携タイプ')}: {connection.get('type', 'Unknown')}\n\n")
        
        from_lang = connection.get("from_language", connection.get("from", "Unknown"))
        to_lang = connection.get("to_language", connection.get("to", "Unknown"))
        
        self.details_text.insert(tk.END, f"{_('元の言語')}: {from_lang.capitalize()}\n")
        self.details_text.insert(tk.END, f"{_('先の言語')}: {to_lang.capitalize()}\n\n")
        
        # 説明
        if "description" in connection:
            self.details_text.insert(tk.END, f"{_('説明')}: {connection['description']}\n\n")
        
        # 値
        if "value" in connection and connection["value"]:
            self.details_text.insert(tk.END, f"{_('値')}: {connection['value']}\n\n")
        
        # ファイル
        if "file" in connection:
            self.details_text.insert(tk.END, f"{_('ファイル')}: {connection['file']}\n\n")
        
        # コンポーネント
        if "component" in connection:
            comp = connection["component"]
            self.details_text.insert(tk.END, f"{_('関連コンポーネント')}:\n")
            self.details_text.insert(tk.END, f"  {_('タイプ')}: {comp.get('type', 'Unknown')}\n")
            self.details_text.insert(tk.END, f"  {_('名前')}: {comp.get('name', 'Unknown')}\n\n")
        
        # その他の属性
        self.details_text.insert(tk.END, f"{_('その他の情報')}:\n")
        for key, value in connection.items():
            if key not in ["type", "from_language", "to_language", "from", "to", 
                         "description", "value", "file", "component"]:
                self.details_text.insert(tk.END, f"  {key}: {value}\n")
    
    def _display_component_details(self, language: str, comp_type: str, comp_data: Dict[str, Any]):
        """コンポーネントの詳細情報を表示"""
        self.details_text.delete(1.0, tk.END)
        
        # 基本情報
        self.details_text.insert(tk.END, f"{_('言語')}: {language.capitalize()}\n")
        self.details_text.insert(tk.END, f"{_('コンポーネントタイプ')}: {comp_type.capitalize()}\n\n")
        
        # 名前
        if "name" in comp_data:
            self.details_text.insert(tk.END, f"{_('名前')}: {comp_data['name']}\n\n")
        
        # ファイル
        if "file" in comp_data:
            self.details_text.insert(tk.END, f"{_('ファイル')}: {comp_data['file']}\n\n")
        
        # クラス固有の情報
        if comp_type == "class" and "parent" in comp_data:
            self.details_text.insert(tk.END, f"{_('親クラス')}: {comp_data.get('parent', 'None')}\n")
            if "type" in comp_data:
                self.details_text.insert(tk.END, f"{_('クラスタイプ')}: {comp_data['type']}\n\n")
        
        # その他の属性
        self.details_text.insert(tk.END, f"{_('その他の情報')}:\n")
        for key, value in comp_data.items():
            if key not in ["name", "file", "parent", "type"]:
                self.details_text.insert(tk.END, f"  {key}: {value}\n")
        
        # 連携情報がある場合は表示
        self._display_component_connections(language, comp_type, comp_data)
    
    def _display_component_connections(self, language: str, comp_type: str, comp_data: Dict[str, Any]):
        """コンポーネントに関連する連携情報を表示"""
        if "connections" not in self.connection_data:
            return
        
        related_connections = []
        
        for conn in self.connection_data["connections"]:
            # コンポーネントに関連する連携を検索
            is_related = False
            
            if "component" in conn and conn.get("from_language", "") == language:
                component = conn["component"]
                if component.get("type") == comp_type and component.get("name") == comp_data.get("name"):
                    is_related = True
            
            # クラス名で直接チェック（Flutter）
            if language == "flutter" and comp_type == "class" and "class" in conn:
                if conn["class"] == comp_data.get("name"):
                    is_related = True
            
            if is_related:
                related_connections.append(conn)
        
        # 関連する連携があれば表示
        if related_connections:
            self.details_text.insert(tk.END, f"\n{_('関連する連携')}:\n")
            for i, conn in enumerate(related_connections):
                to_lang = conn.get("to_language", conn.get("to", "unknown"))
                conn_type = conn.get("type", "unknown")
                desc = conn.get("description", "")
                
                self.details_text.insert(tk.END, f"  {i+1}. {to_lang.capitalize()} ({conn_type}): {desc}\n")
    
    def _update_mermaid(self):
        """マーメード図を更新"""
        if "mermaid" in self.connection_data:
            mermaid_code = self.connection_data["mermaid"]
        else:
            # マーメード図がない場合は簡易的に生成
            mermaid_code = self._generate_simple_mermaid()
        
        self.mermaid_text.delete(1.0, tk.END)
        self.mermaid_text.insert(tk.END, mermaid_code)
    
    def _generate_simple_mermaid(self) -> str:
        """簡易的なマーメード図を生成"""
        mermaid = "```mermaid\nflowchart LR\n"
        
        # 言語ノードを作成
        languages = set()
        connections = self.connection_data.get("connections", [])
        
        for conn in connections:
            from_lang = conn.get("from_language", conn.get("from", "unknown"))
            to_lang = conn.get("to_language", conn.get("to", "unknown"))
            languages.add(from_lang)
            languages.add(to_lang)
        
        # 言語ノードを追加
        for lang in languages:
            mermaid += f"  {lang}[{lang.capitalize()}]:::{lang}\n"
        
        mermaid += "\n"
        
        # 連携を表す線を追加
        for conn in connections:
            from_lang = conn.get("from_language", conn.get("from", "unknown"))
            to_lang = conn.get("to_language", conn.get("to", "unknown"))
            conn_type = conn.get("type", "")
            
            mermaid += f"  {from_lang} -->|{conn_type}| {to_lang}\n"
        
        # スタイル定義
        mermaid += "\n  %% スタイル定義\n"
        mermaid += "  classDef python fill:#306998,stroke:#FFD43B,color:white;\n"
        mermaid += "  classDef flutter fill:#44D1FD,stroke:#0468D7,color:white;\n"
        mermaid += "  classDef javascript fill:#F7DF1E,stroke:#000000,color:black;\n"
        mermaid += "  classDef java fill:#ED8B00,stroke:#5382A1,color:white;\n"
        mermaid += "  classDef unknown fill:#888888,stroke:#444444,color:white;\n"
        mermaid += "```"
        
        return mermaid
    
    def _copy_mermaid(self):
        """マーメード図をクリップボードにコピー"""
        mermaid_text = self.mermaid_text.get(1.0, tk.END)
        if self.copy_callback:
            self.copy_callback(mermaid_text)
        else:
            self.parent.clipboard_clear()
            self.parent.clipboard_append(mermaid_text)
    
    def _copy_details(self):
        """詳細情報をクリップボードにコピー"""
        details_text = self.details_text.get(1.0, tk.END)
        if self.copy_callback:
            self.copy_callback(details_text)
        else:
            self.parent.clipboard_clear()
            self.parent.clipboard_append(details_text)