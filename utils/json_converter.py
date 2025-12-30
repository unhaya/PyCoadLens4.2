# utils/json_converter.py
import json
import os
import re

def text_to_json_structure(text_content):
    """テキスト形式の解析結果をJSON構造に変換する"""
    result = {
        "directory_structure": [],
        "classes": [],
        "functions": [],
        "imports": []
    }
    
    current_section = None
    current_class = None
    current_function = None
    
    # 行ごとに解析
    for line in text_content.split('\n'):
        line = line.rstrip()
        
        # 空行はスキップ
        if not line:
            continue
            
        # セクションヘッダーの検出
        if line.startswith('# '):
            section_name = line[2:].lower()
            if 'ディレクトリ' in section_name:
                current_section = 'directory'
            elif 'クラス' in section_name:
                current_section = 'classes'
            elif '関数' in section_name:
                current_section = 'functions'
            elif 'インポート' in section_name:
                current_section = 'imports'
            else:
                current_section = None
            continue
            
        # 現在のセクションに応じて処理
        if current_section == 'directory':
            if not line.startswith('#'):  # ヘッダー以外の行を追加
                result["directory_structure"].append(line)
                
        elif current_section == 'imports':
            result["imports"].append(line)
            
        elif current_section == 'classes':
            if line.startswith('class '):
                # 新しいクラス定義
                class_info = {"name": "", "file": "", "extends": "", "methods": []}
                
                # クラス名とファイル名を抽出（例: RecognizedText (voice2025.py)）
                class_match = re.match(r'class\s+(\w+)(?:\s+<-\s+(\w+))?\s*(?:\((.*?)\))?', line)
                if class_match:
                    class_info["name"] = class_match.group(1)
                    if class_match.group(2):  # 継承元がある場合
                        class_info["extends"] = class_match.group(2)
                    if class_match.group(3):  # ファイル名がある場合
                        class_info["file"] = class_match.group(3)
                
                current_class = class_info
                result["classes"].append(current_class)
                
            elif line.strip().startswith('メソッド:'):
                # メソッドリストの開始
                continue
                
            elif line.strip().startswith('def ') and current_class:
                # メソッド定義（クラス内のメソッド）
                method_match = re.match(r'\s*def\s+([^(]+)', line)
                if method_match:
                    method_name = method_match.group(1).strip()
                    current_class["methods"].append(method_name)
                    
            elif line.strip() and current_class and line.strip()[0].isspace():
                # クラス配下のインデントされた行（メソッド定義の可能性）
                method_match = re.match(r'\s+([^(]+)\(.*\)', line)
                if method_match:
                    method_name = method_match.group(1).strip()
                    if method_name not in current_class["methods"]:
                        current_class["methods"].append(method_name)
                
        elif current_section == 'functions':
            function_match = re.match(r'(?:def\s+)?([^(]+)(?:\(.*\))?(?:\s+->\s+.*)?', line)
            if function_match:
                func_name = function_match.group(1).strip()
                if func_name and not func_name.startswith('#'):
                    if func_name not in result["functions"]:
                        result["functions"].append(func_name)
    
    return result

def extract_llm_structured_data(text):
    """拡張解析テキストからLLM向け構造化データを抽出する"""
    result = {
        "call_graph": {"data": []},
        "dependencies": {}
    }
    
    # LLM向け構造化データセクションを探す
    start_marker = "## LLM向け構造化データ"
    code_start = "```"
    code_end = "```"
    
    if start_marker in text:
        # セクション開始位置を見つける
        start_pos = text.find(start_marker)
        # コードブロック開始位置を見つける
        code_start_pos = text.find(code_start, start_pos)
        if code_start_pos != -1:
            # コードブロック終了位置を見つける
            code_end_pos = text.find(code_end, code_start_pos + len(code_start))
            if code_end_pos != -1:
                # コードブロック内のテキストを抽出
                code_content = text[code_start_pos + len(code_start):code_end_pos].strip()
                
                # コード内容を解析して構造化
                current_section = None
                current_subsection = None
                
                # コールグラフとデータセクションを格納する変数
                call_graph_data = []
                dependency_data = {}
                current_dependency = None
                
                for line in code_content.split("\n"):
                    if line.startswith("# "):
                        # 新しいメインセクションの開始
                        current_section = line[2:].strip()
                        current_subsection = None
                        current_dependency = None
                        
                    elif current_section == "コールグラフ":
                        # コールグラフの行を追加
                        if line.strip() and " -> " in line:
                            call_graph_data.append(line.strip())
                            
                    elif current_section == "主要な関数依存関係":
                        # 関数依存関係の処理
                        if " -> " in line:
                            # 新しい依存関係の開始
                            parts = line.split(" -> ")
                            if len(parts) == 2:
                                current_dependency = parts[0].strip()
                                deps = [dep.strip() for dep in parts[1].split(",")]
                                dependency_data[current_dependency] = deps
                        elif current_dependency and line.strip():
                            # 既存の依存関係の継続
                            deps = [dep.strip() for dep in line.split(",")]
                            if current_dependency in dependency_data:
                                dependency_data[current_dependency].extend(deps)
                            else:
                                dependency_data[current_dependency] = deps
                
                # 結果をまとめる
                if call_graph_data:
                    result["call_graph"]["data"] = call_graph_data
                if dependency_data:
                    result["dependencies"] = dependency_data
    
    return result

def save_as_json(data, output_path):
    """データをJSONファイルとして保存する"""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return f"JSONファイルを保存しました: {output_path}"