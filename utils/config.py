# utils/config.py

import json
import os
import sys
import traceback

class ConfigManager:
    """
    アプリケーションの設定を管理するクラス
    JSONファイルに設定を保存・読み込みする
    """

    def __init__(self, config_file=None):
        # 実行ファイル(main.py)のあるディレクトリを基準にする
        base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))

        if config_file is None:
            # config ディレクトリのパスを構築
            config_dir = os.path.join(base_dir, "config")
            self.config_file = os.path.join(config_dir, "code_analyzer_config.json")
        else:
            self.config_file = config_file
            config_dir = os.path.dirname(self.config_file)

        # configディレクトリの作成を保証
        self.ensure_dir(config_dir)

        # デフォルト設定
        self.config = {
            "last_directory": "",
            "last_file": "",
            "window_size": {"width": 1280, "height": 1080},
            "excluded_items": {}  # {"directory_path": {"item_path": True/False}}
        }

        # 設定ファイルの読み込みまたは保存
        self.load_config()

    def ensure_dir(self, path):
        """ディレクトリが存在しない場合は作成する"""
        if path and not os.path.exists(path):
            try:
                os.makedirs(path, exist_ok=True)
                print(f"ディレクトリ作成: {path}")
            except Exception as e:
                print(f"[エラー] ディレクトリ作成失敗: {path}\n{e}")
                raise

    def load_config(self):
        """設定ファイルから設定を読み込む"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    self.config.update(loaded_config)
                print(f"設定読み込み成功: {self.config_file}")
            else:
                print("設定ファイルが見つかりません。新しく作成します。")
                self.save_config()
        except Exception as e:
            print(f"[エラー] 設定読み込み中に問題が発生しました: {e}")
            traceback.print_exc()

    def save_config(self):
        """設定をファイルに保存する"""
        try:
            config_dir = os.path.dirname(self.config_file)
            self.ensure_dir(config_dir)

            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            print(f"設定保存完了: {self.config_file}")

            if not os.path.exists(self.config_file):
                print(f"[エラー] 設定ファイルが作成されませんでした: {self.config_file}")
        except Exception as e:
            print(f"[エラー] 設定保存に失敗しました: {e}")
            traceback.print_exc()

    # 以下、設定項目操作メソッドはそのまま保持

    def get_last_directory(self):
        return self.config.get("last_directory", "")

    def set_last_directory(self, directory):
        self.config["last_directory"] = directory
        self.save_config()

    def get_last_file(self):
        return self.config.get("last_file", "")

    def set_last_file(self, file_path):
        self.config["last_file"] = file_path
        self.save_config()

    def get_window_size(self):
        return self.config.get("window_size", {"width": 1000, "height": 775})

    def set_window_size(self, width, height):
        self.config["window_size"] = {"width": width, "height": height}
        self.save_config()

    def get_excluded_items(self, directory):
        directory = os.path.normpath(directory)
        excluded_items = self.config.get("excluded_items", {})
        return excluded_items.get(directory, {})

    def set_excluded_item(self, directory, item_path, is_excluded):
        directory = os.path.normpath(directory)
        item_path = os.path.normpath(item_path)

        if "excluded_items" not in self.config:
            self.config["excluded_items"] = {}

        if directory not in self.config["excluded_items"]:
            self.config["excluded_items"][directory] = {}

        self.config["excluded_items"][directory][item_path] = is_excluded
        self.save_config()

    def clear_excluded_items(self, directory):
        if directory in self.config.get("excluded_items", {}):
            del self.config["excluded_items"][directory]
            self.save_config()

    def get_tab_selection(self):
        return self.config.get("tab_selection", {
            "解析結果": False,
            "拡張解析": False,
            "JSON出力": False,
            "マーメード": False,
            "プロンプト入力": False
        })

    def set_tab_selection(self, tab_selection):
        self.config["tab_selection"] = tab_selection
        self.save_config()

    def get_run_file(self):
        return self.config.get("last_run_file", "")

    def set_run_file(self, file_path):
        self.config["last_run_file"] = file_path
        self.save_config()
        
    def get_language(self):
        """現在の言語設定を取得"""
        return self.config.get("language", "ja")

    def set_language(self, language_code):
        """言語設定を保存"""
        self.config["language"] = language_code
        self.save_config()
