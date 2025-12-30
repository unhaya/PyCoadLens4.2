# ui/tree_view.py

import os
import sys
import traceback
import subprocess
import tkinter as tk
from tkinter import messagebox, ttk
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    # PILがない場合はテキストアイコンのみ使用
    PIL_AVAILABLE = False

from utils.i18n import _


class TooManyItemsException(Exception):
    """表示する項目数の制限に達したことを示す例外"""
    pass

class DirectoryTreeView:
    """ディレクトリとファイルをツリー表示するクラス（カラーアイコン付き）"""
    def __init__(self, parent, config_manager):
        self.parent = parent
        
        # 設定マネージャーを保存
        self.config_manager = config_manager
        
        # アイコン画像の読み込み
        self.load_icons()
        
        # ツリービューの作成
        self.tree = ttk.Treeview(parent)
        self.tree.pack(side=tk.LEFT, expand=True, fill="both")
        
        # スクロールバーの追加
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # ツリービューのカラム設定（status列を非表示に）
        self.tree["columns"] = ()
        self.tree.column("#0", width=300, minwidth=200)
        self.tree.heading("#0", text="  file/folder", anchor="w")
        
        # 除外リスト
        self.excluded_items = set()
        
        # 処理中フラグ（処理の重複実行を防止）
        self.is_processing = False
        
        # イベントバインド
        self.tree.bind("<Control-Button-1>", self.toggle_exclusion)  # Ctrl+クリック
        self.tree.bind("<Double-1>", self.on_item_double_click)  # ダブルクリック
        
        # 右クリックメニューの設定
        self.setup_context_menu()
        
        # 現在のディレクトリパス
        self.current_dir = None
        
        # ステータステキスト - カラーラベルつき（処理内部で利用するため残す）
        self.included_text = _("status_included", "✓ 含む")
        self.excluded_text = _("status_excluded", "✗ 除外")
        
        # 選択されたファイル（ダブルクリック用）
        self.selected_file = None
        
        # 選択されたディレクトリ
        self.selected_dir = None
        
        # ファイル選択コールバック
        self.on_file_selected = None
        
        # ディレクトリ選択コールバック
        self.on_dir_selected = None
        
        # 最大処理アイテム数
        self.max_items_to_process = 1000
        
        # 追加: スキップするファイル拡張子のリスト
        self.skip_extensions = ['.exe', '.dll', '.bin', '.so', '.pyc', '.pyd']
        
        # 追加: スキップするフォルダ名のリスト
        self.skip_folders = ['__pycache__', 'node_modules', 'build', 'dist', 'venv', 'env', '.git', '.idea', '.vscode']
        
        # 追加: EXEファイルが含まれるフォルダをスキップするかどうかのフラグ - デフォルトでTrue
        self.skip_exe_folders = True

    def load_icons(self):
        """アイコン画像を読み込む（複数の候補パスから検索する改良版）"""
        # デフォルトアイコンを設定（PILがない場合や画像が見つからない場合用）
        self.folder_icon = None
        self.file_icon = None
        self.locked_folder_icon = None
        self.locked_file_icon = None
        
        if not PIL_AVAILABLE:
            print("PILライブラリがインストールされていません。テキストアイコンを使用します。")
            return

        try:
            # アイコンを探す複数の候補パスを設定
            icon_paths = []
            
            # 1. 現在のファイルからの相対パス
            current_dir = os.path.dirname(os.path.abspath(__file__))
            icon_paths.append(os.path.join(current_dir, "icon"))
            
            # 2. プロジェクトルートディレクトリからの相対パス
            root_dir = os.path.dirname(os.path.dirname(current_dir))
            icon_paths.append(os.path.join(root_dir, "ui", "icon"))
            icon_paths.append(os.path.join(root_dir, "icon"))
            
            # 3. PyInstallerでexe化された場合のパス
            try:
                if getattr(sys, 'frozen', False):
                    # PyInstaller環境
                    exe_path = sys._MEIPASS
                    icon_paths.append(os.path.join(exe_path, "icon"))
                    icon_paths.append(os.path.join(exe_path, "ui", "icon"))
            except (AttributeError, ImportError):
                pass
            
            # 4. 絶対パスも一応残しておく（テスト用）
            icon_paths.append(r"D:\OneDrive\In the middle of an update\code_analysis\refactoring\ui\icon")
            
            # アイコンファイル名のバリエーション
            folder_filenames = ["tree_View_folder.png", "folder.png", "icons8-フォルダ-48.png", "folder_icon.png", "directory.png"]
            file_filenames = ["file.png", "icons8-資料-48.png", "file_icon.png", "document.png"]
            
            # アイコンを見つける
            folder_path = None
            file_path = None
            
            # 各候補パスとファイル名の組み合わせを試す
            for icon_dir in icon_paths:
                if not os.path.exists(icon_dir):
                    print(f"パスが存在しません: {icon_dir}")
                    continue
                    
                print(f"アイコン検索パス: {icon_dir}")
                
                # フォルダアイコンの検索
                for fname in folder_filenames:
                    path = os.path.join(icon_dir, fname)
                    if os.path.exists(path):
                        folder_path = path
                        print(f"フォルダアイコンを発見: {path}")
                        break
                
                # ファイルアイコンの検索
                for fname in file_filenames:
                    path = os.path.join(icon_dir, fname)
                    if os.path.exists(path):
                        file_path = path
                        print(f"ファイルアイコンを発見: {path}")
                        break
                
                # 両方見つかったら終了
                if folder_path and file_path:
                    break
            
            # アイコンが見つからない場合は早期リターン
            if not folder_path or not file_path:
                print("アイコンが見つかりませんでした。テキストアイコンを使用します。")
                return
            
            # 見つかったアイコンを読み込む
            # フォルダアイコン
            with Image.open(folder_path) as original_folder:
                resized_folder = original_folder.resize((24, 24), Image.LANCZOS)
                self.folder_icon = ImageTk.PhotoImage(resized_folder)
                # ロックされたフォルダアイコン（グレースケール）
                locked_folder = resized_folder.convert("L").convert("RGBA")
                self.locked_folder_icon = ImageTk.PhotoImage(locked_folder)

            # ファイルアイコン
            with Image.open(file_path) as original_file:
                resized_file = original_file.resize((24, 24), Image.LANCZOS)
                self.file_icon = ImageTk.PhotoImage(resized_file)
                # ロックされたファイルアイコン（グレースケール）
                locked_file = resized_file.convert("L").convert("RGBA")
                self.locked_file_icon = ImageTk.PhotoImage(locked_file)
            
            print(f"アイコンを正常に読み込みました。フォルダ: {folder_path}, ファイル: {file_path}")
        except ImportError:
            print("PILライブラリがインストールされていません。テキストアイコンを使用します。")
        except Exception as e:
            print(f"アイコンの読み込みエラー: {e}")
            # エラーが発生した場合はテキストアイコンを使用

    def set_file_selected_callback(self, callback):
        """ファイル選択時のコールバック関数を設定"""
        self.on_file_selected = callback

    def set_dir_selected_callback(self, callback):
        """ディレクトリ選択時のコールバック関数を設定"""
        self.on_dir_selected = callback

    def setup_context_menu(self):
        """右クリックメニューの設定"""
        self.context_menu = tk.Menu(self.tree, tearoff=0)

        # 定数としてメニュー項目のキーを定義
        self.MENU_OPEN_EXPLORER = _("ui.context_menu.open_explorer", "エクスプローラーで開く")
        self.MENU_OPEN_DEFAULT = _("ui.context_menu.open_default", "デフォルトアプリで開く")

        # メニュー項目の追加（ラベルを変数として保存）
        self.context_menu.add_command(label=self.MENU_OPEN_EXPLORER, command=self.open_in_explorer)
        self.context_menu.add_command(label=self.MENU_OPEN_DEFAULT, command=self.open_with_default_app)
        
        # 右クリックイベントをバインド
        if sys.platform == 'darwin':  # macOS
            self.tree.bind("<Button-2>", self.show_context_menu)
        else:  # Windows/Linux
            self.tree.bind("<Button-3>", self.show_context_menu)

    def show_context_menu(self, event):
        """コンテキストメニューを表示"""
        # クリックされた項目を特定
        item_id = self.tree.identify_row(event.y)
        if item_id:
            # 項目を選択
            self.tree.selection_set(item_id)
            # アイテムパスを取得
            item_path = self.get_item_path(item_id)
            
            # ファイルまたはディレクトリによってメニュー項目を有効/無効化
            is_dir = os.path.isdir(item_path) if item_path else False
            
            # デフォルトアプリで開くメニューをファイルの場合のみ有効化
            # 変数を使用してメニュー項目を指定
            self.context_menu.entryconfig(self.MENU_OPEN_DEFAULT, state=tk.NORMAL if not is_dir else tk.DISABLED)
            
            # メニューを表示
            try:
                self.context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.context_menu.grab_release()

    def open_in_explorer(self):
        """選択したアイテムをエクスプローラーで開く"""
        selected_items = self.tree.selection()
        if not selected_items:
            return
        
        item_path = self.get_item_path(selected_items[0])
        if not item_path:
            return
        
        # ディレクトリでない場合は親ディレクトリを取得
        if not os.path.isdir(item_path):
            item_path = os.path.dirname(item_path)
        
        # OSに応じてファイルマネージャーを開く
        if sys.platform == 'darwin':  # macOS
            subprocess.Popen(['open', item_path])
        elif sys.platform == 'win32':  # Windows
            subprocess.Popen(['explorer', item_path])
        else:  # Linux
            try:
                subprocess.Popen(['xdg-open', item_path])
            except Exception:
                # 失敗した場合は一般的なファイラーを試す
                try:
                    subprocess.Popen(['nautilus', item_path])
                except Exception:
                    try:
                        subprocess.Popen(['thunar', item_path])
                    except Exception:
                        messagebox.showinfo(_("info_title", "情報"), _("info_cannot_open", "'{0}'を開けませんでした。").format(item_path))
    
    def open_with_default_app(self):
        """選択したファイルをデフォルトアプリで開く"""
        selected_items = self.tree.selection()
        if not selected_items:
            return
        
        item_path = self.get_item_path(selected_items[0])
        if not item_path or os.path.isdir(item_path):
            return
        
        # OSに応じてデフォルトアプリでファイルを開く
        if sys.platform == 'darwin':  # macOS
            subprocess.Popen(['open', item_path])
        elif sys.platform == 'win32':  # Windows
            os.startfile(item_path)
        else:  # Linux
            try:
                subprocess.Popen(['xdg-open', item_path])
            except Exception:
                messagebox.showinfo(_("info_title", "情報"), _("info_cannot_open", "'{0}'を開けませんでした。").format(item_path))
    
    def include_selected(self):
        """選択したアイテムを解析に含める"""
        selected_items = self.tree.selection()
        if not selected_items:
            return
        
        for item_id in selected_items:
            if item_id in self.excluded_items:
                # 含む状態に切り替え
                event = type('Event', (), {'y': self.tree.bbox(item_id)[1] + 5})()
                self.toggle_exclusion(event)
    
    def exclude_selected(self):
        """選択したアイテムを解析から除外"""
        selected_items = self.tree.selection()
        if not selected_items:
            return
        
        for item_id in selected_items:
            if item_id not in self.excluded_items:
                # 除外状態に切り替え
                event = type('Event', (), {'y': self.tree.bbox(item_id)[1] + 5})()
                self.toggle_exclusion(event)
    
    def on_item_double_click(self, event):
        """ツリーアイテムがダブルクリックされたときの処理"""
        if not hasattr(self, 'tree') or not self.tree or not self.tree.winfo_exists():
            return

        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return

        # アイテムがディレクトリか確認
        is_dir = len(self.tree.get_children(item_id)) > 0
        if is_dir:
            # ディレクトリの場合は開閉を切り替え
            if self.tree.item(item_id, "open"):
                self.tree.item(item_id, open=False)
            else:
                self.tree.item(item_id, open=True)
            
            # ディレクトリパスを取得
            dir_path = self.get_item_path(item_id)
            if dir_path and os.path.isdir(dir_path):
                # 現在の選択状態を保存
                self.selected_dir = dir_path
                
                # ディレクトリ選択コールバックを呼び出す
                if self.on_dir_selected:
                    self.on_dir_selected(dir_path)
            return

        # ファイルの場合はパスを取得
        full_path = self.get_item_path(item_id)
        if full_path and full_path.endswith('.py'):
            print(f"ファイル選択: {full_path}")  # デバッグ用
            self.selected_file = full_path
            
            # 設定に保存
            self.config_manager.set_last_file(full_path)
            
            if self.on_file_selected:
                self.on_file_selected(full_path)

    def get_item_path(self, item_id):
        """ツリーアイテムのフルパスを取得（階層の深さに関わらず）"""
        if not self.current_dir or not item_id:
            return None
        
        # ルートノードかチェック
        if item_id == self.tree.get_children("")[0]:
            return self.current_dir
        
        path_parts = []
        current = item_id
        
        # 親アイテムを辿ってパスを構築
        while current:
            item_text = self.tree.item(current, "text").strip()
            # 先頭の絵文字やスペースを削除
            if item_text.startswith("📁 ") or item_text.startswith("🐍 ") or item_text.startswith("🔒 ") or item_text.startswith("📄 "):
                item_text = item_text[2:].strip()
            elif " " in item_text and item_text[0] != " ":
                # 先頭が絵文字の場合（フォーマットが " 名前"）
                item_text = item_text.split(" ", 1)[1].strip()
            
            # ルートノードに達したかチェック
            if current == self.tree.get_children("")[0]:
                break
            
            # 空でないテキストのみ追加
            if item_text:
                path_parts.insert(0, item_text)
            
            parent = self.tree.parent(current)
            if not parent:
                break
            
            current = parent
        
        # カレントディレクトリをベースにパスを構築
        full_path = os.path.normpath(os.path.join(self.current_dir, *path_parts))
        return full_path
   
    def toggle_exclusion(self, event):
        """Ctrl+クリックで項目の除外/含むを切り替え（エラーハンドリング追加）"""
        # すでに処理中の場合は新たな操作を受け付けない
        if self.is_processing:
            messagebox.showinfo(_("info_title", "情報"), _("info_processing", "現在処理中です。しばらくお待ちください。"))
            return
            
        try:
            # 処理中フラグをセット
            self.is_processing = True
            
            # クリックされた項目を特定
            item_id = self.tree.identify_row(event.y)
            if not item_id:
                self.is_processing = False
                return
            
            # 現在の状態を確認（excluded_itemsセットの有無で判断）
            is_excluded = item_id in self.excluded_items
            
            # アイテムのパスを取得し正規化
            item_path = self.get_item_path(item_id)
            if not item_path:
                self.is_processing = False
                return
            
            item_path = os.path.normpath(item_path)
            print(f"切り替えるアイテムのパス: {item_path}")  # デバッグ用
            
            # 子アイテムの数を事前に確認
            child_count = self._count_children(item_id)
            
            # 子アイテムが多すぎる場合は確認
            if child_count > self.max_items_to_process:
                confirm = messagebox.askyesno(
                    _("confirm_title", "確認"), 
                    _("confirm_many_items", "このフォルダには{0}個の項目が含まれています。\n処理に時間がかかる可能性があります。続行しますか？").format(child_count)
                )
                if not confirm:
                    self.is_processing = False
                    return
            
            # バックグラウンド処理のためのプログレスバーを表示
            if child_count > 100:
                progress_window = tk.Toplevel(self.parent)
                progress_window.title(_("progress_title", "処理中"))
                progress_window.geometry("300x100")
                progress_window.resizable(False, False)
                progress_window.transient(self.parent)
                
                progress_label = ttk.Label(progress_window, text=_("progress_processing_items", "項目を処理中... ({0}/{1})").format(0, child_count))
                progress_label.pack(pady=10)
                
                progress_bar = ttk.Progressbar(progress_window, mode="determinate", maximum=100)
                progress_bar.pack(fill="x", padx=20)
                
                # ウィンドウを画面中央に配置
                progress_window.update_idletasks()
                x = self.parent.winfo_rootx() + (self.parent.winfo_width() - progress_window.winfo_width()) // 2
                y = self.parent.winfo_rooty() + (self.parent.winfo_height() - progress_window.winfo_height()) // 2
                progress_window.geometry(f"+{x}+{y}")
            else:
                progress_window = None
                progress_label = None
                progress_bar = None
            
            # UI更新を実行
            self._update_exclusion_status(item_id, is_excluded, progress_window, progress_label, progress_bar)
            
        except Exception as e:
            messagebox.showerror(_("error_title", "エラー"), f"処理中にエラーが発生しました: {str(e)}")
            
            traceback.print_exc()
        finally:
            self.is_processing = False
    
    def _update_exclusion_status(self, item_id, is_excluded, progress_window=None, progress_label=None, progress_bar=None):
        """項目の除外状態を更新（バックグラウンド処理）"""
        # 項目のパスを取得
        item_path = self.get_item_path(item_id)
        
        if not is_excluded:  # 現在含む状態 → 除外状態に変更
            # 空のvaluesを設定
            self.tree.item(item_id, values=())
            self.excluded_items.add(item_id)
            
            # 設定に状態を保存
            self.config_manager.set_excluded_item(self.current_dir, item_path, True)
            
            # アイコンを変更
            is_dir = len(self.tree.get_children(item_id)) > 0
            if is_dir and self.locked_folder_icon:
                self.tree.item(item_id, image=self.locked_folder_icon)
            elif not is_dir and self.locked_file_icon:
                self.tree.item(item_id, image=self.locked_file_icon)
            else:
                # アイコンが使えない場合はテキストを変更
                text = self.tree.item(item_id, "text")
                if "📁" in text:
                    self.tree.item(item_id, text=text.replace("📁", "🔒"))
                elif "🐍" in text or "📄" in text:
                    self.tree.item(item_id, text=text.replace("🐍", "🔒").replace("📄", "🔒"))
            
            # セルの背景色を変更
            self.tree.tag_configure('excluded', foreground='#999999')
            self.tree.item(item_id, tags=('excluded',))
            
            # 子アイテムも全て除外
            self._set_children_status_with_progress(item_id, "exclude", progress_window, progress_label, progress_bar)
        else:  # 現在除外状態 → 含む状態に変更
            # 空のvaluesを設定
            self.tree.item(item_id, values=())
            
            # 設定に状態を保存
            self.config_manager.set_excluded_item(self.current_dir, item_path, False)
            
            # アイコンを戻す
            is_dir = len(self.tree.get_children(item_id)) > 0
            if is_dir and self.folder_icon:
                self.tree.item(item_id, image=self.folder_icon)
            elif not is_dir and self.file_icon:
                self.tree.item(item_id, image=self.file_icon)
            else:
                # アイコンが使えない場合はテキストを変更
                text = self.tree.item(item_id, "text")
                if "🔒" in text:
                    if is_dir:
                        self.tree.item(item_id, text=text.replace("🔒", "📁"))
                    else:
                        # ファイル拡張子を確認
                        file_ext = os.path.splitext(item_path)[1].lower()
                        if file_ext == '.py':
                            self.tree.item(item_id, text=text.replace("🔒", "🐍"))
                        else:
                            self.tree.item(item_id, text=text.replace("🔒", "📄"))
            
            # セルの背景色を元に戻す
            self.tree.item(item_id, tags=())
            
            if item_id in self.excluded_items:
                self.excluded_items.remove(item_id)
            
            # 子アイテムも全て含む
            self._set_children_status_with_progress(item_id, "include", progress_window, progress_label, progress_bar)
        
        # プログレスウィンドウを閉じる
        if progress_window and progress_window.winfo_exists():
            progress_window.destroy()
    
      
    def _count_children(self, item_id, count=0):
        """アイテムの子アイテム数を再帰的にカウント"""
        children = self.tree.get_children(item_id)
        count += len(children)
        
        for child_id in children:
            count = self._count_children(child_id, count)
        
        return count
    
    def _set_children_status_with_progress(self, parent_id, status, progress_window=None, progress_label=None, progress_bar=None):
        """子アイテムのステータスを再帰的に設定（プログレス表示付き）"""
        children = self.tree.get_children(parent_id)
        total_children = len(children)
        
        # 子ノードがなければ何もしない
        if total_children == 0:
            return
        
        # プログレスバーの更新間隔（子アイテムが多い場合は更新頻度を下げる）
        if total_children > 1000:
            update_interval = 100
        elif total_children > 100:
            update_interval = 20
        else:
            update_interval = 5
        
        for i, child_id in enumerate(children):
            # プログレス表示の更新
            if progress_window and i % update_interval == 0:
                if not progress_window.winfo_exists():
                    return  # ウィンドウが閉じられた場合は処理を中断
                
                progress_pct = (i / total_children) * 100
                progress_bar["value"] = progress_pct
                progress_label.config(text=_("progress_processing_items", "項目を処理中... ({0}/{1})").format(i, total_children))
                progress_window.update()
            
            is_dir = len(self.tree.get_children(child_id)) > 0
            
            # 子アイテムのパスを取得し正規化
            try:
                child_path = self.get_item_path(child_id)
                if not child_path:
                    continue
                
                child_path = os.path.normpath(child_path)
                
                if status == "exclude":
                    # 空のvaluesを設定
                    self.tree.item(child_id, values=())
                    self.excluded_items.add(child_id)
                    
                    # 設定に状態を保存
                    self.config_manager.set_excluded_item(self.current_dir, child_path, True)
                    
                    # アイコンを変更
                    if is_dir and self.locked_folder_icon:
                        self.tree.item(child_id, image=self.locked_folder_icon)
                    elif not is_dir and self.locked_file_icon:
                        self.tree.item(child_id, image=self.locked_file_icon)
                    else:
                        # アイコンが使えない場合はテキストを変更
                        text = self.tree.item(child_id, "text")
                        if "📁" in text:
                            self.tree.item(child_id, text=text.replace("📁", "🔒"))
                        elif "🐍" in text or "📄" in text:
                            self.tree.item(child_id, text=text.replace("🐍", "🔒").replace("📄", "🔒"))
                    
                    # セルの背景色を変更
                    self.tree.item(child_id, tags=('excluded',))
                else:
                    # 空のvaluesを設定
                    self.tree.item(child_id, values=())
                    
                    # 設定に状態を保存
                    self.config_manager.set_excluded_item(self.current_dir, child_path, False)
                    
                    # アイコンを戻す
                    if is_dir and self.folder_icon:
                        self.tree.item(child_id, image=self.folder_icon)
                    elif not is_dir and self.file_icon:
                        self.tree.item(child_id, image=self.file_icon)
                    else:
                        # アイコンが使えない場合はテキストを変更
                        text = self.tree.item(child_id, "text")
                        if "🔒" in text:
                            if is_dir:
                                self.tree.item(child_id, text=text.replace("🔒", "📁"))
                            else:
                                # ファイル拡張子を確認
                                file_ext = os.path.splitext(child_path)[1].lower()
                                if file_ext == '.py':
                                    self.tree.item(child_id, text=text.replace("🔒", "🐍"))
                                else:
                                    self.tree.item(child_id, text=text.replace("🔒", "📄"))
                    
                    # セルの背景色を元に戻す
                    self.tree.item(child_id, tags=())
                    
                    if child_id in self.excluded_items:
                        self.excluded_items.remove(child_id)
                
                # 10個ごとにUIを更新
                if i % 10 == 0:
                    self.tree.update()
                
                # 再帰的に子ノードを処理（深さ優先）
                if is_dir:
                    self._set_children_status_with_progress(child_id, status, progress_window, progress_label, progress_bar)
            
            except Exception as e:
                print(f"アイテム処理エラー: {str(e)} - スキップします")
                continue
        
        # 最終更新
        if progress_window and progress_window.winfo_exists():
            progress_bar["value"] = 100
            progress_label.config(text=_("progress_processing_items", "項目を処理中... ({0}/{1})").format(total_children, total_children))
            progress_window.update()
    
    def load_directory(self, path):
        """ディレクトリ構造をツリービューに読み込む（エラーハンドリング強化）"""
        try:
            # 処理中フラグを設定
            self.is_processing = True
            
            # 現在のツリービューをクリア
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            self.current_dir = os.path.normpath(path)
            self.excluded_items.clear()
            
            # 選択されたファイルをリセット
            self.selected_file = None
            
            # 設定に保存
            self.config_manager.set_last_directory(path)
            
            # ディレクトリが大きすぎないか確認（ファイル数をカウント）
            total_items = 0
            large_directory = False
            max_items_to_display = 5000  # 一度に表示する最大項目数
            
            for root, dirs, files in os.walk(path):
                # スキップすべきフォルダ名を除外
                dirs[:] = [d for d in dirs if d not in self.skip_folders]
                
                # EXEファイルを含むフォルダをスキップする場合
                if self.skip_exe_folders:
                    has_exe = any(f.lower().endswith(tuple(self.skip_extensions)) for f in files)
                    if has_exe:
                        dirs[:] = []  # サブディレクトリを探索しない
                
                total_items += len(dirs) + len(files)
                if total_items > max_items_to_display:
                    large_directory = True
                    break
            
            # 大きなディレクトリの場合は警告
            if large_directory:
                confirm = messagebox.askyesno(
                    _("confirm_title", "確認"), 
                    f"このディレクトリには{max_items_to_display}個以上の項目が含まれています。\n"
                    "全ての項目を読み込むと時間がかかったり、アプリケーションが応答しなくなる可能性があります。\n\n"
                    "続行しますか？\n"
                    f"（「いいえ」を選択すると、最初の{max_items_to_display}個の項目のみが表示されます）"
                )
                limit_items = not confirm
            else:
                limit_items = False
            
            # プログレスバーウィンドウの表示
            if total_items > 100:
                progress_window = tk.Toplevel(self.parent)
                progress_window.title(_("progress_loading_directory", "ディレクトリを読み込み中"))
                progress_window.geometry("300x100")
                progress_window.resizable(False, False)
                progress_window.transient(self.parent)
                
                progress_label = ttk.Label(progress_window, text=_("progress_loading_structure", "ディレクトリ構造を読み込み中..."))
                progress_label.pack(pady=10)
                
                progress_bar = ttk.Progressbar(progress_window, mode="indeterminate")
                progress_bar.pack(fill="x", padx=20)
                progress_bar.start(10)
                
                # ウィンドウを画面中央に配置
                progress_window.update_idletasks()
                x = self.parent.winfo_rootx() + (self.parent.winfo_width() - progress_window.winfo_width()) // 2
                y = self.parent.winfo_rooty() + (self.parent.winfo_height() - progress_window.winfo_height()) // 2
                progress_window.geometry(f"+{x}+{y}")
                progress_window.update()
            else:
                progress_window = None
            
            # ルートディレクトリを追加
            if self.folder_icon:
                # 空のvaluesを設定
                root_item = self.tree.insert("", "end", text=f" {os.path.basename(path)}", 
                                values=(), image=self.folder_icon, open=True)
            else:
                # 空のvaluesを設定
                root_item = self.tree.insert("", "end", text=f"📁 {os.path.basename(path)}", 
                                values=(), open=True)
            
            # 再帰的にディレクトリ構造を構築（項目数制限あり）
            counters = {"items": 0, "limit": max_items_to_display if limit_items else None}
            try:
                self._load_directory_recursively(root_item, path, counters)
            except TooManyItemsException:
                if progress_window and progress_window.winfo_exists():
                    progress_label.config(text=f"表示制限に達しました: {max_items_to_display}項目")
                    progress_window.update()
            
            # プログレスウィンドウを閉じる
            if progress_window and progress_window.winfo_exists():
                progress_bar.stop()
                progress_window.destroy()
            
            # 表示制限に達した場合は通知
            if limit_items and counters["items"] >= max_items_to_display:
                messagebox.showinfo(
                    _("info_title", "情報"), 
                    _("info_display_limit", "表示項目数が制限に達しました ({0}項目)。\n全ての項目が表示されているわけではありません。").format(max_items_to_display)
                )
            
            # デバッグ出力
            print(f"ディレクトリを読み込みました: {self.current_dir}")
            print(f"項目数: {counters['items']}")
            print(f"除外アイテム設定: {self.config_manager.get_excluded_items(self.current_dir)}")
        
        except Exception as e:
            messagebox.showerror(_("error_title", "エラー"), _("error_loading_directory", "ディレクトリの読み込み中にエラーが発生しました: {0}").format(str(e)))
            
            traceback.print_exc()
        
        finally:
            # 処理中フラグを解除
            self.is_processing = False
    
    def _load_directory_recursively(self, parent, path, counters):
        """再帰的にディレクトリ構造を読み込む（EXEフォルダスキップをデフォルト有効に）"""
        try:
            # 表示制限に達したかチェック
            if counters["limit"] is not None and counters["items"] >= counters["limit"]:
                raise TooManyItemsException("表示制限に達しました")
            
            # ディレクトリ内の項目をソート（ディレクトリ→ファイル）
            try:
                items = os.listdir(path)
            except PermissionError:
                # アクセス権限がない場合は空のvaluesを設定
                self.tree.item(parent, values=())
                return
            except Exception as e:
                # その他のエラー
                print(f"ディレクトリ読み込みエラー: {str(e)} - スキップします")
                return
            
            dirs = []
            files = []
            
            # EXEファイルを含むかどうかをチェック
            has_exe = False
            
            for item in items:
                item_path = os.path.join(path, item)
                try:
                    # フォルダ名に基づくスキップをチェック
                    basename = os.path.basename(item_path)
                    if os.path.isdir(item_path):
                        if basename in self.skip_folders:
                            continue
                        dirs.append(item)
                    else:
                        # EXEファイルのチェック
                        if any(item.lower().endswith(ext) for ext in self.skip_extensions):
                            has_exe = True
                        
                        files.append(item)
                except Exception as e:
                    print(f"項目チェックエラー: {str(e)} - スキップします")
                    continue
            
            # EXEファイルが含まれていて、スキップ設定がONの場合
            if has_exe and self.skip_exe_folders:
                # このディレクトリ自体は表示するが、中身は空のvaluesを設定
                self.tree.item(parent, values=())
                return
            
            # 設定から除外状態を取得
            excluded_items = self.config_manager.get_excluded_items(self.current_dir)
            
            # ディレクトリを追加
            for dir_name in sorted(dirs):
                # 表示制限に達したかチェック
                if counters["limit"] is not None and counters["items"] >= counters["limit"]:
                    raise TooManyItemsException("表示制限に達しました")
                
                counters["items"] += 1
                
                try:
                    dir_path = os.path.normpath(os.path.join(path, dir_name))
                    
                    # 設定から除外状態を取得 - 正規化されたパスを使用
                    is_excluded = excluded_items.get(dir_path, False)
                    
                    if self.folder_icon:
                        image = self.locked_folder_icon if is_excluded else self.folder_icon
                        # valuesにステータステキストを表示しない
                        dir_id = self.tree.insert(parent, "end", text=f" {dir_name}", 
                                             values=(), image=image, open=False)
                    else:
                        icon = "🔒" if is_excluded else "📁"
                        # valuesにステータステキストを表示しない
                        dir_id = self.tree.insert(parent, "end", text=f"{icon} {dir_name}", 
                                             values=(), open=False)
                    
                    if is_excluded:
                        self.excluded_items.add(dir_id)
                        self.tree.tag_configure('excluded', foreground='#999999')
                        self.tree.item(dir_id, tags=('excluded',))
                    
                    # 100個ごとにUIを更新
                    if counters["items"] % 100 == 0:
                        self.tree.update()
                    
                    # サブディレクトリを再帰的に処理
                    self._load_directory_recursively(dir_id, dir_path, counters)
                
                except TooManyItemsException:
                    # 再帰呼び出しで制限に達した場合は上位に伝播
                    raise
                except Exception as e:
                    print(f"ディレクトリ追加エラー: {str(e)} - スキップします")
                    continue
            
            # ファイルを追加（EXEファイルはスキップ）
            for file_name in sorted(files):
                # スキップすべき拡張子なら除外
                if any(file_name.lower().endswith(ext) for ext in self.skip_extensions):
                    continue
                
                # 表示制限に達したかチェック
                if counters["limit"] is not None and counters["items"] >= counters["limit"]:
                    raise TooManyItemsException("表示制限に達しました")
                
                counters["items"] += 1
                
                try:
                    file_path = os.path.normpath(os.path.join(path, file_name))
                    
                    # 設定から除外状態を取得 - 正規化されたパスを使用
                    is_excluded = excluded_items.get(file_path, False)
                    
                    # ファイルアイコンの選択（拡張子に基づく）
                    file_ext = os.path.splitext(file_name)[1].lower()
                    if file_ext == '.py':
                        icon_text = "🐍"  # Pythonファイル
                    elif file_ext == '.dart':
                        icon_text = "📱"  # Dartファイル
                    else:
                        icon_text = "📄"  # その他のファイル
                    
                    if self.file_icon:
                        image = self.locked_file_icon if is_excluded else self.file_icon
                        # valuesにステータステキストを表示しない
                        file_id = self.tree.insert(parent, "end", text=f" {file_name}", 
                                                values=(), image=image)
                    else:
                        icon = "🔒" if is_excluded else icon_text
                        # valuesにステータステキストを表示しない
                        file_id = self.tree.insert(parent, "end", text=f"{icon} {file_name}", 
                                                values=())
                    
                    if is_excluded:
                        self.excluded_items.add(file_id)
                        self.tree.tag_configure('excluded', foreground='#999999')
                        self.tree.item(file_id, tags=('excluded',))
                    
                    # 100個ごとにUIを更新
                    if counters["items"] % 100 == 0:
                        self.tree.update()
                
                except TooManyItemsException:
                    # 再帰呼び出しで制限に達した場合は上位に伝播
                    raise
                except Exception as e:
                    print(f"ファイル追加エラー: {str(e)} - スキップします")
                    continue
        
        except PermissionError:
            # アクセス権限がない場合は空のvaluesを設定
            self.tree.item(parent, values=())
        except TooManyItemsException:
            # 項目数制限に達した場合は上位に伝播
            raise
        except Exception as e:
            print(f"ディレクトリ処理エラー: {str(e)} - スキップします")
            
    # オプション設定のためのトグルメソッド
    def toggle_skip_exe_folders(self):
        """EXEファイルを含むフォルダをスキップするかどうかを切り替える"""
        self.skip_exe_folders = not self.skip_exe_folders
        
        # 設定マネージャーに保存
        if hasattr(self.config_manager, 'set_skip_exe_folders'):
            self.config_manager.set_skip_exe_folders(self.skip_exe_folders)
            
        return self.skip_exe_folders

    def get_included_files(self, include_python_only=True):
        """解析対象のファイルパスリストを取得"""
        if not self.current_dir or not self.tree or not self.tree.winfo_exists():
            return []
        
        included_files = []
        
        def traverse_tree(node, parent_path):
            # 現在のノードが除外リストに含まれているかチェック
            if node in self.excluded_items:
                return
            
            item_text = self.tree.item(node, "text")
            # 先頭の絵文字やスペースを削除
            clean_text = item_text.strip()
            if clean_text.startswith("📁 ") or clean_text.startswith("🐍 ") or clean_text.startswith("🔒 ") or clean_text.startswith("📄 "):
                clean_text = clean_text[2:].strip()
            elif " " in clean_text and clean_text[0] != " ":
                clean_text = clean_text.split(" ", 1)[1].strip()
            
            current_path = os.path.join(parent_path, clean_text)
            
            # ファイルかディレクトリかを確認
            is_dir = len(self.tree.get_children(node)) > 0
            if not is_dir:
                # 修正: PythonファイルとDartファイルを含める条件
                if not include_python_only:
                    included_files.append(current_path)  # すべてのファイルを含める
                elif clean_text.endswith('.py') or clean_text.endswith('.dart'):
                    included_files.append(current_path)  # PythonまたはDartファイルを含める
            
            # 子ノードを処理
            for child in self.tree.get_children(node):
                traverse_tree(child, current_path)
        
        # ルートディレクトリから全てのノードを処理
        root_node = self.tree.get_children()[0]
        # ルートディレクトリのテキストから絵文字とスペースを削除
        root_text = self.tree.item(root_node, "text").strip()
        if root_text.startswith("📁 ") or root_text.startswith("🔒 "):
            root_text = root_text[2:].strip()
        elif " " in root_text and root_text[0] != " ":
            root_text = root_text.split(" ", 1)[1].strip()
        
        parent_dir = os.path.dirname(self.current_dir)
        traverse_tree(root_node, parent_dir)
        
        return included_files
