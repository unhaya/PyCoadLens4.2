# core/analyzer.py
import ast
import os

class CodeAnalyzer:
    """
    Pythonコードを解析して、クラス名、関数名を抽出するクラス
    """
    def __init__(self):
        self.imports = []
        self.classes = []
        self.functions = []
        self.report = ""
        self.char_count = 0
        self.include_imports = True
        self.include_docstrings = True 
    
    def reset(self):
        """解析結果をリセットする"""
        self.imports = []
        self.classes = []
        self.functions = []
        self.report = ""
        self.char_count = 0
    
    def analyze_file(self, file_path):
        """ファイルパスからコードを読み込んで解析する"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                code = file.read()
            return self.analyze_code(code, os.path.basename(file_path))
        except Exception as e:
            return f"ファイル解析エラー: {str(e)}", 0

    def analyze_files(self, file_paths):
        """複数のファイルを解析する"""
        self.reset()
        report_parts = []
        total_char_count = 0
        
        # ディレクトリ構造情報を生成
        all_dirs = set()
        for file_path in file_paths:
            dir_name = os.path.dirname(file_path)
            all_dirs.add(dir_name)
        
        # ディレクトリ構造をレポートに追加
        dir_structure = "# プロジェクト構造\n"
        root_dir = os.path.commonpath(list(all_dirs)) if all_dirs else ""
        if root_dir:
            dir_structure += f"ルートディレクトリ: {root_dir}\n"
            
            # サブディレクトリの一覧を表示
            for dir_path in sorted(all_dirs):
                rel_path = os.path.relpath(dir_path, root_dir)
                if rel_path != '.':  # ルートディレクトリ自体は除外
                    dir_structure += f"- {rel_path}/\n"
            
            dir_structure += "\n"
        
        report_parts.append(dir_structure)
        total_char_count += len(dir_structure)
        
        # 元の処理（ファイルごとの解析）を継続
        # ファイルをディレクトリごとにグループ化
        dir_files = {}
        for file_path in file_paths:
            dir_name = os.path.dirname(file_path)
            if dir_name not in dir_files:
                dir_files[dir_name] = []
            dir_files[dir_name].append(file_path)
        
        # ディレクトリごとに処理
        for dir_path, files in dir_files.items():
            # ディレクトリ名を追加
            dir_report = f"\n## ディレクトリ: {dir_path}\n"
            
            # Pythonファイルのみをフィルタリング
            py_files = [f for f in files if f.lower().endswith('.py')]
            
            # Pythonファイルがある場合のみ処理
            if py_files:
                # ディレクトリ内の各Pythonファイルを処理
                for file_path in sorted(py_files):
                    try:
                        file_name = os.path.basename(file_path)
                        
                        with open(file_path, 'r', encoding='utf-8') as f:
                            code = f.read()
                        
                        # ファイルの文字数を表示
                        file_char_count = len(code)
                        
                        # ファイルごとの解析結果
                        self.reset()
                        result, _ = self.analyze_code(code, file_name)
                        file_report = f"\n### ファイル: {file_name}\n"
                        file_report += f"文字数: {file_char_count:,}\n\n"
                        file_report += result
                        
                        dir_report += file_report
                        total_char_count += len(file_report)
                    except Exception as e:
                        file_report = f"\n### ファイル: {os.path.basename(file_path)}\n解析エラー: {str(e)}\n"
                        dir_report += file_report
                        total_char_count += len(file_report)
            
            report_parts.append(dir_report)

        # ファイル文字数の追加
        file_report = f"\n### ファイル: {file_name}\n"
        # ファイルの文字数を表示
        file_report += f"文字数: {len(code):,}\n\n"
        file_report += result

        # すべてのディレクトリのレポートを結合
        self.report = "\n".join(report_parts)
        self.char_count = total_char_count
        return self.report, self.char_count

    def analyze_code(self, code, filename="", directory_structure=""):
        """Pythonコードを解析する"""
        self.reset()
        try:
            tree = ast.parse(code)
            
            # docstring（モジュールレベルのドキュメント文字列）を取得
            module_docstring = ast.get_docstring(tree)
            
            # インポート文を格納する辞書を初期化（モジュール名をキーとする）
            import_dict = {}
            
            # インポート文、クラス、関数を抽出
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        if 'direct_import' not in import_dict:
                            import_dict['direct_import'] = []
                        import_dict['direct_import'].append(f"import {name.name}")
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    if module not in import_dict:
                        import_dict[module] = []
                    for name in node.names:
                        import_dict[module].append(name.name)
                elif isinstance(node, ast.ClassDef):
                    class_methods = []
                    class_docstring = ast.get_docstring(node)
                    
                    for method in node.body:
                        if isinstance(method, ast.FunctionDef):
                            method_docstring = ast.get_docstring(method)
                            # クラスメソッド内の関数を検索
                            inner_functions = []
                            for inner_node in ast.walk(method):
                                if isinstance(inner_node, ast.FunctionDef) and inner_node != method:
                                    inner_docstring = ast.get_docstring(inner_node)
                                    inner_functions.append({
                                        'name': inner_node.name,
                                        'docstring': inner_docstring
                                    })
                            
                            class_methods.append({
                                'name': method.name,
                                'docstring': method_docstring,
                                'inner_functions': inner_functions
                            })
                    
                    self.classes.append({
                        'name': node.name,
                        'docstring': class_docstring,
                        'methods': class_methods
                    })
                elif isinstance(node, ast.FunctionDef):
                    # トップレベルの関数かどうかをチェック（クラス内のメソッドではない）
                    function_docstring = ast.get_docstring(node)
                    
                    # すでに抽出したクラスメソッドの中に含まれていないかチェック
                    is_method = False
                    for cls in self.classes:
                        if any(method['name'] == node.name for method in cls['methods']):
                            is_method = True
                            break
                    
                    if not is_method:
                        # 関数内の関数を検索
                        inner_functions = []
                        for inner_node in ast.walk(node):
                            if isinstance(inner_node, ast.FunctionDef) and inner_node != node:
                                inner_docstring = ast.get_docstring(inner_node)
                                inner_functions.append({
                                    'name': inner_node.name,
                                    'docstring': inner_docstring
                                })
                        
                        self.functions.append({
                            'name': node.name,
                            'docstring': function_docstring,
                            'inner_functions': inner_functions
                        })
            
            # インポート辞書を整形された形式に変換
            self.imports = []
            for module, names in import_dict.items():
                if module == 'direct_import':
                    # 直接インポートは既にフォーマット済み
                    self.imports.extend(sorted(names))
                else:
                    # 同じモジュールからのインポートをまとめる
                    self.imports.append(f"from {module} import {', '.join(sorted(names))}")
            
            # ディレクトリ構造情報の追加
            self.directory_structure = directory_structure
            
            # レポートを生成
            self.report = self.generate_report(filename)
            self.char_count = len(code)  # コード全体の文字数を保存
            return self.report, self.char_count
        except SyntaxError as e:
            return f"構文エラー: {str(e)}", 0
        except Exception as e:
            return f"解析エラー: {str(e)}", 0
    
    def generate_report(self, filename=""):
        """解析結果からレポートを生成する"""
        report = ""
        
        # ディレクトリ構造情報があれば追加
        if hasattr(self, 'directory_structure') and self.directory_structure:
            report += "# ディレクトリ構造\n"
            report += self.directory_structure
            report += "\n\n"
        
        # インポート文を追加（フラグがTrueの場合のみ）
        if self.include_imports and self.imports:
            report += "# インポート\n"
            for import_stmt in self.imports:
                report += f"{import_stmt}\n"
            report += "\n"

        # クラスを追加
        if self.classes:
            report += "# クラス\n"
            for cls in self.classes:
                report += f"class {cls['name']}:\n"
                # クラスのdocstringを追加（フラグがTrueかつdocstringがある場合）
                if self.include_docstrings and cls['docstring']:
                    # 簡潔にするために1行目だけ表示
                    first_line = cls['docstring'].split('\n')[0].strip()
                    report += f"    \"{first_line}\"\n"
                
                # メソッドを追加
                if cls['methods']:
                    for method in cls['methods']:
                        report += f"    def {method['name']}()\n"
                        # メソッドのdocstringを追加（フラグがTrueかつdocstringがある場合）
                        if self.include_docstrings and method['docstring']:
                            first_line = method['docstring'].split('\n')[0].strip()
                            report += f"        \"{first_line}\"\n"
                        
                        # メソッド内の内部関数を追加
                        if 'inner_functions' in method and method['inner_functions']:
                            for inner_func in method['inner_functions']:
                                report += f"        def {inner_func['name']}()\n"
                                if self.include_docstrings and inner_func['docstring']:
                                    first_line = inner_func['docstring'].split('\n')[0].strip()
                                    report += f"            \"{first_line}\"\n"
                report += "\n"
        
        # 関数を追加
        if self.functions:
            report += "# 関数\n"
            for func in self.functions:
                report += f"def {func['name']}()\n"
                # 関数のdocstringを追加（フラグがTrueかつdocstringがある場合）
                if self.include_docstrings and func['docstring']:
                    first_line = func['docstring'].split('\n')[0].strip()
                    report += f"    \"{first_line}\"\n"
                
                # 関数内の内部関数を追加
                if 'inner_functions' in func and func['inner_functions']:
                    for inner_func in func['inner_functions']:
                        report += f"    def {inner_func['name']}()\n"
                        if self.include_docstrings and inner_func['docstring']:
                            first_line = inner_func['docstring'].split('\n')[0].strip()
                            report += f"        \"{first_line}\"\n"
            report += "\n"
            
        return report