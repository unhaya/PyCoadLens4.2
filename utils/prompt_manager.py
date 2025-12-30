# utils/prompt_manager.py
import json
import uuid
import os

class PromptManager:
    """プロンプトを管理するクラス"""
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.prompts = {}  # {id: {name: str, content: str}}
        self.load_prompts()
    
    def load_prompts(self):
        """設定ファイルからプロンプトを読み込む"""
        # configからプロンプトを取得
        prompts = self.config_manager.config.get("prompts", {})
        
        if not prompts:
            # デフォルトプロンプトを作成
            self.create_default_prompt()
        else:
            self.prompts = prompts
            print(f"{len(self.prompts)}個のプロンプトを読み込みました")
    
    def create_default_prompt(self):
        """デフォルトプロンプトを作成（最低1つは必要）"""
        default_prompts = {
            "default": {
                "name": "標準解析プロンプト",
                "content": """# [ファイル/ディレクトリ名]の解析プロンプト

以下のコード構造を分析して：
[解析結果]

## 質問/指示
[ここに質問や指示を入力してください]

## 特記事項
[特記事項があれば記入してください]
"""
            },
            "astroid": {
                "name": "拡張解析プロンプト（型・継承・依存関係）",
                "content": """# [ファイル/ディレクトリ名]の拡張解析プロンプト（astroid）

以下のコード構造と意味的関係を分析して、コードの理解と改善点を示してください。
構文構造だけでなく、型情報、継承関係、依存関係も含まれています：

[解析結果]

## 質問/指示
以下の観点からコードを分析してください：
1. クラス設計と継承関係の適切さ
2. メソッド間の依存関係と結合度
3. 型の一貫性と適切な使用
4. リファクタリングの機会
5. デザインパターンの検出と応用可能性

## コードの改善提案
[具体的な改善提案があれば記入してください]
"""
            },
            "llm_json": {
                "name": "LLM用JSON構造化データプロンプト",
                "content": """# [ファイル/ディレクトリ名]のLLM向け構造化データ解析

拡張解析レポートの最後に含まれるLLM向け構造化JSONデータを使用して、以下の質問に答えてください：

```json
[json出力]
```

## 質問/指示
提供されたJSON構造データに基づいて、以下の点を分析してください：

1. このコードベースの主要なコンポーネントとその関係
2. クラス階層の設計とその効果
3. 関数/メソッド間の依存関係から見えるアーキテクチャの特徴
4. コードの改善点や最適化の可能性
5. このコードが採用している設計パターンやアーキテクチャパターン

## 特記事項
JSON構造化データは、astroidライブラリによって抽出された型情報、継承関係、依存関係を含んでいます。
"""
            }
        }
        
        self.prompts = default_prompts
        self.save_prompts()
        print("デフォルトプロンプトを作成しました")
    
    def save_prompts(self):
        """プロンプトを設定ファイルに保存"""
        self.config_manager.config["prompts"] = self.prompts
        self.config_manager.save_config()
        print("プロンプトを保存しました")
    
    def get_prompt(self, prompt_id):
        """IDからプロンプトを取得"""
        return self.prompts.get(prompt_id, {}).get("content", "")
    
    def get_prompt_name(self, prompt_id):
        """IDからプロンプト名を取得"""
        return self.prompts.get(prompt_id, {}).get("name", "")
    
    def add_prompt(self, name, content):
        """新しいプロンプトを追加"""
        # ユニークなIDを生成
        prompt_id = f"prompt_{str(uuid.uuid4())[:8]}"
        self.prompts[prompt_id] = {
            "name": name,
            "content": content
        }
        self.save_prompts()
        return prompt_id
    
    def update_prompt(self, prompt_id, name=None, content=None):
        """プロンプトを更新"""
        if prompt_id in self.prompts:
            if name is not None:
                self.prompts[prompt_id]["name"] = name
            if content is not None:
                self.prompts[prompt_id]["content"] = content
            self.save_prompts()
            return True
        return False
    
    def delete_prompt(self, prompt_id):
        """プロンプトを削除"""
        if prompt_id in self.prompts and len(self.prompts) > 1:
            del self.prompts[prompt_id]
            self.save_prompts()
            return True
        return False
    
    def get_all_prompts(self):
        """すべてのプロンプトを取得"""
        return self.prompts