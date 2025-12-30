# core/dependency.py

import ast
import os
import traceback

def generate_call_graph(python_files):
    """指定されたPythonファイルからコールグラフを生成する"""
    try:
        if not python_files:
            return "コールグラフ生成対象のPythonファイルがありません。"
        
        # 関数/メソッドの呼び出し関係を保存する辞書
        call_graph = {}
        
        # 全てのモジュールをパースして保存
        modules = {}
        module_functions = {}  # モジュール内の関数とメソッドを記録
        
        # Step 1: すべてのモジュールをパースし、関数とメソッドを登録
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8-sig') as file:
                    code = file.read()

                # 有効なPythonコードかどうか事前チェック
                try:
                    compile(code, file_path, 'exec')
                except SyntaxError:
                    print(f"コールグラフ: スキップ（構文エラー）: {file_path}")
                    continue

                module = ast.parse(code)
                module_name = os.path.basename(file_path).replace('.py', '')
                modules[module_name] = module
                
                # このモジュール内の関数とメソッドを記録
                module_functions[module_name] = {}
                
                # 関数の登録
                for node in module.body:
                    if isinstance(node, ast.FunctionDef):
                        full_name = f"{module_name}.{node.name}"
                        module_functions[module_name][node.name] = full_name
                        call_graph[full_name] = set()
                
                # クラスとそのメソッドの登録
                for node in module.body:
                    if isinstance(node, ast.ClassDef):
                        class_name = node.name
                        for method in node.body:
                            if isinstance(method, ast.FunctionDef):
                                full_name = f"{module_name}.{class_name}.{method.name}"
                                module_functions[module_name][f"{class_name}.{method.name}"] = full_name
                                call_graph[full_name] = set()
            
            except Exception as e:
                print(f"ファイル {file_path} のパース中にエラー: {e}")
        
        # Step 2: 各モジュールを再度走査して呼び出し関係を構築
        for module_name, module in modules.items():
            _analyze_module_calls(module, module_name, modules, module_functions, call_graph)
        
        # Step 3: コールグラフをテキスト形式で整形
        result = "# コールグラフ\n"
        
        # 呼び出し元がある関数のみを表示（外部から呼ばれないユーティリティ関数を除外）
        has_callers = set()
        for callee_set in call_graph.values():
            has_callers.update(callee_set)
        
        # 呼び出し元から呼び出し先を整理
        sorted_callers = sorted(call_graph.keys())
        for caller in sorted_callers:
            if caller in has_callers or call_graph[caller]:  # 呼び出される関数か、他の関数を呼び出す関数
                callees = sorted(call_graph[caller])
                if callees:
                    result += f"{caller} -> {', '.join(callees)}\n"
        
        return result
    
    except ImportError:
        return "astroidライブラリがインストールされていません。\npip install astroid でインストールしてください。"
    except Exception as e:
        
        traceback.print_exc()
        return f"コールグラフの生成中にエラーが発生しました:\n{str(e)}"

def _analyze_module_calls(module, module_name, modules, module_functions, call_graph):
    """モジュール内の関数呼び出しを解析する"""
    
    # 関数定義を処理
    for node in module.body:
        if isinstance(node, ast.FunctionDef):
            caller_name = f"{module_name}.{node.name}"
            for child_node in node.body:
                _find_calls_in_node(child_node, caller_name, module_functions, call_graph)
        
        # クラス内のメソッドを処理
        elif isinstance(node, ast.ClassDef):
            class_name = node.name
            for method in node.body:
                if isinstance(method, ast.FunctionDef):
                    caller_name = f"{module_name}.{class_name}.{method.name}"
                    for child_node in method.body:
                        _find_calls_in_node(child_node, caller_name, module_functions, call_graph)

def _find_calls_in_node(node, caller_name, module_functions, call_graph):
    """ノード内の関数呼び出しを再帰的に検索"""
    # Call ノードの場合は関数呼び出しを記録
    if isinstance(node, ast.Call):
        try:
            # node.func が Name 型の場合（直接の関数呼び出し）
            if isinstance(node.func, ast.Name):
                called_name = node.func.name
                
                # 呼び出し先の関数をモジュール関数から探す
                for module_name, functions in module_functions.items():
                    if called_name in functions:
                        full_called_name = functions[called_name]
                        if caller_name in call_graph:
                            call_graph[caller_name].add(full_called_name)
            
            # node.func が Attribute 型の場合 (obj.method() 形式)
            elif isinstance(node.func, ast.Attribute) and hasattr(node.func, 'attr'):
                # self.method() 形式の呼び出しを処理
                if isinstance(node.func.value, ast.Name) and node.func.value.id == 'self':
                    # caller_name から "module.class.method" 形式を解析
                    parts = caller_name.split('.')
                    if len(parts) >= 3:  # module.class.method 形式であることを確認
                        module_name, class_name = parts[0], parts[1]
                        method_key = f"{class_name}.{node.func.attr}"
                        
                        # 呼び出し先のメソッドをモジュール関数から探す
                        if module_name in module_functions and method_key in module_functions[module_name]:
                            full_called_name = module_functions[module_name][method_key]
                            if caller_name in call_graph:
                                call_graph[caller_name].add(full_called_name)
        except AttributeError:
            # node.func に必要な属性がない場合は無視
            pass
    
    # 子ノードを再帰的に処理
    for child in ast.iter_child_nodes(node):
        _find_calls_in_node(child, caller_name, module_functions, call_graph)