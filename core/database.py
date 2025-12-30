# core/database.py
import os
import sqlite3
import time
from datetime import datetime
import traceback

class CodeDatabase:
    """コードスニペット管理用データベース"""
    
    def __init__(self, db_path="code_snippets.db"):
        self.db_path = db_path
        self.connection = None
        self.init_database()
    
    def init_database(self):
        """データベース初期化"""
        try:
            self.connection = sqlite3.connect(self.db_path)
            cursor = self.connection.cursor()
            
            # コードスニペットテーブル
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS code_snippets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                dir_path TEXT,
                name TEXT NOT NULL,
                type TEXT CHECK(type IN ('class', 'function', 'import')) NOT NULL,
                description TEXT,
                code TEXT NOT NULL,
                line_start INTEGER,
                line_end INTEGER,
                char_count INTEGER,
                tags TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # インデックスを追加
            cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_code_snippets_file_path 
            ON code_snippets(file_path)
            ''')
            
            cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_code_snippets_name 
            ON code_snippets(name)
            ''')
            
            cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_code_snippets_type 
            ON code_snippets(type)
            ''')
            
            # ファイル管理テーブル
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS code_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE,
                last_parsed_time TIMESTAMP
            )
            ''')
            
            self.connection.commit()
            print("データベース初期化完了")
        except Exception as e:
            print(f"データベース初期化エラー: {str(e)}")
            traceback.print_exc()
    
    def add_code_snippet(self, file_path, dir_path, name, type_name, 
                         code, line_start, line_end, char_count, 
                         description=None, tags=None):
        """コードスニペットをデータベースに追加"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
            INSERT INTO code_snippets (
                file_path, dir_path, name, type, description, 
                code, line_start, line_end, char_count, tags
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (file_path, dir_path, name, type_name, description, 
                  code, line_start, line_end, char_count, tags))
            self.connection.commit()
            return True
        except Exception as e:
            print(f"スニペット追加エラー: {str(e)} - ファイル: {file_path}, 名前: {name}")
            traceback.print_exc()
            return False
    
    def add_code_snippet_without_commit(self, file_path, dir_path, name, type_name, 
                                        code, line_start, line_end, char_count, 
                                        description=None, tags=None):
        """トランザクション内で使用するためのコードスニペット追加（コミットなし）"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
            INSERT INTO code_snippets (
                file_path, dir_path, name, type, description, 
                code, line_start, line_end, char_count, tags
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (file_path, dir_path, name, type_name, description, 
                  code, line_start, line_end, char_count, tags))
            # コミットしない
            return True
        except Exception as e:
            print(f"スニペット追加エラー (コミットなし): {str(e)}")
            traceback.print_exc()
            return False
            
    def clear_file_snippets_without_commit(self, file_path):
        """トランザクション内で使用するためのスニペット削除（コミットなし）"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('DELETE FROM code_snippets WHERE file_path = ?', (file_path,))
            # コミットしない
            return True
        except Exception as e:
            print(f"スニペット削除エラー (コミットなし): {str(e)}")
            traceback.print_exc()
            return False
    
    def update_file_timestamp(self, file_path):
        """ファイルの解析タイムスタンプを更新"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
            INSERT OR REPLACE INTO code_files (file_path, last_parsed_time)
            VALUES (?, ?)
            ''', (file_path, datetime.now().timestamp()))
            self.connection.commit()
            return True
        except Exception as e:
            print(f"タイムスタンプ更新エラー: {str(e)}")
            traceback.print_exc()
            return False
    
    def needs_update(self, file_path):
        """ファイルの更新が必要かどうかを判断"""
        if not os.path.exists(file_path):
            return False
            
        try:
            cursor = self.connection.cursor()
            cursor.execute('SELECT last_parsed_time FROM code_files WHERE file_path = ?', 
                          (file_path,))
            result = cursor.fetchone()
            
            if not result:
                return True  # まだ解析されていない
                
            last_parsed = result[0]
            last_modified = os.path.getmtime(file_path)
            
            return last_modified > last_parsed
        except Exception as e:
            print(f"更新チェックエラー: {str(e)}")
            traceback.print_exc()
            return True  # エラーの場合は再解析を推奨
    
    def get_snippets_by_file(self, file_path):
        """ファイルに関連するすべてのスニペットを取得"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
            SELECT id, name, type, code, line_start, line_end, char_count, description
            FROM code_snippets
            WHERE file_path = ?
            ORDER BY line_start
            ''', (file_path,))
            return cursor.fetchall()
        except Exception as e:
            print(f"スニペット取得エラー: {str(e)}")
            traceback.print_exc()
            return []
    
    def clear_file_snippets(self, file_path):
        """ファイルに関連するスニペットをすべて削除"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('DELETE FROM code_snippets WHERE file_path = ?', (file_path,))
            self.connection.commit()
            return True
        except Exception as e:
            print(f"スニペット削除エラー: {str(e)}")
            traceback.print_exc()
            return False
    
    def close(self):
        """データベース接続を閉じる"""
        if self.connection:
            try:
                self.connection.close()
                return True
            except Exception as e:
                print(f"データベース接続クローズエラー: {str(e)}")
                traceback.print_exc()
                return False
            
    def begin_transaction(self):
        """トランザクションを開始する"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("BEGIN TRANSACTION")
            return True
        except Exception as e:
            print(f"トランザクション開始エラー: {str(e)}")
            traceback.print_exc()
            return False

    def commit_transaction(self):
        """トランザクションをコミットする"""
        try:
            self.connection.commit()
            return True
        except Exception as e:
            print(f"トランザクションコミットエラー: {str(e)}")
            traceback.print_exc()
            return False

    def rollback_transaction(self):
        """トランザクションをロールバックする"""
        try:
            self.connection.rollback()
            return True
        except Exception as e:
            print(f"トランザクションロールバックエラー: {str(e)}")
            traceback.print_exc()
            return False
    
    def update_file_timestamp_without_commit(self, file_path):
        """ファイルの解析タイムスタンプを更新（コミットなし）"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
            INSERT OR REPLACE INTO code_files (file_path, last_parsed_time)
            VALUES (?, ?)
            ''', (file_path, datetime.now().timestamp()))
            # コミットしない
            return True
        except Exception as e:
            print(f"タイムスタンプ更新エラー (コミットなし): {str(e)}")
            traceback.print_exc()
            return False
            
    def get_code_by_name(self, file_path, name, exact_match=True):
        """名前でコードスニペットを検索"""
        try:
            cursor = self.connection.cursor()
            
            # 名前から不要な文字を削除して正規化
            cleaned_name = name.strip()
            if cleaned_name.startswith("def "):
                cleaned_name = cleaned_name[4:].split("(")[0].strip()
            elif cleaned_name.startswith("class "):
                cleaned_name = cleaned_name[6:].split("(")[0].strip()
            
            if exact_match:
                # 完全一致検索 + クラス内メソッド検索
                cursor.execute('''
                SELECT name, code, description, type FROM code_snippets 
                WHERE file_path = ? AND (name = ? OR name LIKE ? OR name LIKE ?)
                ''', (file_path, cleaned_name, f"%.{cleaned_name}", f"%.{cleaned_name}(%"))
            else:
                # より柔軟な部分一致検索
                cursor.execute('''
                SELECT name, code, description, type FROM code_snippets 
                WHERE file_path = ? AND 
                (name = ? OR name LIKE ? OR name LIKE ? OR name LIKE ? OR name LIKE ? OR name LIKE ?)
                ORDER BY 
                    CASE 
                        WHEN name = ? THEN 0
                        WHEN name LIKE ? THEN 1
                        WHEN name LIKE ? THEN 2
                        ELSE 3
                    END,
                    length(name)
                ''', (file_path, cleaned_name, 
                     f"{cleaned_name}.%", f"%.{cleaned_name}", f"%.{cleaned_name}.%",
                     f"%.{cleaned_name}(%", f"%def {cleaned_name}(%",
                     cleaned_name, f"{cleaned_name}.%", f"%.{cleaned_name}"))
            
            results = cursor.fetchall()
            if not results:
                # デバッグ用：検索条件を詳細に表示
                print(f"検索失敗: ファイル={file_path}, 名前={cleaned_name}, 元の名前={name}")
            return results
        except Exception as e:
            print(f"名前検索エラー: {str(e)}")
            traceback.print_exc()
            return []

    def get_stats(self):
        """データベース統計情報を取得"""
        try:
            cursor = self.connection.cursor()
            
            # スニペット数
            cursor.execute('SELECT COUNT(*) FROM code_snippets')
            snippet_count = cursor.fetchone()[0]
            
            # ファイル数
            cursor.execute('SELECT COUNT(*) FROM code_files')
            file_count = cursor.fetchone()[0]
            
            # タイプ別分布
            cursor.execute('''
            SELECT type, COUNT(*) FROM code_snippets 
            GROUP BY type ORDER BY COUNT(*) DESC
            ''')
            type_stats = cursor.fetchall()
            
            return {
                "snippet_count": snippet_count,
                "file_count": file_count,
                "type_distribution": type_stats
            }
        except Exception as e:
            print(f"統計情報取得エラー: {str(e)}")
            traceback.print_exc()
            return {"snippet_count": 0, "file_count": 0, "type_distribution": []}