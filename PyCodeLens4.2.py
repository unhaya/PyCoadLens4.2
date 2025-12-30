"""
code_analysis/
├── core/            # 核となる分析機能
│   ├── analyzer.py  # コード解析の基本機能
│   ├── astroid_analyzer.py
│   └── dependency.py
├── llm/             # LLM最適化関連機能
│   ├── optimizer.py
│   ├── tokenizer.py
│   └── importance.py
├── ui/              # UI関連コンポーネント
│   ├── main_window.py
│   ├── tree_view.py
│   ├── prompt_manager_ui.py
│   └── syntax_highlighter.py
├── utils/           # ユーティリティ機能
│   ├── config.py
│   ├── json_converter.py
│   └── file_utils.py
└── main.py          # エントリーポイント

"""

# main.py (プロジェクトのルート)
import sys
import os
import tkinter as tk
import traceback
from tkinter import messagebox
try:
    from ttkthemes import ThemedTk
except ImportError:
    ThemedTk = None
    
# プロジェクトのルートディレクトリをパスに追加
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)
print(f"Python検索パス: {project_root} をパスに追加しました")

from ui.main_window import MainWindow
from utils.config import ConfigManager

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


# グローバルな例外ハンドラ
def global_exception_handler(exc_type, exc_value, exc_traceback):
    # フォーマットされたトレースバックを取得
    error_text = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    
    try:
        # エラーメッセージをダイアログで表示
        from ui.error_display import ErrorDisplayWindow
        ErrorDisplayWindow(error_text, f"{os.path.basename(sys.argv[0])}の実行エラー")
    except Exception:
        # GUIが機能しない場合のフォールバック
        print(error_text, file=sys.stderr)
        # 一時ファイルにエラーを書き込む
        try:
            import tempfile
            fd, temp_path = tempfile.mkstemp(suffix='.txt', prefix='python_error_')
            with os.fdopen(fd, 'w') as f:
                f.write(error_text)
            print(f"エラーログが保存されました: {temp_path}", file=sys.stderr)
        except Exception:
            pass
    
    # 例外を再度発生させずに終了
    sys.exit(1)

def main():
    try:
        # グローバル例外ハンドラを設定
        sys.excepthook = global_exception_handler
        
        # アプリケーションウィンドウの作成
        if ThemedTk:
            # ThemedTkを使用して洗練されたテーマを適用
            root = ThemedTk(theme="arc")  # 'arc'テーマを使用
        else:
            # ThemedTkが利用できない場合は通常のTkを使用
            root = tk.Tk()
            
            messagebox.showinfo("情報", 
                               "ttkthemesライブラリがインストールされていないため、デフォルトテーマを使用します。\n"
                               "pip install ttkthemes でインストールすると、より洗練されたUIになります。")
        
        # 依存ライブラリのチェック
        missing_libs = []
        
        # astroidライブラリのチェック
        try:
            import astroid
            print(f"astroidライブラリが利用可能です: バージョン {astroid.__version__}")
        except ImportError:
            missing_libs.append("astroid")
            print("astroidライブラリがインストールされていません。拡張解析機能は無効になります。")
        
        # PILライブラリのチェック（ファイル先頭でチェック済み）
        if PIL_AVAILABLE:
            print("PILライブラリ (Pillow) が利用可能です")
        else:
            missing_libs.append("Pillow")
            print("PILライブラリ (Pillow) がインストールされていません。テキストアイコンを使用します。")
        
        # 依存ライブラリのインストール案内
        if missing_libs:
            
            message = "以下のライブラリがインストールされていないため、一部の機能が制限されます：\n\n"
            
            if "astroid" in missing_libs:
                message += "- astroid: LLM向けの拡張解析機能（型推論、継承関係、依存関係）\n"
                message += "  インストール方法: pip install astroid\n\n"
            
            if "Pillow" in missing_libs:
                message += "- Pillow: カラーアイコン表示機能\n"
                message += "  インストール方法: pip install Pillow\n\n"
            
            message += "これらのライブラリをインストールすると、より高度な機能が利用できます。\n"
            message += "アプリは制限された機能で動作を続けます。"
            
            messagebox.showinfo("ライブラリの依存関係", message)
        
        # ウィンドウアイコンの設定
        try:
            # アイコンを探す複数の候補パスを設定
            icon_paths = []
            
            # 1. 実行ファイルと同じディレクトリのiconフォルダ
            exe_dir = os.path.dirname(os.path.abspath(__file__))
            icon_paths.append(os.path.join(exe_dir, "icon"))
            
            # 2. カレントディレクトリのiconフォルダ
            icon_paths.append(os.path.join(os.getcwd(), "icon"))
            
            # 3. PyInstallerでexe化された場合のパス
            try:
                if getattr(sys, 'frozen', False):
                    # PyInstaller環境
                    exe_path = sys._MEIPASS
                    icon_paths.append(os.path.join(exe_path, "icon"))
            except (AttributeError, ImportError):
                pass
            
            # 4. 親ディレクトリのiconフォルダ
            icon_paths.append(os.path.join(os.path.dirname(exe_dir), "icon"))
            
            # 5. 以前指定されていたパス（後方互換性のため）
            icon_paths.append(r"D:\OneDrive\In the middle of an update\code_analysis\icon")
            
            # アイコンファイル名のバリエーション
            icon_filenames = ["icons8-検査コード-48.png", "app_icon.png", "code_analyzer.png", "app.png", "icon.png"]
            
            # アイコンファイルを探す
            icon_path = None
            for dir_path in icon_paths:
                if not os.path.exists(dir_path):
                    continue
                    
                for fname in icon_filenames:
                    path = os.path.join(dir_path, fname)
                    if os.path.exists(path):
                        icon_path = path
                        break
                
                if icon_path:
                    break
            
            # アイコンパスの存在確認
            if icon_path and os.path.exists(icon_path):
                # PILが利用可能な場合
                if PIL_AVAILABLE:
                    with Image.open(icon_path) as icon_image:
                        icon_photo = ImageTk.PhotoImage(icon_image)
                        root.iconphoto(True, icon_photo)
                    print(f"アイコンを設定しました: {icon_path}")
                else:
                    # PILがない場合はiconbitmapを試す（.icoファイル用）
                    if icon_path.lower().endswith('.ico'):
                        root.iconbitmap(icon_path)
                        print(f"ICOアイコンを設定しました: {icon_path}")
                    else:
                        print("PILライブラリがないため、PNGアイコンを設定できません。")
            else:
                print("アプリケーションアイコンが見つかりませんでした。")
        except Exception as e:
            print(f"アイコン設定エラー: {e}")
        
        # 設定マネージャーを初期化
        config_manager = ConfigManager()
        
        # メインウィンドウを作成
        app = MainWindow(root)
        
        # メインループを開始
        root.mainloop()
    
    except Exception as e:
        # 予期しない例外が発生した場合
        error_message = f"アプリケーション起動中に予期しないエラーが発生しました:\n{str(e)}\n\n{traceback.format_exc()}"
        print(error_message)
        try:
            messagebox.showerror("エラー", error_message)
        except Exception:
            pass
        sys.exit(1)

if __name__ == "__main__":
    main()






















# # main.py (プロジェクトのルート)
# import sys
# import os
# import tkinter as tk
# import traceback

# try:
    # from ttkthemes import ThemedTk
# except ImportError:
    # ThemedTk = None

# from ui.main_window import MainWindow
# from utils.config import ConfigManager

# # グローバルな例外ハンドラ
# def global_exception_handler(exc_type, exc_value, exc_traceback):
    # # フォーマットされたトレースバックを取得
    # error_text = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    
    # try:
        # # エラーメッセージをダイアログで表示
        # from ui.error_display import ErrorDisplayWindow
        # ErrorDisplayWindow(error_text, f"{os.path.basename(sys.argv[0])}の実行エラー")
    # except:
        # # GUIが機能しない場合のフォールバック
        # print(error_text, file=sys.stderr)
        # # 一時ファイルにエラーを書き込む
        # try:
            # import tempfile
            # fd, temp_path = tempfile.mkstemp(suffix='.txt', prefix='python_error_')
            # with os.fdopen(fd, 'w') as f:
                # f.write(error_text)
            # print(f"エラーログが保存されました: {temp_path}", file=sys.stderr)
        # except:
            # pass
    
    # # 例外を再度発生させずに終了
    # sys.exit(1)

# def main():
    # try:
        # # グローバル例外ハンドラを設定
        # sys.excepthook = global_exception_handler
        
        # # アプリケーションウィンドウの作成
        # if ThemedTk:
            # # ThemedTkを使用して洗練されたテーマを適用
            # root = ThemedTk(theme="arc")  # 'arc'テーマを使用
        # else:
            # # ThemedTkが利用できない場合は通常のTkを使用
            # root = tk.Tk()
            # 
            # messagebox.showinfo("情報", 
                               # "ttkthemesライブラリがインストールされていないため、デフォルトテーマを使用します。\n"
                               # "pip install ttkthemes でインストールすると、より洗練されたUIになります。")
        
        # # 依存ライブラリのチェック
        # missing_libs = []
        
        # # astroidライブラリのチェック
        # try:
            # import astroid
            # print(f"astroidライブラリが利用可能です: バージョン {astroid.__version__}")
        # except ImportError:
            # missing_libs.append("astroid")
            # print("astroidライブラリがインストールされていません。拡張解析機能は無効になります。")
        
        # # PILライブラリのチェック
        # try:
            # from PIL import Image, ImageTk
        # except ImportError:
            # missing_libs.append("Pillow")
            # print("PILライブラリ (Pillow) がインストールされていません。テキストアイコンを使用します。")
        
        # # 依存ライブラリのインストール案内
        # if missing_libs:
            # message = "以下のライブラリがインストールされていないため、一
