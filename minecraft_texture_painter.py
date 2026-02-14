import tkinter as tk
from tkinter import ttk, colorchooser, filedialog, messagebox, simpledialog
from PIL import Image, ImageTk, ImageDraw
import json
import os
import math
import random
import copy


class MinecraftBlockTexturePainter:
    """Редактор текстур Minecraft с поддержкой всех 6 граней блока"""

    FACE_NAMES = ["top", "bottom", "front", "back", "left", "right"]
    FACE_LABELS = {
        "top": "⬆ Верх (Top)",
        "bottom": "⬇ Низ (Bottom)",
        "front": "🔲 Перед (Front)",
        "back": "🔳 Зад (Back)",
        "left": "◀ Лево (Left)",
        "right": "▶ Право (Right)"
    }

    def __init__(self, root):
        self.root = root
        self.root.title("Minecraft Block Texture Painter — Java Edition")
        self.root.geometry("1500x900")
        self.root.configure(bg="#1e1e2e")
        self.root.minsize(1200, 700)

        # --- Настройки ---
        self.texture_size = 16
        self.pixel_size = 22
        self.current_color = "#b5503c"
        self.secondary_color = "#8e8e86"
        self.current_tool = "pencil"
        self.grid_visible = True
        self.symmetry_x = False
        self.symmetry_y = False
        self.current_face = "front"

        # --- Данные текстур для каждой грани ---
        self.faces = {}
        for face in self.FACE_NAMES:
            self.faces[face] = {}
            for x in range(self.texture_size):
                for y in range(self.texture_size):
                    self.faces[face][(x, y)] = None

        # --- Режим: одинаковые все грани ---
        self.link_all_faces = False
        self.link_sides = False  # Связать 4 боковые грани

        # --- История ---
        self.history = []
        self.history_index = -1
        self.max_history = 60
        self.save_state()

        # --- Буфер обмена ---
        self.clipboard = None
        self.clipboard_face = None

        # --- Drag для фигур ---
        self.drag_start = None

        # --- Палитра Minecraft ---
        self.mc_palette = [
            "#000000", "#ffffff", "#ff0000", "#00ff00", "#0000ff",
            "#ffff00", "#ff00ff", "#00ffff", "#808080", "#c0c0c0",
            "#800000", "#808000", "#008000", "#800080", "#008080",
            "#000080", "#ff8000", "#80ff00", "#00ff80", "#0080ff",
            "#8000ff", "#ff0080", "#ff8080", "#80ff80", "#8080ff",
            "#ffff80", "#ff80ff", "#80ffff", "#404040", "#a0a0a0",
            "#8B7355", "#6B8E23", "#228B22", "#8B4513", "#D2691E",
            "#A0522D", "#696969", "#556B2F", "#2E8B57", "#3CB371",
            "#4682B4", "#5F9EA0", "#B8860B", "#DAA520", "#CD853F",
            "#DEB887", "#F5DEB3", "#FAEBD7", "#FFE4C4", "#FFDEAD",
            "#1a1a2e", "#16213e", "#0f3460", "#533483", "#e94560",
            "#7c3aed", "#2563eb", "#059669", "#d97706", "#dc2626",
        ]
        self.custom_palette = []

        # --- Шаблоны ---
        self.templates = {
            "Камень": self.tpl_stone,
            "Дерево (бревно)": self.tpl_wood_log,
            "Земля": self.tpl_dirt,
            "Трава": self.tpl_grass,
            "Кирпич": self.tpl_brick,
            "Доски": self.tpl_planks,
            "Песок": self.tpl_sand,
            "Булыжник": self.tpl_cobblestone,
            "Руда (железо)": self.tpl_iron_ore,
            "TNT": self.tpl_tnt,
        }

        self.build_ui()
        self.bind_shortcuts()
        self.draw_face_canvas()
        self.update_3d_preview()

    # =============================================
    #  ИНТЕРФЕЙС
    # =============================================

    def build_ui(self):
        self.build_menu()

        main = tk.Frame(self.root, bg="#1e1e2e")
        main.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Левая панель — инструменты
        self.build_tools_panel(main)

        # Центр — редактор граней + 3D превью
        center = tk.Frame(main, bg="#1e1e2e")
        center.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Верхняя часть центра — выбор граней + холст
        top_center = tk.Frame(center, bg="#1e1e2e")
        top_center.pack(fill=tk.BOTH, expand=True)

        self.build_face_selector(top_center)
        self.build_canvas_area(top_center)
        self.build_3d_preview(top_center)

        # Нижняя часть центра — 6 мини-превью
        self.build_all_faces_preview(center)

        # Правая панель — цвета
        self.build_right_panel(main)

        # Нижний статус-бар
        self.build_status_bar()

    # ---------- МЕНЮ ----------

    def build_menu(self):
        mb = tk.Menu(self.root)
        self.root.config(menu=mb)

        # Файл
        fm = tk.Menu(mb, tearoff=0)
        mb.add_cascade(label="Файл", menu=fm)
        fm.add_command(label="Новый блок", command=self.new_block, accelerator="Ctrl+N")
        fm.add_separator()
        fm.add_command(label="Открыть текстуру (.png)", command=self.open_single_png)
        fm.add_command(label="Открыть атлас блока (.png)", command=self.open_atlas)
        fm.add_command(label="Открыть проект (.json)", command=self.open_project)
        fm.add_separator()
        fm.add_command(label="Сохранить атлас блока (.png)", command=self.save_atlas, accelerator="Ctrl+S")
        fm.add_command(label="Сохранить каждую грань отдельно", command=self.save_faces_separate)
        fm.add_command(label="Сохранить проект (.json)", command=self.save_project)
        fm.add_separator()
        fm.add_command(label="Экспорт ресурспака", command=self.export_resourcepack)
        fm.add_separator()
        fm.add_command(label="Выход", command=self.root.quit)

        # Редактирование
        em = tk.Menu(mb, tearoff=0)
        mb.add_cascade(label="Редактирование", menu=em)
        em.add_command(label="Отменить", command=self.undo, accelerator="Ctrl+Z")
        em.add_command(label="Повторить", command=self.redo, accelerator="Ctrl+Y")
        em.add_separator()
        em.add_command(label="Копировать грань", command=self.copy_face, accelerator="Ctrl+C")
        em.add_command(label="Вставить в грань", command=self.paste_face, accelerator="Ctrl+V")
        em.add_command(label="Копировать на все грани", command=self.copy_to_all_faces)
        em.add_command(label="Копировать на боковые грани", command=self.copy_to_side_faces)
        em.add_separator()
        em.add_command(label="Очистить грань", command=self.clear_current_face)
        em.add_command(label="Очистить весь блок", command=self.clear_all_faces)
        em.add_command(label="Залить грань цветом", command=self.fill_current_face)

        # Преобразования
        tm = tk.Menu(mb, tearoff=0)
        mb.add_cascade(label="Преобразования", menu=tm)
        tm.add_command(label="Повернуть на 90° →", command=lambda: self.rotate_face(90))
        tm.add_command(label="Повернуть на 90° ←", command=lambda: self.rotate_face(-90))
        tm.add_command(label="Повернуть на 180°", command=lambda: self.rotate_face(180))
        tm.add_separator()
        tm.add_command(label="Отразить горизонтально", command=lambda: self.flip_face("h"))
        tm.add_command(label="Отразить вертикально", command=lambda: self.flip_face("v"))
        tm.add_separator()
        tm.add_command(label="Сдвиг вверх", command=lambda: self.shift_face(0, -1))
        tm.add_command(label="Сдвиг вниз", command=lambda: self.shift_face(0, 1))
        tm.add_command(label="Сдвиг влево", command=lambda: self.shift_face(-1, 0))
        tm.add_command(label="Сдвиг вправо", command=lambda: self.shift_face(1, 0))

        # Фильтры
        flm = tk.Menu(mb, tearoff=0)
        mb.add_cascade(label="Фильтры", menu=flm)
        flm.add_command(label="Яркость + (грань)", command=lambda: self.adjust_brightness(20))
        flm.add_command(label="Яркость - (грань)", command=lambda: self.adjust_brightness(-20))
        flm.add_command(label="Оттенки серого", command=self.grayscale_face)
        flm.add_command(label="Инвертировать цвета", command=self.invert_face)
        flm.add_command(label="Добавить шум", command=self.noise_face)

        # Шаблоны
        tplm = tk.Menu(mb, tearoff=0)
        mb.add_cascade(label="Шаблоны", menu=tplm)
        for name, func in self.templates.items():
            tplm.add_command(label=name, command=func)

        # Размер
        sm = tk.Menu(mb, tearoff=0)
        mb.add_cascade(label="Размер", menu=sm)
        for s in [16, 32, 64, 128]:
            sm.add_command(label=f"{s}×{s}", command=lambda sz=s: self.resize_texture(sz))
        sm.add_command(label="Свой размер...", command=self.custom_resize)

        # Вид
        vm = tk.Menu(mb, tearoff=0)
        mb.add_cascade(label="Вид", menu=vm)
        vm.add_command(label="Сетка вкл/выкл", command=self.toggle_grid, accelerator="G")
        vm.add_command(label="Увеличить", command=self.zoom_in, accelerator="+")
        vm.add_command(label="Уменьшить", command=self.zoom_out, accelerator="-")

    # ---------- ИНСТРУМЕНТЫ ----------

    def build_tools_panel(self, parent):
        frame = tk.Frame(parent, bg="#2a2a3d", width=180, relief=tk.RIDGE, bd=1)
        frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 4))
        frame.pack_propagate(False)

        tk.Label(frame, text="🔧 Инструменты", font=("Arial", 11, "bold"),
                 bg="#2a2a3d", fg="#e0e0e0").pack(pady=8)

        tools = [
            ("✏️  Карандаш", "pencil"),
            ("🪣  Заливка", "fill"),
            ("🔲  Ластик", "eraser"),
            ("💧  Пипетка", "eyedropper"),
            ("📏  Линия", "line"),
            ("⬜  Прямоугольник", "rectangle"),
            ("⭕  Круг", "circle"),
            ("⬛  Прямоуг.(зал.)", "filled_rect"),
            ("🔴  Круг (зал.)", "filled_circle"),
            ("🌈  Градиент", "gradient"),
            ("💨  Размытие", "blur"),
            ("✨  Замена цвета", "replace"),
            ("🖌️  Кисть 2px", "brush2"),
            ("🖌️  Кисть 3px", "brush3"),
            ("🎨  Дизеринг", "dither"),
        ]

        self.tool_buttons = {}
        for text, tool in tools:
            btn = tk.Button(frame, text=text, command=lambda t=tool: self.select_tool(t),
                            bg="#3b3b55", fg="#ddd", relief=tk.FLAT,
                            activebackground="#50507a", anchor="w", padx=8, font=("Arial", 9))
            btn.pack(fill=tk.X, padx=4, pady=1)
            self.tool_buttons[tool] = btn
        self.tool_buttons["pencil"].configure(bg="#0078d4")

        ttk.Separator(frame, orient="horizontal").pack(fill=tk.X, padx=4, pady=8)

        # Симметрия
        tk.Label(frame, text="Симметрия:", bg="#2a2a3d", fg="#ccc", font=("Arial", 9)).pack(anchor="w", padx=8)
        self.sym_x_var = tk.BooleanVar()
        self.sym_y_var = tk.BooleanVar()
        tk.Checkbutton(frame, text="X (гориз.)", variable=self.sym_x_var,
                       bg="#2a2a3d", fg="#ccc", selectcolor="#3b3b55",
                       command=lambda: setattr(self, 'symmetry_x', self.sym_x_var.get())).pack(anchor="w", padx=16)
        tk.Checkbutton(frame, text="Y (верт.)", variable=self.sym_y_var,
                       bg="#2a2a3d", fg="#ccc", selectcolor="#3b3b55",
                       command=lambda: setattr(self, 'symmetry_y', self.sym_y_var.get())).pack(anchor="w", padx=16)

        ttk.Separator(frame, orient="horizontal").pack(fill=tk.X, padx=4, pady=8)

        # Связь граней
        tk.Label(frame, text="Связь граней:", bg="#2a2a3d", fg="#ccc", font=("Arial", 9)).pack(anchor="w", padx=8)
        self.link_all_var = tk.BooleanVar()
        self.link_sides_var = tk.BooleanVar()
        tk.Checkbutton(frame, text="Все 6 граней", variable=self.link_all_var,
                       bg="#2a2a3d", fg="#ccc", selectcolor="#3b3b55",
                       command=lambda: setattr(self, 'link_all_faces', self.link_all_var.get())).pack(anchor="w",
                                                                                                      padx=16)
        tk.Checkbutton(frame, text="4 боковые грани", variable=self.link_sides_var,
                       bg="#2a2a3d", fg="#ccc", selectcolor="#3b3b55",
                       command=lambda: setattr(self, 'link_sides', self.link_sides_var.get())).pack(anchor="w",
                                                                                                    padx=16)

        ttk.Separator(frame, orient="horizontal").pack(fill=tk.X, padx=4, pady=8)

        # Прозрачность
        tk.Label(frame, text="Прозрачность:", bg="#2a2a3d", fg="#ccc", font=("Arial", 9)).pack(anchor="w", padx=8)
        self.alpha_var = tk.IntVar(value=255)
        tk.Scale(frame, from_=0, to=255, orient=tk.HORIZONTAL, variable=self.alpha_var,
                 bg="#2a2a3d", fg="#ccc", highlightthickness=0, troughcolor="#3b3b55",
                 length=140).pack(padx=8)

    # ---------- ВЫБОР ГРАНИ ----------

    def build_face_selector(self, parent):
        frame = tk.Frame(parent, bg="#1e1e2e")
        frame.pack(side=tk.LEFT, fill=tk.Y, padx=4)

        tk.Label(frame, text="📦 Грани блока", font=("Arial", 11, "bold"),
                 bg="#1e1e2e", fg="#e0e0e0").pack(pady=8)

        self.face_buttons = {}
        for face in self.FACE_NAMES:
            label = self.FACE_LABELS[face]
            btn = tk.Button(frame, text=label, width=18,
                            command=lambda f=face: self.select_face(f),
                            bg="#3b3b55", fg="#ddd", relief=tk.FLAT,
                            activebackground="#50507a", font=("Arial", 10), anchor="w", padx=8)
            btn.pack(fill=tk.X, padx=4, pady=2)
            self.face_buttons[face] = btn

        self.face_buttons["front"].configure(bg="#0078d4")

        ttk.Separator(frame, orient="horizontal").pack(fill=tk.X, padx=4, pady=10)

        # Быстрые действия
        tk.Label(frame, text="Быстрые действия:", bg="#1e1e2e", fg="#aaa",
                 font=("Arial", 9)).pack(anchor="w", padx=8)

        for text, cmd in [
            ("📋 Копировать → все", self.copy_to_all_faces),
            ("📋 Копировать → бока", self.copy_to_side_faces),
            ("🔄 Повернуть 90°→", lambda: self.rotate_face(90)),
            ("↔ Отразить гориз.", lambda: self.flip_face("h")),
            ("↕ Отразить верт.", lambda: self.flip_face("v")),
        ]:
            tk.Button(frame, text=text, command=cmd,
                      bg="#3b3b55", fg="#ccc", relief=tk.FLAT, font=("Arial", 8),
                      activebackground="#50507a", anchor="w", padx=6).pack(fill=tk.X, padx=4, pady=1)

    # ---------- ХОЛСТ РИСОВАНИЯ ----------

    def build_canvas_area(self, parent):
        frame = tk.Frame(parent, bg="#111122", relief=tk.SUNKEN, bd=2)
        frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4, pady=4)

        self.face_title_var = tk.StringVar(value=self.FACE_LABELS[self.current_face])
        tk.Label(frame, textvariable=self.face_title_var, font=("Arial", 12, "bold"),
                 bg="#111122", fg="#7cacf8").pack(pady=4)

        canvas_size = self.texture_size * self.pixel_size + 1
        self.canvas = tk.Canvas(frame, bg="#111122", width=canvas_size, height=canvas_size,
                                cursor="crosshair", highlightthickness=0)
        self.canvas.pack(expand=True, pady=4)

        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Button-3>", self.on_right_click)
        self.canvas.bind("<Motion>", self.on_move)

    # ---------- 3D ПРЕВЬЮ ----------

    def build_3d_preview(self, parent):
        frame = tk.Frame(parent, bg="#1e1e2e")
        frame.pack(side=tk.LEFT, fill=tk.Y, padx=8)

        tk.Label(frame, text="🧊 3D Превью", font=("Arial", 11, "bold"),
                 bg="#1e1e2e", fg="#e0e0e0").pack(pady=6)

        self.preview_3d_canvas = tk.Canvas(frame, width=240, height=260, bg="#111122",
                                           highlightthickness=1, highlightbackground="#444")
        self.preview_3d_canvas.pack(pady=4)

        # Вращение 3D
        rot_frame = tk.Frame(frame, bg="#1e1e2e")
        rot_frame.pack(pady=4)
        self.rot_x = tk.DoubleVar(value=25)
        self.rot_y = tk.DoubleVar(value=-35)

        tk.Label(rot_frame, text="Гориз:", bg="#1e1e2e", fg="#aaa", font=("Arial", 8)).grid(row=0, column=0)
        tk.Scale(rot_frame, from_=-180, to=180, orient=tk.HORIZONTAL, variable=self.rot_y,
                 command=lambda e: self.update_3d_preview(), bg="#1e1e2e", fg="#aaa",
                 highlightthickness=0, troughcolor="#3b3b55", length=140).grid(row=0, column=1)
        tk.Label(rot_frame, text="Верт:", bg="#1e1e2e", fg="#aaa", font=("Arial", 8)).grid(row=1, column=0)
        tk.Scale(rot_frame, from_=-90, to=90, orient=tk.HORIZONTAL, variable=self.rot_x,
                 command=lambda e: self.update_3d_preview(), bg="#1e1e2e", fg="#aaa",
                 highlightthickness=0, troughcolor="#3b3b55", length=140).grid(row=1, column=1)

        # Превью тайл
        tk.Label(frame, text="Тайл 3×3:", font=("Arial", 9), bg="#1e1e2e", fg="#aaa").pack(pady=(10, 2))
        self.tile_canvas = tk.Canvas(frame, width=150, height=150, bg="#111122",
                                     highlightthickness=1, highlightbackground="#444")
        self.tile_canvas.pack()

    # ---------- ВСЕ 6 ГРАНЕЙ МИНИ ПРЕВЬЮ ----------

    def build_all_faces_preview(self, parent):
        frame = tk.LabelFrame(parent, text="  Все грани блока  ", bg="#1e1e2e", fg="#aaa",
                              font=("Arial", 10, "bold"), relief=tk.GROOVE, bd=1)
        frame.pack(fill=tk.X, padx=8, pady=4)

        inner = tk.Frame(frame, bg="#1e1e2e")
        inner.pack(pady=6)

        self.mini_canvases = {}
        #         Top    Bottom   Front   Back    Left    Right
        layout = [
            (None, "top", None, None, None, None),
            ("left", "front", "right", "back", None, "bottom"),
        ]

        # Расположение: крестообразное
        positions = {
            "top": (0, 1),
            "left": (1, 0),
            "front": (1, 1),
            "right": (1, 2),
            "back": (1, 3),
            "bottom": (2, 1),
        }

        for face, (row, col) in positions.items():
            sub = tk.Frame(inner, bg="#1e1e2e")
            sub.grid(row=row, column=col, padx=3, pady=3)

            short = face[:1].upper() + face[1:]
            tk.Label(sub, text=short, bg="#1e1e2e", fg="#888", font=("Arial", 7)).pack()

            cv = tk.Canvas(sub, width=52, height=52, bg="#222", highlightthickness=1,
                           highlightbackground="#444", cursor="hand2")
            cv.pack()
            cv.bind("<Button-1>", lambda e, f=face: self.select_face(f))
            self.mini_canvases[face] = cv

    # ---------- ПРАВАЯ ПАНЕЛЬ (ЦВЕТА) ----------

    def build_right_panel(self, parent):
        frame = tk.Frame(parent, bg="#2a2a3d", width=210, relief=tk.RIDGE, bd=1)
        frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(4, 0))
        frame.pack_propagate(False)

        tk.Label(frame, text="🎨 Цвета", font=("Arial", 11, "bold"),
                 bg="#2a2a3d", fg="#e0e0e0").pack(pady=8)

        # Основной / вторичный
        cd = tk.Frame(frame, bg="#2a2a3d")
        cd.pack(pady=4)

        tk.Label(cd, text="Осн.", bg="#2a2a3d", fg="#ccc", font=("Arial", 8)).grid(row=0, column=0)
        self.primary_btn = tk.Button(cd, width=4, height=2, bg=self.current_color,
                                     command=self.choose_primary, relief=tk.RAISED, bd=2)
        self.primary_btn.grid(row=1, column=0, padx=4)

        tk.Button(cd, text="⇄", command=self.swap_colors, bg="#3b3b55", fg="white",
                  font=("Arial", 11)).grid(row=1, column=1)

        tk.Label(cd, text="Доп.", bg="#2a2a3d", fg="#ccc", font=("Arial", 8)).grid(row=0, column=2)
        self.secondary_btn = tk.Button(cd, width=4, height=2, bg=self.secondary_color,
                                       command=self.choose_secondary, relief=tk.RAISED, bd=2)
        self.secondary_btn.grid(row=1, column=2, padx=4)

        # HEX
        hf = tk.Frame(frame, bg="#2a2a3d")
        hf.pack(pady=4)
        tk.Label(hf, text="HEX:", bg="#2a2a3d", fg="#ccc", font=("Arial", 9)).pack(side=tk.LEFT)
        self.hex_entry = tk.Entry(hf, width=9, font=("Courier", 10))
        self.hex_entry.pack(side=tk.LEFT, padx=4)
        self.hex_entry.insert(0, self.current_color)
        self.hex_entry.bind("<Return>", self.apply_hex)

        # RGB
        self.r_var = tk.IntVar(value=181)
        self.g_var = tk.IntVar(value=80)
        self.b_var = tk.IntVar(value=60)

        for lbl, var, clr in [("R", self.r_var, "#ff5555"), ("G", self.g_var, "#55ff55"),
                               ("B", self.b_var, "#5555ff")]:
            rf = tk.Frame(frame, bg="#2a2a3d")
            rf.pack(fill=tk.X, padx=8)
            tk.Label(rf, text=lbl, bg="#2a2a3d", fg=clr, width=2, font=("Arial", 9, "bold")).pack(side=tk.LEFT)
            tk.Scale(rf, from_=0, to=255, orient=tk.HORIZONTAL, variable=var,
                     command=self.rgb_changed, bg="#2a2a3d", fg="#ccc",
                     highlightthickness=0, troughcolor="#3b3b55", length=130).pack(side=tk.LEFT)

        ttk.Separator(frame, orient="horizontal").pack(fill=tk.X, padx=4, pady=6)

        # MC палитра
        tk.Label(frame, text="MC Палитра:", bg="#2a2a3d", fg="#ccc", font=("Arial", 9)).pack()
        pf = tk.Frame(frame, bg="#2a2a3d")
        pf.pack(padx=4, pady=4)
        for i, c in enumerate(self.mc_palette):
            r, col = divmod(i, 10)
            tk.Button(pf, bg=c, width=2, height=1, relief=tk.FLAT, bd=0,
                      command=lambda cc=c: self.set_color(cc)).grid(row=r, column=col, padx=1, pady=1)

        ttk.Separator(frame, orient="horizontal").pack(fill=tk.X, padx=4, pady=4)

        # Своя палитра
        tk.Label(frame, text="Своя палитра:", bg="#2a2a3d", fg="#ccc", font=("Arial", 9)).pack()
        self.cust_pal_frame = tk.Frame(frame, bg="#2a2a3d")
        self.cust_pal_frame.pack(padx=4, pady=2)

        cpf = tk.Frame(frame, bg="#2a2a3d")
        cpf.pack()
        tk.Button(cpf, text="+ Добавить", command=self.add_custom_color,
                  bg="#3b3b55", fg="#ccc", font=("Arial", 8), relief=tk.FLAT).pack(side=tk.LEFT, padx=2)
        tk.Button(cpf, text="Из грани", command=self.extract_palette,
                  bg="#3b3b55", fg="#ccc", font=("Arial", 8), relief=tk.FLAT).pack(side=tk.LEFT, padx=2)

    # ---------- СТАТУС ----------

    def build_status_bar(self):
        sf = tk.Frame(self.root, bg="#2a2a3d", height=24)
        sf.pack(fill=tk.X, padx=4, pady=(0, 4))

        self.status_var = tk.StringVar(
            value=f"Готово | {self.texture_size}×{self.texture_size} | Грань: Front | Карандаш")
        tk.Label(sf, textvariable=self.status_var, bg="#2a2a3d", fg="#aaa",
                 anchor="w", padx=8, font=("Arial", 9)).pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.coord_var = tk.StringVar(value="X: — Y: —")
        tk.Label(sf, textvariable=self.coord_var, bg="#2a2a3d", fg="#888",
                 font=("Courier", 9), padx=8).pack(side=tk.RIGHT)

    # =============================================
    #  ПРИВЯЗКА КЛАВИШ
    # =============================================

    def bind_shortcuts(self):
        self.root.bind("<Control-z>", lambda e: self.undo())
        self.root.bind("<Control-y>", lambda e: self.redo())
        self.root.bind("<Control-s>", lambda e: self.save_atlas())
        self.root.bind("<Control-o>", lambda e: self.open_atlas())
        self.root.bind("<Control-n>", lambda e: self.new_block())
        self.root.bind("<Control-c>", lambda e: self.copy_face())
        self.root.bind("<Control-v>", lambda e: self.paste_face())
        self.root.bind("<g>", lambda e: self.toggle_grid())
        self.root.bind("<plus>", lambda e: self.zoom_in())
        self.root.bind("<equal>", lambda e: self.zoom_in())
        self.root.bind("<minus>", lambda e: self.zoom_out())
        # 1-6 выбор грани
        for i, face in enumerate(self.FACE_NAMES):
            self.root.bind(f"<F{i + 1}>", lambda e, f=face: self.select_face(f))

    # =============================================
    #  РИСОВАНИЕ ХОЛСТА
    # =============================================

    def draw_face_canvas(self):
        self.canvas.delete("all")
        pixels = self.faces[self.current_face]
        sz = self.pixel_size
        ts = self.texture_size
        csz = ts * sz

        # Шахматный фон
        hs = sz // 2
        for x in range(ts):
            for y in range(ts):
                px, py = x * sz, y * sz
                for cx in range(2):
                    for cy in range(2):
                        c = "#c0c0c0" if (cx + cy) % 2 == 0 else "#909090"
                        self.canvas.create_rectangle(px + cx * hs, py + cy * hs,
                                                     px + (cx + 1) * hs, py + (cy + 1) * hs,
                                                     fill=c, outline="")
                color = pixels.get((x, y))
                if color:
                    self.canvas.create_rectangle(px, py, px + sz, py + sz, fill=color, outline="")

        if self.grid_visible:
            for i in range(ts + 1):
                p = i * sz
                lc = "#444" if i % 4 != 0 else "#666"
                w = 1 if i % 4 != 0 else 2
                self.canvas.create_line(p, 0, p, csz, fill=lc, width=w)
                self.canvas.create_line(0, p, csz, p, fill=lc, width=w)

        self.canvas.create_rectangle(0, 0, csz, csz, outline="#666", width=2)

        self.update_mini_previews()
        self.update_3d_preview()
        self.update_tile_preview()

    # =============================================
    #  ОБРАБОТКА МЫШИ
    # =============================================

    def get_px(self, event):
        x = event.x // self.pixel_size
        y = event.y // self.pixel_size
        if 0 <= x < self.texture_size and 0 <= y < self.texture_size:
            return x, y
        return None, None

    def on_move(self, event):
        x, y = self.get_px(event)
        if x is not None:
            c = self.faces[self.current_face].get((x, y), "transparent")
            self.coord_var.set(f"X:{x} Y:{y} | {c or 'прозрачный'}")

    def on_click(self, event):
        x, y = self.get_px(event)
        if x is None:
            return
        if self.current_tool in ("line", "rectangle", "circle", "filled_rect",
                                  "filled_circle", "gradient"):
            self.drag_start = (x, y)
            return
        self.apply_tool(x, y)

    def on_drag(self, event):
        x, y = self.get_px(event)
        if x is None:
            return
        if self.current_tool in ("line", "rectangle", "circle", "filled_rect",
                                  "filled_circle", "gradient"):
            if self.drag_start:
                self.draw_face_canvas()
                self.draw_shape_preview(self.drag_start, (x, y))
            return
        if self.current_tool in ("pencil", "eraser", "brush2", "brush3", "dither", "blur"):
            self.apply_tool(x, y, save=False)

    def on_release(self, event):
        x, y = self.get_px(event)
        if self.drag_start and x is not None:
            sx, sy = self.drag_start
            if self.current_tool == "line":
                self.draw_line(sx, sy, x, y)
            elif self.current_tool == "rectangle":
                self.draw_rect(sx, sy, x, y, False)
            elif self.current_tool == "filled_rect":
                self.draw_rect(sx, sy, x, y, True)
            elif self.current_tool == "circle":
                self.draw_ellipse(sx, sy, x, y, False)
            elif self.current_tool == "filled_circle":
                self.draw_ellipse(sx, sy, x, y, True)
            elif self.current_tool == "gradient":
                self.draw_gradient(sx, sy, x, y)
            self.drag_start = None
            self.save_state()
            self.draw_face_canvas()
            return
        if self.current_tool in ("pencil", "eraser", "brush2", "brush3", "dither", "blur"):
            self.save_state()

    def on_right_click(self, event):
        x, y = self.get_px(event)
        if x is not None:
            c = self.faces[self.current_face].get((x, y))
            if c:
                self.set_color(c)

    # =============================================
    #  ИНСТРУМЕНТЫ РИСОВАНИЯ
    # =============================================

    def select_tool(self, tool):
        self.current_tool = tool
        for t, btn in self.tool_buttons.items():
            btn.configure(bg="#0078d4" if t == tool else "#3b3b55")
        names = {"pencil": "Карандаш", "fill": "Заливка", "eraser": "Ластик",
                 "eyedropper": "Пипетка", "line": "Линия", "rectangle": "Прямоуг.",
                 "circle": "Круг", "filled_rect": "Прям.(зал.)", "filled_circle": "Круг(зал.)",
                 "gradient": "Градиент", "blur": "Размытие", "replace": "Замена цвета",
                 "brush2": "Кисть 2px", "brush3": "Кисть 3px", "dither": "Дизеринг"}
        self.update_status(tool=names.get(tool, tool))

    def get_target_faces(self):
        """Возвращает список граней, на которые нужно рисовать"""
        targets = [self.current_face]
        sides = ["front", "back", "left", "right"]
        if self.link_all_faces:
            targets = list(self.FACE_NAMES)
        elif self.link_sides:
            if self.current_face in sides:
                targets = sides
        return targets

    def set_pixel(self, x, y, color):
        if not (0 <= x < self.texture_size and 0 <= y < self.texture_size):
            return
        for face in self.get_target_faces():
            self.faces[face][(x, y)] = color
            if self.symmetry_x:
                self.faces[face][(self.texture_size - 1 - x, y)] = color
            if self.symmetry_y:
                self.faces[face][(x, self.texture_size - 1 - y)] = color
            if self.symmetry_x and self.symmetry_y:
                self.faces[face][(self.texture_size - 1 - x, self.texture_size - 1 - y)] = color

    def apply_tool(self, x, y, save=True):
        pix = self.faces[self.current_face]
        if self.current_tool == "pencil":
            self.set_pixel(x, y, self.current_color)
        elif self.current_tool == "eraser":
            self.set_pixel(x, y, None)
        elif self.current_tool == "fill":
            self.flood_fill(x, y, self.current_color)
        elif self.current_tool == "eyedropper":
            c = pix.get((x, y))
            if c:
                self.set_color(c)
        elif self.current_tool == "replace":
            old = pix.get((x, y))
            if old:
                for face in self.get_target_faces():
                    for k in self.faces[face]:
                        if self.faces[face][k] == old:
                            self.faces[face][k] = self.current_color
        elif self.current_tool == "brush2":
            self._brush(x, y, 2)
        elif self.current_tool == "brush3":
            self._brush(x, y, 3)
        elif self.current_tool == "dither":
            if (x + y) % 2 == 0:
                self.set_pixel(x, y, self.current_color)
            else:
                self.set_pixel(x, y, self.secondary_color)
        elif self.current_tool == "blur":
            self._blur(x, y)

        if save and self.current_tool in ("fill", "replace"):
            self.save_state()
        self.draw_face_canvas()

    def _brush(self, cx, cy, size):
        off = size // 2
        for dx in range(-off, off + 1):
            for dy in range(-off, off + 1):
                self.set_pixel(cx + dx, cy + dy, self.current_color)

    def _blur(self, x, y):
        pix = self.faces[self.current_face]
        nb = []
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                c = pix.get((x + dx, y + dy))
                if c:
                    nb.append(c)
        if nb:
            ar = sum(int(c[1:3], 16) for c in nb) // len(nb)
            ag = sum(int(c[3:5], 16) for c in nb) // len(nb)
            ab = sum(int(c[5:7], 16) for c in nb) // len(nb)
            self.set_pixel(x, y, f"#{ar:02x}{ag:02x}{ab:02x}")

    def flood_fill(self, x, y, new_color):
        for face in self.get_target_faces():
            pix = self.faces[face]
            target = pix.get((x, y))
            if target == new_color:
                continue
            stack = [(x, y)]
            visited = set()
            while stack:
                cx, cy = stack.pop()
                if (cx, cy) in visited:
                    continue
                if not (0 <= cx < self.texture_size and 0 <= cy < self.texture_size):
                    continue
                if pix.get((cx, cy)) != target:
                    continue
                visited.add((cx, cy))
                pix[(cx, cy)] = new_color
                stack.extend([(cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)])

    # --------- ФИГУРЫ ---------

    def draw_line(self, x0, y0, x1, y1):
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            self.set_pixel(x0, y0, self.current_color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy; x0 += sx
            if e2 < dx:
                err += dx; y0 += sy

    def draw_rect(self, x0, y0, x1, y1, filled):
        mnx, mxx = min(x0, x1), max(x0, x1)
        mny, mxy = min(y0, y1), max(y0, y1)
        for x in range(mnx, mxx + 1):
            for y in range(mny, mxy + 1):
                if filled or x in (mnx, mxx) or y in (mny, mxy):
                    self.set_pixel(x, y, self.current_color)

    def draw_ellipse(self, x0, y0, x1, y1, filled):
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        rx, ry = abs(x1 - x0) / 2, abs(y1 - y0) / 2
        if rx == 0 or ry == 0:
            self.draw_line(x0, y0, x1, y1); return
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                v = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
                if (filled and v <= 1.0) or (not filled and 0.5 <= v <= 1.5):
                    self.set_pixel(x, y, self.current_color)

    def draw_gradient(self, x0, y0, x1, y1):
        r0, g0, b0 = self._hex2rgb(self.current_color)
        r1, g1, b1 = self._hex2rgb(self.secondary_color)
        mnx, mxx = min(x0, x1), max(x0, x1)
        mny, mxy = min(y0, y1), max(y0, y1)
        w = max(1, mxx - mnx)
        for x in range(mnx, mxx + 1):
            t = (x - mnx) / w
            r = int(r0 + (r1 - r0) * t)
            g = int(g0 + (g1 - g0) * t)
            b = int(b0 + (b1 - b0) * t)
            c = f"#{r:02x}{g:02x}{b:02x}"
            for y in range(mny, mxy + 1):
                self.set_pixel(x, y, c)

    def draw_shape_preview(self, start, end):
        x0, y0 = start
        x1, y1 = end
        pts = []
        if self.current_tool == "line":
            dx, dy = abs(x1 - x0), abs(y1 - y0)
            sx = 1 if x0 < x1 else -1
            sy = 1 if y0 < y1 else -1
            err = dx - dy
            px, py = x0, y0
            while True:
                pts.append((px, py))
                if px == x1 and py == y1: break
                e2 = 2 * err
                if e2 > -dy: err -= dy; px += sx
                if e2 < dx: err += dx; py += sy
        elif self.current_tool in ("rectangle", "filled_rect"):
            for x in range(min(x0, x1), max(x0, x1) + 1):
                for y in range(min(y0, y1), max(y0, y1) + 1):
                    if self.current_tool == "filled_rect" or x in (min(x0, x1), max(x0, x1)) or y in (
                    min(y0, y1), max(y0, y1)):
                        pts.append((x, y))
        elif self.current_tool in ("circle", "filled_circle"):
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            rx, ry = abs(x1 - x0) / 2, abs(y1 - y0) / 2
            if rx > 0 and ry > 0:
                for x in range(min(x0, x1), max(x0, x1) + 1):
                    for y in range(min(y0, y1), max(y0, y1) + 1):
                        v = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
                        if (self.current_tool == "filled_circle" and v <= 1.0) or (
                                self.current_tool == "circle" and 0.5 <= v <= 1.5):
                            pts.append((x, y))

        sz = self.pixel_size
        for px, py in pts:
            if 0 <= px < self.texture_size and 0 <= py < self.texture_size:
                self.canvas.create_rectangle(px * sz, py * sz, px * sz + sz, py * sz + sz,
                                             fill=self.current_color, outline="#fff", stipple="gray50")

    # =============================================
    #  ЦВЕТА
    # =============================================

    def _hex2rgb(self, h):
        return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)

    def _rgb2hex(self, r, g, b):
        return f"#{max(0, min(255, r)):02x}{max(0, min(255, g)):02x}{max(0, min(255, b)):02x}"

    def set_color(self, c):
        self.current_color = c
        self.primary_btn.configure(bg=c)
        self.hex_entry.delete(0, tk.END)
        self.hex_entry.insert(0, c)
        r, g, b = self._hex2rgb(c)
        self.r_var.set(r); self.g_var.set(g); self.b_var.set(b)

    def choose_primary(self):
        c = colorchooser.askcolor(initialcolor=self.current_color)
        if c[1]: self.set_color(c[1])

    def choose_secondary(self):
        c = colorchooser.askcolor(initialcolor=self.secondary_color)
        if c[1]:
            self.secondary_color = c[1]
            self.secondary_btn.configure(bg=c[1])

    def swap_colors(self):
        self.current_color, self.secondary_color = self.secondary_color, self.current_color
        self.primary_btn.configure(bg=self.current_color)
        self.secondary_btn.configure(bg=self.secondary_color)
        r, g, b = self._hex2rgb(self.current_color)
        self.r_var.set(r); self.g_var.set(g); self.b_var.set(b)
        self.hex_entry.delete(0, tk.END)
        self.hex_entry.insert(0, self.current_color)

    def rgb_changed(self, _=None):
        c = self._rgb2hex(self.r_var.get(), self.g_var.get(), self.b_var.get())
        self.current_color = c
        self.primary_btn.configure(bg=c)
        self.hex_entry.delete(0, tk.END)
        self.hex_entry.insert(0, c)

    def apply_hex(self, _=None):
        h = self.hex_entry.get().strip()
        if not h.startswith("#"): h = "#" + h
        try:
            if len(h) == 7:
                int(h[1:], 16)
                self.set_color(h)
        except ValueError:
            messagebox.showerror("Ошибка", "Неверный HEX!")

    def add_custom_color(self):
        if self.current_color not in self.custom_palette:
            self.custom_palette.append(self.current_color)
            i = len(self.custom_palette) - 1
            r, c = divmod(i, 10)
            tk.Button(self.cust_pal_frame, bg=self.current_color, width=2, height=1, relief=tk.FLAT,
                      command=lambda cc=self.current_color: self.set_color(cc)).grid(row=r, column=c, padx=1, pady=1)

    def extract_palette(self):
        colors = set()
        for c in self.faces[self.current_face].values():
            if c: colors.add(c)
        self.custom_palette = list(colors)
        for w in self.cust_pal_frame.winfo_children(): w.destroy()
        for i, c in enumerate(self.custom_palette):
            r, col = divmod(i, 10)
            tk.Button(self.cust_pal_frame, bg=c, width=2, height=1, relief=tk.FLAT,
                      command=lambda cc=c: self.set_color(cc)).grid(row=r, column=col, padx=1, pady=1)

    # =============================================
    #  ВЫБОР ГРАНИ
    # =============================================

    def select_face(self, face):
        self.current_face = face
        for f, btn in self.face_buttons.items():
            btn.configure(bg="#0078d4" if f == face else "#3b3b55")
        self.face_title_var.set(self.FACE_LABELS[face])
        self.update_status()
        self.draw_face_canvas()

    # =============================================
    #  ПРЕВЬЮ
    # =============================================

    def update_mini_previews(self):
        for face, cv in self.mini_canvases.items():
            img = self._face_to_pil(face)
            img = img.resize((52, 52), Image.NEAREST)
            photo = ImageTk.PhotoImage(img)
            cv.delete("all")
            cv.create_image(26, 26, image=photo)
            cv._photo = photo
            # Подсветка текущей грани
            if face == self.current_face:
                cv.configure(highlightbackground="#0078d4", highlightthickness=2)
            else:
                cv.configure(highlightbackground="#444", highlightthickness=1)

    def update_tile_preview(self):
        img = self._face_to_pil(self.current_face)
        tile = Image.new("RGBA", (self.texture_size * 3, self.texture_size * 3))
        for tx in range(3):
            for ty in range(3):
                tile.paste(img, (tx * self.texture_size, ty * self.texture_size))
        tile = tile.resize((150, 150), Image.NEAREST)
        self.tile_photo = ImageTk.PhotoImage(tile)
        self.tile_canvas.delete("all")
        self.tile_canvas.create_image(75, 75, image=self.tile_photo)

    def update_3d_preview(self):
        """Изометрическое 3D-превью блока"""
        w, h = 240, 260
        img = Image.new("RGBA", (w, h), (17, 17, 34, 255))
        draw = ImageDraw.Draw(img)

        # Получить текстуры граней
        top_img = self._face_to_pil("top").resize((64, 64), Image.NEAREST)
        front_img = self._face_to_pil("front").resize((64, 64), Image.NEAREST)
        right_img = self._face_to_pil("right").resize((64, 64), Image.NEAREST)

        rx = math.radians(self.rot_x.get())
        ry = math.radians(self.rot_y.get())

        # Рисуем простую изометрическую проекцию
        cx, cy = w // 2, h // 2
        size = 50

        # Определяем видимые грани на основе вращения
        show_front = math.cos(ry) > 0
        show_right = math.sin(ry) < 0
        show_top = math.cos(rx) > 0

        # Изометрические координаты
        cos30 = math.cos(math.radians(30))
        sin30 = math.sin(math.radians(30))

        # Вершины куба в изометрии
        def iso(x, y, z):
            sx = cx + (x - z) * cos30 * size / 50
            sy = cy - y * size / 50 + (x + z) * sin30 * size / 50
            return int(sx), int(sy)

        # 8 вершин куба
        v = {
            'ftl': iso(-1, 1, -1), 'ftr': iso(1, 1, -1),
            'fbl': iso(-1, -1, -1), 'fbr': iso(1, -1, -1),
            'btl': iso(-1, 1, 1), 'btr': iso(1, 1, 1),
            'bbl': iso(-1, -1, 1), 'bbr': iso(1, -1, 1),
        }

        # Определение видимых граней и их рисование
        faces_to_draw = []

        if show_top:
            faces_to_draw.append(('top', [v['ftl'], v['ftr'], v['btr'], v['btl']], top_img))
        else:
            faces_to_draw.append(('bottom', [v['fbl'], v['fbr'], v['bbr'], v['bbl']],
                                  self._face_to_pil("bottom").resize((64, 64), Image.NEAREST)))

        if show_front:
            faces_to_draw.append(('front', [v['ftl'], v['ftr'], v['fbr'], v['fbl']], front_img))
        else:
            faces_to_draw.append(('back', [v['btl'], v['btr'], v['bbr'], v['bbl']],
                                  self._face_to_pil("back").resize((64, 64), Image.NEAREST)))

        if show_right:
            faces_to_draw.append(('left', [v['ftl'], v['btl'], v['bbl'], v['fbl']],
                                  self._face_to_pil("left").resize((64, 64), Image.NEAREST)))
        else:
            faces_to_draw.append(('right', [v['ftr'], v['btr'], v['bbr'], v['fbr']], right_img))

        # Рисуем грани с затенением
        shade_map = {'top': 1.0, 'bottom': 0.5, 'front': 0.8, 'back': 0.6, 'left': 0.6, 'right': 0.7}

        for face_name, quad, tex in faces_to_draw:
            shade = shade_map.get(face_name, 0.8)
            # Получить средний цвет текстуры для заливки полигона
            avg_colors = []
            for px in range(0, 64, 8):
                for py in range(0, 64, 8):
                    pixel = tex.getpixel((px, py))
                    if pixel[3] > 0:
                        avg_colors.append(pixel[:3])

            if avg_colors:
                ar = int(sum(c[0] for c in avg_colors) / len(avg_colors) * shade)
                ag = int(sum(c[1] for c in avg_colors) / len(avg_colors) * shade)
                ab = int(sum(c[2] for c in avg_colors) / len(avg_colors) * shade)
            else:
                ar, ag, ab = 60, 60, 60

            fill_color = f"#{ar:02x}{ag:02x}{ab:02x}"
            points = []
            for p in quad:
                points.extend(p)

            if len(points) >= 6:
                draw.polygon(points, fill=(ar, ag, ab, 255), outline=(40, 40, 40, 255))

            # Нарисовать пиксели текстуры на грани
            if len(quad) == 4:
                self._draw_textured_quad(draw, quad, tex, shade)

        self.preview_3d_photo = ImageTk.PhotoImage(img)
        self.preview_3d_canvas.delete("all")
        self.preview_3d_canvas.create_image(w // 2, h // 2, image=self.preview_3d_photo)

    def _draw_textured_quad(self, draw, quad, tex, shade):
        """Рисует текстуру на четырёхугольнике с помощью билинейной интерполяции"""
        # Находим bounding box
        xs = [p[0] for p in quad]
        ys = [p[1] for p in quad]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        # Для каждого пикселя в bounding box проверяем, внутри ли он quad
        w = max(1, max_x - min_x)
        h = max(1, max_y - min_y)

        # Простое текстурирование
        tex_w, tex_h = tex.size
        for sy in range(max(0, min_y), min(260, max_y + 1)):
            for sx in range(max(0, min_x), min(240, max_x + 1)):
                # Биллинейная интерполяция UV координат
                if w > 0 and h > 0:
                    u = (sx - min_x) / w
                    v = (sy - min_y) / h
                    tx = int(u * (tex_w - 1))
                    ty = int(v * (tex_h - 1))
                    tx = max(0, min(tex_w - 1, tx))
                    ty = max(0, min(tex_h - 1, ty))

                    pixel = tex.getpixel((tx, ty))
                    if pixel[3] > 0:
                        r = int(pixel[0] * shade)
                        g = int(pixel[1] * shade)
                        b = int(pixel[2] * shade)
                        # Проверка внутри полигона (упрощённо)
                        if self._point_in_quad(sx, sy, quad):
                            draw.point((sx, sy), fill=(r, g, b, 255))

    def _point_in_quad(self, px, py, quad):
        """Проверка точки внутри четырёхугольника"""
        n = len(quad)
        inside = False
        j = n - 1
        for i in range(n):
            xi, yi = quad[i]
            xj, yj = quad[j]
            if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi + 0.001) + xi):
                inside = not inside
            j = i
        return inside

    def _face_to_pil(self, face):
        """Конвертировать грань в PIL Image"""
        img = Image.new("RGBA", (self.texture_size, self.texture_size), (0, 0, 0, 0))
        pix = self.faces[face]
        for (x, y), c in pix.items():
            if c:
                r, g, b = self._hex2rgb(c)
                img.putpixel((x, y), (r, g, b, 255))
        return img

    # =============================================
    #  ИСТОРИЯ
    # =============================================

    def save_state(self):
        state = {}
        for face in self.FACE_NAMES:
            state[face] = dict(self.faces[face])
        self.history = self.history[:self.history_index + 1]
        self.history.append(state)
        if len(self.history) > self.max_history:
            self.history.pop(0)
        self.history_index = len(self.history) - 1

    def undo(self):
        if self.history_index > 0:
            self.history_index -= 1
            state = self.history[self.history_index]
            for face in self.FACE_NAMES:
                self.faces[face] = dict(state[face])
            self.draw_face_canvas()

    def redo(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            state = self.history[self.history_index]
            for face in self.FACE_NAMES:
                self.faces[face] = dict(state[face])
            self.draw_face_canvas()

    # =============================================
    #  ФАЙЛОВЫЕ ОПЕРАЦИИ
    # =============================================

    def new_block(self):
        if messagebox.askyesno("Новый блок", "Создать новый блок? Несохранённые данные будут потеряны."):
            for face in self.FACE_NAMES:
                for x in range(self.texture_size):
                    for y in range(self.texture_size):
                        self.faces[face][(x, y)] = None
            self.history = []
            self.history_index = -1
            self.save_state()
            self.draw_face_canvas()

    def open_single_png(self):
        """Открыть один PNG и загрузить в текущую грань"""
        fp = filedialog.askopenfilename(filetypes=[("PNG", "*.png")])
        if not fp: return
        try:
            img = Image.open(fp).convert("RGBA")
            if img.width != img.height:
                messagebox.showwarning("Предупреждение", "Текстура не квадратная, будет обрезана")
            sz = min(img.width, img.height)
            if sz != self.texture_size:
                self.resize_texture(sz)
            for x in range(sz):
                for y in range(sz):
                    r, g, b, a = img.getpixel((x, y))
                    self.faces[self.current_face][(x, y)] = self._rgb2hex(r, g, b) if a > 0 else None
            self.save_state()
            self.draw_face_canvas()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def open_atlas(self):
        """
        Открыть атлас — PNG с 6 гранями.
        Расположение (3×2):
        top    | bottom
        front  | back
        left   | right
        """
        fp = filedialog.askopenfilename(filetypes=[("PNG", "*.png")])
        if not fp: return
        try:
            img = Image.open(fp).convert("RGBA")
            # Определяем размер грани
            # Пробуем 3×2 (ш×в) или 2×3
            w, h = img.width, img.height

            if w > h:
                # 3 колонки, 2 ряда
                face_w = w // 3
                face_h = h // 2
                layout = [
                    ("top", 0, 0), ("front", 1, 0), ("right", 2, 0),
                    ("bottom", 0, 1), ("back", 1, 1), ("left", 2, 1),
                ]
            elif h > w:
                # 2 колонки, 3 ряда
                face_w = w // 2
                face_h = h // 3
                layout = [
                    ("top", 0, 0), ("bottom", 1, 0),
                    ("front", 0, 1), ("back", 1, 1),
                    ("left", 0, 2), ("right", 1, 2),
                ]
            else:
                # Квадрат — одна текстура на все грани
                face_w = w
                face_h = h
                layout = [(f, 0, 0) for f in self.FACE_NAMES]

            sz = min(face_w, face_h)
            if sz != self.texture_size:
                self.resize_texture(sz)

            for face, col, row in layout:
                for x in range(sz):
                    for y in range(sz):
                        px = col * face_w + x
                        py = row * face_h + y
                        if px < w and py < h:
                            r, g, b, a = img.getpixel((px, py))
                            self.faces[face][(x, y)] = self._rgb2hex(r, g, b) if a > 0 else None

            self.save_state()
            self.draw_face_canvas()
            messagebox.showinfo("Открыто", f"Атлас загружен: {os.path.basename(fp)}")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def open_project(self):
        """Открыть JSON проект"""
        fp = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not fp: return
        try:
            with open(fp, "r") as f:
                data = json.load(f)
            sz = data.get("size", 16)
            if sz != self.texture_size:
                self.resize_texture(sz)
            for face in self.FACE_NAMES:
                face_data = data.get(face, {})
                for key, val in face_data.items():
                    x, y = map(int, key.split(","))
                    self.faces[face][(x, y)] = val
            self.save_state()
            self.draw_face_canvas()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def save_atlas(self):
        """
        Сохранить атлас 3×2:
        top    | front  | right
        bottom | back   | left
        """
        fp = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")])
        if not fp: return
        try:
            sz = self.texture_size
            atlas = Image.new("RGBA", (sz * 3, sz * 2), (0, 0, 0, 0))
            layout = [
                ("top", 0, 0), ("front", 1, 0), ("right", 2, 0),
                ("bottom", 0, 1), ("back", 1, 1), ("left", 2, 1),
            ]
            for face, col, row in layout:
                face_img = self._face_to_pil(face)
                atlas.paste(face_img, (col * sz, row * sz))
            atlas.save(fp, "PNG")
            messagebox.showinfo("Сохранено", f"Атлас сохранён: {fp}\n\nРасположение:\ntop | front | right\nbottom | back | left")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def save_faces_separate(self):
        """Сохранить каждую грань отдельным PNG"""
        folder = filedialog.askdirectory(title="Выберите папку")
        if not folder: return
        name = simpledialog.askstring("Имя блока", "Базовое имя файлов:", initialvalue="block")
        if not name: return
        try:
            for face in self.FACE_NAMES:
                img = self._face_to_pil(face)
                path = os.path.join(folder, f"{name}_{face}.png")
                img.save(path, "PNG")
            messagebox.showinfo("Сохранено", f"6 файлов сохранены в:\n{folder}")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def save_project(self):
        """Сохранить проект как JSON"""
        fp = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not fp: return
        try:
            data = {"size": self.texture_size}
            for face in self.FACE_NAMES:
                face_data = {}
                for (x, y), c in self.faces[face].items():
                    if c:
                        face_data[f"{x},{y}"] = c
                data[face] = face_data
            with open(fp, "w") as f:
                json.dump(data, f)
            messagebox.showinfo("Сохранено", f"Проект сохранён: {fp}")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def export_resourcepack(self):
        """Экспорт полного ресурспака с моделью блока"""
        folder = filedialog.askdirectory(title="Папка для ресурспака")
        if not folder: return

        pack_name = simpledialog.askstring("Имя", "Имя ресурспака:", initialvalue="my_block_pack")
        if not pack_name: return
        block_name = simpledialog.askstring("Блок", "Имя блока (латиница):", initialvalue="custom_block")
        if not block_name: return

        try:
            base = os.path.join(folder, pack_name)
            tex_dir = os.path.join(base, "assets", "minecraft", "textures", "block")
            model_dir = os.path.join(base, "assets", "minecraft", "models", "block")
            bs_dir = os.path.join(base, "assets", "minecraft", "blockstates")
            os.makedirs(tex_dir, exist_ok=True)
            os.makedirs(model_dir, exist_ok=True)
            os.makedirs(bs_dir, exist_ok=True)

            # pack.mcmeta
            with open(os.path.join(base, "pack.mcmeta"), "w") as f:
                json.dump({"pack": {"pack_format": 15,
                                    "description": f"Block texture pack: {block_name}"}}, f, indent=2)

            # Проверяем, все ли грани одинаковы
            all_same = all(
                self.faces[f] == self.faces["front"] for f in self.FACE_NAMES
            )
            top_bottom_same = self.faces["top"] == self.faces["bottom"]
            sides_same = all(
                self.faces[f] == self.faces["front"] for f in ["back", "left", "right"]
            )

            if all_same:
                # Одна текстура
                self._face_to_pil("front").save(os.path.join(tex_dir, f"{block_name}.png"), "PNG")
                model = {
                    "parent": "minecraft:block/cube_all",
                    "textures": {"all": f"minecraft:block/{block_name}"}
                }
            elif sides_same and top_bottom_same:
                # Верх/низ + бок
                self._face_to_pil("top").save(os.path.join(tex_dir, f"{block_name}_top.png"), "PNG")
                self._face_to_pil("front").save(os.path.join(tex_dir, f"{block_name}_side.png"), "PNG")
                model = {
                    "parent": "minecraft:block/cube_column",
                    "textures": {
                        "end": f"minecraft:block/{block_name}_top",
                        "side": f"minecraft:block/{block_name}_side"
                    }
                }
            elif sides_same:
                # Верх + низ + бок
                self._face_to_pil("top").save(os.path.join(tex_dir, f"{block_name}_top.png"), "PNG")
                self._face_to_pil("bottom").save(os.path.join(tex_dir, f"{block_name}_bottom.png"), "PNG")
                self._face_to_pil("front").save(os.path.join(tex_dir, f"{block_name}_side.png"), "PNG")
                model = {
                    "parent": "minecraft:block/cube_bottom_top",
                    "textures": {
                        "top": f"minecraft:block/{block_name}_top",
                        "bottom": f"minecraft:block/{block_name}_bottom",
                        "side": f"minecraft:block/{block_name}_side"
                    }
                }
            else:
                # Все 6 разные
                for face in self.FACE_NAMES:
                    self._face_to_pil(face).save(os.path.join(tex_dir, f"{block_name}_{face}.png"), "PNG")

                mc_face_map = {
                    "top": "up", "bottom": "down",
                    "front": "south", "back": "north",
                    "left": "west", "right": "east"
                }
                textures = {}
                for face in self.FACE_NAMES:
                    mc_name = mc_face_map[face]
                    textures[mc_name] = f"minecraft:block/{block_name}_{face}"

                model = {
                    "parent": "minecraft:block/cube",
                    "textures": textures
                }

            with open(os.path.join(model_dir, f"{block_name}.json"), "w") as f:
                json.dump(model, f, indent=2)

            # blockstates
            blockstate = {
                "variants": {
                    "": {"model": f"minecraft:block/{block_name}"}
                }
            }
            with open(os.path.join(bs_dir, f"{block_name}.json"), "w") as f:
                json.dump(blockstate, f, indent=2)

            messagebox.showinfo("Экспорт", f"Ресурспак создан: {base}\n\n"
                                            f"Структура:\n"
                                            f"├── pack.mcmeta\n"
                                            f"└── assets/minecraft/\n"
                                            f"    ├── textures/block/{block_name}*.png\n"
                                            f"    ├── models/block/{block_name}.json\n"
                                            f"    └── blockstates/{block_name}.json\n\n"
                                            f"Скопируйте в .minecraft/resourcepacks/")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    # =============================================
    #  ОПЕРАЦИИ С ГРАНЯМИ
    # =============================================

    def copy_face(self):
        self.clipboard = dict(self.faces[self.current_face])
        self.clipboard_face = self.current_face
        self.update_status(msg="Грань скопирована")

    def paste_face(self):
        if self.clipboard:
            self.faces[self.current_face] = dict(self.clipboard)
            self.save_state()
            self.draw_face_canvas()

    def copy_to_all_faces(self):
        src = dict(self.faces[self.current_face])
        for f in self.FACE_NAMES:
            self.faces[f] = dict(src)
        self.save_state()
        self.draw_face_canvas()

    def copy_to_side_faces(self):
        src = dict(self.faces[self.current_face])
        for f in ["front", "back", "left", "right"]:
            self.faces[f] = dict(src)
        self.save_state()
        self.draw_face_canvas()

    def clear_current_face(self):
        for x in range(self.texture_size):
            for y in range(self.texture_size):
                self.faces[self.current_face][(x, y)] = None
        self.save_state()
        self.draw_face_canvas()

    def clear_all_faces(self):
        if messagebox.askyesno("Очистить", "Очистить все 6 граней?"):
            for f in self.FACE_NAMES:
                for x in range(self.texture_size):
                    for y in range(self.texture_size):
                        self.faces[f][(x, y)] = None
            self.save_state()
            self.draw_face_canvas()

    def fill_current_face(self):
        for f in self.get_target_faces():
            for x in range(self.texture_size):
                for y in range(self.texture_size):
                    self.faces[f][(x, y)] = self.current_color
        self.save_state()
        self.draw_face_canvas()

    # =============================================
    #  ПРЕОБРАЗОВАНИЯ ГРАНИ
    # =============================================

    def rotate_face(self, angle):
        for f in self.get_target_faces():
            new = {}
            for (x, y), c in self.faces[f].items():
                if angle == 90:
                    nx, ny = self.texture_size - 1 - y, x
                elif angle == -90:
                    nx, ny = y, self.texture_size - 1 - x
                else:
                    nx, ny = self.texture_size - 1 - x, self.texture_size - 1 - y
                new[(nx, ny)] = c
            self.faces[f] = new
        self.save_state()
        self.draw_face_canvas()

    def flip_face(self, direction):
        for f in self.get_target_faces():
            new = {}
            for (x, y), c in self.faces[f].items():
                if direction == "h":
                    new[(self.texture_size - 1 - x, y)] = c
                else:
                    new[(x, self.texture_size - 1 - y)] = c
            self.faces[f] = new
        self.save_state()
        self.draw_face_canvas()

    def shift_face(self, dx, dy):
        for f in self.get_target_faces():
            new = {}
            for (x, y), c in self.faces[f].items():
                nx = (x + dx) % self.texture_size
                ny = (y + dy) % self.texture_size
                new[(nx, ny)] = c
            self.faces[f] = new
        self.save_state()
        self.draw_face_canvas()

    # =============================================
    #  ФИЛЬТРЫ
    # =============================================

    def adjust_brightness(self, amount):
        for f in self.get_target_faces():
            for k, c in self.faces[f].items():
                if c:
                    r, g, b = self._hex2rgb(c)
                    self.faces[f][k] = self._rgb2hex(r + amount, g + amount, b + amount)
        self.save_state()
        self.draw_face_canvas()

    def grayscale_face(self):
        for f in self.get_target_faces():
            for k, c in self.faces[f].items():
                if c:
                    r, g, b = self._hex2rgb(c)
                    gray = int(0.299 * r + 0.587 * g + 0.114 * b)
                    self.faces[f][k] = self._rgb2hex(gray, gray, gray)
        self.save_state()
        self.draw_face_canvas()

    def invert_face(self):
        for f in self.get_target_faces():
            for k, c in self.faces[f].items():
                if c:
                    r, g, b = self._hex2rgb(c)
                    self.faces[f][k] = self._rgb2hex(255 - r, 255 - g, 255 - b)
        self.save_state()
        self.draw_face_canvas()

    def noise_face(self):
        for f in self.get_target_faces():
            for k, c in self.faces[f].items():
                if c:
                    r, g, b = self._hex2rgb(c)
                    self.faces[f][k] = self._rgb2hex(
                        r + random.randint(-15, 15),
                        g + random.randint(-15, 15),
                        b + random.randint(-15, 15))
        self.save_state()
        self.draw_face_canvas()

    # =============================================
    #  ВИД
    # =============================================

    def toggle_grid(self):
        self.grid_visible = not self.grid_visible
        self.draw_face_canvas()

    def zoom_in(self):
        if self.pixel_size < 48:
            self.pixel_size += 4
            cs = self.texture_size * self.pixel_size + 1
            self.canvas.configure(width=cs, height=cs)
            self.draw_face_canvas()

    def zoom_out(self):
        if self.pixel_size > 6:
            self.pixel_size -= 4
            cs = self.texture_size * self.pixel_size + 1
            self.canvas.configure(width=cs, height=cs)
            self.draw_face_canvas()

    def resize_texture(self, new_size):
        old = self.texture_size
        self.texture_size = new_size

        for face in self.FACE_NAMES:
            old_pix = dict(self.faces[face])
            self.faces[face] = {}
            for x in range(new_size):
                for y in range(new_size):
                    self.faces[face][(x, y)] = old_pix.get((x, y))

        if self.pixel_size * new_size > 700:
            self.pixel_size = max(4, 500 // new_size)

        cs = self.texture_size * self.pixel_size + 1
        self.canvas.configure(width=cs, height=cs)
        self.save_state()
        self.draw_face_canvas()
        self.update_status()

    def custom_resize(self):
        sz = simpledialog.askinteger("Размер", "Введите размер:", minvalue=4, maxvalue=256,
                                     initialvalue=self.texture_size)
        if sz:
            self.resize_texture(sz)

    # =============================================
    #  ШАБЛОНЫ
    # =============================================

    def _fill_face(self, face, gen_func):
        for x in range(self.texture_size):
            for y in range(self.texture_size):
                self.faces[face][(x, y)] = gen_func(x, y)

    def _rnd_shade(self, base_r, base_g, base_b, var=15):
        return self._rgb2hex(
            base_r + random.randint(-var, var),
            base_g + random.randint(-var, var),
            base_b + random.randint(-var, var))

    def tpl_stone(self):
        for f in self.FACE_NAMES:
            self._fill_face(f, lambda x, y: self._rnd_shade(128, 128, 128, 15))
        self.save_state(); self.draw_face_canvas()

    def tpl_dirt(self):
        for f in self.FACE_NAMES:
            self._fill_face(f, lambda x, y: self._rnd_shade(134, 96, 67, 18))
        self.save_state(); self.draw_face_canvas()

    def tpl_sand(self):
        for f in self.FACE_NAMES:
            self._fill_face(f, lambda x, y: self._rnd_shade(219, 207, 163, 15))
        self.save_state(); self.draw_face_canvas()

    def tpl_cobblestone(self):
        for f in self.FACE_NAMES:
            def gen(x, y):
                block = ((x // 4) + (y // 3)) % 3
                bases = [(120, 120, 120), (140, 140, 140), (100, 100, 100)]
                return self._rnd_shade(*bases[block], 12)
            self._fill_face(f, gen)
        self.save_state(); self.draw_face_canvas()

    def tpl_grass(self):
        # Верх — зелёный
        self._fill_face("top", lambda x, y: self._rnd_shade(90, 160, 50, 20))
        # Низ — земля
        self._fill_face("bottom", lambda x, y: self._rnd_shade(134, 96, 67, 18))
        # Бока — земля + трава сверху
        for f in ["front", "back", "left", "right"]:
            def gen_side(x, y):
                if y < 3:
                    return self._rnd_shade(90, 160, 50, 20)
                elif y < 5:
                    return self._rnd_shade(110, 120, 60, 15)
                else:
                    return self._rnd_shade(134, 96, 67, 18)
            self._fill_face(f, gen_side)
        self.save_state(); self.draw_face_canvas()

    def tpl_wood_log(self):
        # Верх/низ — кольца
        for f in ["top", "bottom"]:
            def gen_ring(x, y):
                cx, cy = self.texture_size / 2, self.texture_size / 2
                dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                ring = int(dist) % 3
                if ring == 0:
                    return self._rnd_shade(180, 140, 80, 10)
                elif ring == 1:
                    return self._rnd_shade(160, 120, 65, 10)
                else:
                    return self._rnd_shade(140, 100, 50, 10)
            self._fill_face(f, gen_ring)
        # Бока — кора
        for f in ["front", "back", "left", "right"]:
            def gen_bark(x, y):
                if y % 4 == 0:
                    return self._rnd_shade(80, 55, 30, 10)
                return self._rnd_shade(100, 70, 40, 12)
            self._fill_face(f, gen_bark)
        self.save_state(); self.draw_face_canvas()

    def tpl_planks(self):
        for f in self.FACE_NAMES:
            def gen(x, y):
                base = self._rnd_shade(188, 152, 98, 12)
                if x % 4 == 0:
                    return self._rnd_shade(155, 120, 70, 8)
                return base
            self._fill_face(f, gen)
        self.save_state(); self.draw_face_canvas()

    def tpl_brick(self):
        for f in self.FACE_NAMES:
            def gen(x, y):
                if y % 4 == 0:
                    return self._rnd_shade(142, 142, 134, 8)
                row = y // 4
                offset = 4 if row % 2 == 0 else 0
                if (x + offset) % 8 == 0 and y % 4 != 0:
                    return self._rnd_shade(142, 142, 134, 8)
                return self._rnd_shade(181, 80, 60, 12)
            self._fill_face(f, gen)
        self.save_state(); self.draw_face_canvas()

    def tpl_iron_ore(self):
        for f in self.FACE_NAMES:
            def gen(x, y):
                # Случайные пятна руды
                if random.random() < 0.12:
                    return self._rnd_shade(210, 190, 160, 15)
                return self._rnd_shade(128, 128, 128, 15)
            self._fill_face(f, gen)
        self.save_state(); self.draw_face_canvas()

    def tpl_tnt(self):
        # Верх — белый с кругом
        def gen_top(x, y):
            cx, cy = self.texture_size / 2, self.texture_size / 2
            if math.sqrt((x - cx) ** 2 + (y - cy) ** 2) < self.texture_size / 3:
                return self._rnd_shade(60, 60, 60, 8)
            return self._rnd_shade(200, 200, 200, 10)
        self._fill_face("top", gen_top)

        # Низ
        self._fill_face("bottom", lambda x, y: self._rnd_shade(200, 200, 200, 10))

        # Бока — красный с надписью
        for f in ["front", "back", "left", "right"]:
            def gen_side(x, y):
                if 5 <= y <= 10:
                    return self._rnd_shade(30, 30, 30, 5)
                return self._rnd_shade(200, 50, 40, 12)
            self._fill_face(f, gen_side)
        self.save_state(); self.draw_face_canvas()

    # =============================================
    #  УТИЛИТЫ
    # =============================================

    def update_status(self, tool=None, msg=None):
        t = tool or self.current_tool
        face_name = self.FACE_LABELS[self.current_face].split("(")[0].strip()
        s = f"{self.texture_size}×{self.texture_size} | Грань: {face_name} | Инстр.: {t}"
        if msg:
            s += f" | {msg}"
        self.status_var.set(s)


# =============================================
#  ЗАПУСК
# =============================================

if __name__ == "__main__":
    root = tk.Tk()
    app = MinecraftBlockTexturePainter(root)
    root.mainloop()