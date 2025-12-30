# ui/toolbar.py
"""ツールバー関連のUIコンポーネント"""

import os
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from utils.i18n import _


class ToolbarManager:
    """ツールバーの作成と管理を行うクラス"""

    def __init__(self, main_window):
        """
        ツールバーマネージャーを初期化

        Args:
            main_window: MainWindowインスタンス（親ウィンドウへの参照）
        """
        self.main_window = main_window
        self.toolbar_frame = main_window.toolbar_frame
        self.icon_dir = os.path.join(os.path.dirname(__file__), "icon")
        self.custom_buttons = []
        self.button_images = []

    def setup_custom_buttons(self):
        """カスタムボタンをセットアップ（PNG画像を使用）"""
        # 再分析ボタン
        self._create_reanalyze_button()

        # 画像パスのベースディレクトリを相対パスで指定
        icon_dir = os.path.join(os.path.dirname(__file__), "icon")

        # ボタン設定
        button_configs = [
            {'icon': "folder.png", 'label': "Import", 'command': self.main_window.import_directory},
            {'icon': "analyze.png", 'label': "Analysis", 'command': self.main_window.analyze_selected},
            {'icon': "copy.png", 'label': "Copy", 'command': self.main_window.copy_to_clipboard},
            {'icon': "cleaner.png", 'label': "Clear", 'command': self.main_window.clear_workspace},
            {'icon': "run.png", 'label': "Run", 'command': self.main_window.run_python_file}
        ]

        # ツールバーにカスタムボタンを作成
        for config in button_configs:
            self._create_toolbar_button(icon_dir, config)

    def _create_reanalyze_button(self):
        """再分析ボタンを作成"""
        reanalyze_btn_frame = ttk.Frame(self.toolbar_frame)
        reanalyze_btn_frame.pack(side="left", padx=5)

        # アイコン画像（analyze.pngを再分析ボタンにも使用）
        with Image.open(os.path.join(self.icon_dir, "analyze.png")) as reanalyze_icon:
            reanalyze_icon_image = ImageTk.PhotoImage(reanalyze_icon.resize((24, 24)))

        # アイコンラベル
        reanalyze_icon_label = tk.Label(reanalyze_btn_frame, image=reanalyze_icon_image, bg="#f0f0f0")
        reanalyze_icon_label.image = reanalyze_icon_image  # 参照を保持
        reanalyze_icon_label.pack(side="left")

        # テキストラベル
        self.main_window.reanalyze_text_label = tk.Label(
            reanalyze_btn_frame,
            text=_("buttons.reanalyze", "再分析"),
            bg="#f0f0f0",
            name="reanalyze_label"
        )
        self.main_window.reanalyze_text_label.pack(side="left", padx=2)

        # ボタン機能
        reanalyze_btn_frame.bind("<Button-1>", lambda e: self.main_window.reanalyze_project())
        reanalyze_icon_label.bind("<Button-1>", lambda e: self.main_window.reanalyze_project())
        self.main_window.reanalyze_text_label.bind("<Button-1>", lambda e: self.main_window.reanalyze_project())

        # ホバーエフェクト
        self._bind_hover_effects(reanalyze_btn_frame, reanalyze_icon_label, self.main_window.reanalyze_text_label)

    def _create_toolbar_button(self, icon_dir, config):
        """ツールバーボタンを作成"""
        icon_path = os.path.join(icon_dir, config['icon'])

        # 画像をロード
        icon_photo = None
        try:
            with Image.open(icon_path) as icon_image:
                resized_icon = icon_image.resize((24, 24), Image.LANCZOS)
                icon_photo = ImageTk.PhotoImage(resized_icon)
                self.button_images.append(icon_photo)
        except Exception as e:
            print(f"アイコン画像の読み込みエラー: {e}")

        # フレームを作成
        btn_frame = ttk.Frame(self.toolbar_frame)
        btn_frame.pack(side="left", padx=5)

        # アイコンラベル
        if icon_photo:
            icon_label = tk.Label(btn_frame, image=icon_photo, background="#f0f0f0")
        else:
            icon_label = tk.Label(btn_frame, text="■", font=('Helvetica', 14), background="#f0f0f0")
        icon_label.pack(side="left")

        # テキストラベル
        text_label = tk.Label(btn_frame, text=" " + config['label'],
                              font=('Helvetica', 10), background="#f0f0f0")
        text_label.pack(side="left")

        # クリックイベント
        cmd = config['command']
        icon_label.bind("<Button-1>", lambda e, cmd=cmd: cmd())
        text_label.bind("<Button-1>", lambda e, cmd=cmd: cmd())

        # ホバー効果
        self._bind_hover_effects(btn_frame, icon_label, text_label)

        # ボタンリストに追加
        self.custom_buttons.append({
            'frame': btn_frame,
            'icon': icon_label,
            'text': text_label,
            'command': cmd
        })

    def _bind_hover_effects(self, frame, *widgets):
        """ホバーエフェクトをバインド"""
        enter_func = self._create_enter_function(frame, "#e0e0e0")
        leave_func = self._create_leave_function(frame, "#f0f0f0")

        frame.bind("<Enter>", enter_func)
        frame.bind("<Leave>", leave_func)

        for widget in widgets:
            widget.bind("<Enter>", enter_func)
            widget.bind("<Leave>", leave_func)

    def _create_enter_function(self, frame, color):
        """ホバー時の色変更関数を生成"""
        return lambda e: [w.configure(background=color) for w in frame.winfo_children()]

    def _create_leave_function(self, frame, color):
        """ホバー終了時の色変更関数を生成"""
        return lambda e: [w.configure(background=color) for w in frame.winfo_children()]
