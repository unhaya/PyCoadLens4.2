# core/flutter_analyzer.py

"""
Flutter/Dartコードの解析とPython連携の検出を行うモジュール
"""

import os
import re
from typing import List, Dict, Any

from .language_base import LanguageAnalyzerBase


class FlutterAnalyzer(LanguageAnalyzerBase):
    """Flutter/Dartコードの解析とPython連携の検出"""
    
    def __init__(self):
        super().__init__()
        self.dart_components = {}
        self.python_connections = []
        self.connection_nodes = {}
    
    def reset(self):
        super().reset()
        self.dart_components = {
            "widgets": [],
            "classes": [],
            "methods": [],
            "functions": []
        }
        self.python_connections = []
        self.connection_nodes = {}
    
    def get_file_extensions(self):
        """対応するファイル拡張子"""
        return [".dart"]
    
    def get_language_name(self):
        """言語名を返す"""
        return "Flutter/Dart"
    
    def analyze_file(self, file_path):
        """Dartファイルを解析"""
        self.files.append(file_path)
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # ファイルの内容を解析
            self._analyze_dart_content(file_path, content)
            
        except Exception as e:
            print(f"Error analyzing Flutter file {file_path}: {str(e)}")
    
    def _analyze_dart_content(self, file_path, content):
        """Dartコードの内容を解析"""
        # クラス、ウィジェット、メソッドなどを検出
        self._extract_dart_components(file_path, content)
        
        # Pythonとの連携ポイントを検出
        self._find_python_connections(file_path, content)
    
    def _extract_dart_components(self, file_path, content):
        """Dartのコンポーネント（クラス、関数など）を抽出"""
        filename = os.path.basename(file_path)
        
        # クラス検出
        class_pattern = r"class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w\s,]+))?\s*{"
        for match in re.finditer(class_pattern, content):
            class_name = match.group(1)
            parent_class = match.group(2)
            
            # クラスタイプの判定
            class_type = "Class"
            if parent_class in ["StatelessWidget", "StatefulWidget", "Widget"]:
                class_type = "Widget"
            elif "State<" in content:
                class_type = "State"
            
            self.dart_components["classes"].append({
                "name": class_name,
                "parent": parent_class,
                "type": class_type,
                "file": filename
            })
            
            # 接続ノード情報を保存
            node_id = f"flutter_class_{len(self.dart_components['classes']) - 1}"
            self.connection_nodes[class_name] = {
                "node_id": node_id,
                "type": "class",
                "name": class_name
            }
        
        # メソッド検出
        method_pattern = r"(?:@override\s+)?(?:void|String|int|double|bool|Future|List|Map|Widget|dynamic|\w+)\s+(\w+)\s*\([^)]*\)\s*(?:async)?\s*{"
        for match in re.finditer(method_pattern, content):
            method_name = match.group(1)
            if method_name not in ["build", "initState", "dispose"]:  # 一般的なライフサイクルメソッドを除外
                self.dart_components["methods"].append({
                    "name": method_name,
                    "file": filename
                })
        
        # トップレベル関数検出
        function_pattern = r"(?:void|String|int|double|bool|Future|List|Map|Widget|dynamic|\w+)\s+(\w+)\s*\([^)]*\)\s*(?:async)?\s*{"
        current_pos = 0
        for match in re.finditer(function_pattern, content):
            # クラス内のメソッドではなく、トップレベルの関数のみを抽出
            match_start = match.start()
            
            # 直前に"class"キーワードがあるか確認
            prev_content = content[max(0, match_start - 500):match_start]
            if not re.search(r"class\s+\w+", prev_content.split("\n")[-1]):
                func_name = match.group(1)
                self.dart_components["functions"].append({
                    "name": func_name,
                    "file": filename
                })
                
                # 接続ノード情報を保存
                node_id = f"flutter_func_{len(self.dart_components['functions']) - 1}"
                self.connection_nodes[func_name] = {
                    "node_id": node_id,
                    "type": "function",
                    "name": func_name
                }
    
    def _find_python_connections(self, file_path, content):
        """Pythonとの連携ポイントを検出"""
        filename = os.path.basename(file_path)
        
        # FFI関連の検出
        if "dart:ffi" in content:
            ffi_conn = {
                "type": "FFI",
                "file": filename,
                "description": "Dart FFI may be used to connect with Python"
            }
            self.python_connections.append(ffi_conn)
        
        # MethodChannel検出（Flutter-ネイティブ間通信）
        method_channel_pattern = r"MethodChannel\(['\"]([^'\"]+)['\"]\)"
        for match in re.finditer(method_channel_pattern, content):
            channel_name = match.group(1)
            channel_conn = {
                "type": "MethodChannel",
                "channel": channel_name,
                "file": filename,
                "description": f"MethodChannel '{channel_name}' could be used with Python backend"
            }
            self.python_connections.append(channel_conn)
            
            # どのクラスに属するか推定（単純な実装として、最も近いクラスを関連付け）
            match_pos = match.start()
            for cls in self.dart_components["classes"]:
                if cls["file"] == filename:
                    channel_conn["class"] = cls["name"]
                    break
        
        # HTTP/API呼び出し検出
        http_patterns = [
            r"http\.get\(['\"]([^'\"]+)['\"]\)",
            r"http\.post\(['\"]([^'\"]+)['\"]\)",
            r"dio\.get\(['\"]([^'\"]+)['\"]\)",
            r"dio\.post\(['\"]([^'\"]+)['\"]\)"
        ]
        
        for pattern in http_patterns:
            for match in re.finditer(pattern, content):
                url = match.group(1) if match.groups() else "unknown_url"
                http_conn = {
                    "type": "HTTP_API",
                    "url": url,
                    "file": filename,
                    "description": f"HTTP API call to {url}"
                }
                self.python_connections.append(http_conn)
                
                # どのクラスに属するか推定
                match_pos = match.start()
                for cls in self.dart_components["classes"]:
                    if cls["file"] == filename:
                        http_conn["class"] = cls["name"]
                        break
    
    def find_connections(self, other_analyzer):
        """他の言語解析器（主にPython）との連携ポイントを検出"""
        connections = []
        
        # 他の解析器がPythonの場合
        if hasattr(other_analyzer, "get_language_name") and other_analyzer.get_language_name() == "Python":
            # 各連携ポイントをチェック
            for conn in self.python_connections:
                connection = {
                    "from": "flutter",
                    "to": "python",
                    "type": conn["type"],
                    "description": conn["description"]
                }
                
                # クラスが特定できている場合、ノードIDを設定
                if "class" in conn and conn["class"] in self.connection_nodes:
                    node_info = self.connection_nodes[conn["class"]]
                    connection["from_node"] = node_info["node_id"]
                else:
                    # デフォルトは最初のクラスを使用
                    if self.dart_components["classes"]:
                        cls_name = self.dart_components["classes"][0]["name"]
                        if cls_name in self.connection_nodes:
                            connection["from_node"] = self.connection_nodes[cls_name]["node_id"]
                
                # Python側のノードは仮でAPIとする
                connection["to_node"] = "python_api"
                
                connections.append(connection)
        
        return connections
    
    def generate_report(self):
        """解析結果レポートを生成"""
        return {
            "language": "flutter",
            "file_count": len(self.files),
            "components": self.dart_components,
            "python_connections": self.python_connections
        }
    
    def generate_mermaid(self):
        """Flutter-Python連携のマーメード図を生成"""
        mermaid = "```mermaid\nflowchart LR\n"
        
        # クラスノード
        for i, cls in enumerate(self.dart_components["classes"]):
            node_id = f"flutter_class_{i}"
            icon = "📱" if cls["type"] == "Widget" else "🔷"
            mermaid += f"    {node_id}[\"{icon} {cls['name']}\"]:::flutter\n"
        
        # 関数ノード
        for i, func in enumerate(self.dart_components["functions"]):
            node_id = f"flutter_func_{i}"
            mermaid += f"    {node_id}[\"⚙️ {func['name']}()\"]:::flutter\n"
        
        # 連携ノード
        if self.python_connections:
            for i, conn in enumerate(self.python_connections):
                conn_type = conn["type"]
                if conn_type == "MethodChannel":
                    channel = conn.get("channel", "unknown")
                    if "class" in conn:
                        class_name = conn["class"]
                        for j, cls in enumerate(self.dart_components["classes"]):
                            if cls["name"] == class_name:
                                node_id = f"flutter_class_{j}"
                                mermaid += f"    {node_id} -->|\"Channel: {channel}\"|python_api\n"
                                break
                elif conn_type == "HTTP_API":
                    url = conn.get("url", "unknown")
                    if "class" in conn:
                        class_name = conn["class"]
                        for j, cls in enumerate(self.dart_components["classes"]):
                            if cls["name"] == class_name:
                                node_id = f"flutter_class_{j}"
                                mermaid += f"    {node_id} -->|\"API: {url}\"|python_api\n"
                                break
                elif conn_type == "FFI":
                    # FFIはプロジェクト全体の関係として表示
                    if self.dart_components["classes"]:
                        node_id = f"flutter_class_0"  # 最初のクラスを代表として使用
                        mermaid += f"    {node_id} -->|\"FFI\"|python_ffi\n"
        
        # スタイル定義
        mermaid += "  classDef flutter fill:#44D1FD,stroke:#0468D7,color:white;\n"
        mermaid += "```"
        
        return mermaid