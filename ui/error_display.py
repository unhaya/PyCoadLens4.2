# ui/error_display.py

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from utils.i18n import _ 

class ErrorDisplayWindow:
    """エラーメッセージを表示するウィンドウクラス"""
    
    def __init__(self, error_text, title=_("error_title", "実行エラー")):
        """
        エラー表示ウィンドウを初期化
        
        Args:
            error_text (str): 表示するエラーテキスト
            title (str): ウィンドウのタイトル
        """
        # ルートウィンドウを作成
        self.root = tk.Tk()
        self.root.title(title)
        self.root.withdraw()  # 一時的に非表示
        
        # エラーウィンドウの作成
        self.window = tk.Toplevel(self.root)
        self.window.title(title)
        self.window.protocol("WM_DELETE_WINDOW", self.root.destroy)  # ウィンドウが閉じられたらルートも終了
        
        # メインフレーム
        main_frame = ttk.Frame(self.window, padding=10)
        main_frame.pack(fill="both", expand=True)
        
        # エラーメッセージ表示エリア
        error_label = ttk.Label(main_frame, text=_("error_content_label", "エラー内容:"))
        error_label.pack(anchor="w")
        
        # スクロール可能なテキストエリア
        self.text_area = scrolledtext.ScrolledText(main_frame, width=60, height=15, wrap="word")
        self.text_area.pack(fill="both", expand=True, pady=5)
        self.text_area.insert("1.0", error_text)
        self.text_area.config(state="disabled")  # 読み取り専用に設定
        
        # ボタンフレーム
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(10, 0))
        
        # ボタンの配置
        copy_button = ttk.Button(button_frame, text=_("copy_button", "コピー"), command=self.copy_to_clipboard)
        copy_button.pack(side="left", padx=5)
        
        save_button = ttk.Button(button_frame, text=_("save_button", "保存"), command=self.save_to_file)
        save_button.pack(side="left", padx=5)
        
        close_button = ttk.Button(button_frame, text=_("close_button", "閉じる"), command=self.root.destroy)
        close_button.pack(side="right", padx=5)
        
        # ウィンドウを画面中央に配置
        self.center_window()
        
        # ウィンドウを表示して、メインループを開始
        self.window.deiconify()
        self.root.mainloop()
    
    def center_window(self):
        """ウィンドウを画面中央に配置する"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")
    
    def copy_to_clipboard(self):
        """エラーテキストをクリップボードにコピー"""
        error_text = self.text_area.get("1.0", "end-1c")
        self.window.clipboard_clear()
        self.window.clipboard_append(error_text)
        messagebox.showinfo(_("copy_info_title", "コピー"), _("copy_info_message", "エラー内容をクリップボードにコピーしました。"))
    
    def save_to_file(self):
        """エラーテキストをファイルに保存"""
        error_text = self.text_area.get("1.0", "end-1c")
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[(_("text_file", "テキストファイル"), "*.txt"), (_("all_files", "すべてのファイル"), "*.*")],
            title=_("save_error_log_title", "エラーログの保存")
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as file:
                    file.write(error_text)
                messagebox.showinfo(_("save_info_title", "保存"), _("save_info_message", "エラー内容を {0} に保存しました。").format(file_path))
            except Exception as e:
                messagebox.showerror(_("save_error_title", "保存エラー"), _("save_error_message", "ファイルの保存中にエラーが発生しました：\n{0}").format(str(e)))
                
    def reset(self, error_text="", title=None):
        """
        エラー表示の内容をリセットする
        
        Args:
            error_text (str): 新しく表示するエラーテキスト（空なら消去）
            title (str): 新しいウィンドウタイトル（Noneなら変更なし）
        """
        # タイトルの更新（指定された場合）
        if title is not None:
            self.window.title(title)
        
        # テキストエリアの内容を更新
        self.text_area.config(state="normal")  # 一時的に編集可能に
        self.text_area.delete("1.0", "end")    # 内容を消去
        
        if error_text:
            self.text_area.insert("1.0", error_text)  # 新しいテキストを表示
        
        self.text_area.config(state="disabled")  # 読み取り専用に戻す
        
        # ウィンドウを再度中央に配置
        self.center_window()