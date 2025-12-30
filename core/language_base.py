# core/language_base.py

"""
言語解析のための基底クラスモジュール
すべての言語固有の解析クラスはこのクラスを継承する
"""

import os
import re
from abc import ABC, abstractmethod


class LanguageAnalyzerBase(ABC):
    """多言語対応のための基底クラス"""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """状態をリセット"""
        self.files = []
        self.components = {}
        self.connections = []
    
    @abstractmethod
    def get_file_extensions(self):
        """対応するファイル拡張子のリストを返す"""
        pass
    
    def can_analyze(self, file_path):
        """このファイルを解析できるか判定"""
        ext = os.path.splitext(file_path)[1].lower()
        return ext in self.get_file_extensions()
    
    @abstractmethod
    def analyze_file(self, file_path):
        """ファイルを解析"""
        pass
    
    def analyze_files(self, file_paths):
        """複数ファイルを解析"""
        for file_path in file_paths:
            if self.can_analyze(file_path):
                self.analyze_file(file_path)
        return self.generate_report()
    
    @abstractmethod
    def find_connections(self, other_analyzer):
        """他の言語解析器との連携ポイントを検出"""
        pass
    
    @abstractmethod
    def generate_report(self):
        """解析結果レポートを生成"""
        pass
    
    @abstractmethod
    def generate_mermaid(self):
        """マーメード図を生成"""
        pass
    
    def get_language_name(self):
        """言語名を返す（サブクラスでオーバーライド可能）"""
        return "Unknown"
    
    def extract_components(self, content):
        """コンテンツからコンポーネントを抽出するヘルパーメソッド"""
        # 言語固有の実装でオーバーライドする
        pass