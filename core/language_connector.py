# core/language_connector.py

"""
言語間の連携ポイントを検出して分析するモジュール
"""

import os
import re
from typing import Dict, List, Any, Tuple

from .language_base import LanguageAnalyzerBase


class LanguageConnector:
    """異なる言語間の連携ポイントを検出・分析するクラス"""
    
    def __init__(self):
        self.connection_patterns = self._initialize_patterns()
        self.detected_connections = []
    
    def _initialize_patterns(self) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """言語ごとの連携パターンを初期化"""
        return {
            "python": {
                "api": [
                    {
                        "pattern": r"@app\.route\(['\"]([^'\"]+)['\"]\)",
                        "description": "Flask API endpoint",
                        "type": "web_api"
                    },
                    {
                        "pattern": r"@api_view\(\[",
                        "description": "Django REST Framework API",
                        "type": "web_api"
                    },
                    {
                        "pattern": r"class\s+\w+\(APIView\)",
                        "description": "Django REST API View",
                        "type": "web_api"
                    },
                    {
                        "pattern": r"fastapi\.(?:get|post|put|delete)\(['\"]([^'\"]+)['\"]\)",
                        "description": "FastAPI endpoint",
                        "type": "web_api"
                    }
                ],
                "ffi": [
                    {
                        "pattern": r"ctypes\.CDLL\(['\"]([^'\"]+)['\"]\)",
                        "description": "C FFI via ctypes",
                        "type": "c_ffi"
                    },
                    {
                        "pattern": r"cffi\.",
                        "description": "C FFI via CFFI",
                        "type": "c_ffi"
                    }
                ],
                "flutter": [
                    {
                        "pattern": r"MethodChannel\(['\"]([^'\"]+)['\"]\)\.setMethodCallHandler",
                        "description": "Flutter MethodChannel handler",
                        "type": "flutter_channel"
                    }
                ]
            },
            "flutter": {
                "python": [
                    {
                        "pattern": r"MethodChannel\(['\"]([^'\"]+)['\"]\)",
                        "description": "Method Channel to Native/Python",
                        "type": "python_channel"
                    },
                    {
                        "pattern": r"http\.(?:get|post|put|delete)\(['\"]([^'\"]+)['\"]\)",
                        "description": "HTTP API call",
                        "type": "python_api"
                    },
                    {
                        "pattern": r"dio\.(?:get|post|put|delete)\(['\"]([^'\"]+)['\"]\)",
                        "description": "HTTP API call via Dio",
                        "type": "python_api"
                    }
                ]
            }
            # 他の言語のパターンも同様に追加可能
        }
    
    def detect_connections(self, analyzers: Dict[str, LanguageAnalyzerBase]) -> List[Dict[str, Any]]:
        """複数の言語解析器から連携ポイントを検出"""
        self.detected_connections = []
        
        # 言語ペアごとに連携を検出
        languages = list(analyzers.keys())
        for i in range(len(languages)):
            for j in range(i+1, len(languages)):
                lang1 = languages[i]
                lang2 = languages[j]
                
                # 双方向で連携を検出
                self._detect_between(lang1, lang2, analyzers[lang1], analyzers[lang2])
                self._detect_between(lang2, lang1, analyzers[lang2], analyzers[lang1])
        
        return self.detected_connections
    
    def _detect_between(self, from_lang: str, to_lang: str, from_analyzer: LanguageAnalyzerBase, to_analyzer: LanguageAnalyzerBase):
        """2つの言語間の連携を検出"""
        # from_langからto_langへの連携パターンがあるか確認
        if from_lang in self.connection_patterns and to_lang in self.connection_patterns[from_lang]:
            patterns = self.connection_patterns[from_lang][to_lang]
            
            # from_analyzorの各ファイルでパターンを検索
            for file_path in from_analyzer.files:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    # 各パターンで検索
                    for pattern_info in patterns:
                        for match in re.finditer(pattern_info["pattern"], content):
                            value = match.group(1) if match.groups() else ""
                            
                            connection = {
                                "from_language": from_lang,
                                "to_language": to_lang,
                                "file": file_path,
                                "type": pattern_info["type"],
                                "description": pattern_info["description"],
                                "value": value,
                                "match": match.group(0)
                            }
                            
                            # 連携に関連するコンポーネントを探す
                            component = self._find_related_component(from_analyzer, file_path, match.start())
                            if component:
                                connection["component"] = component
                            
                            self.detected_connections.append(connection)
                
                except Exception as e:
                    print(f"Error detecting connections in {file_path}: {str(e)}")
    
    def _find_related_component(self, analyzer: LanguageAnalyzerBase, file_path: str, position: int) -> Dict[str, Any]:
        """連携に関連するコンポーネント（クラス・関数など）を特定"""
        # この実装はLanguageAnalyzerBaseに追加機能が必要になる可能性があります
        # 単純な実装としては、ファイル名と位置情報からコンポーネントを推測
        filename = os.path.basename(file_path)
        
        # FlutterAnalyzerとなどの特定の解析器の場合
        if hasattr(analyzer, "dart_components"):
            # クラスをチェック
            for cls in analyzer.dart_components["classes"]:
                if cls["file"] == filename:
                    return {
                        "type": "class",
                        "name": cls["name"]
                    }
            
            # 関数をチェック
            for func in analyzer.dart_components["functions"]:
                if func["file"] == filename:
                    return {
                        "type": "function",
                        "name": func["name"]
                    }
        
        # AstroidAnalyzerなどの場合は別の方法で関連コンポーネントを探す必要がある
        
        return None
    
    def generate_connection_mermaid(self) -> str:
        """検出された連携のマーメード図を生成"""
        mermaid = "```mermaid\nflowchart LR\n"
        
        # 言語ごとのサブグラフとノード
        languages = {}
        
        # 連携から言語を特定
        for conn in self.detected_connections:
            from_lang = conn["from_language"]
            to_lang = conn["to_language"]
            
            if from_lang not in languages:
                languages[from_lang] = {"nodes": {}}
            if to_lang not in languages:
                languages[to_lang] = {"nodes": {}}
            
            # コンポーネントがある場合はノードを追加
            if "component" in conn:
                comp = conn["component"]
                node_id = f"{from_lang}_{comp['type']}_{comp['name']}"
                
                languages[from_lang]["nodes"][node_id] = {
                    "name": comp["name"],
                    "type": comp["type"]
                }
        
        # 言語ごとのサブグラフを作成
        for lang_id, lang_info in languages.items():
            lang_name = lang_id.capitalize()
            mermaid += f"  subgraph {lang_name}\n"
            
            # ノードを追加
            for node_id, node_info in lang_info["nodes"].items():
                icon = "🔷" if node_info["type"] == "class" else "⚙️"
                mermaid += f"    {node_id}[\"{icon} {node_info['name']}\"]:::{lang_id}\n"
            
            # 言語にノードがない場合はデフォルトノードを追加
            if not lang_info["nodes"]:
                mermaid += f"    {lang_id}_default[\"{lang_name}\"]:::{lang_id}\n"
            
            mermaid += "  end\n\n"
        
        # 連携を表す線を追加
        for conn in self.detected_connections:
            from_lang = conn["from_language"]
            to_lang = conn["to_language"]
            
            # 開始ノードを決定
            from_node = f"{from_lang}_default"
            if "component" in conn:
                comp = conn["component"]
                from_node = f"{from_lang}_{comp['type']}_{comp['name']}"
            
            # 終了ノードを決定
            to_node = f"{to_lang}_default"
            
            # 連携の説明
            description = conn.get("description", "")
            if "value" in conn and conn["value"]:
                description += f": {conn['value']}"
            
            mermaid += f"  {from_node} -->|{description}| {to_node}\n"
        
        # スタイル定義
        mermaid += "  %% スタイル定義\n"
        mermaid += "  classDef python fill:#306998,stroke:#FFD43B,color:white;\n"
        mermaid += "  classDef flutter fill:#44D1FD,stroke:#0468D7,color:white;\n"
        mermaid += "  classDef javascript fill:#F7DF1E,stroke:#000000,color:black;\n"
        mermaid += "  classDef java fill:#ED8B00,stroke:#5382A1,color:white;\n"
        mermaid += "  classDef cpp fill:#659AD2,stroke:#004482,color:white;\n"
        mermaid += "```"
        
        return mermaid