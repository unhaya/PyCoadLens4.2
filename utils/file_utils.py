# utils/file_utils.py
import os
import subprocess
import sys
import tempfile
import time
import traceback

def open_in_explorer(file_path):
    """ファイルまたはディレクトリをエクスプローラーで開く"""
    # ディレクトリでない場合は親ディレクトリを取得
    if not os.path.isdir(file_path):
        file_path = os.path.dirname(file_path)
    
    # OSに応じてファイルマネージャーを開く
    if sys.platform == 'darwin':  # macOS
        subprocess.Popen(['open', file_path])
    elif sys.platform == 'win32':  # Windows
        subprocess.Popen(['explorer', file_path])
    else:  # Linux
        try:
            subprocess.Popen(['xdg-open', file_path])
        except Exception:
            # 失敗した場合は一般的なファイラーを試す
            try:
                subprocess.Popen(['nautilus', file_path])
            except Exception:
                try:
                    subprocess.Popen(['thunar', file_path])
                except Exception:
                    return False
    return True

def open_with_default_app(file_path):
    """ファイルをデフォルトのアプリケーションで開く"""
    if not os.path.isfile(file_path):
        return False
    
    # OSに応じてデフォルトアプリでファイルを開く
    try:
        if sys.platform == 'darwin':  # macOS
            subprocess.Popen(['open', file_path])
        elif sys.platform == 'win32':  # Windows
            os.startfile(file_path)
        else:  # Linux
            subprocess.Popen(['xdg-open', file_path])
        return True
    except Exception:
        return False

def create_temp_error_log():
    """一時的なエラーログファイルを作成する"""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".log")
    return temp_file.name

def run_python_file(python_path, file_path, error_log_path):
    """Pythonファイルを実行する"""
    try:
        if sys.platform == 'win32':  # Windows
            # 新しいコンソールウィンドウで実行し、エラーをファイルにリダイレクト
            cmd = f'start cmd /c "{python_path} "{file_path}" 2> "{error_log_path}" & pause"'
            subprocess.Popen(cmd, shell=True)
            return True
        elif sys.platform == 'darwin':  # macOS
            # Terminal.appを開いて実行し、エラーをファイルにリダイレクト
            apple_script = f'''
            tell application "Terminal"
                do script "{python_path} \\"{file_path}\\" 2> \\"{error_log_path}\\"; echo \\"\nPress enter to close...\\"; read"
                activate
            end tell
            '''
            subprocess.Popen(['osascript', '-e', apple_script])
            return True
        else:  # Linux
            # ターミナルを開いて実行
            cmd = f'{python_path} "{file_path}" 2> "{error_log_path}"; echo "Press enter to close..."; read'
            try:
                subprocess.Popen(['x-terminal-emulator', '-e', cmd])
                return True
            except Exception:
                try:
                    subprocess.Popen(['gnome-terminal', '--', 'bash', '-c', cmd])
                    return True
                except Exception:
                    try:
                        subprocess.Popen(['xterm', '-e', cmd])
                        return True
                    except Exception:
                        return False
    except Exception:
        return False

def try_delete_file(file_path, retry_count=3, retry_delay=0.5):
    """ファイルを安全に削除する（リトライ機能付き）"""
    for i in range(retry_count):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
        except Exception:
            if i < retry_count - 1:
                time.sleep(retry_delay)
    return False