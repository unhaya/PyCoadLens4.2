# core/astroid_analyzer.py

import os
import traceback
import astroid
from .language_base import LanguageAnalyzerBase

class AstroidAnalyzer(LanguageAnalyzerBase):
    """
    astroidを使用して、より深いコード解析を行うクラス
    型情報、継承関係、依存関係などの意味的な情報を抽出する
    """
    def __init__(self):
        super().__init__()
        self.reset()

    def reset(self):
        """解析結果をリセットする"""
        super().reset()
        self._ast_nodes = {}
        self._imports = {}
        self._dependencies = {}
        self._function_info = {}
        self._method_info = {}
        self._class_info = {}
        self._module_info = {}
        
        # 以前の属性も維持
        self.imports = []
        self.classes = []
        self.functions = []
        self.dependencies = {}  # 関数/メソッド間の依存関係
        self.inheritance = {}   # クラスの継承関係
        self.type_info = {}     # 変数・引数・戻り値の型情報
        self.report = ""
        self.char_count = 0
        
        # 言語連携関連の属性を追加
        self.python_components = {
            "classes": [],
            "functions": [],
            "methods": []
        }
        self.connection_points = []
        self.connection_nodes = {}

    def get_file_extensions(self):
        """対応するファイル拡張子"""
        return [".py"]
    
    def get_language_name(self):
        """言語名を返す"""
        return "Python"

    def analyze_file(self, file_path):
        """ファイルパスからコードを読み込んで解析する"""
        try:
            self.files.append(file_path)  # 言語ベースクラス用
            
            with open(file_path, 'r', encoding='utf-8') as file:
                code = file.read()
            return self.analyze_code(code, file_path)
        except ImportError:
            return "astroidライブラリがインストールされていません。pip install astroid でインストールしてください。", 0
        except Exception as e:
            return f"ファイル解析エラー: {str(e)}", 0

    def analyze_code(self, code, file_path=""):
        """astroidを使ってPythonコードを解析する"""
        self.reset()
        try:
            filename = os.path.basename(file_path) if file_path else ""
            
            tree = astroid.parse(code)
            
            # モジュールレベルのドキュメント文字列
            module_docstring = tree.doc_node.value if tree.doc_node else None
            
            # インポート文を解析
            self._extract_imports(tree)
            
            # クラスと関数を解析
            for node in tree.body:
                if isinstance(node, astroid.ClassDef):
                    self._analyze_class(node, file_path)
                elif isinstance(node, astroid.FunctionDef):
                    self._analyze_function(node, file_path)
            
            # 継承関係と依存関係を解析
            self._analyze_dependencies(tree)
            
            # レポート生成
            self.report = self.generate_report(filename)
            self.char_count = len(self.report)
            return self.report, self.char_count
            
        except ImportError:
            return "astroidライブラリがインストールされていません。pip install astroid でインストールしてください。", 0
        except Exception as e:
            return f"解析エラー: {str(e)}", 0
            
    def _extract_imports(self, tree):
        """インポート文を抽出して解析する"""
        
        for node in tree.body:
            if isinstance(node, astroid.Import):
                for name in node.names:
                    self.imports.append(f"import {name[0]}")
            elif isinstance(node, astroid.ImportFrom):
                module = node.modname
                names = [name[0] for name in node.names]
                self.imports.append(f"from {module} import {', '.join(names)}")

    def _analyze_dependencies(self, tree):
        """関数間やクラス間の依存関係を解析する（エラー処理強化版）"""
        
        try:
            # 関数呼び出しを検出して依存関係を構築
            for node in tree.body:
                try:
                    if isinstance(node, astroid.FunctionDef):
                        self._find_dependencies(node, node.name)
                    elif isinstance(node, astroid.ClassDef):
                        for method in node.body:
                            if isinstance(method, astroid.FunctionDef):
                                self._find_dependencies(method, f"{node.name}.{method.name}")
                except Exception as e:
                    print(f"依存関係解析中にエラー ({getattr(node, 'name', 'unknown')}): {e}")
        except Exception as e:
            print(f"依存関係全体の解析中にエラー: {e}")

    def _find_dependencies(self, node, caller_name):
        """ノード内の関数呼び出しを検出して依存関係を記録する（エラー処理強化版）"""
        
        try:
            if caller_name not in self.dependencies:
                self.dependencies[caller_name] = set()
            
            # get_childrenはエラーを起こす可能性があるので安全に処理
            try:
                children = list(node.get_children())
            except Exception:
                children = []
                
            for child in children:
                try:
                    if isinstance(child, astroid.Call):
                        try:
                            if isinstance(child.func, astroid.Name):
                                self.dependencies[caller_name].add(child.func.name)
                            elif isinstance(child.func, astroid.Attribute):
                                # 安全に属性参照を取得
                                if isinstance(child.func.expr, astroid.Name):
                                    self.dependencies[caller_name].add(f"{child.func.expr.name}.{child.func.attrname}")
                        except Exception as e:
                            print(f"関数呼び出し解析中にエラー: {e}")
                    
                    # 再帰的に子ノードも調査（子ノードがエラーでも中断しない）
                    try:
                        self._find_dependencies(child, caller_name)
                    except Exception as e:
                        print(f"依存関係の再帰処理中にエラー: {e}")
                except Exception as e:
                    print(f"子ノード処理中にエラー: {e}")
        except Exception as e:
            print(f"依存関係検索中にエラー ({caller_name}): {e}")

    def _analyze_function(self, node, file_path="", is_inner=False):
        """トップレベルまたは内部関数を解析する"""
        try:
            # 基本情報
            func_info = {
                'name': node.name,
                'docstring': node.doc_node.value if hasattr(node, 'doc_node') and node.doc_node else None,
                'parameters': [],
                'return_type': None,
                'inner_functions': []
            }
            
            # 引数の解析
            try:
                if hasattr(node, 'args') and hasattr(node.args, 'args'):
                    for arg in node.args.args:
                        param_name = getattr(arg, 'name', 'unknown')
                        param_info = {'name': param_name}
                        
                        # 型アノテーションがある場合（安全にチェック）
                        try:
                            if hasattr(arg, 'annotation') and arg.annotation:
                                param_info['type'] = self._get_annotation_name(arg.annotation)
                        except Exception:
                            # 型注釈の取得に失敗した場合は無視
                            pass
                            
                        func_info['parameters'].append(param_info)
            except Exception as e:
                print(f"関数引数の解析中にエラー: {e}")
            
            # 戻り値の型アノテーション（安全にチェック）
            try:
                if hasattr(node, 'returns') and node.returns:
                    func_info['return_type'] = self._get_annotation_name(node.returns)
                else:
                    # 戻り値の型を推論
                    func_info['return_type'] = self._infer_return_type(node)
            except Exception as e:
                print(f"関数の戻り値型解析中にエラー: {e}")
                func_info['return_type'] = "unknown"
            
            # 内部関数を解析
            try:
                for child in node.body:
                    if isinstance(child, astroid.FunctionDef):
                        try:
                            inner_func = self._analyze_function(child, file_path, is_inner=True)
                            func_info['inner_functions'].append(inner_func)
                        except Exception as e:
                            print(f"内部関数 {getattr(child, 'name', 'unknown')} の解析中にエラー: {e}")
            except Exception as e:
                print(f"関数内の内部関数走査中にエラー: {e}")
            
            # 内部関数でない場合はfunctionsリストに追加
            if not is_inner:
                self.functions.append(func_info)
                
                # 言語連携用のコンポーネント情報を収集
                filename = os.path.basename(file_path) if file_path else "unknown"
                py_func_info = {
                    "name": node.name,
                    "file": filename,
                    "type": "Function",
                    "params": [p.get('name', 'unknown') for p in func_info['parameters']]
                }
                self.python_components["functions"].append(py_func_info)
                
                # 接続ノード情報を保存
                node_id = f"python_func_{len(self.python_components['functions']) - 1}"
                self.connection_nodes[node.name] = {
                    "node_id": node_id,
                    "type": "function",
                    "name": node.name
                }
                
                # 連携ポイントを検出
                self._detect_connection_points(node, file_path)
            
            return func_info
        except Exception as e:
            print(f"関数 {getattr(node, 'name', 'unknown')} の解析中に例外が発生: {e}")
            # 最低限の情報を含む空の関数情報を返す
            return {'name': getattr(node, 'name', 'unknown'), 'parameters': [], 'inner_functions': []}

    def _analyze_method(self, node, file_path=""):
        """クラスメソッドを解析する"""
        
        try:
            # 基本情報
            method_info = {
                'name': node.name,
                'docstring': node.doc_node.value if hasattr(node, 'doc_node') and node.doc_node else None,
                'parameters': [],
                'return_type': None,
                'inner_functions': []
            }
            
            # 引数の解析
            try:
                if hasattr(node, 'args') and hasattr(node.args, 'args'):
                    for arg in node.args.args:
                        if arg.name == 'self':
                            continue  # selfパラメータはスキップ
                            
                        param_name = getattr(arg, 'name', 'unknown')
                        param_info = {'name': param_name}
                        
                        # 型アノテーションがある場合（安全にチェック）
                        try:
                            if hasattr(arg, 'annotation') and arg.annotation:
                                param_info['type'] = self._get_annotation_name(arg.annotation)
                        except Exception:
                            # 型注釈の取得に失敗した場合は無視
                            pass
                                
                        method_info['parameters'].append(param_info)
            except Exception as e:
                print(f"メソッド引数の解析中にエラー: {e}")
            
            # 戻り値の型アノテーション（安全にチェック）
            try:
                if hasattr(node, 'returns') and node.returns:
                    method_info['return_type'] = self._get_annotation_name(node.returns)
                else:
                    # 戻り値の型を推論
                    method_info['return_type'] = self._infer_return_type(node)
            except Exception as e:
                print(f"メソッドの戻り値型解析中にエラー: {e}")
                method_info['return_type'] = "unknown"
            
            # 内部関数を解析
            try:
                for child in node.body:
                    if isinstance(child, astroid.FunctionDef):
                        try:
                            inner_func = self._analyze_function(child, file_path, is_inner=True)
                            method_info['inner_functions'].append(inner_func)
                        except Exception as e:
                            print(f"メソッド内の内部関数 {getattr(child, 'name', 'unknown')} の解析中にエラー: {e}")
            except Exception as e:
                print(f"メソッド内の内部関数走査中にエラー: {e}")
            
            # 言語連携用のメソッド情報を収集
            filename = os.path.basename(file_path) if file_path else "unknown"
            py_method_info = {
                "name": node.name,
                "file": filename,
                "type": "Method",
                "params": [p.get('name', 'unknown') for p in method_info['parameters']]
            }
            self.python_components["methods"].append(py_method_info)
            
            # 連携ポイントを検出
            self._detect_connection_points(node, file_path)
            
            return method_info
            
        except Exception as e:
            print(f"メソッド {getattr(node, 'name', 'unknown')} の解析中に例外が発生: {e}")
            # 最低限の情報を含む空のメソッド情報を返す
            return {'name': getattr(node, 'name', 'unknown'), 'parameters': [], 'inner_functions': []}

    def _get_annotation_name(self, annotation):
        """型アノテーションノードから型名を取得する（エラー処理強化版）"""
        
        try:
            if isinstance(annotation, astroid.Name):
                return annotation.name
            elif isinstance(annotation, astroid.Attribute):
                # 安全に属性参照を取得
                expr_name = "unknown"
                try:
                    if hasattr(annotation.expr, 'name'):
                        expr_name = annotation.expr.name
                except Exception:
                    pass
                return f"{expr_name}.{annotation.attrname}"
            elif isinstance(annotation, astroid.Subscript):
                # ジェネリック型（List[str]など）
                value_name = "unknown"
                try:
                    value_name = self._get_annotation_name(annotation.value)
                except Exception:
                    pass
                    
                # ジェネリック型のパラメータの取得（バージョン間の違いに対応）
                try:
                    # astroid 2.x系
                    if hasattr(annotation, 'slice') and hasattr(annotation.slice, 'value'):
                        slice_value = annotation.slice.value
                        if isinstance(slice_value, astroid.Name):
                            return f"{value_name}[{slice_value.name}]"
                        elif isinstance(slice_value, astroid.Tuple):
                            elts = []
                            for elt in slice_value.elts:
                                if isinstance(elt, astroid.Name):
                                    elts.append(elt.name)
                            return f"{value_name}[{', '.join(elts)}]"
                    # astroid 2.0以前または異なる構造
                    elif hasattr(annotation, 'slice'):
                        return f"{value_name}[...]"
                except Exception:
                    # どのパターンにも一致しない場合は簡略化した形式を返す
                    return f"{value_name}[?]"
                    
                # どれにも一致しない場合
                return value_name
            # その他の型は文字列化して返す
            return str(type(annotation).__name__)
        except Exception as e:
            print(f"型アノテーション解析中にエラー: {e}")
            return "unknown"

    def _infer_type(self, node):
        """ノードから型を推論する（エラー処理強化版）"""
        try:
            if node is None:
                return "unknown"
                
            # SafeInferの使用を検討
            inferred = list(node.infer())
            if not inferred:
                return "unknown"
                
            # 推論結果の最初の要素を使用
            first = inferred[0]
            
            if hasattr(first, "pytype"):
                pytype = first.pytype()
                return pytype.split(".")[-1]
            else:
                return type(first).__name__
        except StopIteration:
            # StopIterationを捕捉して適切に処理
            return "unknown"
        except Exception as e:
            print(f"型推論エラー: {str(e)}")
            return "unknown"

    def _infer_return_type(self, node):
        """関数の戻り値の型を推論する（エラー処理強化版）"""
        
        types = set()
        return_values = []
        
        try:
            # return文を探す
            for child_node in node.get_children():
                if isinstance(child_node, astroid.Return) and child_node.value:
                    return_values.append(child_node.value)
            
            # 各return文の型を推論
            for return_node in return_values:
                try:
                    inferred = list(return_node.infer())
                    if inferred:
                        for inf in inferred:
                            if hasattr(inf, "pytype"):
                                types.add(inf.pytype().split(".")[-1])
                            else:
                                types.add(type(inf).__name__)
                except StopIteration:
                    # StopIterationをここで処理
                    continue
                except Exception as e:
                    print(f"戻り値型推論エラー: {str(e)}")
                    continue
                    
            if len(types) == 0:
                return "None"
            elif len(types) == 1:
                return list(types)[0]
            else:
                return " | ".join(sorted(types))
        except Exception as e:
            print(f"戻り値型推論全体エラー: {str(e)}")
            return "unknown"   
    
    def _analyze_class(self, node, file_path=""):
        """クラス定義を解析する（エラー処理強化版）"""
        
        try:
            # 基本情報の取得
            class_info = {
                'name': node.name,
                'docstring': node.doc_node.value if hasattr(node, 'doc_node') and node.doc_node else None,
                'methods': [],
                'base_classes': [],
                'attributes': []
            }
            
            # 継承関係を解析
            try:
                for base in node.bases:
                    if isinstance(base, astroid.Name):
                        class_info['base_classes'].append(base.name)
                    elif isinstance(base, astroid.Attribute):
                        base_expr_name = getattr(base.expr, 'name', 'unknown')
                        class_info['base_classes'].append(f"{base_expr_name}.{base.attrname}")
            except Exception as e:
                print(f"継承関係の解析中にエラー: {e}")
            
            # 継承関係を記録
            self.inheritance[node.name] = class_info['base_classes']
            
            # メソッドとクラス変数を解析
            for child in node.body:
                try:
                    if isinstance(child, astroid.FunctionDef):
                        method_info = self._analyze_method(child, file_path)
                        class_info['methods'].append(method_info)
                    elif isinstance(child, astroid.Assign):
                        for target in child.targets:
                            if isinstance(target, astroid.AssignName):
                                # クラス変数を記録（安全に型を推論）
                                attr_type = "unknown"
                                try:
                                    attr_type = self._infer_type(child.value)
                                except Exception as e:
                                    print(f"属性型推論エラー: {e}")
                                
                                class_info['attributes'].append({
                                    'name': target.name,
                                    'type': attr_type
                                })
                except Exception as e:
                    print(f"クラス内のノード解析中にエラー: {e}")
                    continue
            
            self.classes.append(class_info)
            
            # 言語連携用のコンポーネント情報を収集
            filename = os.path.basename(file_path) if file_path else "unknown"
            class_info = {
                "name": node.name,
                "file": filename,
                "type": "Class",
                "methods": [m['name'] for m in class_info['methods']],
                "base_classes": class_info['base_classes']
            }
            self.python_components["classes"].append(class_info)

            # 接続ノード情報を保存
            node_id = f"python_class_{len(self.python_components['classes']) - 1}"
            self.connection_nodes[node.name] = {
                "node_id": node_id,
                "type": "class",
                "name": node.name
            }
            
            return class_info
        except Exception as e:
            print(f"クラス {getattr(node, 'name', 'unknown')} の解析中に例外が発生: {e}")
            # 最低限の情報を含む空のクラス情報を返す
            return {'name': getattr(node, 'name', 'unknown'), 'methods': [], 'base_classes': [], 'attributes': []}
    
    def _detect_connection_points(self, node, file_path):
        """ノード内の言語連携ポイントを検出"""
        filename = os.path.basename(file_path) if file_path else "unknown"
        
        # 関数呼び出しを検査
        for call_node in node.nodes_of_class(astroid.Call):
            # 呼び出し元のオブジェクト名を取得
            caller = ""
            if hasattr(call_node, 'func') and hasattr(call_node.func, 'as_string'):
                caller = call_node.func.as_string()
            
            # Flask APIエンドポイント
            if 'app.route' in caller:
                for arg in call_node.args:
                    if isinstance(arg, astroid.Const) and isinstance(arg.value, str):
                        endpoint = arg.value
                        self.connection_points.append({
                            "type": "web_api",
                            "framework": "Flask",
                            "endpoint": endpoint,
                            "file": filename,
                            "description": f"Flask API endpoint: {endpoint}",
                            "node": node.name
                        })
            
            # FastAPI エンドポイント
            elif any(method in caller for method in ['fastapi.get', 'fastapi.post', 'fastapi.put', 'fastapi.delete']):
                for arg in call_node.args:
                    if isinstance(arg, astroid.Const) and isinstance(arg.value, str):
                        endpoint = arg.value
                        self.connection_points.append({
                            "type": "web_api",
                            "framework": "FastAPI",
                            "endpoint": endpoint,
                            "file": filename,
                            "description": f"FastAPI endpoint: {endpoint}",
                            "node": node.name
                        })
            
            # ctypes FFI
            elif 'ctypes.CDLL' in caller:
                for arg in call_node.args:
                    if isinstance(arg, astroid.Const) and isinstance(arg.value, str):
                        lib_path = arg.value
                        self.connection_points.append({
                            "type": "c_ffi",
                            "lib_path": lib_path,
                            "file": filename,
                            "description": f"C FFI via ctypes: {lib_path}",
                            "node": node.name
                        })
            
            # Flutter MethodChannel
            elif 'MethodChannel' in caller:
                self.connection_points.append({
                    "type": "flutter_channel",
                    "file": filename,
                    "description": "Flutter Method Channel handler",
                    "node": node.name
                })
    
    def generate_report(self, filename=""):
        """解析結果からわかりやすいレポートを生成する（必要な情報のみ）"""
        report = ""
        
        # ファイル名
        if filename:
            report += f"# {filename} の解析レポート\n\n"
        else:
            report += "# Pythonコード解析レポート\n\n"
        
        # インポート文は除外 (冗長情報)
        
        # プロジェクト構造 (重要情報1)
        # この部分はディレクトリ情報から生成されるため、ここでは変更なし
        
        # クラス階層図 (重要情報2)
        if self.classes:
            report += "## クラス階層図\n"
            for cls in self.classes:
                if cls['base_classes']:
                    report += f"- **{cls['name']}** ← {', '.join(cls['base_classes'])}\n"
                else:
                    report += f"- **{cls['name']}**\n"
            report += "\n"
        
        # ファイル間の依存関係 - シンプルに保持
        if self.inheritance:
            report += "## ファイル間の依存関係\n"
            # ここは重要なファイル間の依存関係のみを表示するよう変更
            report += "- **<ファイル名>.py** (依存なし)\n" # 必要に応じて実際の依存関係を表示
            report += "\n"
        
        # 各クラスのメソッド一覧 (重要情報3)
        if self.classes:
            report += "## ファイルごとの詳細情報\n"
            if filename:
                report += f"### {filename}\n"
                
            report += "**クラス:**\n"
            for cls in self.classes:
                base_classes = f" (継承: {', '.join(cls['base_classes'])})" if cls['base_classes'] else ""
                report += f"- `{cls['name']}`{base_classes}\n"
                
                # メソッド（シンプルに名前のみ表示）
                if cls['methods']:
                    report += "  **メソッド:**\n"
                    for method in cls['methods']:
                        report += f"  - `{method['name']}`\n"
            report += "\n"
        
        # トップレベル関数リスト（シンプルに表示）
        if self.functions:
            report += "**関数:**\n"
            for func in self.functions:
                report += f"- `{func['name']}`\n"
            report += "\n"
        
        # 言語連携情報
        if self.connection_points:
            report += "## 言語連携情報\n"
            report += "**連携ポイント:**\n"
            for point in self.connection_points:
                point_type = point.get("type", "unknown")
                desc = point.get("description", "")
                report += f"- `{point_type}`: {desc}\n"
            report += "\n"
        
        # LLM向け構造化データ (重要情報4)
        report += "## LLM向け構造化データ\n"
        report += "```\n"
        # コンパクトなフォーマットでデータを出力
        compact_data = "# クラス一覧\n"
        for cls in self.classes:
            base_info = f" <- {', '.join(cls['base_classes'])}" if cls['base_classes'] else ""
            compact_data += f"{cls['name']}{base_info}\n"

            if cls['methods']:
                compact_data += "  メソッド:\n"
                for m in cls['methods']:
                    params = ", ".join(p['name'] for p in m['parameters'])
                    ret_type = f" -> {m['return_type']}" if m['return_type'] and m['return_type'] != "unknown" else ""
                    compact_data += f"    {m['name']}({params}){ret_type}\n"
            compact_data += "\n"
        compact_data += "# 関数一覧\n"
        for func in self.functions:
            params = ", ".join(p['name'] for p in func['parameters'])
            ret_type = f" -> {func['return_type']}" if func['return_type'] and func['return_type'] != "unknown" else ""
            compact_data += f"{func['name']}({params}){ret_type}\n"
        compact_data += "\n"
        # 主要な依存関係のみ表示
        if self.dependencies:
            compact_data += "# 主要な依存関係\n"
            for caller, callees in self.dependencies.items():
                if callees:  # 空でない場合のみ
                    compact_data += f"{caller} -> {', '.join(callees)}\n"
            compact_data += "\n"
        
        # 言語連携情報も追加
        if self.connection_points:
            compact_data += "# 言語連携ポイント\n"
            for point in self.connection_points:
                point_type = point.get("type", "unknown")
                desc = point.get("description", "")
                compact_data += f"{point_type}: {desc}\n"
            compact_data += "\n"
        
        report += compact_data
        report += "```\n"
        
        return report

    def find_connections(self, other_analyzer):
        """他の言語解析器との連携ポイントを検出"""
        connections = []
        
        # Flutter解析器との連携を検出
        if hasattr(other_analyzer, 'get_language_name') and other_analyzer.get_language_name() == "Flutter/Dart":
            # Python側のWebAPIとFlutter側のHTTP呼び出しを照合
            for point in self.connection_points:
                if point["type"] == "web_api":
                    endpoint = point.get("endpoint", "")
                    
                    # Flutter側のHTTP_API連携を探す
                    for flutter_conn in other_analyzer.python_connections:
                        if flutter_conn["type"] == "HTTP_API":
                            url = flutter_conn.get("url", "")
                            if endpoint in url:
                                connection = {
                                    "from": "flutter",
                                    "to": "python",
                                    "type": "http_api",
                                    "description": f"API call from Flutter to Python endpoint {endpoint}",
                                    "flutter_file": flutter_conn.get("file", ""),
                                    "python_file": point.get("file", "")
                                }
                                
                                # ノードIDを設定
                                if "node" in point and point["node"] in self.connection_nodes:
                                    connection["to_node"] = self.connection_nodes[point["node"]]["node_id"]
                                else:
                                    connection["to_node"] = "python_api"
                                
                                if "class" in flutter_conn and flutter_conn["class"] in other_analyzer.connection_nodes:
                                    connection["from_node"] = other_analyzer.connection_nodes[flutter_conn["class"]]["node_id"]
                                
                                connections.append(connection)
                
            # Python側のMethodChannelハンドラとFlutter側のMethodChannelを照合
            for point in self.connection_points:
                if point["type"] == "flutter_channel":
                    # Flutter側のMethodChannel連携を探す
                    for flutter_conn in other_analyzer.python_connections:
                        if flutter_conn["type"] == "MethodChannel":
                            channel = flutter_conn.get("channel", "")
                            connection = {
                                "from": "flutter",
                                "to": "python",
                                "type": "method_channel",
                                "description": f"Method Channel from Flutter to Python: {channel}",
                                "channel": channel,
                                "flutter_file": flutter_conn.get("file", ""),
                                "python_file": point.get("file", "")
                            }
                            
                            # ノードIDを設定
                            if "node" in point and point["node"] in self.connection_nodes:
                                connection["to_node"] = self.connection_nodes[point["node"]]["node_id"]
                            else:
                                connection["to_node"] = "python_channel_handler"
                            
                            if "class" in flutter_conn and flutter_conn["class"] in other_analyzer.connection_nodes:
                                connection["from_node"] = other_analyzer.connection_nodes[flutter_conn["class"]]["node_id"]
                            
                            connections.append(connection)
        
        return connections

    def generate_mermaid(self):
        """Pythonコンポーネントと連携ポイントのマーメード図を生成"""
        mermaid = "```mermaid\nflowchart LR\n"
        
        # クラスノード
        for i, cls in enumerate(self.python_components["classes"]):
            node_id = f"python_class_{i}"
            icon = "🐍"
            mermaid += f"    {node_id}[\"{icon} {cls['name']}\"]:::python\n"
        
        # 関数ノード
        for i, func in enumerate(self.python_components["functions"]):
            node_id = f"python_func_{i}"
            mermaid += f"    {node_id}[\"⚙️ {func['name']}()\"]:::python\n"
        
        # 連携ポイント
        api_endpoints = []
        c_ffi_libs = []
        flutter_channels = []
        
        for point in self.connection_points:
            if point["type"] == "web_api":
                endpoint = point.get("endpoint", "unknown")
                framework = point.get("framework", "Web")
                api_endpoints.append({
                    "endpoint": endpoint,
                    "framework": framework,
                    "node": point.get("node", "")
                })
            elif point["type"] == "c_ffi":
                lib_path = point.get("lib_path", "unknown")
                c_ffi_libs.append({
                    "lib_path": lib_path,
                    "node": point.get("node", "")
                })
            elif point["type"] == "flutter_channel":
                flutter_channels.append({
                    "node": point.get("node", "")
                })
        
        # APIエンドポイントノード
        if api_endpoints:
            mermaid += f"    python_api[\"🌐 API Endpoints\"]:::python\n"
            
            # 関連する関数/クラスとの接続
            for endpoint in api_endpoints:
                node_name = endpoint["node"]
                if node_name in self.connection_nodes:
                    node_id = self.connection_nodes[node_name]["node_id"]
                    mermaid += f"    {node_id} -->|{endpoint['framework']} {endpoint['endpoint']}| python_api\n"
        
        # C FFIノード
        if c_ffi_libs:
            mermaid += f"    python_ffi[\"🔌 C FFI\"]:::python\n"
            
            # 関連する関数/クラスとの接続
            for lib in c_ffi_libs:
                node_name = lib["node"]
                if node_name in self.connection_nodes:
                    node_id = self.connection_nodes[node_name]["node_id"]
                    mermaid += f"    {node_id} -->|{lib['lib_path']}| python_ffi\n"
        
        # Flutter Channelノード
        if flutter_channels:
            mermaid += f"    python_channel_handler[\"📱 Flutter Channel Handler\"]:::python\n"
            
            # 関連する関数/クラスとの接続
            for channel in flutter_channels:
                node_name = channel["node"]
                if node_name in self.connection_nodes:
                    node_id = self.connection_nodes[node_name]["node_id"]
                    mermaid += f"    {node_id} -->|Flutter Channel| python_channel_handler\n"
        
        # スタイル定義
        mermaid += "  classDef python fill:#306998,stroke:#FFD43B,color:white;\n"
        mermaid += "```"
        
        return mermaid