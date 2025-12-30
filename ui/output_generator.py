# ui/output_generator.py
"""出力生成機能を管理するクラス"""

import os
import tkinter as tk
import traceback

from utils.i18n import _
from utils.json_converter import text_to_json_structure, extract_llm_structured_data


class OutputGenerator:
    """マーメードダイアグラムやJSON出力を生成するクラス"""

    def __init__(self, main_window):
        """
        出力ジェネレーターを初期化

        Args:
            main_window: MainWindowインスタンス（親ウィンドウへの参照）
        """
        self.main_window = main_window

    def generate_mermaid_output(self):
        """現在の解析結果からマーメードダイアグラムを生成してマーメードタブに表示する"""
        mw = self.main_window

        # 既存の解析結果を取得
        if not hasattr(mw, 'astroid_analyzer') or not mw.astroid_analyzer.dependencies:
            mw.mermaid_text.delete(1.0, tk.END)
            mw.mermaid_text.insert(tk.END, "マーメードダイアグラム生成に必要な解析データがありません。")
            return

        try:
            # マーメードテキスト初期化
            mermaid_text = ""

            # 1. クラス図
            if mw.astroid_analyzer.classes:
                mermaid_text += "```mermaid\n%% クラス図\nclassDiagram\n"

                # クラス定義と継承関係
                for cls in mw.astroid_analyzer.classes:
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
            sorted_callers = sorted(mw.astroid_analyzer.dependencies.items(),
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
                if mw.current_dir:
                    python_files = mw.dir_tree_view.get_included_files(include_python_only=True)
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
                    if hasattr(mw, 'astroid_analyzer') and hasattr(mw.astroid_analyzer, 'functions'):
                        # main関数を探す
                        main_functions = [f for f in mw.astroid_analyzer.functions if f.get('name') == 'main']
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
            mw.mermaid_text.delete(1.0, tk.END)
            mw.mermaid_text.insert(tk.END, mermaid_text)

            # シンタックスハイライト適用
            if hasattr(mw, 'mermaid_highlighter'):
                mw.mermaid_highlighter.highlight()

            # 文字数更新
            current_tab_index = mw.tab_control.index(mw.tab_control.select())
            if current_tab_index == 3:  # マーメードタブ
                char_count = len(mermaid_text)
                mw.char_count_label.config(text=_("ui.status.char_count_value", "文字数: {0}").format(char_count))

        except Exception as e:
            traceback.print_exc()
            mw.mermaid_text.delete(1.0, tk.END)
            mw.mermaid_text.insert(tk.END, f"マーメードダイアグラム生成中にエラーが発生しました: {str(e)}")

    def generate_json_output(self):
        """現在の解析結果からJSON出力を生成してJSONタブに表示する"""
        mw = self.main_window

        # 現在の解析結果を取得
        result_text = mw.result_text.get(1.0, "end-1c")
        extended_text = mw.extended_text.get(1.0, "end-1c")

        if not result_text.strip():
            mw.json_text.delete(1.0, tk.END)
            mw.json_text.insert(tk.END, "JSONに変換する解析結果がありません。")
            return

        try:
            # テキストをJSON構造に変換
            json_data = text_to_json_structure(result_text)

            # ディレクトリ構造をJSONの冒頭に追加
            if mw.selected_file:
                # ファイルモードの場合は、そのファイルを含むディレクトリを取得
                python_files = [mw.selected_file]
            else:
                # ディレクトリモードの場合は含まれるPythonファイルを取得
                python_files = mw.dir_tree_view.get_included_files(include_python_only=True)

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
            mw.json_text.delete(1.0, tk.END)
            mw.json_text.insert(tk.END, json_string)

            # シンタックスハイライトを適用
            mw.json_highlighter.highlight()

            # 現在表示されているタブがJSONタブの場合のみ文字数を更新
            current_tab_index = mw.tab_control.index(mw.tab_control.select())
            if current_tab_index == 2:  # JSONタブ (JSONタブが3番目)
                char_count = len(json_string)
                mw.char_count_label.config(text=_("ui.status.char_count_value", "文字数: {0}").format(char_count))

        except Exception as e:
            traceback.print_exc()
            mw.json_text.delete(1.0, tk.END)
            mw.json_text.insert(tk.END, f"JSON変換中にエラーが発生しました: {str(e)}")

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

    def generate_advanced_mermaid_for_llm(self):
        """LLM向けに詳細なコード情報をマーメードダイアグラムで生成する"""
        mw = self.main_window

        try:
            mermaid_text = ""

            # 1. 拡張クラス図（docstring情報付き）
            mermaid_text += "```mermaid\n"
            mermaid_text += "classDiagram\n"

            # サブシステム境界の定義
            modules = set()
            for cls in mw.astroid_analyzer.classes:
                module = cls.get("module", "unknown")
                modules.add(module)

            # サブグラフでモジュール/サブシステムを表現
            for module in modules:
                mermaid_text += f"  namespace {module} {{\n"
                # モジュール内のクラスを追加
                for cls in [c for c in mw.astroid_analyzer.classes if c.get("module") == module]:
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
            for func in mw.astroid_analyzer.functions:
                func_name = func["name"]

                # 入力パラメータと出力(戻り値)の分析
                params = [p.get("name") for p in func.get("parameters", [])]

                # 関数の呼び出し関係を検証
                if func_name in mw.astroid_analyzer.dependencies:
                    for callee in mw.astroid_analyzer.dependencies[func_name]:
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
            for func in mw.astroid_analyzer.functions:
                func_name = func["name"]
                # 関数の複雑さを推定
                lines = func.get("source_lines", 0)
                calls = len(mw.astroid_analyzer.dependencies.get(func_name, []))
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
                module_classes = [c for c in mw.astroid_analyzer.classes if c.get("module") == module]
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
