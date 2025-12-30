# llm/tokenizer.py
import re

class TokenCounter:
    """
    トークン数を推定するためのユーティリティクラス
    大規模言語モデルのトークン数を簡易的に推定する
    """
    def __init__(self):
        # 英語の平均的なトークンサイズ（1トークンあたり約4文字）
        self.avg_chars_per_token = 4
        
        # 日本語のトークン化は異なるため、日本語テキスト検出用
        self.japanese_pattern = re.compile(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]')
    
    def count_tokens(self, text):
        """テキストのトークン数を簡易的に推定する"""
        if not text:
            return 0
        
        # 日本語文字を含むかチェック
        has_japanese = bool(self.japanese_pattern.search(text))
        
        if has_japanese:
            # 日本語テキストの場合、1トークンあたり約1.5文字と仮定
            return len(text) / 1.5
        else:
            # 英語テキストの場合
            return len(text) / self.avg_chars_per_token
    
    def estimate_tokens_for_code(self, code_text):
        """コードのトークン数を推定する（コードは通常より多くのトークンを使用）"""
        # コードはより多くのトークンを使用する傾向があるため、係数を調整
        return len(code_text) / 3.5
    
    def estimate_tokens_for_structured_data(self, json_str):
        """構造化データ（JSON）のトークン数を推定する"""
        # JSON形式の文字列はよりトークン化効率が良いため、係数を調整
        return len(json_str) / 4.5

class TokenBudgetOptimizer:
    """
    トークン予算に基づいてテキストを最適化するクラス
    """
    def __init__(self, max_tokens=4000):
        self.max_tokens = max_tokens
        self.token_counter = TokenCounter()
    
    def optimize_text(self, text, priority_sections=None):
        """
        テキストをトークン予算内に収まるように最適化する
        priority_sections: 優先的に残すべきセクションのリスト（正規表現パターン）
        """
        estimated_tokens = self.token_counter.count_tokens(text)
        
        if estimated_tokens <= self.max_tokens:
            return text  # すでに予算内に収まっている
        
        # セクションごとに分割（# で始まる見出しを基準）
        sections = re.split(r'(^#+ .+$)', text, flags=re.MULTILINE)
        
        # 見出しと内容を組み合わせる
        paired_sections = []
        i = 0
        while i < len(sections):
            if i+1 < len(sections) and sections[i].startswith('#'):
                # 見出しとその内容を組み合わせる
                paired_sections.append((sections[i], sections[i+1]))
                i += 2
            else:
                # 見出しがない場合は内容だけを追加
                paired_sections.append(("", sections[i]))
                i += 1
        
        # 優先セクションと非優先セクションを分離
        priority_content = []
        normal_content = []
        
        for heading, content in paired_sections:
            is_priority = False
            
            if priority_sections:
                for pattern in priority_sections:
                    if re.search(pattern, heading, re.IGNORECASE):
                        is_priority = True
                        break
            
            if is_priority:
                priority_content.append((heading, content))
            else:
                normal_content.append((heading, content))
        
        # 優先コンテンツを追加
        result = []
        tokens_used = 0
        
        for heading, content in priority_content:
            section = heading + content
            section_tokens = self.token_counter.count_tokens(section)
            
            if tokens_used + section_tokens <= self.max_tokens:
                result.append(section)
                tokens_used += section_tokens
            else:
                # 優先セクションでも長すぎる場合は一部を切り詰める
                reduced_content = self._truncate_content(content, self.max_tokens - tokens_used - self.token_counter.count_tokens(heading))
                result.append(heading + reduced_content)
                tokens_used += self.token_counter.count_tokens(heading + reduced_content)
                break  # これ以上追加できない
        
        # 優先コンテンツを追加した後も余裕がある場合は、通常コンテンツも追加
        if tokens_used < self.max_tokens:
            for heading, content in normal_content:
                section = heading + content
                section_tokens = self.token_counter.count_tokens(section)
                
                if tokens_used + section_tokens <= self.max_tokens:
                    result.append(section)
                    tokens_used += section_tokens
                else:
                    # 一部だけ追加
                    available_tokens = self.max_tokens - tokens_used
                    if available_tokens > self.token_counter.count_tokens(heading) + 50:  # 最低50トークン分の内容を追加する価値があるか
                        reduced_content = self._truncate_content(content, available_tokens - self.token_counter.count_tokens(heading))
                        result.append(heading + reduced_content)
                    break
        
        return "".join(result)
    
    def _truncate_content(self, content, max_tokens):
        """コンテンツを指定されたトークン数に収まるように切り詰める"""
        if self.token_counter.count_tokens(content) <= max_tokens:
            return content
        
        # 行ごとに分割
        lines = content.split('\n')
        result = []
        tokens = 0
        
        for line in lines:
            line_tokens = self.token_counter.count_tokens(line + '\n')
            if tokens + line_tokens <= max_tokens:
                result.append(line)
                tokens += line_tokens
            else:
                # 1行でも長すぎる場合は文字単位で切り詰める
                if not result:
                    chars_to_keep = int(max_tokens * self.token_counter.avg_chars_per_token)
                    return line[:chars_to_keep] + "...\n(トークン制限により切り詰められました)"
                break
        
        if result:
            return '\n'.join(result) + "\n...\n(トークン制限により切り詰められました)"
        else:
            return "(トークン制限により内容が省略されました)"