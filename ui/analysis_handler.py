# ui/analysis_handler.py
"""解析機能を管理するクラス"""

import os
import tkinter as tk
from tkinter import ttk, messagebox
import traceback

from utils.i18n import _
from core.dependency import generate_call_graph
from utils.code_extractor import CodeExtractor


class AnalysisHandler:
    """解析処理を管理するクラス"""

    def __init__(self, main_window):
        """
        解析ハンドラーを初期化

        Args:
            main_window: MainWindowインスタンス（親ウィンドウへの参照）
        """
        self.main_window = main_window

    def analyze_selected(self):
        """選択されたファイルまたはディレクトリを解析"""
        mw = self.main_window

        # ファイルモードかディレクトリモードかを明示的に確認
        file_mode = mw.selected_file and os.path.isfile(mw.selected_file)

        # ファイルモードの場合は、そのファイルだけを解析
        if file_mode:
            self.analyze_file(mw.selected_file)
            return

        # ディレクトリモードの場合は、含まれるPythonファイルのみを解析
        included_files = mw.dir_tree_view.get_included_files(include_python_only=True)

        if not included_files:
            messagebox.showinfo("情報", "解析対象のPythonファイルがありません。\n"
                               "ディレクトリを選択し、Pythonファイルが含まれていることを確認してください。\n"
                               "または、Pythonファイルがすべて「除外」状態になっていないか確認してください。")
            return

        # 解析実行
        result, char_count = mw.analyzer.analyze_files(included_files)

        # 結果表示
        mw.result_text.delete(1.0, tk.END)
        mw.result_text.insert(tk.END, result)
        mw.result_highlighter.highlight()
        mw.char_count_label.config(text=_("ui.status.char_count_value", "文字数: {0}").format(char_count))

        # ステータス更新
        mw.file_status.config(text=f"{len(included_files)} 個のPythonファイルを解析しました")

        # 拡張解析を実行
        self.perform_extended_analysis(included_files)

    def analyze_file(self, file_path):
        """単一のファイルを解析"""
        mw = self.main_window

        try:
            # 通常の解析（UI表示用）
            result, char_count = mw.analyzer.analyze_file(file_path)

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
            mw.result_text.delete(1.0, tk.END)
            mw.result_text.insert(tk.END, formatted_result)
            mw.result_highlighter.highlight()

            # コード抽出モジュールを使用してデータベースに保存
            extractor = CodeExtractor(mw.code_database)

            try:
                # コード抽出と保存を実行
                snippet_count = extractor.extract_from_file(file_path)
                mw.current_file = file_path  # 現在のファイルパスを保存

                # ステータス表示を更新
                mw.file_status.config(
                    text=_("ui.status.file_extracted", "ファイル: {0}（{1}個のスニペットを抽出）")
                    .format(os.path.basename(file_path), snippet_count)
                )
            except Exception as ex:
                print(f"コード抽出エラー: {str(ex)}")
                traceback.print_exc()
                # エラーは表示するが処理は続行

            # 現在表示されているタブが解析結果タブの場合のみ文字数を更新
            current_tab_index = mw.tab_control.index(mw.tab_control.select())
            if current_tab_index == 0:
                mw.char_count_label.config(text=_("ui.status.char_count_value", "文字数: {0}").format(file_char_count))

            # 拡張解析を実行
            self.perform_extended_analysis([file_path])

            # JSON出力を生成
            mw.generate_json_output()

            # マーメードダイアグラムを生成
            mw.generate_mermaid_output()

        except Exception as e:
            traceback.print_exc()
            messagebox.showerror(
                _("ui.dialogs.error_title", "エラー"),
                _("ui.messages.analysis_error", "ファイルの解析中にエラーが発生しました:\n{0}").format(str(e))
            )

    def perform_extended_analysis(self, python_files):
        """astroidによる拡張解析を実行する"""
        mw = self.main_window

        try:
            import astroid

            if not python_files:
                mw.extended_text.delete(1.0, tk.END)
                mw.extended_text.insert(tk.END, "拡張解析対象のPythonファイルがありません。")
                return

            # 解析結果を保存する辞書
            analysis_results = {}
            module_nodes = {}

            # プログレスウィンドウを表示
            progress_window = tk.Toplevel(mw.root)
            progress_window.title("拡張解析中")
            progress_window.geometry("400x100")
            progress_window.transient(mw.root)

            progress_label = ttk.Label(progress_window, text=f"ファイルを解析中... (0/{len(python_files)})")
            progress_label.pack(pady=10)

            progress_bar = ttk.Progressbar(progress_window, mode="determinate", maximum=100)
            progress_bar.pack(fill="x", padx=20)

            # ウィンドウを中央に配置
            progress_window.update_idletasks()
            x = mw.root.winfo_rootx() + (mw.root.winfo_width() - progress_window.winfo_width()) // 2
            y = mw.root.winfo_rooty() + (mw.root.winfo_height() - progress_window.winfo_height()) // 2
            progress_window.geometry(f"+{x}+{y}")

            # 統合解析レポート用の情報
            all_classes = []
            all_functions = []
            all_dependencies = {}
            all_inheritance = {}

            # ディレクトリ構造を取得
            directory_structure = mw.get_directory_structure(python_files)

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
                    mw.astroid_analyzer.reset()
                    file_result, _ = mw.astroid_analyzer.analyze_code(code, os.path.basename(file_path))

                    # 結果を蓄積
                    analysis_results[file_path] = {
                        'name': os.path.basename(file_path),
                        'classes': mw.astroid_analyzer.classes.copy(),
                        'functions': mw.astroid_analyzer.functions.copy(),
                        'dependencies': mw.astroid_analyzer.dependencies.copy(),
                        'inheritance': mw.astroid_analyzer.inheritance.copy(),
                        'char_count': file_char_count  # 文字数を追加
                    }

                    # データベースにタイムスタンプを更新
                    mw.code_database.update_file_timestamp(file_path)

                    # 全体のリストに追加
                    all_classes.extend(mw.astroid_analyzer.classes)
                    all_functions.extend(mw.astroid_analyzer.functions)
                    all_dependencies.update(mw.astroid_analyzer.dependencies)
                    all_inheritance.update(mw.astroid_analyzer.inheritance)

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
            mw.extended_text.delete(1.0, tk.END)
            mw.extended_text.insert(tk.END, report)
            mw.extended_highlighter.highlight()

            # 現在表示されているタブが拡張解析タブの場合のみ文字数を更新
            current_tab_index = mw.tab_control.index(mw.tab_control.select())
            if current_tab_index == 1:  # 拡張解析タブ
                char_count = len(report)
                mw.char_count_label.config(text=_("ui.status.char_count_value", "文字数: {0}").format(char_count))

            # JSON出力を生成（拡張解析の後に呼び出し）
            mw.generate_json_output()

            # マーメードダイアグラムを生成
            mw.generate_mermaid_output()

        except ImportError:
            mw.extended_text.delete(1.0, tk.END)
            mw.extended_text.insert(tk.END, "astroidライブラリがインストールされていません。\n"
                                    "pip install astroid でインストールしてください。")
        except Exception as e:
            mw.extended_text.delete(1.0, tk.END)
            error_msg = f"拡張解析中にエラーが発生しました:\n{str(e)}"
            print(error_msg)
            traceback.print_exc()
            mw.extended_text.insert(tk.END, error_msg)

    def reanalyze_project(self):
        """プロジェクト全体を再分析"""
        mw = self.main_window

        try:
            # 確認ダイアログ
            if not messagebox.askyesno(_("確認"),
                _("プロジェクト全体を再分析します。この処理には時間がかかる場合があります。続行しますか？")):
                return

            # 進捗ダイアログ
            progress_window = tk.Toplevel(mw.root)
            progress_window.title(_("プロジェクト再分析"))
            progress_window.transient(mw.root)
            progress_window.geometry("400x150")
            progress_window.resizable(False, False)

            progress_label = ttk.Label(progress_window, text=_("データベースをリセットしています..."))
            progress_label.pack(pady=10)

            progress_bar = ttk.Progressbar(progress_window, mode="determinate")
            progress_bar.pack(fill="x", padx=20, pady=10)

            # データベースをリセット
            mw.code_database.connection.execute("DELETE FROM code_snippets")
            mw.code_database.connection.commit()

            # プロジェクトファイルの一覧取得
            files = []
            if hasattr(mw, "directory_tree") and mw.directory_tree:
                files = mw.directory_tree.get_included_files()

            # 進捗計算
            total_files = len(files)
            progress_bar["maximum"] = total_files

            # ファイルを再分析
            file_count = 0
            extractor = CodeExtractor(mw.code_database)

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
            if hasattr(mw, "current_file") and mw.current_file:
                self.analyze_file(mw.current_file)

        except Exception as e:
            print(f"プロジェクト再分析エラー: {str(e)}")
            traceback.print_exc()
            messagebox.showerror(_("エラー"),
                _(f"再分析中にエラーが発生しました:\n{str(e)}"))
