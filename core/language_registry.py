# core/language_registry.py

"""
言語解析器の登録と管理を行うレジストリモジュール
"""

import os
from typing import Dict, List, Optional, Any


class LanguageRegistry:
    """言語解析器の登録と管理"""
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """シングルトンパターンでインスタンスを取得"""
        if cls._instance is None:
            cls._instance = LanguageRegistry()
        return cls._instance
    
    def __init__(self):
        self.analyzers = {}
        self.language_info = {}
    
    def register_analyzer(self, language_id: str, analyzer, language_display_name: str = None):
        """言語解析器を登録"""
        self.analyzers[language_id] = analyzer
        self.language_info[language_id] = {
            "display_name": language_display_name or language_id.capitalize()
        }
        
    def get_analyzer(self, language_id: str):
        """指定された言語の解析器を取得"""
        return self.analyzers.get(language_id)
    
    def get_analyzer_for_file(self, file_path: str):
        """ファイルに対応する解析器を取得"""
        for analyzer in self.analyzers.values():
            if analyzer.can_analyze(file_path):
                return analyzer
        return None
    
    def get_available_languages(self) -> List[str]:
        """利用可能な言語IDリストを取得"""
        return list(self.analyzers.keys())
    
    def get_language_display_names(self) -> Dict[str, str]:
        """言語IDと表示名のマッピングを取得"""
        return {lang_id: info["display_name"] 
                for lang_id, info in self.language_info.items()}
    
    def analyze_multi_language_project(self, file_paths: List[str]) -> Dict[str, Any]:
        """複数言語のプロジェクトを解析"""
        results = {}
        
        # 各解析器をリセット
        for language_id, analyzer in self.analyzers.items():
            analyzer.reset()
            
        # 各ファイルを適切な解析器で解析
        for file_path in file_paths:
            analyzer = self.get_analyzer_for_file(file_path)
            if analyzer:
                analyzer.analyze_file(file_path)
        
        # 言語間の連携を検出
        connections = []
        analyzers_list = list(self.analyzers.values())
        for i in range(len(analyzers_list)):
            for j in range(i+1, len(analyzers_list)):
                connections.extend(
                    analyzers_list[i].find_connections(analyzers_list[j])
                )
        
        # 結果を収集
        for language_id, analyzer in self.analyzers.items():
            results[language_id] = analyzer.generate_report()
        
        results["connections"] = connections
        return results
    
    def generate_multi_language_mermaid(self) -> str:
        """複数言語の連携を表すマーメード図を生成"""
        mermaid = "```mermaid\nflowchart LR\n"
        
        # 言語ごとのサブグラフを作成
        for language_id, analyzer in self.analyzers.items():
            display_name = self.language_info[language_id]["display_name"]
            mermaid += f"  subgraph {display_name}\n"
            
            # 言語ごとのマーメード図要素を追加
            lang_mermaid = analyzer.generate_mermaid()
            if lang_mermaid:
                # マーメード図テキストから実際のノード定義部分だけを抽出
                content = self._extract_mermaid_content(lang_mermaid)
                mermaid += content
            
            mermaid += "  end\n\n"
        
        # 言語間の連携を表す線を追加
        analyzers_list = list(self.analyzers.values())
        for i in range(len(analyzers_list)):
            for j in range(i+1, len(analyzers_list)):
                connections = analyzers_list[i].find_connections(analyzers_list[j])
                for conn in connections:
                    if "from_node" in conn and "to_node" in conn:
                        mermaid += f"  {conn['from_node']} -->|{conn.get('description', '')}| {conn['to_node']}\n"
        
        # スタイル定義
        mermaid += "  %% スタイル定義\n"
        mermaid += "  classDef python fill:#306998,stroke:#FFD43B,color:white;\n"
        mermaid += "  classDef flutter fill:#44D1FD,stroke:#0468D7,color:white;\n"
        mermaid += "  classDef javascript fill:#F7DF1E,stroke:#000000,color:black;\n"
        mermaid += "  classDef java fill:#ED8B00,stroke:#5382A1,color:white;\n"
        mermaid += "  classDef cpp fill:#659AD2,stroke:#004482,color:white;\n"
        mermaid += "```"
        
        return mermaid
    
    def _extract_mermaid_content(self, mermaid_text: str) -> str:
        """マーメード図テキストから中身だけを抽出"""
        if "```mermaid" in mermaid_text:
            # バッククォートやflowchartなどの宣言を除去
            content = mermaid_text.split("```mermaid", 1)[1]
            if "```" in content:
                content = content.split("```", 1)[0]
            
            lines = content.strip().split("\n")
            # flowchart宣言行と最後のスタイル定義を除去
            filtered_lines = []
            for line in lines:
                if line.strip().startswith("flowchart") or "classDef" in line:
                    continue
                filtered_lines.append(line)
            
            return "\n".join(filtered_lines)
        return ""