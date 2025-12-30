# ui/syntax_highlighter.py
import re
import tkinter as tk

class SyntaxHighlighter:
    """
    Pythonコードに構文ハイライトを適用するクラス
    """
    def __init__(self, text_widget):
        self.text_widget = text_widget
        
        # 構文ハイライトの色定義
        self.colors = {
            'keywords': '#FF7700',  # オレンジ
            'builtins': '#0086B3',  # 水色
            'strings': '#008800',   # 緑
            'comments': '#888888',  # グレー
            'functions': '#0000FF', # 青
            'classes': '#990000',   # 赤
            'docstrings': '#067D17', # 深緑
        }
        
        # キーワードと組み込み関数の定義
        self.keywords = ['and', 'as', 'assert', 'break', 'class', 'continue', 'def', 
                   'del', 'elif', 'else', 'except', 'False', 'finally', 'for', 
                   'from', 'global', 'if', 'import', 'in', 'is', 'lambda', 'None', 
                   'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'True', 
                   'try', 'while', 'with', 'yield']
        
        self.builtins = ['abs', 'all', 'any', 'ascii', 'bin', 'bool', 'bytearray', 
                   'bytes', 'callable', 'chr', 'classmethod', 'compile', 'complex', 
                   'delattr', 'dict', 'dir', 'divmod', 'enumerate', 'eval', 'exec', 
                   'filter', 'float', 'format', 'frozenset', 'getattr', 'globals', 
                   'hasattr', 'hash', 'help', 'hex', 'id', 'input', 'int', 'isinstance', 
                   'issubclass', 'iter', 'len', 'list', 'locals', 'map', 'max', 'memoryview', 
                   'min', 'next', 'object', 'oct', 'open', 'ord', 'pow', 'print', 'property', 
                   'range', 'repr', 'reversed', 'round', 'set', 'setattr', 'slice', 'sorted', 
                   'staticmethod', 'str', 'sum', 'super', 'tuple', 'type', 'vars', 'zip']
        
        # テキストウィジェットのタグを設定
        for tag, color in self.colors.items():
            self.text_widget.tag_configure(tag, foreground=color)
    
    def highlight(self, event=None):
        """テキストにシンタックスハイライトを適用"""
        # 現在のテキストをすべて取得
        content = self.text_widget.get("1.0", "end-1c")
        
        # すべてのタグをクリア
        for tag in self.colors.keys():
            self.text_widget.tag_remove(tag, "1.0", "end")
        
        # 構文ハイライトを適用
        self._apply_highlights(content)
    
    def _apply_highlights(self, content):
        """ハイライトを適用する内部メソッド"""
        # コメント（#から行末まで）
        for match in re.finditer(r'#.*$', content, re.MULTILINE):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            self.text_widget.tag_add('comments', start, end)
        
        # 文字列（三重引用符）
        for match in re.finditer(r'""".*?"""|\'\'\'.*?\'\'\'', content, re.DOTALL):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            self.text_widget.tag_add('docstrings', start, end)
        
        # 文字列（単一または二重引用符）
        for match in re.finditer(r'"[^"\\]*(?:\\.[^"\\]*)*"|\'[^\'\\]*(?:\\.[^\'\\]*)*\'', content):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            self.text_widget.tag_add('strings', start, end)
        
        # クラス定義とdef
        for match in re.finditer(r'\b(class|def)\s+(\w+)', content):
            keyword_start = f"1.0+{match.start(1)}c"
            keyword_end = f"1.0+{match.end(1)}c"
            self.text_widget.tag_add('keywords', keyword_start, keyword_end)
            
            if match.group(1) == 'class':
                name_start = f"1.0+{match.start(2)}c"
                name_end = f"1.0+{match.end(2)}c"
                self.text_widget.tag_add('classes', name_start, name_end)
            else:
                name_start = f"1.0+{match.start(2)}c"
                name_end = f"1.0+{match.end(2)}c"
                self.text_widget.tag_add('functions', name_start, name_end)
        
        # キーワード
        for keyword in self.keywords:
            for match in re.finditer(r'\b' + keyword + r'\b', content):
                start = f"1.0+{match.start()}c"
                end = f"1.0+{match.end()}c"
                self.text_widget.tag_add('keywords', start, end)
        
        # 組み込み関数
        for builtin in self.builtins:
            for match in re.finditer(r'\b' + builtin + r'\b', content):
                start = f"1.0+{match.start()}c"
                end = f"1.0+{match.end()}c"
                self.text_widget.tag_add('builtins', start, end)