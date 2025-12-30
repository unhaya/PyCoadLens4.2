# utils/i18n.py

import json
import os
from typing import Dict, Any

class I18nManager:
    """多言語対応を管理するクラス"""
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.translations = {}
        self.current_language = self.config_manager.get_language() or "ja"
        self.load_translations()
    
    def load_translations(self):
        """翻訳リソースファイルを読み込む"""
        languages = ["ja", "en"]  # 対応言語リスト
        base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "locales")
        
        for lang in languages:
            lang_file = os.path.join(base_path, f"{lang}.json")
            if os.path.exists(lang_file):
                try:
                    with open(lang_file, "r", encoding="utf-8") as f:
                        self.translations[lang] = json.load(f)
                except Exception as e:
                    print(f"Failed to load language file {lang_file}: {e}")
                    self.translations[lang] = {}
            else:
                self.translations[lang] = {}
    
    def set_language(self, language_code):
        """言語を設定する"""
        if language_code in self.translations:
            self.current_language = language_code
            self.config_manager.set_language(language_code)
            return True
        return False
    
    def get_current_language(self):
        """現在の言語コードを取得"""
        return self.current_language
    
    def translate(self, key, default=None):
        """キーに基づいてテキストを翻訳"""
        if default is None:
            default = key
            
        if self.current_language not in self.translations:
            return default
            
        # ネストされたキーに対応（例: "menu.file.open"）
        parts = key.split(".")
        current = self.translations[self.current_language]
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
                
        return current if isinstance(current, str) else default
    
    def get_available_languages(self):
        """利用可能な言語リストを取得"""
        return list(self.translations.keys())

# グローバルなインスタンス（遅延初期化用）
_i18n_manager = None

def init_i18n(config_manager):
    """I18nManagerを初期化"""
    global _i18n_manager
    _i18n_manager = I18nManager(config_manager)
    return _i18n_manager

def get_i18n():
    """I18nManagerのインスタンスを取得"""
    return _i18n_manager

# 翻訳のためのショートカット関数
def _(key, default=None):
    """翻訳関数のショートカット"""
    if _i18n_manager:
        return _i18n_manager.translate(key, default)
    return default or key