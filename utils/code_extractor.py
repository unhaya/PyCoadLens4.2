# utils/code_extractor.py

import ast
import os
import tokenize
import io
import traceback
import concurrent.futures

class CodeExtractor:
    """
    Pythonコードから関数・クラス・メソッドを抽出し、
    コードブロック全体を適切な形式でデータベースに格納するクラス
    """
    
    def __init__(self, database):
        """
        データベース接続を受け取って初期化
        
        :param database: CodeDatabaseのインスタンス
        """
        self.database = database
        self.source_code = ""
        self.source_lines = []
        self.file_path = ""
        self.dir_path = ""
    
    def extract_from_file(self, file_path):
        """
        ファイルからコードを抽出してデータベースに格納
        
        :param file_path: 解析するPythonファイルのパス
        :return: 抽出されたコード要素の数
        """
        self.file_path = file_path
        self.dir_path = os.path.dirname(file_path)
        
        # ファイルからコードを読み込む
        try:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.source_code = f.read()
                    self.source_lines = self.source_code.splitlines()
            except UnicodeDecodeError:
                # UTF-8で読めない場合は代替エンコーディングを試す
                try:
                    with open(file_path, 'r', encoding='shift-jis') as f:
                        self.source_code = f.read()
                        self.source_lines = self.source_code.splitlines()
                    print(f"注意: ファイル {file_path} はShift-JISエンコーディングで読み込みました")
                except UnicodeDecodeError:
                    # さらに他のエンコーディングを試す
                    try:
                        with open(file_path, 'r', encoding='cp932') as f:
                            self.source_code = f.read()
                            self.source_lines = self.source_code.splitlines()
                        print(f"注意: ファイル {file_path} はCP932エンコーディングで読み込みました")
                    except Exception:
                        print(f"エラー: ファイル {file_path} を読み込めません")
                        return 0
            
            # データベースのタイムスタンプを更新
            self.database.update_file_timestamp(file_path)
            
            # 既存のコードスニペットをクリア
            self.database.clear_file_snippets(file_path)
            
            # トランザクションを開始
            self.database.begin_transaction()
            
            try:
                # コード要素を抽出してデータベースに格納
                count = self._extract_and_store()
                
                # トランザクションをコミット
                self.database.commit_transaction()
                
                return count
                
            except SyntaxError as se:
                # 構文エラーの場合はロールバック
                self.database.rollback_transaction()
                print(f"構文エラー: {file_path} - {str(se)}")
                return 0
            except Exception as e:
                # その他のエラーの場合もロールバック
                self.database.rollback_transaction()
                print(f"ファイル解析エラー: {file_path} - {str(e)}")
                traceback.print_exc()
                return 0
                
        except Exception as e:
            print(f"ファイル読み込みエラー: {file_path} - {str(e)}")
            traceback.print_exc()
            return 0

    def _extract_and_store(self):
        """
        コード要素を抽出しデータベースに格納する内部メソッド（改良版）
        
        :return: 抽出されたコード要素の数
        """
        try:
            # 構文解析でエラーが出る場合に備えてトライキャッチ
            try:
                tree = ast.parse(self.source_code)
            except SyntaxError as se:
                print(f"構文解析エラー ({self.file_path}): {str(se)}")
                return 0
                
            count = 0
            
            # デバッグ出力
            print(f"ファイル解析開始: {self.file_path}")
            
            # モジュールレベルのインポート文を抽出
            imports = self._extract_imports(tree)
            for imp in imports:
                try:
                    self._store_snippet(
                        name=imp["statement"],
                        type_name="import",
                        code=imp["statement"],
                        line_start=imp["line_start"],
                        line_end=imp["line_end"],
                        char_count=len(imp["statement"]),
                        description="インポート文"
                    )
                    count += 1
                except Exception as import_error:
                    print(f"インポート保存エラー: {str(import_error)}")
            
            # クラスを抽出
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.ClassDef):
                    try:
                        # クラス全体のコードを抽出
                        class_start = node.lineno
                        class_end = self._get_end_line(node)
                        
                        if class_end <= class_start:
                            # 問題がある場合は最後まで
                            class_end = len(self.source_lines)
                        
                        # 範囲チェック
                        if class_start > len(self.source_lines):
                            print(f"警告: クラス {node.name} の開始行 ({class_start}) がファイル範囲外です")
                            continue
                            
                        if class_end > len(self.source_lines):
                            class_end = len(self.source_lines)
                        
                        class_code = "\n".join(self.source_lines[class_start-1:class_end])
                        class_docstring = ast.get_docstring(node) or ""
                        
                        # デバッグ出力
                        print(f"クラス抽出: {node.name} (行 {class_start}-{class_end})")
                        
                        # クラスをデータベースに格納
                        self._store_snippet(
                            name=node.name,
                            type_name="class",
                            code=class_code,
                            line_start=class_start,
                            line_end=class_end,
                            char_count=len(class_code),
                            description=class_docstring
                        )
                        count += 1
                        
                        # クラスのメソッドも格納
                        for class_item in node.body:
                            if isinstance(class_item, ast.FunctionDef):
                                try:
                                    method_start = class_item.lineno
                                    method_end = self._get_end_line(class_item)
                                    
                                    if method_end <= method_start:
                                        # 問題がある場合はクラスの終了まで
                                        method_end = class_end
                                    
                                    # 範囲チェック
                                    if method_start > len(self.source_lines):
                                        print(f"警告: メソッド {node.name}.{class_item.name} の開始行がファイル範囲外です")
                                        continue
                                        
                                    if method_end > len(self.source_lines):
                                        method_end = len(self.source_lines)
                                    
                                    method_code = "\n".join(self.source_lines[method_start-1:method_end])
                                    method_docstring = ast.get_docstring(class_item) or ""
                                    
                                    # メソッド名にはクラス名とドットを付与
                                    method_name = f"{node.name}.{class_item.name}"
                                    
                                    # デバッグ出力
                                    print(f"メソッド抽出: {method_name} (行 {method_start}-{method_end})")
                                    
                                    self._store_snippet(
                                        name=method_name,
                                        type_name="function",  # メソッドもfunction型として保存
                                        code=method_code,
                                        line_start=method_start,
                                        line_end=method_end,
                                        char_count=len(method_code),
                                        description=method_docstring
                                    )
                                    count += 1
                                except Exception as method_error:
                                    print(f"メソッド保存エラー: {node.name}.{class_item.name} - {str(method_error)}")
                                    traceback.print_exc()
                    except Exception as class_error:
                        print(f"クラス保存エラー: {node.name} - {str(class_error)}")
                        traceback.print_exc()
            
            # トップレベルの関数を抽出
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.FunctionDef):
                    try:
                        # 関数全体のコードを抽出
                        func_start = node.lineno
                        func_end = self._get_end_line(node)
                        
                        if func_end <= func_start:
                            # 問題がある場合は最後まで
                            func_end = len(self.source_lines)
                        
                        # 範囲チェック
                        if func_start > len(self.source_lines):
                            print(f"警告: 関数 {node.name} の開始行がファイル範囲外です")
                            continue
                            
                        if func_end > len(self.source_lines):
                            func_end = len(self.source_lines)
                        
                        function_code = "\n".join(self.source_lines[func_start-1:func_end])
                        function_docstring = ast.get_docstring(node) or ""
                        
                        # デバッグ出力
                        print(f"関数抽出: {node.name} (行 {func_start}-{func_end})")
                        
                        # 関数をデータベースに格納
                        self._store_snippet(
                            name=node.name,
                            type_name="function",
                            code=function_code,
                            line_start=func_start,
                            line_end=func_end,
                            char_count=len(function_code),
                            description=function_docstring
                        )
                        count += 1
                    except Exception as func_error:
                        print(f"関数保存エラー: {node.name} - {str(func_error)}")
                        traceback.print_exc()
            
            print(f"ファイル解析完了: {self.file_path} - {count}個のスニペット抽出")
            return count
            
        except Exception as e:
            print(f"コード抽出全体エラー: {str(e)}")
            traceback.print_exc()
            return 0

    def _extract_imports(self, tree):
        """
        インポート文を抽出
        
        :param tree: ASTツリー
        :return: インポート文のリスト
        """
        imports = []
        
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                # 通常のインポート (import xxx)
                statement = "import " + ", ".join(name.name for name in node.names)
                imports.append({
                    "statement": statement,
                    "line_start": node.lineno,
                    "line_end": node.lineno
                })
            elif isinstance(node, ast.ImportFrom):
                # fromインポート (from xxx import yyy)
                module = node.module or ""
                names = ", ".join(name.name for name in node.names)
                statement = f"from {module} import {names}"
                imports.append({
                    "statement": statement,
                    "line_start": node.lineno,
                    "line_end": node.lineno
                })
        
        return imports
    
    def _get_node_source(self, node):
        """
        ASTノードのソースコードを取得
        
        :param node: ASTノード
        :return: ノードのソースコード全体
        """
        # ノードの開始行と終了行を取得
        start_line = node.lineno
        end_line = self._get_end_line(node)
        
        # 対応するソースコード行を取得して結合
        source_lines = self.source_lines[start_line-1:end_line]
        return "\n".join(source_lines)
        
    def _get_end_line(self, node):
        """
        ASTノードの終了行番号を取得（簡略版）
        
        :param node: ASTノード
        :return: 終了行番号
        """
        # end_lineno属性があれば使用（Python 3.8以降）
        if hasattr(node, 'end_lineno') and node.end_lineno is not None:
            return node.end_lineno
        
        # 開始行と初期インデントレベルを取得
        start_line = node.lineno
        if start_line >= len(self.source_lines):
            return len(self.source_lines)
        
        # インデントレベルを取得
        try:
            node_indent = self._get_indent_level(self.source_lines[start_line-1])
        except Exception:
            # エラーの場合はファイルの最後行を返す
            return len(self.source_lines)
        
        # 開始行の次の行から探索開始
        for i in range(start_line, len(self.source_lines)):
            line = self.source_lines[i]
            
            # 空行またはコメント行はスキップ
            if not line.strip() or line.strip().startswith('#'):
                continue
            
            # インデントを確認
            current_indent = self._get_indent_level(line)
            
            # 元のインデントレベル以下の行があれば終了
            if current_indent <= node_indent:
                return i
        
        # 見つからない場合はファイルの最後行を返す
        return len(self.source_lines)
    def _get_indent_level(self, line):
        """
        行のインデントレベル（スペース/タブの数）を取得（改良版）
        
        :param line: ソースコード行
        :return: インデントレベル
        """
        if not line:
            return 0
            
        # スペースとタブの扱いを設定
        tab_size = 4  # タブのスペース数を設定
        
        indent = 0
        for char in line:
            if char == ' ':
                indent += 1
            elif char == '\t':
                # タブを特定のスペース数として扱う
                indent += tab_size - (indent % tab_size)
            else:
                break
        return indent
    
    def _store_snippet(self, name, type_name, code, line_start, line_end, char_count, description=""):
        """
        コードスニペットをデータベースに格納
        
        :param name: スニペット名（関数名/クラス名など）
        :param type_name: スニペットタイプ（class/function/import）
        :param code: コード全体
        :param line_start: 開始行番号
        :param line_end: 終了行番号
        :param char_count: 文字数
        :param description: 説明（docstring）
        """
        self.database.add_code_snippet(
            file_path=self.file_path,
            dir_path=self.dir_path,
            name=name,
            type_name=type_name,
            code=code,
            line_start=line_start,
            line_end=line_end,
            char_count=char_count,
            description=description
        )
        
    def _is_valid_python_code(self, code):
        """コードがPythonとして有効かチェック"""
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False

    def _get_decorator_names(self, node):
        """ノードに付与されたデコレータ名のリストを取得"""
        decorators = []
        if hasattr(node, 'decorator_list'):
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Name):
                    decorators.append(decorator.id)
                elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
                    decorators.append(decorator.func.id)
                elif isinstance(decorator, ast.Attribute):
                    # 例: @some.decorator
                    attr_name = []
                    current = decorator
                    while isinstance(current, ast.Attribute):
                        attr_name.insert(0, current.attr)
                        current = current.value
                    if isinstance(current, ast.Name):
                        attr_name.insert(0, current.id)
                    decorators.append('.'.join(attr_name))
        return decorators
        
    def _extract_code_fallback(self, file_path, start_line, end_line):
        """AST解析が失敗した場合のバックアップ手段として、行範囲からコードを抽出"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            if start_line < 1 or end_line > len(lines):
                # 範囲外の場合
                return None
                
            code_lines = lines[start_line-1:end_line]
            return ''.join(code_lines)
        except Exception as e:
            print(f"フォールバックコード抽出エラー: {str(e)}")
            return None
            
    def extract_with_progress(self, file_path, progress_callback=None):
        """
        進捗表示付きでファイルからコードを抽出
        
        :param file_path: 解析するPythonファイルのパス
        :param progress_callback: 進捗を表示するコールバック関数 (percent, message)
        :return: 抽出されたコード要素の数
        """
        if progress_callback:
            progress_callback(0, f"ファイルを読み込み中: {os.path.basename(file_path)}")
            
        try:
            # ファイル読み込み
            with open(file_path, 'r', encoding='utf-8') as f:
                self.source_code = f.read()
                self.source_lines = self.source_code.splitlines()
            
            if progress_callback:
                progress_callback(10, "構文解析準備中...")
                
            self.file_path = file_path
            self.dir_path = os.path.dirname(file_path)
            
            # データベース操作
            self.database.update_file_timestamp(file_path)
            self.database.clear_file_snippets(file_path)
            self.database.begin_transaction()
            
            if progress_callback:
                progress_callback(20, "構文解析中...")
                
            try:
                # 構文解析
                tree = ast.parse(self.source_code)
                
                if progress_callback:
                    progress_callback(40, "インポート文を抽出中...")
                    
                # インポート文抽出
                imports = self._extract_imports(tree)
                for imp in imports:
                    self._store_snippet(
                        name=imp["statement"],
                        type_name="import",
                        code=imp["statement"],
                        line_start=imp["line_start"],
                        line_end=imp["line_end"],
                        char_count=len(imp["statement"]),
                        description="インポート文"
                    )
                
                if progress_callback:
                    progress_callback(60, "クラス定義を抽出中...")
                    
                # クラス抽出（既存の_extract_and_storeの処理）
                # ...
                
                if progress_callback:
                    progress_callback(80, "関数定義を抽出中...")
                    
                # 関数抽出（既存の_extract_and_storeの処理）
                # ...
                
                # トランザクションをコミット
                self.database.commit_transaction()
                
                if progress_callback:
                    progress_callback(100, "完了")
                    
                return True
                
            except Exception as e:
                self.database.rollback_transaction()
                if progress_callback:
                    progress_callback(100, f"エラー: {str(e)}")
                return False
                
        except Exception as e:
            if progress_callback:
                progress_callback(100, f"エラー: {str(e)}")
            return False

    def extract_multi_files(self, file_paths, max_workers=None):
        """
        複数ファイルを並列処理
        
        :param file_paths: 解析するファイルパスのリスト
        :param max_workers: 最大並列処理数（Noneの場合はCPUコア数）
        :return: {file_path: 成功したかどうか}の辞書
        """
        results = {}
        
        # 1つのファイルを処理する関数
        def process_one_file(file_path):
            try:
                extractor = CodeExtractor(self.database)
                success = extractor.extract_from_file(file_path)
                return file_path, success > 0
            except Exception as e:
                print(f"並列処理エラー ({file_path}): {str(e)}")
                return file_path, False
        
        # 並列処理実行
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {executor.submit(process_one_file, file_path): file_path for file_path in file_paths}
            
            for future in concurrent.futures.as_completed(future_to_file):
                file_path, success = future.result()
                results[file_path] = success
        
        return results