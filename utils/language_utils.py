# utils/language_utils.py

"""
多言語対応のためのユーティリティ関数を提供するモジュール
"""

import os
import re
from typing import Dict, List, Any, Optional


def detect_language(file_path: str) -> str:
    """ファイル拡張子から言語を推定"""
    ext = os.path.splitext(file_path)[1].lower()
    
    language_map = {
        ".py": "python",
        ".dart": "flutter",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".java": "java",
        ".kt": "kotlin",
        ".c": "c",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".h": "c_header",
        ".hpp": "cpp_header",
        ".go": "go",
        ".rs": "rust",
        ".swift": "swift",
        ".rb": "ruby",
        ".php": "php",
        ".cs": "csharp",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".xml": "xml",
        ".html": "html",
        ".css": "css",
        ".scss": "scss",
        ".sass": "sass"
    }
    
    return language_map.get(ext, "unknown")


def get_language_display_name(language_id: str) -> str:
    """言語IDから表示名を取得"""
    display_names = {
        "python": "Python",
        "flutter": "Flutter/Dart",
        "javascript": "JavaScript",
        "typescript": "TypeScript",
        "java": "Java",
        "kotlin": "Kotlin",
        "c": "C",
        "cpp": "C++",
        "c_header": "C Header",
        "cpp_header": "C++ Header",
        "go": "Go",
        "rust": "Rust",
        "swift": "Swift",
        "ruby": "Ruby",
        "php": "PHP",
        "csharp": "C#",
        "json": "JSON",
        "yaml": "YAML",
        "xml": "XML",
        "html": "HTML",
        "css": "CSS",
        "scss": "SCSS",
        "sass": "Sass"
    }
    
    return display_names.get(language_id, language_id.capitalize())


def get_language_color(language_id: str) -> str:
    """言語IDに対応する色コードを取得（マーメード図などで使用）"""
    colors = {
        "python": "#306998",
        "flutter": "#44D1FD",
        "javascript": "#F7DF1E",
        "typescript": "#3178C6",
        "java": "#ED8B00",
        "kotlin": "#7F52FF",
        "c": "#A8B9CC",
        "cpp": "#659AD2",
        "go": "#00ADD8",
        "rust": "#DEA584",
        "swift": "#FA7343",
        "ruby": "#CC342D",
        "php": "#777BB4",
        "csharp": "#178600"
    }
    
    return colors.get(language_id, "#888888")


class ConnectionPattern:
    """言語間連携の共通パターン定義"""
    
    # 連携パターンの種類
    API_CALL = "api_call"
    FFI = "ffi"
    FILE_IO = "file_io"
    SUBPROCESS = "subprocess"
    IPC = "ipc"
    
    @staticmethod
    def get_patterns_for_language(language_id: str) -> Dict[str, List[str]]:
        """言語ごとの一般的な連携パターンを取得"""
        patterns = {
            "python": {
                "api_patterns": [
                    r"@app\.route\(['\"]([^'\"]+)['\"]\)",  # Flask
                    r"@api_view\(\[",  # Django REST framework
                    r"class\s+\w+\(APIView\)",  # Django REST framework
                    r"fastapi\.(?:get|post|put|delete)\(['\"]([^'\"]+)['\"]\)",  # FastAPI
                ],
                "ffi_patterns": [
                    r"ctypes\.CDLL\(['\"]([^'\"]+)['\"]\)",  # ctypes
                    r"from\s+cffi\s+import",  # CFFI
                ],
                "subprocess_patterns": [
                    r"subprocess\.(?:Popen|call|run)\(",  # subprocess
                    r"os\.system\(",  # os.system
                ],
                "file_patterns": [
                    r"with\s+open\(['\"]([^'\"]+)['\"]",  # ファイル操作
                    r"json\.(?:load|dump)\(",  # JSON操作
                ],
                "flutter_patterns": [
                    r"MethodChannel\(['\"]([^'\"]+)['\"]\)\.setMethodCallHandler",  # Flutter channel
                ]
            },
            "flutter": {
                "api_patterns": [
                    r"http\.(?:get|post|put|delete)\(['\"]([^'\"]+)['\"]\)",  # HTTP request
                    r"dio\.(?:get|post|put|delete)\(['\"]([^'\"]+)['\"]\)",  # Dio HTTP client
                ],
                "ipc_patterns": [
                    r"MethodChannel\(['\"]([^'\"]+)['\"]\)",  # Platform channel
                    r"EventChannel\(['\"]([^'\"]+)['\"]\)",  # Event channel
                ],
                "ffi_patterns": [
                    r"import\s+'dart:ffi'",  # Dart FFI
                    r"DynamicLibrary\.(?:open|process)\(",  # DynamicLibrary
                ],
                "file_patterns": [
                    r"File\(['\"]([^'\"]+)['\"]\)",  # File I/O
                    r"rootBundle\.loadString\(",  # Asset loading
                ],
            },
            "javascript": {
                "api_patterns": [
                    r"fetch\(['\"]([^'\"]+)['\"]\)",  # Fetch API
                    r"axios\.(?:get|post|put|delete)\(['\"]([^'\"]+)['\"]\)",  # Axios
                ],
                "file_patterns": [
                    r"fs\.(?:readFile|writeFile)\(",  # Node.js ファイル操作
                    r"JSON\.(?:parse|stringify)\(",  # JSON操作
                ],
                "subprocess_patterns": [
                    r"child_process\.(?:spawn|exec|execFile)\(",  # Node.js プロセス
                ],
            },
            # 他の言語も同様に定義可能
        }
        
        return patterns.get(language_id, {})
    
    @staticmethod
    def match_patterns(content: str, patterns: List[str]) -> List[str]:
        """コンテンツに対してパターンマッチングを実行"""
        matches = []
        for pattern in patterns:
            for match in re.finditer(pattern, content):
                if match.groups():
                    matches.append(match.group(1))
                else:
                    matches.append(match.group(0))
        return matches


def extract_imports(file_path: str, language_id: str = None) -> List[Dict[str, str]]:
    """ファイルからインポート文を抽出"""
    if language_id is None:
        language_id = detect_language(file_path)
    
    imports = []
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 言語ごとのインポートパターン
        if language_id == "python":
            # Pythonのimport文
            import_patterns = [
                r"import\s+([\w\.]+)(?:\s+as\s+(\w+))?",
                r"from\s+([\w\.]+)\s+import\s+(.+)"
            ]
            
            for pattern in import_patterns:
                for match in re.finditer(pattern, content):
                    if "from" in pattern:
                        module = match.group(1)
                        imported = match.group(2)
                        imports.append({
                            "type": "from_import",
                            "module": module,
                            "imported": imported.strip()
                        })
                    else:
                        module = match.group(1)
                        alias = match.group(2) if match.group(2) else None
                        imports.append({
                            "type": "import",
                            "module": module,
                            "alias": alias
                        })
        
        elif language_id == "flutter":
            # Dartのimport文
            import_pattern = r"import\s+['\"]([^'\"]+)['\"](?:\s+as\s+(\w+))?;"
            
            for match in re.finditer(import_pattern, content):
                module = match.group(1)
                alias = match.group(2) if match.groups() > 1 and match.group(2) else None
                imports.append({
                    "type": "import",
                    "module": module,
                    "alias": alias
                })
        
        elif language_id in ["javascript", "typescript"]:
            # JS/TSのimport文
            import_patterns = [
                r"import\s+(?:\*\s+as\s+(\w+)|{\s*([^}]+)\s*}|\s*(\w+)\s*)\s+from\s+['\"]([^'\"]+)['\"]",
                r"const\s+(\w+)\s+=\s+require\(['\"]([^'\"]+)['\"]\)"
            ]
            
            for pattern in import_patterns:
                for match in re.finditer(pattern, content):
                    if "require" in pattern:
                        var_name = match.group(1)
                        module = match.group(2)
                        imports.append({
                            "type": "require",
                            "module": module,
                            "var_name": var_name
                        })
                    else:
                        namespace = match.group(1)
                        named_imports = match.group(2)
                        default_import = match.group(3)
                        module = match.group(4)
                        
                        if namespace:
                            imports.append({
                                "type": "namespace_import",
                                "module": module,
                                "namespace": namespace
                            })
                        elif named_imports:
                            imports.append({
                                "type": "named_imports",
                                "module": module,
                                "imports": [imp.strip() for imp in named_imports.split(",")]
                            })
                        elif default_import:
                            imports.append({
                                "type": "default_import",
                                "module": module,
                                "name": default_import
                            })
        
    except Exception as e:
        print(f"Error extracting imports from {file_path}: {str(e)}")
    
    return imports


def analyze_imports_for_connections(file_imports: Dict[str, List[Dict[str, str]]]) -> List[Dict[str, Any]]:
    """異なる言語間のインポート関係から連携ポイントを検出"""
    connections = []
    
    # Python-Flutterの連携を検出
    python_imports = file_imports.get("python", [])
    flutter_imports = file_imports.get("flutter", [])
    
    # Pythonで使われるFlutter関連モジュール
    flutter_related_modules = ["flutter", "dart"]
    
    for file_path, imports in python_imports.items():
        for imp in imports:
            module = imp.get("module", "")
            if any(flutter_mod in module.lower() for flutter_mod in flutter_related_modules):
                connections.append({
                    "from_language": "python",
                    "to_language": "flutter",
                    "file": file_path,
                    "module": module,
                    "type": "import",
                    "description": f"Python importing Flutter-related module: {module}"
                })
    
    # Flutter側からPython関連の検出
    python_related_keywords = ["python", "ffi"]
    
    for file_path, imports in flutter_imports.items():
        for imp in imports:
            module = imp.get("module", "")
            if any(py_keyword in module.lower() for py_keyword in python_related_keywords):
                connections.append({
                    "from_language": "flutter",
                    "to_language": "python",
                    "file": file_path,
                    "module": module,
                    "type": "import",
                    "description": f"Flutter importing Python-related module: {module}"
                })
    
    return connections