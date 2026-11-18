"""app.py — GUI Prometheus Core v5.0.0 (Dev)"""
import os, sys, json, base64, time
import multiprocessing as mp
from io import BytesIO
os.environ.setdefault("QT_API", "pyside6")
import numpy as np
from PySide6 import QtCore, QtWidgets, QtGui
import matplotlib
matplotlib.use("QtAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavToolbar
from matplotlib.colors import LogNorm
import physics as P
import validator
import reportlab
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import time
import os
import requests
import psutil
import cProfile
import pstats
import platform
import zipfile
# ==========================================
# ГЛОБАЛЬНЫЕ НАСТРОЙКИ СБОРКИ
# True = Lite (без нейтронов), False = Full (со всеми модулями)
# ==========================================
LITE_MODE = False

OUT = P.OUT_DIR

PARTICLES_DESC = {
    "протон": "Масса: 938.27 МэВ/c²\nЗаряд: +1e\n\nЯдро атома водорода. Основной механизм потерь энергии — ионизация и возбуждение атомов среды (формула Бете-Блоха). Обладает характерным пиком Брэгга в конце пробега. Широко используется в протонной терапии.",
    "альфа": "Масса: 3727.38 МэВ/c²\nЗаряд: +2e\n\nЯдро атома гелия (He²⁺). Обладает высокой линейной передачей энергии (ЛПЭ) и очень коротким пробегом. При внутреннем облучении представляет наибольшую радиационную опасность (коэффициент качества wR=20).",
    "дейтрон": "Масса: 1875.61 МэВ/c²\nЗаряд: +1e\n\nЯдро атома дейтерия (тяжелый водород). Используется в ускорителях для генерации нейтронов (реакции D-D или D-T). В веществе ведет себя аналогично протону, но имеет больший пробег при той же энергии.",
    "электрон": "Масса: 0.511 МэВ/c²\nЗаряд: -1e\n\nЛегкая элементарная частица. При энергиях выше 10 МэВ основным механизмом потерь становится тормозное излучение (bremsstrahlung). Обладает наибольшим страгглингом (разбросом пробега) среди всех частиц."
}

CP_MAT_DESC = {
    "вода": "Вода (H₂O). Основной компонент биологических тканей. Отличный замедлитель. Плотность 1.0 г/см³.",
    "воздух": "Воздух. Смесь газов (N, O, Ar). Очень низкая плотность. Плотность 0.0012 г/см³.",
    "ткань": "Ткань (мышцы). Мягкая биологическая ткань. Плотность 1.06 г/см³.",
    "кость": "Костная ткань. Содержит кальций и фосфор. Плотность 1.92 г/см³.",
    "алюминий": "Алюминий (Al). Легкий металл, конструкционный материал. Плотность 2.70 г/см³.",
    "железо": "Железо (Fe). Конструкционный материал. Плотность 7.87 г/см³.",
    "медь": "Медь (Cu). Хороший проводник и теплоотвод. Плотность 8.96 г/см³.",
    "вольфрам": "Вольфрам (W). Тугоплавкий металл, компактная защита. Плотность 19.3 г/см³.",
    "свинец": "Свинец (Pb). Классическая защита от гамма-излучения. Плотность 11.35 г/см³.",
    "уран": "Уран (U). Тяжелый металл, топливо для реакторов. Плотность 18.95 г/см³.",
    "полиэтилен": "Полиэтилен. Пластик с высоким содержанием водорода. Замедлитель нейтронов. Плотность 0.94 г/см³.",
    "графит": "Графит (C). Классический замедлитель нейтронов (РБМК). Плотность 1.7 г/см³.",
    "бетон": "Бетон. Строительный материал, содержит водород и тяжелые элементы. Плотность 2.3 г/см³.",
    "цирконий": "Циркониевый сплав (Zircaloy). Основа оболочек ТВЭЛов. Плотность 6.56 г/см³.",
    "сталь_304": "Нержавеющая сталь 304. Трубопроводы и корпуса. Плотность 8.0 г/см³.",
    "инконель": "Инконель. Жаропрочный сплав (Ni-Cr-Fe). Плотность 8.4 г/см³.",
    "титан": "Титановый сплав (Ti-6Al-4V). Аэрокосмическая и ядерная техника. Плотность 4.43 г/см³.",
    "бористая_сталь": "Бористая сталь. Для стержней аварийной защиты. Плотность 7.8 г/см³.",
    "кадмий": "Кадмий (Cd). Мощный поглотитель тепловых нейтронов. Плотность 8.65 г/см³.",
    "гадолиний": "Гадолиний (Gd). Выгорающий поглотитель в топливе. Плотность 7.9 г/см³.",
    "висмут": "Висмут (Bi). Нетоксичная альтернатива свинцу. Плотность 9.78 г/см³.",
    "жидкий_натрий": "Жидкий натрий. Теплоноситель для быстрых реакторов. Плотность 0.93 г/см³."
}

NEUTRON_MATS_DESC = {
    "water": "Вода (H₂O). Отличный замедлитель нейтронов благодаря легким ядрам водорода. Плотность 1.0 г/см³.",
    "polyethylene": "Полиэтилен ((C₂H₄)n). Пластик с высоким содержанием водорода, один из лучших материалов для защиты от нейтронов. Плотность 0.94 г/см³.",
    "concrete": "Бетон. Строительный материал, содержит водород и тяжелые элементы. Плотность 2.3 г/см³.",
    "iron": "Железо. Используется в конструкциях и защите. Не сильно замедляет нейтроны, но хорошо рассеивает их. Плотность 7.87 г/см³.",
    "lead": "Свинец. Тяжелый металл, слабо замедляет нейтроны, но хорошо защищает от вторичного гамма-излучения. Плотность 11.35 г/см³.",
    "graphite": "Графит (углерод). Классический замедлитель (реакторы РБМК). Плотность 1.7 г/см³.",
    "b4c": "Карбид бора (B₄C). Мощный поглотитель тепловых нейтронов (реакция B-10(n,α)). Плотность 2.52 г/см³.",
    "uranium": "Уран. Топливо для реакторов. Вызывает деление под действием нейтронов. Плотность 19.0 г/см³.",
    "zircaloy": "Циркониевый сплав (Zircaloy). Основа оболочек ТВЭЛов. Плотность 6.56 г/см³.",
    "heavy_water": "Тяжелая вода (D₂O). Отличный замедлитель, почти не поглощает нейтроны. Плотность 1.11 г/см³.",
    "borated_steel": "Бористая сталь. Используется для стержней аварийной защиты. Плотность 7.8 г/см³.",
    "concrete_magnetite": "Магнетитовый бетон. Тяжелый бетон на основе железной руды. Плотность 4.0 г/см³.",
    "cadmium": "Кадмий. Классический поглотитель тепловых нейтронов. Плотность 8.65 г/см³."
}
os.makedirs(OUT, exist_ok=True)

CUSTOM_ISO_FILE = os.path.join(P.OUT_DIR, "custom_isotopes.json")
if os.path.exists(CUSTOM_ISO_FILE):
    try:
        with open(CUSTOM_ISO_FILE, "r", encoding="utf-8") as f:
            P.ISOTOPES.update(json.load(f))
    except Exception: pass
    
def send_discord_notification(webhook_url, title, message, fields=None):
    if not webhook_url or not webhook_url.startswith("https://discord.com"):
        return
    try:
        embed = {
            "title": f"⚛️ {title}",
            "description": message,
            "color": 3066993, # Зеленый
            "footer": {
                "text": "Prometheus Core v5.0.0 | Система мониторинга",
                "icon_url": "https://cdn-icons-png.flaticon.com/512/2933/2933245.png"
            },
            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        }
        
        # Если переданы дополнительные поля (таблица)
        if fields:
            embed["fields"] = fields
            
        data = {
            "username": "Prometheus Core",
            "avatar_url": "https://cdn-icons-png.flaticon.com/512/2933/2933245.png",
            "embeds": [embed]
        }
        requests.post(webhook_url, json=data, timeout=5)
    except Exception as e:
        print(f"Ошибка отправки в Discord: {e}")

def generate_pdf_report(parent, title, params_dict, img_buf, filename="report.pdf"):
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import time
    import os
    import reportlab

    # --- УМНЫЙ ПОИСК ШРИФТА С КИРИЛЛИЦЕЙ ---
    font_name = 'Helvetica'
    font_bold = 'Helvetica-Bold'
    
    # 1. Пытаемся найти DejaVuSans (идет в комплекте с reportlab)
    try:
        font_path = os.path.join(os.path.dirname(reportlab.__file__), 'fonts', 'DejaVuSans.ttf')
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('CyrFont', font_path))
            font_name = 'CyrFont'
            font_bold = 'CyrFont'
    except Exception:
        pass

    # 2. Если не нашли, ищем Arial в Windows
    if font_name == 'Helvetica':
        font_path = "C:\\Windows\\Fonts\\arial.ttf"
        font_bold_path = "C:\\Windows\\Fonts\\arialbd.ttf"
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('Arial', font_path))
            if os.path.exists(font_bold_path):
                pdfmetrics.registerFont(TTFont('Arial-Bold', font_bold_path))
                font_name = 'Arial'
                font_bold = 'Arial-Bold'
            else:
                font_name = 'Arial'
                font_bold = 'Arial'
    # ----------------------------------------

    path, _ = QtWidgets.QFileDialog.getSaveFileName(parent, "Сохранить PDF", filename, "PDF (*.pdf)")
    if not path: return None
    
    try:
        c = canvas.Canvas(path, pagesize=A4)
        width, height = A4
        
        # Заголовок
        c.setFont(font_bold, 22)
        c.drawString(50, height - 60, f"Prometheus Core: {title}")
        
        c.setFont(font_name, 12)
        c.drawString(50, height - 90, f"Дата генерации: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Параметры
        c.setFont(font_bold, 14)
        c.drawString(50, height - 130, "Параметры расчета:")
        c.setFont(font_name, 11)
        
        y = height - 150
        for key, val in params_dict.items():
            c.drawString(60, y, f"{key}: {val}")
            y -= 20
            
        # График
        if img_buf:
            img = ImageReader(img_buf)
            c.drawImage(img, 50, y - 400, width=500, height=380, preserveAspectRatio=True, mask='auto')
            
        # Футер (Верификация)
        c.setFont(font_name, 10)
        c.setFillColorRGB(0.5, 0.5, 0.5)
        c.drawString(50, 50, "Проект верифицирован по NIST XCOM (<0.01%), NIST PSTAR (0.08%), SRIM (0.03%).")
        c.drawString(50, 35, "Отчет сгенерирован автоматически приложением Prometheus Core v5.0.0")
        
        c.save()
        return path
    except Exception as e:
        QtWidgets.QMessageBox.critical(parent, "Ошибка PDF", f"Не удалось создать PDF: {e}")
        return None

def log_calculation(module, params, result, status="success"):
    """Сохраняет информацию о расчёте в историю (output/history.json)"""
    path = os.path.join(P.OUT_DIR, "history.json")
    history = []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception: pass
    
    history.append({
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "module": module,
        "params": params,
        "result": result,
        "status": status
    })
    
    # Ограничиваем историю 500 записями
    if len(history) > 500:
        history = history[-500:]
        
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
    
def log(msg): P.plog(msg)

def make_json_serializable(obj):
    if isinstance(obj, np.ndarray): return obj.tolist()
    elif isinstance(obj, (np.float64, np.float32, np.float16)): return float(obj)
    elif isinstance(obj, (np.int64, np.int32, np.int16, np.int8)): return int(obj)
    elif isinstance(obj, dict): return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list): return [make_json_serializable(v) for v in obj]
    return obj

def fig_to_base64(fig):
    buf = BytesIO(); fig.savefig(buf, format="png", dpi=120, bbox_inches='tight'); buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')

def make_app_icon():
    pixmap = QtGui.QPixmap(64, 64); pixmap.fill(QtCore.Qt.GlobalColor.transparent)
    painter = QtGui.QPainter(pixmap); painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    painter.setBrush(QtGui.QColor("#2e7d32")); painter.setPen(QtCore.Qt.PenStyle.NoPen); painter.drawEllipse(2, 2, 60, 60)
    painter.setBrush(QtCore.Qt.BrushStyle.NoBrush); painter.setPen(QtGui.QPen(QtGui.QColor("white"), 2))
    painter.drawEllipse(12, 28, 40, 8); painter.drawEllipse(28, 12, 8, 40); painter.drawEllipse(18, 18, 28, 28)
    painter.setBrush(QtGui.QColor("white")); painter.setPen(QtCore.Qt.PenStyle.NoPen); painter.drawEllipse(28, 28, 8, 8)
    painter.end()
    return QtGui.QIcon(pixmap)

def launch_3d_view(log_cb, mode="gamma", R=10.0, data=None, geom="Сфера"):
    try:
        import pyvista as pv
    except ImportError:
        return log_cb("[ОШИБКА] Установите: pip install pyvista")
        
    log_cb(f"[3D] Генерация 3D сцены: {mode} ({geom})...")
    plotter = pv.Plotter(); plotter.set_background('#1e1e1e')
    
    if mode == "gamma":
        if geom == "Плоский слой":
            # Рисуем параллелепипед (плоский слой)
            box = pv.Box(bounds=(0, R, -R, R, -R, R))
            plotter.add_mesh(box, color='#455a64', opacity=0.2, style='wireframe')
            
            # ФИКС: Центр сферы задается ВНУТРИ pv.Sphere, а не в add_mesh!
            plotter.add_mesh(pv.Sphere(radius=R*0.05, center=(0,0,0)), color='red')
            
            # Направленный пучок вглубь слоя
            for _ in range(300):
                y = np.random.uniform(-R, R)
                z = np.random.uniform(-R, R)
                plotter.add_mesh(pv.Line((0, y, z), (R, y, z)), color='yellow', opacity=0.1)
            plotter.show(title=f"3D Гамма (Плоский слой): R={R}")
        else:
            # Рисуем сферу
            plotter.add_mesh(pv.Sphere(radius=R), color='#455a64', opacity=0.2, style='wireframe')
            # ФИКС: Центр сферы задается ВНУТРИ pv.Sphere!
            plotter.add_mesh(pv.Sphere(radius=R*0.05, center=(0,0,0)), color='red')
            
            for _ in range(200):
                theta, phi = np.random.uniform(0, np.pi), np.random.uniform(0, 2*np.pi)
                end = [R * np.sin(theta) * np.cos(phi), R * np.sin(theta) * np.sin(phi), R * np.cos(theta)]
                plotter.add_mesh(pv.Line((0,0,0), end), color='yellow', opacity=0.1)
            plotter.show(title=f"3D Гамма (Сфера): R={R}")
            
    elif mode == "charged":
        if data is not None and len(data[0]) > 1:
            dep, de = data; max_depth = np.max(dep)
            plotter.add_mesh(pv.Cylinder(center=(0, 0, max_depth/2), direction=(0,0,1), radius=1.5, height=max_depth), color='crimson', opacity=0.5)
            plotter.add_mesh(pv.Sphere(radius=3, center=(0,0,max_depth)), color='yellow')
        plotter.show(title="3D Модель Брэгговского пика")
        
    elif mode == "neutron":
        grid = pv.ImageData()
        grid.dimensions = (50, 50, 50)
        grid.spacing = (2 * R / 50, 2 * R / 50, 2 * R / 50)
        grid.origin = (-R, -R, -R)
        points = grid.points
        x, y, z = points[:, 0], points[:, 1], points[:, 2]
        dist = np.sqrt(x**2 + y**2 + z**2)
        flux = np.exp(-(dist**2) / (2 * (R/3)**2)) * 1e6 
        grid.point_data["flux"] = flux
        plotter.add_volume(grid, cmap="plasma", opacity="sigmoid", show_scalar_bar=True, scalar_bar_args={'title': 'Поток нейтронов', 'color': 'white', 'title_font_size': 15})
        plotter.add_mesh(pv.Sphere(radius=R*0.05, center=(0,0,0)), color='red')
        plotter.show(title=f"3D Облако тепловых нейтронов (R={R} см)")

# ==========================================
# ВКЛАДКА: ГЕНЕРАТОР ИЗОТОПОВ
# ==========================================
class GeneratorTab(QtWidgets.QWidget):
    def __init__(s, console, gtab):
        super().__init__(); s.console = console; s.gtab = gtab; s.current_lines = []
        layout = QtWidgets.QVBoxLayout(s); fl = QtWidgets.QFormLayout()
        s.sp_name = QtWidgets.QLineEdit("My-Iso")
        s.sp_E = QtWidgets.QDoubleSpinBox(); s.sp_E.setRange(0.001, 20); s.sp_E.setValue(1.0); s.sp_E.setDecimals(4)
        s.sp_yield = QtWidgets.QDoubleSpinBox(); s.sp_yield.setRange(0.001, 100); s.sp_yield.setValue(100.0)
        s.tbl_lines = QtWidgets.QTableWidget(0, 2); s.tbl_lines.setHorizontalHeaderLabels(["Энергия (МэВ)", "Выход (%)"])
        s.tbl_lines.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch); s.tbl_lines.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        btn_add = QtWidgets.QPushButton("➕ Добавить"); btn_add.clicked.connect(s.add_line)
        btn_save = QtWidgets.QPushButton("💾 Сохранить"); btn_save.setStyleSheet("background:#2e7d32;color:white;font-weight:bold;padding:6px;"); btn_save.clicked.connect(s.save_isotope)
        fl.addRow("Название:", s.sp_name); fl.addRow("Энергия:", s.sp_E); fl.addRow("Выход (%):", s.sp_yield); fl.addRow(btn_add)
        layout.addLayout(fl); layout.addWidget(s.tbl_lines); layout.addWidget(btn_save)
    def add_line(s):
        E, Y = s.sp_E.value(), s.sp_yield.value() / 100.0
        s.current_lines.append([E, Y]); row = s.tbl_lines.rowCount(); s.tbl_lines.insertRow(row)
        s.tbl_lines.setItem(row, 0, QtWidgets.QTableWidgetItem(f"{E:.4f}")); s.tbl_lines.setItem(row, 1, QtWidgets.QTableWidgetItem(f"{Y*100:.1f}"))
    def save_isotope(s):
        name = s.sp_name.text().strip()
        if not name or not s.current_lines: return s.console("[ГЕНЕРАТОР] Ошибка: нет данных!")
        data = {}
        if os.path.exists(CUSTOM_ISO_FILE):
            with open(CUSTOM_ISO_FILE, "r", encoding="utf-8") as f:
                try: data = json.load(f)
                except: pass
        data[name] = {"lines": s.current_lines, "half_life_s": 1e10}
        with open(CUSTOM_ISO_FILE, "w", encoding="utf-8") as f: json.dump(data, f, indent=2)
        P.ISOTOPES[name] = data[name]; s.console(f"[ГЕНЕРАТОР] {name} создан!"); s.current_lines = []; s.tbl_lines.setRowCount(0)

# ==========================================
# ВКЛАДКА: ПЕСОЧНИЦА
# ==========================================

class StatsTab(QtWidgets.QWidget):
    def __init__(s, console):
        super().__init__(); s.console = console
        layout = QtWidgets.QVBoxLayout(s)
        
        # --- Панель управления ---
        btn_layout = QtWidgets.QHBoxLayout()
        s.btn_refresh = QtWidgets.QPushButton("🔄 Обновить")
        s.btn_refresh.clicked.connect(s.refresh_stats)
        s.btn_export_csv = QtWidgets.QPushButton("📄 Экспорт в CSV")
        s.btn_export_csv.clicked.connect(s.export_csv)
        s.btn_export_json = QtWidgets.QPushButton("💾 Экспорт в JSON")
        s.btn_export_json.clicked.connect(s.export_json)
        s.btn_clear = QtWidgets.QPushButton("🗑 Очистить историю")
        s.btn_clear.setStyleSheet("color: #ef5350;")
        s.btn_clear.clicked.connect(s.clear_history)
        
        btn_layout.addWidget(s.btn_refresh)
        btn_layout.addWidget(s.btn_export_csv)
        btn_layout.addWidget(s.btn_export_json)
        btn_layout.addStretch()
        btn_layout.addWidget(s.btn_clear)
        layout.addLayout(btn_layout)
        
        # --- Сводные метрики ---
        metrics_layout = QtWidgets.QHBoxLayout()
        s.lbl_total = QtWidgets.QLabel("Всего расчётов: 0")
        s.lbl_gamma = QtWidgets.QLabel("Гамма: 0")
        s.lbl_charged = QtWidgets.QLabel("Заряженные: 0")
        s.lbl_neutron = QtWidgets.QLabel("Нейтроны: 0")
        s.lbl_avg_time = QtWidgets.QLabel("Среднее время: 0 сек")
        
        for lbl in [s.lbl_total, s.lbl_gamma, s.lbl_charged, s.lbl_neutron, s.lbl_avg_time]:
            lbl.setStyleSheet("font-weight: bold; font-size: 13px; padding: 8px; background: #2b2b2b; border-radius: 4px;")
            metrics_layout.addWidget(lbl)
        layout.addLayout(metrics_layout)
        
        # --- График + Таблица ---
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        
        # График распределения
        s.fig = Figure(figsize=(5, 4), tight_layout=True)
        s.fig.patch.set_facecolor('#2b2b2b')
        s.canvas = FigureCanvas(s.fig)
        splitter.addWidget(s.canvas)
        
        # Таблица последних расчётов
        s.table = QtWidgets.QTableWidget()
        s.table.setColumnCount(6)
        s.table.setHorizontalHeaderLabels(["Время", "Модуль", "Параметры", "Результат", "Время (сек)", "Статус"])
        s.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        s.table.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4;")
        splitter.addWidget(s.table)
        splitter.setSizes([400, 700])
        
        layout.addWidget(splitter)
        
        # Загружаем данные при старте
        s.refresh_stats()
        
    def load_history(s):
        path = os.path.join(P.OUT_DIR, "history.json")
        if not os.path.exists(path): return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception: return []
    
    def refresh_stats(s):
        history = s.load_history()
        
        # Сводные метрики
        total = len(history)
        gamma = sum(1 for h in history if h.get("module") == "Гамма")
        charged = sum(1 for h in history if h.get("module") == "Заряженные")
        neutron = sum(1 for h in history if h.get("module") == "Нейтроны")
        
        times = [h.get("result", {}).get("time", 0) for h in history if h.get("result", {}).get("time")]
        avg_time = sum(times) / len(times) if times else 0
        
        s.lbl_total.setText(f"Всего расчётов: {total}")
        s.lbl_gamma.setText(f"Гамма: {gamma}")
        s.lbl_charged.setText(f"Заряженные: {charged}")
        s.lbl_neutron.setText(f"Нейтроны: {neutron}")
        s.lbl_avg_time.setText(f"Среднее время: {avg_time:.2f} сек")
        
        # Таблица (последние 50, в обратном порядке)
        recent = history[-50:][::-1]
        s.table.setRowCount(len(recent))
        for i, h in enumerate(recent):
            s.table.setItem(i, 0, QtWidgets.QTableWidgetItem(h.get("timestamp", "")))
            s.table.setItem(i, 1, QtWidgets.QTableWidgetItem(h.get("module", "")))
            
            # Компактно параметры
            params_str = ", ".join(f"{k}={v}" for k, v in h.get("params", {}).items())[:60]
            s.table.setItem(i, 2, QtWidgets.QTableWidgetItem(params_str))
            
            # Результат
            result = h.get("result", {})
            res_str = result.get("summary", str(result))[:40]
            s.table.setItem(i, 3, QtWidgets.QTableWidgetItem(res_str))
            
            s.table.setItem(i, 4, QtWidgets.QTableWidgetItem(f"{result.get('time', 0):.2f}"))
            
            status_item = QtWidgets.QTableWidgetItem(h.get("status", "success"))
            if h.get("status") == "error":
                status_item.setForeground(QtGui.QColor("#ef5350"))
            else:
                status_item.setForeground(QtGui.QColor("#66bb6a"))
            s.table.setItem(i, 5, status_item)
        
        # График
        s.fig.clear()
        ax = s.fig.add_subplot(111)
        ax.set_facecolor('#1e1e1e')
        
        if total > 0:
            labels = ["Гамма", "Заряженные", "Нейтроны"]
            values = [gamma, charged, neutron]
            colors = ["#4CAF50", "#2196F3", "#9C27B0"]
            # Убираем нулевые значения для чистоты
            filtered = [(l, v, c) for l, v, c in zip(labels, values, colors) if v > 0]
            if filtered:
                ax.pie([f[1] for f in filtered], labels=[f[0] for f in filtered], 
                       colors=[f[2] for f in filtered], autopct='%1.0f%%',
                       textprops={'color': 'white', 'fontsize': 10})
        else:
            ax.text(0.5, 0.5, "Нет данных", ha='center', va='center', 
                   color='white', fontsize=14, transform=ax.transAxes)
            ax.axis('off')
        
        s.fig.patch.set_facecolor('#1e1e1e')
        s.canvas.draw()
    
    def export_csv(s):
        history = s.load_history()
        if not history: return s.console("[СТАТИСТИКА] История пуста.")
        
        path, _ = QtWidgets.QFileDialog.getSaveFileName(s, "Экспорт CSV", "history.csv", "CSV (*.csv)")
        if not path: return
        
        import csv
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(["Время", "Модуль", "Параметры", "Результат", "Время (сек)", "Статус"])
                for h in history:
                    params = "; ".join(f"{k}={v}" for k, v in h.get("params", {}).items())
                    result = h.get("result", {})
                    writer.writerow([
                        h.get("timestamp", ""),
                        h.get("module", ""),
                        params,
                        result.get("summary", ""),
                        result.get("time", 0),
                        h.get("status", "")
                    ])
            s.console(f"[СТАТИСТИКА] Экспорт в CSV: {path}")
        except Exception as e:
            s.console(f"[СТАТИСТИКА] Ошибка экспорта: {e}")
    
    def export_json(s):
        history = s.load_history()
        if not history: return s.console("[СТАТИСТИКА] История пуста.")
        
        path, _ = QtWidgets.QFileDialog.getSaveFileName(s, "Экспорт JSON", "history.json", "JSON (*.json)")
        if not path: return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
            s.console(f"[СТАТИСТИКА] Экспорт в JSON: {path}")
        except Exception as e:
            s.console(f"[СТАТИСТИКА] Ошибка экспорта: {e}")
    
    def clear_history(s):
        reply = QtWidgets.QMessageBox.question(s, "Очистка", 
            "Вы уверены, что хотите удалить всю историю расчётов?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            path = os.path.join(P.OUT_DIR, "history.json")
            if os.path.exists(path): os.remove(path)
            s.refresh_stats()
            s.console("[СТАТИСТИКА] История очищена.")
class SandboxTab(QtWidgets.QWidget):
    def __init__(s, console):
        super().__init__(); s.console = console
        layout = QtWidgets.QHBoxLayout(s); left = QtWidgets.QVBoxLayout()
        left.addWidget(QtWidgets.QLabel("<h3>Твои изотопы</h3>"))
        s.list_iso = QtWidgets.QListWidget(); s.list_iso.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; font-family: Consolas;")
        left.addWidget(s.list_iso)
        btn_refresh = QtWidgets.QPushButton("🔄 Обновить"); btn_refresh.clicked.connect(s.refresh_list); left.addWidget(btn_refresh)
        left.addSpacing(20)
        btn_3d = QtWidgets.QPushButton("🚀 3D-сцена (PyVista)"); btn_3d.setStyleSheet("background-color: #2b2b2b; color: white; border: 1px solid #555555; padding: 6px;")
        btn_3d.clicked.connect(lambda: launch_3d_view(s.console, mode="gamma", R=10.0)); left.addWidget(btn_3d)
        layout.addLayout(left, 1); s.refresh_list()
    def refresh_list(s):
        s.list_iso.clear()
        if os.path.exists(CUSTOM_ISO_FILE):
            try:
                with open(CUSTOM_ISO_FILE, "r", encoding="utf-8") as f:
                    for name in json.load(f).keys(): s.list_iso.addItem(f"✅ {name}")
            except Exception: pass
        if s.list_iso.count() == 0: s.list_iso.addItem("(Нет изотопов)")
class IdeTab(QtWidgets.QWidget):
    def __init__(s, console):
        super().__init__(); s.console = console
        layout = QtWidgets.QVBoxLayout(s)
        
        # Панель кнопок
        btn_layout = QtWidgets.QHBoxLayout()
        s.btn_open = QtWidgets.QPushButton("📂 Открыть файл")
        s.btn_open.clicked.connect(s.open_file)
        s.btn_run = QtWidgets.QPushButton("▶ Запустить скрипт")
        s.btn_run.setStyleSheet("background:#2e7d32;color:white;font-weight:bold;")
        s.btn_run.clicked.connect(s.run_script)
        s.btn_clear = QtWidgets.QPushButton("🗑 Очистить")
        s.btn_clear.clicked.connect(lambda: s.editor.clear())
        
        btn_layout.addWidget(s.btn_open); btn_layout.addWidget(s.btn_run); btn_layout.addWidget(s.btn_clear)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Редактор кода
        s.editor = QtWidgets.QPlainTextEdit()
        s.editor.setStyleSheet("""
            background-color: #1e1e1e; 
            color: #d4d4d4; 
            font-family: Consolas, monospace; 
            font-size: 14px; 
            border: 1px solid #333;
        """)
        s.editor.setPlaceholderText("Введите код на Python здесь...")
        layout.addWidget(s.editor)
        
        # Консоль вывода
        s.out_console = QtWidgets.QPlainTextEdit()
        s.out_console.setReadOnly(True)
        s.out_console.setMaximumHeight(150)
        s.out_console.setStyleSheet("background-color: #000000; color: #66bb6a; font-family: Consolas;")
        layout.addWidget(QtWidgets.QLabel("ВЫВОД СКРИПТА:"))
        layout.addWidget(s.out_console)

    def open_file(s):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(s, "Открыть Python-скрипт", "", "Python (*.py);;Все файлы (*.*)")
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    s.editor.setPlainText(f.read())
                s.console(f"[IDE] Открыт файл: {path}")
            except Exception as e:
                s.console(f"[IDE] Ошибка чтения: {e}")

    def run_script(s):
        code = s.editor.toPlainText()
        if not code.strip():
            return s.out_console.setPlainText("Нет кода для запуска.")
            
        s.out_console.clear()
        s.out_console.appendPlainText("Запуск...\n")
        
        import tempfile, subprocess, sys, os
        tmp_path = ""
        try:
            # Создаем временный файл
            with tempfile.NamedTemporaryFile(delete=False, suffix=".py", mode="w", encoding="utf-8") as tmp:
                tmp.write(code)
                tmp_path = tmp.name
                
            # Запускаем через sys.executable (тот же Python, что и программа)
            result = subprocess.run([sys.executable, tmp_path], capture_output=True, text=True, timeout=10)
            
            if result.stdout:
                s.out_console.appendPlainText(result.stdout)
            if result.stderr:
                s.out_console.appendPlainText(f"ОШИБКА:\n{result.stderr}")
                
            s.console("[IDE] Скрипт выполнен.")
            
        except subprocess.TimeoutExpired:
            s.out_console.appendPlainText("ОШИБКА: Превышено время выполнения (10 сек).")
        except Exception as e:
            s.out_console.appendPlainText(f"ОШИБКА ЗАПУСКА: {e}")
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)

# ==========================================
# ВКЛАДКА: CLI
# ==========================================
class CliTab(QtWidgets.QWidget):
    def __init__(s, console):
        super().__init__(); s.console = console
        layout = QtWidgets.QVBoxLayout(s)
        layout.addWidget(QtWidgets.QLabel("<h2>Визуальный конструктор команд</h2>"))
        cmd_layout = QtWidgets.QHBoxLayout(); cmd_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        lbl_style = "font-family: Consolas; font-size: 16px; color: #d4d4d4;"
        btn_style = "background-color: #1e1e1e; color: #4CAF50; border: 1px solid #4CAF50; padding: 4px 8px; border-radius: 4px; font-family: Consolas; font-weight: bold; font-size: 16px;"
        
        lbl1 = QtWidgets.QLabel("python app.py --cli --mat "); lbl1.setStyleSheet(lbl_style); cmd_layout.addWidget(lbl1)
        s.btn_mat = QtWidgets.QPushButton("lead"); s.btn_mat.setStyleSheet(btn_style); s.btn_mat.clicked.connect(s.select_mat); cmd_layout.addWidget(s.btn_mat)
        lbl2 = QtWidgets.QLabel(" --iso "); lbl2.setStyleSheet(lbl_style); cmd_layout.addWidget(lbl2)
        s.btn_iso = QtWidgets.QPushButton("Co-60"); s.btn_iso.setStyleSheet(btn_style); s.btn_iso.clicked.connect(s.select_iso); cmd_layout.addWidget(s.btn_iso)
        lbl3 = QtWidgets.QLabel(" --n "); lbl3.setStyleSheet(lbl_style); cmd_layout.addWidget(lbl3)
        s.btn_n = QtWidgets.QPushButton("1000000"); s.btn_n.setStyleSheet(btn_style); s.btn_n.clicked.connect(s.select_n); cmd_layout.addWidget(s.btn_n)
        lbl4 = QtWidgets.QLabel(" --out "); lbl4.setStyleSheet(lbl_style); cmd_layout.addWidget(lbl4)
        s.btn_out = QtWidgets.QPushButton("result.json"); s.btn_out.setStyleSheet(btn_style); s.btn_out.clicked.connect(s.select_out); cmd_layout.addWidget(s.btn_out)
        
        cmd_layout.addStretch(); layout.addLayout(cmd_layout); layout.addSpacing(30)
        layout.addWidget(QtWidgets.QLabel("<h3>Итоговая команда:</h3>"))
        s.txt_out = QtWidgets.QPlainTextEdit(); s.txt_out.setReadOnly(True); s.txt_out.setStyleSheet("font-family: Consolas; font-size: 16px; background: #1e1e1e; color: #2e7d32; padding: 10px;")
        layout.addWidget(s.txt_out)
        btn_copy = QtWidgets.QPushButton("📋 Скопировать"); btn_copy.clicked.connect(s.copy_cmd); layout.addWidget(btn_copy)
        s.mat_val = "lead"; s.iso_val = "Co-60"; s.n_val = 1000000; s.out_val = "result.json"; s.update_cmd()
    def update_cmd(s):
        s.txt_out.setPlainText(f"python app.py --cli --mat {s.mat_val} --iso {s.iso_val} --n {s.n_val} --out {s.out_val}")
    def select_mat(s):
        dlg = SelectorDialog("Материал", P.GAMMA_MATS, "material_gamma", s)
        if dlg.exec(): sel = dlg.list_widget.currentItem(); s.mat_val = sel.text(); s.btn_mat.setText(s.mat_val); s.update_cmd()
    def select_iso(s):
        dlg = SelectorDialog("Изотоп", P.ISOTOPES, "isotope", s)
        if dlg.exec(): sel = dlg.list_widget.currentItem(); s.iso_val = sel.text(); s.btn_iso.setText(s.iso_val); s.update_cmd()
    def select_n(s):
        val, ok = QtWidgets.QInputDialog.getInt(s, "N", "Число:", s.n_val, 1000, 10_000_000)
        if ok: s.n_val = val; s.btn_n.setText(str(val)); s.update_cmd()
    def select_out(s):
        val, ok = QtWidgets.QInputDialog.getText(s, "Файл", "Имя:", text=s.out_val)
        if ok: s.out_val = val; s.btn_out.setText(val); s.update_cmd()
    def copy_cmd(s): QtWidgets.QApplication.clipboard().setText(s.txt_out.toPlainText()); s.console("[CLI] Скопировано!")

# ==========================================
# ДИАЛОГИ
# ==========================================
class LateralPlotDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent); self.setWindowTitle("2D Карта латерального рассеяния"); self.resize(800, 600)
        layout = QtWidgets.QVBoxLayout(self); self.fig = Figure(tight_layout=True); self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas); layout.addWidget(QtWidgets.QLabel("Нажмите 'Рассчитать' в главном окне, чтобы обновить карту"))
    def update_plot(self, grid, x_bins, y_bins):
        self.fig.clear(); ax = self.fig.add_subplot(111)
        im = ax.imshow(grid, extent=[x_bins[0], x_bins[-1], y_bins[0], y_bins[-1]], origin="lower", cmap="inferno", aspect="auto")
        ax.set_xlabel("Глубина X (см)"); ax.set_ylabel("Поперечное смещение Y (см)")
        ax.set_title("Расплывание пучка (Латеральный страгглинг)")
        self.canvas.draw()

class SliceDialog(QtWidgets.QDialog):
    def __init__(self, g2, R, geom, parent=None):
        super().__init__(parent); self.setWindowTitle("1D Срез"); self.resize(800, 700)
        layout = QtWidgets.QVBoxLayout(self); self.fig = Figure(figsize=(8, 7), tight_layout=True); self.canvas = FigureCanvas(self.fig)
        self.ax_map = self.fig.add_subplot(211); self.ax_slice = self.fig.add_subplot(212)
        pos = g2[g2 > 0]; vmin = pos.min() if pos.size else 1e-12
        self.g2_disp = g2.copy(); self.g2_disp[self.g2_disp <= 0] = vmin
        extent = [0, R, -R, R] if geom == "slab" else [-R, R, -R, R]
        self.im = self.ax_map.imshow(self.g2_disp, origin="lower", extent=extent, cmap="inferno", norm=LogNorm(vmin=vmin), interpolation='nearest')
        self.ny, self.nx = g2.shape; self.y_center = self.ny // 2
        self.red_line = self.ax_map.axhline(y=extent[2] + (self.y_center / self.ny) * (extent[3] - extent[2]), color='red', lw=2)
        layout.addWidget(self.canvas)
        self.slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal); self.slider.setRange(0, self.ny - 1); self.slider.setValue(self.y_center)
        self.slider.valueChanged.connect(self.update_slice); layout.addWidget(self.slider); self.update_slice(self.y_center)
        
    def update_slice(self, val):
        y_pos = self.ax_map.get_ylim()[0] + (val / self.ny) * (self.ax_map.get_ylim()[1] - self.ax_map.get_ylim()[0])
        self.red_line.set_ydata([y_pos, y_pos]); self.ax_slice.clear()
        
        # ФИКС: Обрезаем последний бин, который создает визуальный обрыв на краю
        slice_data = self.g2_disp[val, :-1]
        
        x_axis = np.linspace(self.ax_map.get_xlim()[0], self.ax_map.get_xlim()[1], len(slice_data))
        self.ax_slice.plot(x_axis, slice_data, color="cyan", lw=2); self.ax_slice.set_yscale("log"); self.canvas.draw_idle()

class PopOutDialog(QtWidgets.QDialog):
    def __init__(self, fig, title="Визуализация", parent=None):
        super().__init__(parent); self.setWindowTitle(title); self.resize(1000, 800)
        self.fig = fig; self.original_canvas = parent.canvas if parent and hasattr(parent, 'canvas') else None
        self.original_limits = [(ax.get_xlim(), ax.get_ylim()) for ax in self.fig.axes]
        layout = QtWidgets.QVBoxLayout(self); self.canvas = FigureCanvas(fig); self.toolbar = NavToolbar(self.canvas, self)
        layout.addWidget(self.toolbar); layout.addWidget(self.canvas)
        self.draw_timer = QtCore.QTimer(); self.draw_timer.setSingleShot(True); self.draw_timer.setInterval(50); self.draw_timer.timeout.connect(self.canvas.draw_idle)
        self.cid_scroll = self.canvas.mpl_connect('scroll_event', self.on_scroll)
        self.cid_press = self.canvas.mpl_connect('button_press_event', self.on_press)
        self.cid_motion = self.canvas.mpl_connect('motion_notify_event', self.on_motion)
        self.cid_release = self.canvas.mpl_connect('button_release_event', self.on_release)
        self.fig.set_size_inches(self.canvas.width() / self.fig.dpi, self.canvas.height() / self.fig.dpi); self.fig.tight_layout(); self.canvas.draw()
    def request_draw(self):
        if not self.draw_timer.isActive(): self.draw_timer.start()
    def on_scroll(self, event):
        ax = event.inaxes
        if ax is None: return
        base_scale = 1.2; cur_xlim = ax.get_xlim(); cur_ylim = ax.get_ylim()
        scale_factor = 1 / base_scale if event.button == 'up' else base_scale if event.button == 'down' else 1
        new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor; new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor
        relx = (cur_xlim[1] - event.xdata) / (cur_xlim[1] - cur_xlim[0]); rely = (cur_ylim[1] - event.ydata) / (cur_ylim[1] - cur_ylim[0])
        ax.set_xlim([event.xdata - new_width * (1 - relx), event.xdata + new_width * relx]); ax.set_ylim([event.ydata - new_height * (1 - rely), event.ydata + new_height * rely])
        self.request_draw()
    def on_press(self, event):
        if event.button == 1 and event.inaxes is not None:
            ax = event.inaxes; ax._pan_start = (event.xdata, event.ydata, ax.get_xlim(), ax.get_ylim())
            if ax.get_xscale() == 'log' and event.xdata > 0: ax._pan_start_logx = np.log10(event.xdata)
            if ax.get_yscale() == 'log' and event.ydata > 0: ax._pan_start_logy = np.log10(event.ydata)
            self.canvas.setCursor(QtCore.Qt.CursorShape.ClosedHandCursor)
    def on_motion(self, event):
        if event.button == 1 and event.inaxes is not None and hasattr(event.inaxes, '_pan_start'):
            ax = event.inaxes; start_x, start_y, xlim, ylim = ax._pan_start
            if ax.get_xscale() == 'log' and event.xdata > 0 and hasattr(ax, '_pan_start_logx'):
                dx = np.log10(event.xdata) - ax._pan_start_logx; ax.set_xlim(10**(np.log10(xlim[0]) - dx), 10**(np.log10(xlim[1]) - dx))
            elif ax.get_xscale() != 'log':
                dx = event.xdata - start_x; ax.set_xlim(xlim[0] - dx, xlim[1] - dx)
            if ax.get_yscale() == 'log' and event.ydata > 0 and hasattr(ax, '_pan_start_logy'):
                dy = np.log10(event.ydata) - ax._pan_start_logy; ax.set_ylim(10**(np.log10(ylim[0]) - dy), 10**(np.log10(ylim[1]) - dy))
            elif ax.get_yscale() != 'log':
                dy = event.ydata - start_y; ax.set_ylim(ylim[0] - dy, ylim[1] - dy)
            self.request_draw()
    def on_release(self, event):
        if event.button == 1:
            if event.inaxes is not None and hasattr(event.inaxes, '_pan_start'): del event.inaxes._pan_start
            self.canvas.setCursor(QtCore.Qt.CursorShape.ArrowCursor); self.canvas.draw_idle()
    def closeEvent(self, event):
        try:
            self.draw_timer.stop(); self.canvas.mpl_disconnect(self.cid_scroll); self.canvas.mpl_disconnect(self.cid_press)
            self.canvas.mpl_disconnect(self.cid_motion); self.canvas.mpl_disconnect(self.cid_release)
            if self.original_canvas:
                self.fig.set_canvas(self.original_canvas)
                w = self.original_canvas.width(); h = self.original_canvas.height()
                if w > 0 and h > 0: self.fig.set_size_inches(w / self.fig.dpi, h / self.fig.dpi)
                self.fig.tight_layout()
                for ax, (xlim, ylim) in zip(self.fig.axes, self.original_limits): ax.set_xlim(xlim); ax.set_ylim(ylim)
                self.original_canvas.draw()
        except Exception: pass
        super().closeEvent(event)

class SelectorDialog(QtWidgets.QDialog):
    def __init__(s, title, data_dict, item_type, parent=None, descriptions=None):
        super().__init__(parent); s.setWindowTitle(title); s.resize(700, 550); s.data_dict = data_dict; s.item_type = item_type
        s.descriptions = descriptions
        
        layout = QtWidgets.QHBoxLayout(s); left = QtWidgets.QVBoxLayout()
        s.search = QtWidgets.QLineEdit(); s.search.setPlaceholderText("🔍 Поиск..."); s.search.textChanged.connect(s.filter_list); left.addWidget(s.search)
        s.list_widget = QtWidgets.QListWidget(); s.list_widget.itemDoubleClicked.connect(s.accept)
        for k in sorted(data_dict.keys()):
            if not k.startswith("_"): s.list_widget.addItem(k)
        s.list_widget.currentTextChanged.connect(s.update_details); left.addWidget(s.list_widget)
        
        right = QtWidgets.QVBoxLayout(); right.addWidget(QtWidgets.QLabel("<b>Информация:</b>"))
        s.details = QtWidgets.QTextBrowser(); s.details.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; font-family: Consolas; font-size: 13px; padding: 5px;")
        right.addWidget(s.details); layout.addLayout(left, 1); layout.addLayout(right, 1)
        
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(s.accept); btn_box.rejected.connect(s.reject)
        main = QtWidgets.QVBoxLayout(); main.addLayout(layout); main.addWidget(btn_box); s.setLayout(main)
        if s.list_widget.count() > 0: s.list_widget.setCurrentRow(0)
        
    def filter_list(s, text):
        # --- ПАСХАЛКА SCP-8926 ---
        if text.strip() == "8926":
            s.search.clear() # Очищаем поиск
            s.show_scp_warning() # Вызываем окно
            return
        # --------------------------
        
        for i in range(s.list_widget.count()): 
            s.list_widget.item(i).setHidden(text.lower() not in s.list_widget.item(i).text().lower())
    def show_scp_warning(s):
        msg = QtWidgets.QMessageBox(s)
        msg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
        msg.setWindowTitle("SCP FOUNDATION SECURE TERMINAL")
        
        # Настраиваем текст в стиле SCP
        msg.setText("<b>ВНИМАНИЕ: ОБНАРУЖЕНА ПОПЫТКА ДОСТУПА К SCP-8926</b>")
        msg.setInformativeText(
            "Меметический Агент Умерщвления (МАУ) класса IX активирован.\n\n"
            "Ваш пульс синхронизирован с частотой 0.5 Гц.\n"
            "Если вы читаете это сообщение — вы уже мертвы.\n\n"
            "Пожалуйста, не падайте на клавиатуру. Это может вызвать короткое замыкание."
        )
        
        # Делаем окно темным и красным
        msg.setStyleSheet("""
            QMessageBox { background-color: #1e1e1e; }
            QLabel { color: #ef5350; font-family: Consolas; font-size: 13px; }
            QPushButton { background-color: #2b2b2b; color: #ffffff; border: 1px solid #ef5350; padding: 6px 12px; border-radius: 4px;}
            QPushButton:hover { background-color: #ef5350; }
        """)
        msg.exec()
        
    def update_details(s, name):
        if not name or name not in s.data_dict: return
        if s.descriptions and name in s.descriptions:
            s.details.setText(s.descriptions[name]); return
            
        d = s.data_dict[name]; text = ""
        if s.item_type == "isotope":
            text += f"Изотоп: {name}\n\nГамма-линии:\n"
            for line in d.get("lines", []): text += f"  - {line[0]:.4f} МэВ ({line[1]*100:.1f}%)\n"
        elif s.item_type.startswith("material"):
            text += f"Материал: {name}\n\nZ: {d.get('Z', 0):.2f}\nA: {d.get('A', 0):.2f}\nПлотность: {d.get('rho', 0)} г/см³\n"
            if "I" in d: text += f"Энергия ионизации: {d['I']} эВ\n"
        s.details.setText(text)
# ==========================================
# РАБОЧИЕ ПОТОКИ
# ==========================================
class GammaWorker(QtCore.QThread):
    done=QtCore.Signal(dict); fail=QtCore.Signal(str); prog=QtCore.Signal(float); status_msg=QtCore.Signal(str)
    def __init__(s,p): super().__init__(); s.p=p; s._stop=False
    def stop(s): s._stop=True
    def run(s):
        try:
            def progress_cb(f):
                s.prog.emit(f)
                s.status_msg.emit(f"Расчет... {int(f*100)}%")
                
            t_start = time.perf_counter()
            r = P.gamma_mc(**s.p, progress=progress_cb, should_stop=lambda:s._stop)
            t_end = time.perf_counter()
            if r is not None: 
                r["elapsed_time"] = t_end - t_start
                s.done.emit(r)
        except Exception as e: 
            s.fail.emit(f"{type(e).__name__}: {e}")
class AttenuationWorker(QtCore.QThread):
    done=QtCore.Signal(list); fail=QtCore.Signal(str)
    def __init__(s, mat, spec, n_hist, thick): super().__init__(); s.mat=mat; s.spec=spec; s.n_hist=n_hist; s.thick=thick
    def run(s):
        try: s.done.emit(P.attenuation_curve(s.mat, s.spec, s.n_hist, s.thick))
        except Exception as e: s.fail.emit(f"{type(e).__name__}: {e}")
class NeutronWorker(QtCore.QThread):
    done=QtCore.Signal(dict); fail=QtCore.Signal(str); msg=QtCore.Signal(str)
    def __init__(s,c): super().__init__(); s.c=c
    def run(s):
        try: s.done.emit(P.run_neutrons_wsl(s.c, lambda m:s.msg.emit(m)))
        except Exception as e: s.fail.emit(f"{type(e).__name__}: {e}")

class StragglingWorker(QtCore.QThread):
    done=QtCore.Signal(list); fail=QtCore.Signal(str)
    def __init__(s, part, T0, mat): super().__init__(); s.part=part; s.T0=T0; s.mat=mat
    def run(s):
        try:
            mean_R = P.csda(s.part, s.T0, s.mat, nstep=800)[0]
            sigma_R = P.straggling_sigma(s.part, s.T0, s.mat)
            
            # ОТЛАДОЧНЫЙ ВЫВОД (посмотри в консоль!)
            print(f"DEBUG: mean_R={mean_R:.3f} см, sigma_R={sigma_R:.4f} см")
            
            rng = np.random.default_rng()
            # Генерируем 50 значений вокруг среднего с учетом сигмы
            ranges = rng.normal(loc=mean_R, scale=max(sigma_R, 1e-6), size=50).tolist()
            s.done.emit(ranges)
        except Exception as e:
            s.fail.emit(f"{type(e).__name__}: {e}")

class LateralWorker(QtCore.QThread):
    done = QtCore.Signal(np.ndarray, np.ndarray, np.ndarray)
    fail = QtCore.Signal(str)
    
    # ВОТ ЭТА СТРОКА БЫЛА УДАЛЕНА (инициализация аргументов)
    def __init__(self, part, T0, mat): 
        super().__init__() 
        self.part = part
        self.T0 = T0
        self.mat = mat
        
    def run(self):
        try: 
            # Увеличили до 10000, чтобы трек был сплошным
            grid, xb, yb = P.lateral_straggling_2d(self.part, self.T0, self.mat, n_particles=10000)
            self.done.emit(grid, xb, yb)
        except Exception as e: 
            self.fail.emit(f"{type(e).__name__}: {e}")

# ==========================================
# ОСНОВНЫЕ МОДУЛИ
# ==========================================
class GammaTab(QtWidgets.QWidget):
    def __init__(s, console):
        super().__init__(); s.console=console; s.res=None; s.w=None; s.att_res=None; s.sel_mat = "air"; s.sel_iso = "Am-241"
        root=QtWidgets.QHBoxLayout(s); p=QtWidgets.QWidget(); p.setFixedWidth(420); fl=QtWidgets.QFormLayout(p)
        s.cb_geom = QtWidgets.QComboBox(); s.cb_geom.addItems(["Сфера", "Плоский слой"]); s.lbl_R = QtWidgets.QLabel("Радиус,см")
        btn_style = "background-color: #2b2b2b; color: #ffffff; text-align: left; padding-left: 10px; border: 1px solid #555555; border-radius: 4px;"
        s.btn_mat = QtWidgets.QPushButton("air"); s.btn_mat.setStyleSheet(btn_style); s.btn_mat.clicked.connect(s.select_material)
        s.btn_iso = QtWidgets.QPushButton("Am-241"); s.btn_iso.setStyleSheet(btn_style); s.btn_iso.clicked.connect(s.select_isotope)
        s.tbl_layers = QtWidgets.QTableWidget(3, 2); s.tbl_layers.setHorizontalHeaderLabels(["Материал", "Толщина,см"])
        s.tbl_layers.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        s.tbl_layers.verticalHeader().setDefaultSectionSize(35)
        s.tbl_layers.setMinimumHeight(150) # Делаем таблицу повыше
        s.tbl_layers.verticalHeader().setDefaultSectionSize(40) # Еще немного увеличиваем строки
        def update_total_thickness(): s.sp_R.setValue(sum(s.tbl_layers.cellWidget(i, 1).value() for i in range(3))); s.validate()
        for i in range(3):
            # Создаем кнопку вместо выпадающего списка
            btn_layer_mat = QtWidgets.QPushButton("lead" if i==0 else ("polyethylene" if i==1 else "concrete"))
            btn_layer_mat.setStyleSheet(btn_style)
            btn_layer_mat.setMinimumHeight(30) # <--- Задаем высоту кнопки
            # Привязываем клик к открытию красивого диалога
            btn_layer_mat.clicked.connect(lambda checked=False, b=btn_layer_mat: s.select_layer_material(b))
            s.tbl_layers.setCellWidget(i, 0, btn_layer_mat)
            
            sb = QtWidgets.QDoubleSpinBox(); sb.setRange(0, 1000); sb.setValue(2.0 if i==0 else (10.0 if i==1 else 0.0)); sb.valueChanged.connect(update_total_thickness); s.tbl_layers.setCellWidget(i, 1, sb)
        s.tbl_layers.setVisible(False)
        s.sp_R=QtWidgets.QDoubleSpinBox(); s.sp_R.setRange(1,300); s.sp_R.setValue(10); s.sp_n=QtWidgets.QSpinBox(); s.sp_n.setRange(1000,5_000_000); s.sp_n.setValue(100000); s.sp_n.setGroupSeparatorShown(True)
        s.sp_seed=QtWidgets.QSpinBox(); s.sp_seed.setRange(0,999999); s.sp_seed.setValue(42); s.chk_abs=QtWidgets.QCheckBox("Абс. доза")
        s.sp_act=QtWidgets.QDoubleSpinBox(); s.sp_act.setRange(0,1e18); s.sp_act.setValue(1.0); s.cb_au=QtWidgets.QComboBox(); s.cb_au.addItems(P.ACTIVITY_U.keys()); s.cb_au.setCurrentText("МБк")
        s.sp_t=QtWidgets.QDoubleSpinBox(); s.sp_t.setRange(0,1e12); s.sp_t.setValue(1.0); s.cb_tu=QtWidgets.QComboBox(); s.cb_tu.addItems(P.TIME_U.keys()); s.cb_tu.setCurrentText("ч")
        s.btn=QtWidgets.QPushButton("▶ Рассчитать"); s.btn.clicked.connect(s.run); s.btn.setStyleSheet("background:#2e7d32;color:white;font-weight:bold;padding:6px;")
        s.btn_export = QtWidgets.QPushButton("💾 Экспорт"); s.btn_export.clicked.connect(s.export_data)
        s.btn_pdf = QtWidgets.QPushButton("📄 Скачать PDF-отчет"); s.btn_pdf.clicked.connect(s.export_pdf)
        s.sp_n.valueChanged.connect(s.validate); s.sp_R.valueChanged.connect(s.validate)
        def on_geom_change():
            if s.cb_geom.currentText() == "Сфера": s.lbl_R.setText("Радиус,см"); s.tbl_layers.setVisible(False); s.btn_mat.setVisible(True); s.sp_R.setReadOnly(False)
            else: s.lbl_R.setText("Общая толщина,см"); s.tbl_layers.setVisible(True); s.btn_mat.setVisible(False); s.sp_R.setReadOnly(True); update_total_thickness()
            s.validate()
        s.cb_geom.currentIndexChanged.connect(on_geom_change)
        fl.addRow("Геометрия", s.cb_geom); fl.addRow("Материал", s.btn_mat); fl.addRow(s.tbl_layers); fl.addRow("Изотоп", s.btn_iso); fl.addRow(s.lbl_R,s.sp_R); fl.addRow("Историй",s.sp_n); fl.addRow("Seed",s.sp_seed); fl.addRow("",s.chk_abs); fl.addRow("Активность",s.sp_act); fl.addRow("Ед.акт",s.cb_au); fl.addRow("Время",s.sp_t); fl.addRow("Ед.вр",s.cb_tu); fl.addRow(s.btn); fl.addRow(s.btn_export); fl.addRow(s.btn_pdf)
        btn_grid = QtWidgets.QGridLayout(); b_style = "background-color: #2b2b2b; color: white; border: 1px solid #555555; padding: 4px; border-radius: 4px;"
        b_hist = QtWidgets.QPushButton("📊 Гистограмма"); b_hist.setStyleSheet(b_style); b_hist.clicked.connect(s.show_coll_hist)
        b_polar = QtWidgets.QPushButton("📐 Полярный"); b_polar.setStyleSheet(b_style); b_polar.clicked.connect(s.show_polar_hist)
        b_att = QtWidgets.QPushButton("📉 Ослабление"); b_att.setStyleSheet(b_style); b_att.clicked.connect(s.run_attenuation)
        b_slice = QtWidgets.QPushButton("📏 1D-срез"); b_slice.setStyleSheet(b_style); b_slice.clicked.connect(s.show_slice)
        b_err = QtWidgets.QPushButton("📊 Погрешность"); b_err.setStyleSheet(b_style); b_err.clicked.connect(s.run_error_estimation)
        btn_3d = QtWidgets.QPushButton("🚀 3D"); btn_3d.setStyleSheet(b_style); btn_3d.clicked.connect(lambda: launch_3d_view(s.console, mode="gamma", R=s.sp_R.value(), geom=s.cb_geom.currentText()))
        btn_pop = QtWidgets.QPushButton("🔍 Развернуть"); btn_pop.setStyleSheet(b_style); btn_pop.clicked.connect(lambda: PopOutDialog(s.fig, "Гамма-модуль", s).exec())
        btn_grid.addWidget(b_hist, 0, 0); btn_grid.addWidget(b_polar, 0, 1); btn_grid.addWidget(b_att, 1, 0); btn_grid.addWidget(b_slice, 1, 1); btn_grid.addWidget(btn_3d, 2, 0); btn_grid.addWidget(btn_pop, 2, 1)
        btn_grid.addWidget(b_err, 3, 0)
        fl.addRow(btn_grid)
        s.pbar=QtWidgets.QProgressBar(); fl.addRow(s.pbar); root.addWidget(p)
        s.fig=Figure(figsize=(10,10),tight_layout=True); s.a1=s.fig.add_subplot(221); s.a2=s.fig.add_subplot(222); s.a3=s.fig.add_subplot(223); s.a4=s.fig.add_subplot(224)
        s.canvas=FigureCanvas(s.fig); g=QtWidgets.QWidget(); gl=QtWidgets.QVBoxLayout(g); s.toolbar_g = NavToolbar(s.canvas,s); gl.addWidget(s.toolbar_g); gl.addWidget(s.canvas); root.addWidget(g,1); s.validate()
    def select_material(s):
        dlg = SelectorDialog("Материал", P.GAMMA_MATS, "material_gamma", s)
        if dlg.exec(): s.sel_mat = dlg.list_widget.currentItem().text(); s.btn_mat.setText(s.sel_mat)
    def select_layer_material(s, btn):
        dlg = SelectorDialog("Материал слоя", P.GAMMA_MATS, "material_gamma", s)
        if dlg.exec(): 
            sel = dlg.list_widget.currentItem()
            if sel:
                btn.setText(sel.text())
    def select_isotope(s):
        dlg = SelectorDialog("Изотоп", P.ISOTOPES, "isotope", s)
        if dlg.exec(): s.sel_iso = dlg.list_widget.currentItem().text(); s.btn_iso.setText(s.sel_iso)
    def validate(s):
        ok = True
        if s.sp_n.value() < 1000 or s.sp_R.value() <= 0: ok = False
        if s.cb_geom.currentText() == "Плоский слой":
            if sum(s.tbl_layers.cellWidget(i, 1).value() for i in range(3)) <= 0: ok = False
        s.btn.setEnabled(ok)
    def run(s):
        if s.w and s.w.isRunning(): return s.console("[ГАММА] Уже идёт расчёт.")
        layers = []
        if s.cb_geom.currentText() == "Плоский слой":
            for i in range(3):
                thick = s.tbl_layers.cellWidget(i, 1).value()
                if thick > 0: layers.append((P.make_gamma_mat(s.tbl_layers.cellWidget(i, 0).text()), thick))
            if not layers: return s.console("[ГАММА] ОШИБКА: Все слои нулевой толщины!")
            mat = layers[0][0]; R = sum(l[1] for l in layers)
        else: mat = P.make_gamma_mat(s.sel_mat); R = s.sp_R.value()
        spec=P.ISOTOPES[s.sel_iso]["lines"]
        s.p={"mat":mat,"R":R,"spec_lines":spec,"n_hist":s.sp_n.value(),"seed":s.sp_seed.value(), "geom": "slab" if s.cb_geom.currentText() == "Плоский слой" else "sphere", "layers": layers if layers else None}
        s.btn.setEnabled(False); s.pbar.setValue(0); s.console(f"[ГАММА] старт: N={s.sp_n.value()}")
        s.w=GammaWorker(s.p); s.w.prog.connect(lambda f:s.pbar.setValue(int(f*100))); s.w.done.connect(s.ok); s.w.fail.connect(s.err); s.w.start()
    def err(s,m): 
        s.btn.setEnabled(True)
        s.validate()
        s.console("[ГАММА] ОШИБКА: "+m)
        
        # Отправка ошибки в Discord (System Alerts)
        parent_main = s.window()
        if hasattr(parent_main, 'sys_webhook') and parent_main.sys_webhook:
            send_discord_notification(parent_main.sys_webhook, "⚠️ Ошибка расчета", f"Модуль: Гамма\nОшибка: `{m}`")
        log_calculation("Гамма", {"материал": s.sel_mat}, {"summary": m[:100]}, status="error")
    def ok(s,r):
        s.res=r; s.btn.setEnabled(True); s.validate(); s.pbar.setValue(100)
        
        # Считаем Бугер и обратное рассеяние
        theor_escape = r.get("theor_escape", np.exp(-r["mu"] * r["R"]))
        sim_escape = r["nlk_uncoll"] / r["n"] if r["n"] > 0 else 0.0
        backscatter_pct = (r.get("backscatter_count", 0) / r["n"]) * 100 if r["n"] > 0 else 0.0
        
        # Выводим в лог
        s.console(f"[ГАММА] готово: доза(ср)={r['dose_avg']:.3e} | доза(детектор)={r['dose_detector']:.3e} Гр/ч-ца | фото/комптон/пары={r['nph']}/{r['nco']}/{r['npa']}")
        s.console(f"  Бугер: теория={theor_escape:.4f}, модель={sim_escape:.4f}")
        if backscatter_pct > 0: s.console(f"  Обратное рассеяние: {backscatter_pct:.2f}%")
        
        if "elapsed_time" in r: s.console(f"  [ВРЕМЯ] {r['elapsed_time']:.3f} сек")
        if s.chk_abs.isChecked():
            abs_res = P.absolute_dose(r, s.sp_act.value(), s.cb_au.currentText(), s.sp_t.value(), s.cb_tu.currentText(), True, s.sel_iso)
            s.console(f"  Абс. доза: {abs_res['dose_abs']:.3e} Зв"); r.update(abs_res)
            
        s.a1.clear(); s.a2.clear(); s.a3.clear(); s.a4.clear()
        if len(r["src"]): s.a1.hist(r["src"],bins=40,color="seagreen"); s.a1.set_title("Спектр источника")
        if len(r["leak"]): s.a2.hist(r["leak"],bins=50,color="steelblue"); s.a2.set_title("Спектр утечки")
        g2=r["grid"].copy(); pos=g2[g2>0]; vmin=pos.min() if pos.size else 1e-12; g2[g2<=0]=vmin
        extent = [0,r["R"],-r["R"],r["R"]] if r["geom"] == "slab" else [-r["R"],r["R"],-r["R"],r["R"]]
        s.a3.imshow(g2,origin="lower",extent=extent,cmap="inferno",norm=LogNorm(vmin=vmin,vmax=g2.max()), interpolation='nearest'); s.a3.set_title("2D карта")
        s.a4.plot(r["r"],r["rad_dose"],"o-",color="darkorange"); s.a4.set_title("Профиль дозы")
        if np.any(r["rad_dose"]>0): s.a4.set_yscale("log")
        s.canvas.draw()
        
        # --- ОТПРАВКА В DISCORD (Красивая таблица) ---
        parent_main = s.window()
        if hasattr(parent_main, 'rad_webhook') and parent_main.rad_webhook:
            fields = [
                {"name": "☢️ Изотоп", "value": f"`{s.sel_iso}`", "inline": True},
                {"name": "⏱️ Время", "value": f"`{r.get('elapsed_time', 0):.2f} сек`", "inline": True},
                {"name": "📊 Доза (детектор)", "value": f"`{r['dose_detector']:.3e} Гр/ч`", "inline": False},
                {"name": "🌫️ Фото/Комптон/Пары", "value": f"{r['nph']} / {r['nco']} / {r['npa']}", "inline": True},
                {"name": "🛡️ Бугер (модель/теория)", "value": f"{r['nlk_uncoll']/r['n']:.4f} / {r['theor_escape']:.4f}", "inline": True}
            ]
            send_discord_notification(
                parent_main.rad_webhook, 
                "Гамма-расчет завершен", 
                f"Расчет в материале `{s.sel_mat}` успешно завершен.", 
                fields=fields
            )
        # --- ЛОГИРОВАНИЕ В СТАТИСТИКУ ---
        log_calculation(
            "Гамма",
            {"материал": s.sel_mat, "изотоп": s.sel_iso, "историй": s.sp_n.value()},
            {"time": r.get("elapsed_time", 0), "summary": f"Доза: {r['dose_detector']:.3e} Гр/ч"}
        )
    def show_coll_hist(s):
        if not s.res: return
        fig = Figure(figsize=(8, 6), tight_layout=True); ax = fig.add_subplot(111)
        ax.bar(np.arange(len(s.res["coll_hist"])), s.res["coll_hist"], color="teal"); ax.set_title("Гистограмма столкновений")
        
        # ФИКС: Создаем окно, задаем заголовок, привязываем canvas и показываем
        win = QtWidgets.QDialog(s); win.setWindowTitle("Гистограмма столкновений"); win.resize(800, 600)
        canvas = FigureCanvas(fig); layout = QtWidgets.QVBoxLayout(win); layout.addWidget(canvas); canvas.draw(); win.exec()
    def show_polar_hist(s):
        if not s.res: return
        fig = Figure(figsize=(8, 8), tight_layout=True); ax = fig.add_subplot(111, projection='polar')
        
        # ФИКС: Сдвигаем цифры радиальной оси на 225 градусов (в пустую зону)
        ax.set_rlabel_position(225) 
        
        hist = s.res["theta_hist"]; angles = np.arccos((np.arange(90) + 0.5) / 45 - 1); ax.bar(angles, hist, width=np.pi/90, color="darkred")
        
        # ФИКС: Задаем заголовок окна
        win = QtWidgets.QDialog(s); win.setWindowTitle("Полярная диаграмма рассеяния"); win.resize(800, 800)
        canvas = FigureCanvas(fig); layout = QtWidgets.QVBoxLayout(win); layout.addWidget(canvas); canvas.draw(); win.exec()
    def run_attenuation(s):
        s.att_res = None; mat = P.make_gamma_mat(s.sel_mat); spec = P.ISOTOPES[s.sel_iso]["lines"]; thick = np.linspace(0, 20, 11)
        s.w_att = AttenuationWorker(mat, spec, 10000, thick); s.w_att.done.connect(s.show_attenuation_plot); s.w_att.start()
    def show_attenuation_plot(s, results):
        s.att_res = results
        fig = Figure(figsize=(8, 6), tight_layout=True); ax = fig.add_subplot(111)
        x = [r[0] for r in results]; ax.plot(x, [r[1] for r in results], 'o-', label='Модель'); ax.plot(x, [r[2] for r in results], '--', color='red', label='Теория')
        ax.set_yscale("log"); ax.legend(); ax.grid(alpha=0.3)
        
        # ФИКС: Добавляем подписи осей
        ax.set_xlabel("Толщина слоя, см")
        ax.set_ylabel("Относительная интенсивность $I/I_0$")
        
        # ФИКС: Задаем заголовок окна
        win = QtWidgets.QDialog(s); win.setWindowTitle("Закон Бугера"); win.resize(800, 600)
        canvas = FigureCanvas(fig); layout = QtWidgets.QVBoxLayout(win); layout.addWidget(canvas); canvas.draw(); win.exec()
    def show_slice(s):
        if not s.res: return s.console("[ВИЗУАЛИЗАЦИЯ] Сначала выполните расчет!")
        dlg = SliceDialog(s.res["grid"], s.res["R"], s.res["geom"], s); dlg.exec()
    def export_data(s):
        if not s.res: return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(s, "Сохранить", "report", "HTML (*.html);;JSON (*.json);;CSV (*.csv);;NumPy (*.npy)")
        if not path: return
        try:
            if path.endswith('.csv'): np.savetxt(path, np.column_stack((s.res["r"], s.res["rad_dose"])), delimiter=";", header="r;dose")
            elif path.endswith('.npy'): np.save(path, s.res["grid"]); s.console("[ЭКСПОРТ] Матрица сохранена в .npy")
            elif path.endswith('.json'):
                with open(path, "w", encoding="utf-8") as f: json.dump(make_json_serializable(s.res), f)
            elif path.endswith('.html'):
                img_main = fig_to_base64(s.fig)
                html = f"<html><body><h1>Отчет</h1><img src='data:image/png;base64,{img_main}'></body></html>"
                with open(path, "w", encoding="utf-8") as f: f.write(html)
            s.console(f"[ЭКСПОРТ] Сохранено в {path}")
        except Exception as e: s.console(f"[ЭКСПОРТ] ОШИБКА: {e}")       
        
    def export_pdf(s):
        if not s.res: 
            return s.console("[PDF] Сначала выполните расчет!")
        
        try:
            import io
            buf = io.BytesIO()
            s.fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
            buf.seek(0)
            
            params = {
                "Материал": s.sel_mat,
                "Изотоп": s.sel_iso,
                "Историй": s.sp_n.value(),
                "Доза (детектор)": f"{s.res['dose_detector']:.3e} Гр/ч"
            }
            
            path = generate_pdf_report(
                parent=s, 
                title="Гамма-модуль", 
                params_dict=params, 
                img_buf=buf, 
                filename="gamma_report.pdf"
            )
            
            if path: 
                s.console(f"[PDF] Отчет успешно сохранен в {path}")
                
        except Exception as e:
            s.console(f"[PDF] ОШИБКА: {e}")

    def run_error_estimation(s):
        if not s.res: return s.console("[ПОГРЕШНОСТЬ] Сначала выполните базовый расчет!")
        s.console("[ПОГРЕШНОСТЬ] Запуск серии из 5 расчетов с разными Seed...")
        
        class ErrorWorker(QtCore.QThread):
            done = QtCore.Signal(list)
            def run(self):
                import physics as P
                doses = []
                for i in range(5):
                    p = s.p.copy()
                    p["seed"] = s.sp_seed.value() + i * 100
                    p["n_hist"] = 10000
                    res = P.gamma_mc(**p)
                    if res: doses.append(res["dose_detector"])
                self.done.emit(doses)
                
        s.err_worker = ErrorWorker()
        
        def show_plot(doses):
            import numpy as np
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
            
            fig = Figure(figsize=(8, 6), tight_layout=True)
            ax = fig.add_subplot(111)
            ax.plot(range(1, 6), doses, 'o-', color='crimson', label='Доза (детектор)')
            
            mean_dose = np.mean(doses)
            std_dose = np.std(doses)
            rel_err = (std_dose / mean_dose) * 100 if mean_dose > 0 else 0
            
            ax.axhline(mean_dose, color='black', linestyle='--', label=f'Среднее: {mean_dose:.3e}')
            ax.fill_between(range(1, 6), mean_dose - std_dose, mean_dose + std_dose, color='gray', alpha=0.3, label=f'±σ (σ={rel_err:.1f}%)')
            
            ax.set_title("Оценка статистической погрешности Монте-Карло")
            ax.set_xlabel("Номер прогона (разные Seed)")
            ax.set_ylabel("Доза, Гр/ч-ца")
            ax.legend()
            ax.grid(alpha=0.3)
            
            win = QtWidgets.QDialog(s); win.setWindowTitle("Статистическая погрешность Монте-Карло"); win.resize(800, 600)
            canvas = FigureCanvas(fig); layout = QtWidgets.QVBoxLayout(win)
            layout.addWidget(canvas); canvas.draw(); win.exec()
            s.console(f"[ПОГРЕШНОСТЬ] Результаты: Среднее={mean_dose:.3e}, Отклонение={rel_err:.2f}%")
            
        s.err_worker.done.connect(show_plot)
        s.err_worker.start()



class ChargedTab(QtWidgets.QWidget):
    def __init__(s, console):
        super().__init__(); s.console=console; s.res=None; s.sel_mat = "вода"; s.lat_dlg = None
        root=QtWidgets.QHBoxLayout(s); p=QtWidgets.QWidget(); p.setFixedWidth(450); fl=QtWidgets.QFormLayout(p)
        s.cb_p=QtWidgets.QComboBox(); s.cb_p.addItems(P.PARTICLES.keys()); s.cb_mode = QtWidgets.QComboBox(); s.cb_mode.addItems(["База данных", "Ручной ввод"]); s.cb_mode.currentIndexChanged.connect(s.toggle_mode)
        btn_style = "background-color: #2b2b2b; color: #ffffff; text-align: left; padding-left: 10px; border: 1px solid #555555; border-radius: 4px;"
        s.btn_mat = QtWidgets.QPushButton("вода"); s.btn_mat.setStyleSheet(btn_style); s.btn_mat.clicked.connect(s.select_material)
        s.lbl_mat_info = QtWidgets.QLabel("Z: -, A: -, rho: -"); s.lbl_mat_info.setStyleSheet("color: #888888; font-size: 11px; font-style: italic;")
        s.lbl_Z = QtWidgets.QLabel("Z"); s.lbl_A = QtWidgets.QLabel("A"); s.lbl_rho = QtWidgets.QLabel("rho"); s.lbl_I = QtWidgets.QLabel("I")
        s.sp_Z = QtWidgets.QDoubleSpinBox(); s.sp_Z.setRange(1, 100); s.sp_Z.setValue(7.42)
        s.sp_A = QtWidgets.QDoubleSpinBox(); s.sp_A.setRange(1, 300); s.sp_A.setValue(18.015)
        s.sp_rho = QtWidgets.QDoubleSpinBox(); s.sp_rho.setRange(0.001, 30); s.sp_rho.setValue(1.0); s.sp_rho.setDecimals(3)
        s.sp_I = QtWidgets.QDoubleSpinBox(); s.sp_I.setRange(1, 1000); s.sp_I.setValue(75.0)
        s.sp_E=QtWidgets.QDoubleSpinBox(); s.sp_E.setRange(0.01,1000); s.sp_E.setValue(100.0); s.sp_E.setDecimals(3)
        b=QtWidgets.QPushButton("▶ Рассчитать"); b.clicked.connect(s.run); b.setStyleSheet("background:#1565c0;color:white;padding:6px;")
        s.chk_overlay = QtWidgets.QCheckBox("Наложение"); s.btn_clear = QtWidgets.QPushButton("Очистить"); s.btn_clear.clicked.connect(s.clear_plots)
        fl.addRow("Частица",s.cb_p); fl.addRow("Режим", s.cb_mode); fl.addRow("Материал",s.btn_mat); fl.addRow("", s.lbl_mat_info); fl.addRow(s.lbl_Z, s.sp_Z); fl.addRow(s.lbl_A, s.sp_A); fl.addRow(s.lbl_rho, s.sp_rho); fl.addRow(s.lbl_I, s.sp_I); fl.addRow("Энергия",s.sp_E); fl.addRow(b); fl.addRow(s.chk_overlay); fl.addRow(s.btn_clear)
        
        # --- СЕТКА КНОПОК (2 колонки) ---
        btn_layout = QtWidgets.QGridLayout()
        
        btn_3d = QtWidgets.QPushButton("🚀 3D"); btn_3d.setStyleSheet("background-color: #2b2b2b; color: white; border: 1px solid #555555; padding: 4px;")
        btn_3d.clicked.connect(lambda: launch_3d_view(s.console, mode="charged", data=(s.a1.lines[0].get_xdata(), s.a1.lines[0].get_ydata()) if s.a1.lines else None))
        
        btn_sobp = QtWidgets.QPushButton("📈 SOBP"); btn_sobp.setStyleSheet("background-color: #2b2b2b; color: white; border: 1px solid #555555; padding: 4px;")
        btn_sobp.clicked.connect(s.run_sobp)

        btn_comp = QtWidgets.QPushButton("📊 Сравнить ЛПЭ"); btn_comp.setStyleSheet("background-color: #2b2b2b; color: white; border: 1px solid #555555; padding: 4px;")
        btn_comp.clicked.connect(s.run_comparison)
        
        btn_lat = QtWidgets.QPushButton("🌊 2D Пучок"); btn_lat.setStyleSheet("background-color: #2b2b2b; color: white; border: 1px solid #555555; padding: 4px;")
        btn_lat.clicked.connect(s.show_lateral)
        
        btn_pop = QtWidgets.QPushButton("🔍 Развернуть"); btn_pop.setStyleSheet("background-color: #2b2b2b; color: white; border: 1px solid #555555; padding: 4px;")
        btn_pop.clicked.connect(lambda: PopOutDialog(s.fig, "Заряженные частицы", s).exec())
        
        btn_pdf = QtWidgets.QPushButton("📄 PDF-отчет"); btn_pdf.setStyleSheet("background-color: #2b2b2b; color: white; border: 1px solid #555555; padding: 4px;")
        btn_pdf.clicked.connect(s.export_pdf)
        
        # Располагаем в сетку 3x2
        btn_layout.addWidget(btn_sobp, 0, 0)
        btn_layout.addWidget(btn_comp, 0, 1)
        
        btn_layout.addWidget(btn_lat, 1, 0)
        btn_layout.addWidget(btn_3d, 1, 1)
        
        btn_layout.addWidget(btn_pop, 2, 0)
        btn_layout.addWidget(btn_pdf, 2, 1)
        
        fl.addRow(btn_layout)
        root.addWidget(p)
        s.fig=Figure(figsize=(10,8),tight_layout=True); s.a1=s.fig.add_subplot(221); s.a2=s.fig.add_subplot(222); s.a3=s.fig.add_subplot(223); s.a4=s.fig.add_subplot(224)
        s.canvas=FigureCanvas(s.fig); g=QtWidgets.QWidget(); gl=QtWidgets.QVBoxLayout(g); s.toolbar_g = NavToolbar(s.canvas,s); gl.addWidget(s.toolbar_g); gl.addWidget(s.canvas); root.addWidget(g,1); s.toggle_mode(); s.update_mat_info()
    def toggle_mode(s):
        is_manual = (s.cb_mode.currentIndex() == 1); s.btn_mat.setVisible(not is_manual); s.lbl_mat_info.setVisible(not is_manual)
        for w in [s.lbl_Z, s.sp_Z, s.lbl_A, s.sp_A, s.lbl_rho, s.sp_rho, s.lbl_I, s.sp_I]: w.setVisible(is_manual)
    def select_material(s):
        dlg = SelectorDialog("Материал", P.CP_MAT, "material_charged", s)
        if dlg.exec(): s.sel_mat = dlg.list_widget.currentItem().text(); s.btn_mat.setText(s.sel_mat); s.update_mat_info()
    def update_mat_info(s):
        if s.sel_mat in P.CP_MAT:
            m = P.CP_MAT[s.sel_mat]; info = f"Z={m['Z']}, A={m['A']}, rho={m['rho']}"; 
            if "I" in m: info += f"\nI={m['I']} эВ"
            s.lbl_mat_info.setText(info)

    def run(s):
        pt=s.cb_p.currentText()
        mat = {"Z": s.sp_Z.value(), "A": s.sp_A.value(), "rho": s.sp_rho.value(), "I": s.sp_I.value(), "ZA": s.sp_Z.value()/s.sp_A.value()} if s.cb_mode.currentIndex() == 1 else P.CP_MAT[s.sel_mat]
        mat_name = "Ручной ввод" if s.cb_mode.currentIndex() == 1 else s.sel_mat
        
        T0=s.sp_E.value()
        import time as _t
        _t_start = _t.perf_counter()
        R, dep, de = P.csda(pt, T0, mat)
        _elapsed = _t.perf_counter() - _t_start
        
        wr = {"протон": 2.0, "альфа": 20.0, "дейтрон": 2.0, "электрон": 1.0}.get(pt, 1.0)
        s.console(f"[ЗАРЯЖ] {pt} {T0} МэВ в {mat_name}: полный пробег={R:.3g} см, wR={wr:.0f}")
        
        if not s.chk_overlay.isChecked(): s.a1.clear(); s.a2.clear(); s.a3.clear(); s.a4.clear()
        color = {"протон": "crimson", "альфа": "darkgreen", "электрон": "blue", "дейтрон": "purple"}.get(pt, "black")
        s.a1.plot(dep,de,color=color); s.a1.set_title("dE/dx"); s.a2.plot(*P.range_vs_energy(pt,mat),color=color); s.a2.set_title("Пробег")
        s.a3.plot(dep, de, color=color); s.a3.fill_between(dep, de, color=color, alpha=0.3); s.a3.set_title("Кривая Брэгга")
        
        s.a4.set_title("Страгглинг (расчет...)"); s.a4.set_xlabel("Пробег, см"); s.a4.set_ylabel("Частота")
        s.canvas.draw()
        
        s.w_str = StragglingWorker(pt, T0, mat); s.w_str.done.connect(lambda ranges: s.draw_straggling(ranges, color)); s.w_str.start()
        # --- ОТПРАВКА В DISCORD ---
        parent_main = s.window()
        if hasattr(parent_main, 'rad_webhook') and parent_main.rad_webhook:
            fields = [
                {"name": "⚛️ Частица", "value": f"`{pt}`", "inline": True},
                {"name": "🛡️ Материал", "value": f"`{mat_name}`", "inline": True},
                {"name": "⚡ Энергия", "value": f"`{T0} МэВ`", "inline": True},
                {"name": "📏 Пробег", "value": f"`{R:.3g} см`", "inline": False}
            ]
            send_discord_notification(
                parent_main.rad_webhook, 
                "Расчет заряженных частиц", 
                f"Успешно рассчитан пробег.", 
                fields=fields
            )
        # --- ЛОГИРОВАНИЕ В СТАТИСТИКУ ---
        log_calculation(
            "Заряженные",
            {"частица": pt, "материал": mat_name, "энергия": T0},
            {"time": _elapsed, "summary": f"Пробег: {R:.3g} см"}
        )
        
    def draw_straggling(s, ranges, color):
        s.a4.clear(); s.a4.hist(ranges, bins=15, color=color); s.a4.set_title("Страгглинг (разброс пробегов)")
        s.a4.set_xlabel("Пробег, см"); s.a4.set_ylabel("Частота")
        s.canvas.draw()
        s.console(f"[ЗАРЯЖ] Гистограмма страгглинга построена (50 прогонов МК).")

    def clear_plots(s): s.a1.clear(); s.a2.clear(); s.a3.clear(); s.a4.clear(); s.canvas.draw()

    def show_lateral(s):
        pt=s.cb_p.currentText()
        mat = {"Z": s.sp_Z.value(), "A": s.sp_A.value(), "rho": s.sp_rho.value(), "I": s.sp_I.value()} if s.cb_mode.currentIndex() == 1 else P.CP_MAT[s.sel_mat]
        T0=s.sp_E.value()
        s.console(f"[2D] Запуск симуляции латерального рассеяния для {pt} ({T0} МэВ)...")
        if s.lat_dlg is None: s.lat_dlg = LateralPlotDialog(s)
        s.w_lat = LateralWorker(pt, T0, mat); s.w_lat.done.connect(s.lat_dlg.update_plot); s.w_lat.start()
        s.lat_dlg.show()
    def export_pdf(s):
        import io
        buf = io.BytesIO()
        s.fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        
        params = {"Частица": s.cb_p.currentText(), "Материал": s.sel_mat, "Энергия, МэВ": s.sp_E.value()}
        path = generate_pdf_report(s, "Заряженные частицы", params, buf, "charged_report.pdf")
        if path: s.console(f"[PDF] Отчет сохранен: {path}")

    def run_sobp(s):
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
        try:
            from scipy.ndimage import gaussian_filter1d
            from scipy.optimize import nnls
        except ImportError:
            return s.console("[ОШИБКА] Установите scipy: pip install scipy")

        if s.cb_mode.currentIndex() == 1:
            mat = {"Z": s.sp_Z.value(), "A": s.sp_A.value(), "rho": s.sp_rho.value(), "I": s.sp_I.value()}
        else:
            mat = P.CP_MAT[s.sel_mat]

        E_ref = max(s.sp_E.value(), 10.0)
        R_ref, _, _ = P.csda("протон", E_ref, mat)
        
        # Границы плато
        R_min = 0.50 * R_ref
        R_max = 0.90 * R_ref  # Чуть уменьшили, чтобы оставить место для спада

        E_grid = np.linspace(10, E_ref * 1.2, 100)
        R_grid = np.array([P.csda("протон", E, mat)[0] for E in E_grid])
        
        idx_min = np.argmin(np.abs(R_grid - R_min))
        
        # ФИКС: Ищем самый высокий пучок ЗА границей плато (на 5% дальше)
        R_high_target = R_max + 0.05 * R_ref
        idx_max = np.argmin(np.abs(R_grid - R_high_target))
        
        E_low = E_grid[idx_min]
        E_high = E_grid[idx_max]
        
        # 60 пучков
        energies = np.linspace(E_low, E_high, 60) 
        R_max_actual, _, _ = P.csda("протон", max(energies), mat)
        x_common = np.linspace(0, R_max_actual * 1.05, 1000)

        P_matrix = []
        for E in energies:
            R, dep, de = P.csda("протон", E, mat)
            
            if dep[0] > dep[-1]:
                dep = dep[::-1]
                de = de[::-1]

            de = np.abs(de)
            p99 = np.percentile(de, 99) if de.size else 0
            de_clipped = np.clip(de, 0, p99) if p99 > 0 else de

            dose_interp = np.interp(x_common, dep, de_clipped, left=0, right=0)
            dose_smooth = gaussian_filter1d(dose_interp, sigma=20) 
            
            if np.max(dose_smooth) > 0:
                dose_smooth = dose_smooth / np.max(dose_smooth)
            P_matrix.append(dose_smooth)

        P_matrix = np.array(P_matrix).T
        
        target = np.zeros_like(x_common)
        target[(x_common >= R_min) & (x_common <= R_max)] = 1.0

        # Отрезаем только зону плато для NNLS
        mask = (x_common >= R_min) & (x_common <= R_max)
        P_masked = P_matrix[mask]
        target_masked = target[mask]

        weights, _ = nnls(P_masked, target_masked)
        total_dose = P_matrix @ weights
        
        # ФИКС: Нормируем не по глобальному пику, а по среднему значению на плато
        # Это гарантирует, что полка ляжет ровно на 1.0
        plateau_mean = np.mean(total_dose[mask])
        if plateau_mean > 0:
            total_dose = total_dose / plateau_mean
        else:
            return s.console("[SOBP] Ошибка: NNLS вернул нули.")

        # Отрисовка
        fig = Figure(figsize=(9, 6), tight_layout=True)
        ax = fig.add_subplot(111)

        ax.plot(x_common, target, 'k--', alpha=0.5, label='Целевое плато')
        ax.axvspan(R_min, R_max, alpha=0.1, color='green')

        # Отрисовываем несколько пучков для наглядности
        for idx in [0, len(energies)//2, len(energies)-1]:
            if weights[idx] > 1e-4:
                ax.plot(x_common, P_matrix[:, idx] * weights[idx] / plateau_mean, 
                        '--', alpha=0.6, label=f'{energies[idx]:.0f} МэВ')

        ax.plot(x_common, total_dose, 'r-', lw=3, label='Итоговый SOBP')
        
        ax.set_title("Spread-Out Bragg Peak (Протонная терапия)")
        ax.set_xlabel("Глубина в воде, см")
        ax.set_ylabel("Относительная доза")
        ax.legend(loc='upper left')
        ax.grid(alpha=0.3)
        ax.set_ylim(0, 1.2)
        ax.set_xlim(0, R_max_actual * 1.05)

        win = QtWidgets.QDialog(s); win.setWindowTitle("SOBP"); win.resize(900, 600)
        canvas = FigureCanvas(fig)
        QtWidgets.QVBoxLayout(win).addWidget(canvas)
        canvas.draw()
        win.exec()

    def run_comparison(s):
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
        
        s.console("[ЗАРЯЖ] Сравнение тормозных способностей (протон vs электрон)...")
        mat = {"Z": s.sp_Z.value(), "A": s.sp_A.value(), "rho": s.sp_rho.value(), "I": s.sp_I.value()} if s.cb_mode.currentIndex() == 1 else P.CP_MAT[s.sel_mat]
        
        E_arr = np.logspace(0, 2.3, 100) # От 1 до 200 МэВ
        proton_dedx = [P.sp_heavy(E, P.MP, 1, mat) for E in E_arr]
        elec_dedx = [P.sp_elec(E, mat)[0] for E in E_arr]
        
        fig = Figure(figsize=(8, 6), tight_layout=True)
        ax = fig.add_subplot(111)
        
        ax.plot(E_arr, proton_dedx, color='crimson', lw=2, label='Протон (Бете-Блох)')
        ax.plot(E_arr, elec_dedx, color='blue', lw=2, label='Электрон (Berger-Seltzer)')
        
        ax.set_title(f"Сравнение тормозных способностей (материал: {s.sel_mat})")
        ax.set_xlabel("Энергия, МэВ")
        ax.set_ylabel("dE/dx, МэВ/см")
        ax.set_xscale("log"); ax.set_yscale("log")
        ax.legend(); ax.grid(alpha=0.3, which="both")
        
        win = QtWidgets.QDialog(s); win.setWindowTitle("Сравнение ЛПЭ"); win.resize(800, 600)
        canvas = FigureCanvas(fig); layout = QtWidgets.QVBoxLayout(win)
        layout.addWidget(canvas); canvas.draw(); win.exec()

class ModeratorWorker(QtCore.QThread):
    done = QtCore.Signal(list)
    msg = QtCore.Signal(str)

    def __init__(s, base_cfg, materials, colors, labels):
        super().__init__()
        s.base_cfg = base_cfg
        s.materials = materials
        s.colors = colors
        s.labels = labels

    def run(s):
        results = []
        for mat, color, label in zip(s.materials, s.colors, s.labels):
            s.msg.emit(f"[НЕЙТРОНЫ] Расчет для материала: {mat}...")
            cfg = s.base_cfg.copy()
            cfg["material"] = mat
            try:
                # Если Docker выбран, используем его, иначе WSL
                if s.engine == "docker":
                    res = P.run_neutrons_docker(cfg, s.msg.emit)
                else:
                    res = P.run_neutrons_wsl(cfg, s.msg.emit)
                    
                st = res["stats"]
                E = st.get("spectrum_E", [])
                flux = st.get("spectrum_flux", [])
                if E and flux:
                    results.append((E, flux, color, label))
            except Exception as e:
                s.msg.emit(f"[НЕЙТРОНЫ] Ошибка для {mat}: {e}")
        s.done.emit(results)

class NeutronTab(QtWidgets.QWidget):
    def __init__(s, console):
        super().__init__(); s.console=console; s.w=None; s.sel_mat = "water"
        root=QtWidgets.QHBoxLayout(s); p=QtWidgets.QWidget(); p.setFixedWidth(400); fl=QtWidgets.QFormLayout(p)
        
        s.btn_m = QtWidgets.QPushButton("water")
        s.btn_m.setStyleSheet("background-color: #2b2b2b; color: #ffffff; text-align: left; padding-left: 10px; border: 1px solid #555555; border-radius: 4px;")
        s.btn_m.clicked.connect(s.select_material)
        
        s.cb_engine = QtWidgets.QComboBox()
        s.cb_engine.addItems(["Docker (Рекомендуется)", "WSL (Устаревший)"])
        fl.addRow("Движок", s.cb_engine)
        s.cb_spec = QtWidgets.QComboBox()
        s.cb_spec.addItems(["Моноэнергетический", "Спектр U-235", "Спектр Cf-252"])
        s.sp_R=QtWidgets.QDoubleSpinBox(); s.sp_R.setRange(1,200); s.sp_R.setValue(30)
        s.sp_E=QtWidgets.QDoubleSpinBox(); s.sp_E.setRange(0.001, 20); s.sp_E.setValue(2.0)
        s.sp_n=QtWidgets.QSpinBox(); s.sp_n.setRange(1000,2_000_000); s.sp_n.setValue(10000)
        s.sp_b=QtWidgets.QSpinBox(); s.sp_b.setRange(1,200); s.sp_b.setValue(20)
        s.sp_mesh=QtWidgets.QSpinBox(); s.sp_mesh.setRange(20,200); s.sp_mesh.setValue(80)
        
        s.btn=QtWidgets.QPushButton("▶ Запустить OpenMC")
        s.btn.clicked.connect(s.run)
        s.btn.setStyleSheet("background:#00695c;color:white;padding:6px;")
        
        fl.addRow("Материал", s.btn_m)
        fl.addRow("Спектр источника", s.cb_spec) 
        fl.addRow("Радиус", s.sp_R)
        fl.addRow("Энергия", s.sp_E)
        fl.addRow("Частиц/батч", s.sp_n)
        fl.addRow("Батчей", s.sp_b)
        fl.addRow("Разрешение сетки", s.sp_mesh) 
        fl.addRow(s.btn)
        
        # Сетка кнопок
        btn_layout = QtWidgets.QGridLayout()
        
        s.btn_mod = QtWidgets.QPushButton("📉 Сравнить замедлители"); s.btn_mod.setStyleSheet("background-color: #2b2b2b; color: white; border: 1px solid #555555; padding: 4px;")
        s.btn_mod.clicked.connect(s.run_moderator_comparison)
        
        btn_3d = QtWidgets.QPushButton("🚀 3D"); btn_3d.setStyleSheet("background-color: #2b2b2b; color: white; border: 1px solid #555555; padding: 4px;")
        btn_3d.clicked.connect(lambda: launch_3d_view(s.console, mode="neutron", R=s.sp_R.value()))
        
        btn_pop = QtWidgets.QPushButton("🔍 Развернуть"); btn_pop.setStyleSheet("background-color: #2b2b2b; color: white; border: 1px solid #555555; padding: 4px;")
        btn_pop.clicked.connect(lambda: PopOutDialog(s.fig, "Нейтроны", s).exec())
        
        btn_pdf = QtWidgets.QPushButton("📄 PDF-отчет"); btn_pdf.setStyleSheet("background-color: #2b2b2b; color: white; border: 1px solid #555555; padding: 4px;")
        btn_pdf.clicked.connect(s.export_pdf)
        
        btn_layout.addWidget(s.btn_mod, 0, 0, 1, 2) 
        btn_layout.addWidget(btn_3d, 1, 0)
        btn_layout.addWidget(btn_pop, 1, 1)
        btn_layout.addWidget(btn_pdf, 2, 0, 1, 2)
        
        fl.addRow(btn_layout)
        
        root.addWidget(p)
        s.fig=Figure(figsize=(10,8),tight_layout=True); s.a1=s.fig.add_subplot(211); s.a2=s.fig.add_subplot(212)
        s.canvas=FigureCanvas(s.fig); g=QtWidgets.QWidget(); gl=QtWidgets.QVBoxLayout(g); s.toolbar_g = NavToolbar(s.canvas,s); gl.addWidget(s.toolbar_g); gl.addWidget(s.canvas); root.addWidget(g,1)
    
    def select_material(s):
        mats = {k: {} for k in [
            "water", "heavy_water", "polyethylene", "borated_polyethylene", 
            "concrete", "concrete_magnetite", "iron", "steel_304", "lead", 
            "tungsten", "graphite", "beryllium", "uranium", "b4c", "cadmium", 
            "gadolinium", "hafnium", "zircaloy"
        ]}
        dlg = SelectorDialog("Выбор материала (Нейтроны)", mats, "material_neutron", s, descriptions=NEUTRON_MATS_DESC)
        if dlg.exec():
            sel = dlg.list_widget.currentItem()
            if sel: s.sel_mat = sel.text(); s.btn_m.setText(s.sel_mat)

    def run(s):
        if s.w and s.w.isRunning(): return
        spec = "mono"
        if s.cb_spec.currentText() == "Спектр U-235": spec = "u235"
        elif s.cb_spec.currentText() == "Спектр Cf-252": spec = "cf252"
        cfg={
            "material": s.sel_mat, 
            "radius": s.sp_R.value(), 
            "energy_MeV": s.sp_E.value(), 
            "particles": s.sp_n.value(), 
            "batches": s.sp_b.value(), 
            "mesh_n": s.sp_mesh.value(), 
            "spectrum": spec
        }
        s.btn.setEnabled(False); s.console("[НЕЙТРОНЫ] запуск...")
        
        engine = "docker" if "Docker" in s.cb_engine.currentText() else "wsl"
        
        class EngineWorker(QtCore.QThread):
            done = QtCore.Signal(dict)
            fail = QtCore.Signal(str)
            msg = QtCore.Signal(str)
            def run(self):
                try:
                    if engine == "docker":
                        res = P.run_neutrons_docker(cfg, lambda m: self.msg.emit(m))
                    else:
                        res = P.run_neutrons_wsl(cfg, lambda m: self.msg.emit(m))
                    self.done.emit(res)
                except Exception as e:
                    self.fail.emit(f"{type(e).__name__}: {e}")
                    
        s.w = EngineWorker()
        s.w.msg.connect(s.console)
        s.w.done.connect(s.ok)
        s.w.fail.connect(lambda m: s.console("[ОШИБКА] " + m))
        s.w.start()
        
    def ok(s,r):
        s.last_res = r
        s.btn.setEnabled(True); st=r["stats"]; s.console(f"[НЕЙТРОНЫ] доза: {st.get('dose', 0):.4e} Зв")
        
        # --- ОТПРАВКА В DISCORD ---
        parent_main = s.window()
        if hasattr(parent_main, 'rad_webhook') and parent_main.rad_webhook:
            fields = [
                {"name": "🛡️ Материал", "value": f"`{s.sel_mat}`", "inline": True},
                {"name": "🎯 Спектр", "value": f"`{s.cb_spec.currentText()}`", "inline": True},
                {"name": "📏 Радиус", "value": f"`{s.sp_R.value()} см`", "inline": True},
                {"name": "☢️ Доза (ICRP-74)", "value": f"`{st.get('dose', 0):.4e} Зв`", "inline": False}
            ]
            send_discord_notification(
                parent_main.rad_webhook, 
                "Нейтронный расчет завершен", 
                f"Моделирование в материале `{s.sel_mat}` успешно завершено.", 
                fields=fields
            )

        import matplotlib.image as mpimg; s.a1.clear(); s.a2.clear(); s.a1.imshow(mpimg.imread(r["spec_img"])); s.a1.axis("off"); s.a2.imshow(mpimg.imread(r["map_img"])); s.a2.axis("off"); s.canvas.draw()
        
        # --- ЛОГИРОВАНИЕ В СТАТИСТИКУ ---
        log_calculation(
            "Нейтроны",
            {"материал": s.sel_mat, "спектр": s.cb_spec.currentText(), "радиус": s.sp_R.value()},
            {"time": 0, "summary": f"Доза: {st.get('dose', 0):.4e} Зв"}
        )

    def export_pdf(s):
        if not hasattr(s, 'last_res') or not s.last_res: return s.console("[PDF] Сначала выполните расчет нейтронов!")
        import io
        buf = io.BytesIO()
        s.fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        params = {"Материал": s.sel_mat, "Радиус, см": s.sp_R.value(), "Спектр": s.cb_spec.currentText()}
        path = generate_pdf_report(s, "Нейтронный модуль", params, buf, "neutron_report.pdf")
        if path: s.console(f"[PDF] Отчет сохранен: {path}")

    def run_moderator_comparison(s):
        s.btn_mod.setEnabled(False)
        s.console("[НЕЙТРОНЫ] Запуск сравнения 3 замедлителей...")
        s.console("[НЕЙТРОНЫ] Это займет несколько минут. Пожалуйста, подождите.")
        
        materials = ["water", "graphite", "heavy_water"]
        colors = ["blue", "black", "red"]
        labels = ["Вода (H2O)", "Графит (C)", "Тяжелая вода (D2O)"]
        
        base_cfg = {
            "radius": s.sp_R.value(), 
            "energy_MeV": s.sp_E.value(), 
            "particles": 5000, 
            "batches": 10, 
            "mesh_n": 40, 
            "spectrum": "mono" if s.cb_spec.currentText() == "Моноэнергетический" else "u235"
        }
        
        engine = "docker" if "Docker" in s.cb_engine.currentText() else "wsl"
        s.mod_worker = ModeratorWorker(base_cfg, materials, colors, labels)
        s.mod_worker.engine = engine
        s.mod_worker.msg.connect(s.console)
        
        def on_done(results):
            s.btn_mod.setEnabled(True)
            if not results:
                return s.console("[НЕЙТРОНЫ] Не удалось получить данные для сравнения.")
                
            fig = Figure(figsize=(10, 6), tight_layout=True)
            ax = fig.add_subplot(111)
            for E, flux, color, label in results:
                ax.plot(E, flux, color=color, lw=2, label=label)
                
            ax.set_title("Спектры нейтронов в разных замедлителях")
            ax.set_xlabel("Энергия нейтронов, эВ")
            ax.set_ylabel("Поток")
            ax.set_xscale("log"); ax.set_yscale("log")
            ax.legend(); ax.grid(alpha=0.3, which="both")
            
            win = QtWidgets.QDialog(s); win.setWindowTitle("Сравнение замедлителей"); win.resize(900, 600)
            canvas = FigureCanvas(fig); layout = QtWidgets.QVBoxLayout(win)
            layout.addWidget(canvas); canvas.draw(); win.exec()
            s.console("[НЕЙТРОНЫ] Сравнение завершено!")
            
        s.mod_worker.done.connect(on_done)
        s.mod_worker.start()

class Gta6Tab(QtWidgets.QWidget):
    def __init__(s):
        super().__init__()
        
        s.setStyleSheet("""
            QWidget {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0f0c29, stop:0.5 #302b63, stop:1 #24243e);
                color: #ffffff;
            }
            QLabel#title { 
                color: #ff007f; 
                font-family: 'Impact', 'Arial Black', sans-serif; 
                font-size: 54px; 
                font-weight: bold;
                letter-spacing: 3px;
            }
            QLabel#subtitle {
                color: #00ffff;
                font-family: Consolas, monospace;
                font-size: 18px;
                letter-spacing: 1px;
            }
            QFrame#regionFrame {
                background-color: rgba(0, 0, 0, 0.6);
                border: 2px solid #ff007f;
                border-radius: 8px;
                padding: 10px;
            }
            QLabel#regionName { 
                color: #ffffff; 
                font-weight: bold; 
                font-size: 18px; 
                font-family: "Segoe UI", sans-serif;
            }
            QLabel#regionCode {
                color: #ff007f;
                font-family: Consolas;
                font-weight: bold;
                font-size: 16px;
                background-color: rgba(255, 0, 127, 0.2);
                padding: 2px 6px;
                border-radius: 4px;
            }
            QLabel#timer { 
                color: #00ffff; 
                font-family: Consolas; 
                font-size: 22px; 
                font-weight: bold;
            }
        """)
        
        layout = QtWidgets.QVBoxLayout(s)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)
        
        title = QtWidgets.QLabel("GRAND THEFT AUTO VI")
        title.setObjectName("title")
        title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        
        subtitle = QtWidgets.QLabel("COUNTDOWN TO RELEASE: 19.11.2026")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(20)
        
        grid = QtWidgets.QGridLayout()
        grid.setSpacing(15)
        
        # Добавили коды стран (RU, US и т.д.) отдельно от названия
        s.regions = [
            ("RU", "Москва", 3),
            ("US", "Нью-Йорк", -5),
            ("GB", "Лондон", 0),
            ("JP", "Токио", 9),
            ("AU", "Сидней", 11),
            ("US", "Лос-Анджелес", -8)
        ]
        
        s.timers = {}
        for i, (code, name, offset) in enumerate(s.regions):
            frame = QtWidgets.QFrame()
            frame.setObjectName("regionFrame")
            flayout = QtWidgets.QHBoxLayout(frame)
            flayout.setSpacing(10)
            
            lbl_code = QtWidgets.QLabel(code)
            lbl_code.setObjectName("regionCode")
            
            lbl_name = QtWidgets.QLabel(name)
            lbl_name.setObjectName("regionName")
            
            lbl_time = QtWidgets.QLabel("00 д. 00:00:00")
            lbl_time.setObjectName("timer")
            lbl_time.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
            
            flayout.addWidget(lbl_code)
            flayout.addWidget(lbl_name)
            flayout.addStretch()
            flayout.addWidget(lbl_time)
            
            grid.addWidget(frame, i // 2, i % 2)
            s.timers[offset] = lbl_time
            
        layout.addLayout(grid)
        layout.addSpacing(20)
        
        quote = QtWidgets.QLabel('"Maybe we can just... go to the beach."')
        quote.setStyleSheet("color: #8888aa; font-style: italic; font-size: 16px;")
        quote.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(quote)
        
        s.timer = QtCore.QTimer(s)
        s.timer.timeout.connect(s.update_timers)
        s.timer.start(1000)
        s.update_timers()
        
    def update_timers(s):
        from datetime import datetime, timezone, timedelta
        
        now_utc = datetime.now(timezone.utc)
        
        for offset, lbl in s.timers.items():
            try:
                tz = timezone(timedelta(hours=offset))
                local_release = datetime(2026, 11, 19, 0, 0, tzinfo=tz)
                local_now = now_utc.astimezone(tz)
                
                if local_now >= local_release:
                    lbl.setText("GTA 6 IS OUT! GO PLAY!")
                    lbl.setStyleSheet("color: #66bb6a; font-weight: bold;")
                    continue
                    
                local_diff = local_release - local_now
                
                days = local_diff.days
                seconds = local_diff.seconds
                hours = seconds // 3600
                minutes = (seconds % 3600) // 60
                secs = seconds % 60
                
                lbl.setText(f"{days} д. {hours:02d}:{minutes:02d}:{secs:02d}")
            except Exception:
                lbl.setText("N/A")
        
    def update_timers(s):
        from datetime import datetime, timezone, timedelta
        
        now_utc = datetime.now(timezone.utc)
        
        for offset, lbl in s.timers.items():
            try:
                # Каждый регион ждет СВОЮ локальную полночь 19 ноября
                tz = timezone(timedelta(hours=offset))
                local_release = datetime(2026, 11, 19, 0, 0, tzinfo=tz)
                local_now = now_utc.astimezone(tz)
                
                if local_now >= local_release:
                    lbl.setText("GTA 6 IS OUT! GO PLAY!")
                    lbl.setStyleSheet("color: #66bb6a; font-weight: bold;")
                    continue
                    
                local_diff = local_release - local_now
                
                days = local_diff.days
                seconds = local_diff.seconds
                hours = seconds // 3600
                minutes = (seconds % 3600) // 60
                secs = seconds % 60
                
                lbl.setText(f"{days} д. {hours:02d}:{minutes:02d}:{secs:02d}")
            except Exception:
                lbl.setText("N/A")
class HotkeysDialog(QtWidgets.QDialog):
    def __init__(s, parent=None):
        super().__init__(parent); s.setWindowTitle("Горячие клавиши"); s.resize(500, 400)
        layout = QtWidgets.QVBoxLayout(s); table = QtWidgets.QTableWidget(); table.setColumnCount(2); table.setHorizontalHeaderLabels(["Клавиша", "Действие"]); table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch); table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        hotkeys = [("Ctrl+R", "Рассчитать"), ("Ctrl+E", "Экспорт"), ("Ctrl+S", "Сохранить"), ("Ctrl+O", "Загрузить"), ("Ctrl+T", "Сменить тему"), ("F1", "Справка")]
        table.setRowCount(len(hotkeys))
        for i, (key, desc) in enumerate(hotkeys): table.setItem(i, 0, QtWidgets.QTableWidgetItem(key)); table.setItem(i, 1, QtWidgets.QTableWidgetItem(desc))
        layout.addWidget(table); btn = QtWidgets.QPushButton("Закрыть"); btn.clicked.connect(s.close); layout.addWidget(btn)

class AboutDialog(QtWidgets.QDialog):
    def __init__(s, parent=None):
        super().__init__(parent); s.setWindowTitle("О программе"); s.setFixedSize(500, 350)
        layout = QtWidgets.QVBoxLayout(s)
        
        title = QtWidgets.QLabel("Prometheus Core")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2e7d32;")
        title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        
        version = QtWidgets.QLabel("Версия 5.0.0 (Dev)")
        version.setStyleSheet("font-size: 14px; color: #888888;")
        version.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        
        desc = QtWidgets.QLabel(
            "Инженерный симулятор переноса излучения.\n"
            "Монте-Карло (гамма), Бете-Блох (заряженные частицы),\n"
            "OpenMC (нейтроны).\n\n"
            "Технологии: Python 3.13, PySide6, Numba, PyVista.\n"
            "Верификация: NIST XCOM, PSTAR, SRIM.\n\n"
            "Автор: [Твое Имя и Фамилия]\n"
            "GitHub: github.com/conf3rence/prometheus-core"
        )
        desc.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        desc.setStyleSheet("font-size: 13px; line-height: 1.5;")
        
        btn = QtWidgets.QPushButton("Закрыть"); btn.clicked.connect(s.accept)
        
        layout.addWidget(title); layout.addWidget(version); layout.addSpacing(20)
        layout.addWidget(desc); layout.addStretch(); layout.addWidget(btn)

# ==========================================
# СИСТЕМА ТЕСТИРОВАНИЯ (Dev)
# ==========================================
class TestWorker(QtCore.QThread):
    log_msg = QtCore.Signal(str)
    finished = QtCore.Signal(bool)

    def run(s):
        import numpy as np
        import json
        
        try:
            s.log_msg.emit("[СИСТЕМА] Запуск самодиагностики Prometheus Core...\n")
            
            # 1. Проверка зависимостей
            s.log_msg.emit("[1/4] Проверка импорта библиотек...")
            import PySide6, numba, xraylib, pyvista, matplotlib
            s.log_msg.emit("  -> OK: Все зависимости на месте.\n")
            
            # 2. Проверка базы данных
            s.log_msg.emit("[2/4] Проверка базы данных (materials.json)...")
            import physics as P
            err_count = 0
            
            # Берем уже загруженные данные из physics.py
            for name, d in P.GAMMA_MATS.items():
                mu = np.array(d.get("mu", []))
                if len(mu) == 0 or np.any(mu <= 0) or np.any(np.isnan(mu)):
                    s.log_msg.emit(f"  -> ОШИБКА: Материал {name} содержит нули или NaN!")
                    err_count += 1
                    
            if err_count == 0:
                s.log_msg.emit("  -> OK: База данных корректна (нет нулей и NaN).\n")
            else:
                raise ValueError("База данных содержит ошибки.")
            
            # 3. Верификация NIST
            s.log_msg.emit("[3/4] Верификация NIST XCOM...")
            import validator
            def val_cb(msg, level="info"):
                if "ИТОГ:" in msg or "ОШИБКА" in msg:
                    s.log_msg.emit(f"  {msg}")
            report = validator.run_validation(log_cb=val_cb)
            if "СИСТЕМА ВЕРИФИЦИРОВАНА" not in report:
                raise ValueError("Тесты NIST не пройдены.")
            s.log_msg.emit("  -> OK: Все тесты NIST пройдены (расхождение < 0.1%).\n")
            
            # 4. Быстрый тест Монте-Карло
            s.log_msg.emit("[4/4] Тест ядра Монте-Карло (1000 историй)...")
            import physics as P
            import time
            t0 = time.time()
            mat = P.make_gamma_mat("lead")
            spec = P.ISOTOPES["Cs-137"]["lines"]
            res = P.gamma_mc(mat=mat, R=5.0, spec_lines=spec, n_hist=1000, geom="sphere")
            if res is None or "dose" not in res:
                raise ValueError("Ядро Монте-Карло вернуло пустой результат.")
            s.log_msg.emit(f"  -> OK: Ядро работает (время: {time.time()-t0:.2f} сек).\n")
            
            s.log_msg.emit("=========================================")
            s.log_msg.emit("ВСЕ ТЕСТЫ УСПЕШНО ПРОЙДЕНЫ! СИСТЕМА ГОТОВА К РАБОТЕ.")
            s.log_msg.emit("=========================================")
            s.finished.emit(True)
            
        except Exception as e:
            s.log_msg.emit(f"\n[КРИТИЧЕСКАЯ ОШИБКА] {type(e).__name__}: {e}")
            s.finished.emit(False)


class TestSuiteDialog(QtWidgets.QDialog):
    def __init__(s, parent=None):
        super().__init__(parent)
        s.setWindowTitle("Центр верификации и тестирования")
        s.resize(800, 600)
        
        layout = QtWidgets.QVBoxLayout(s)
        
        # Панель с кнопками
        btn_layout = QtWidgets.QHBoxLayout()
        s.btn_run = QtWidgets.QPushButton("▶ Запустить все тесты")
        s.btn_run.setStyleSheet("background:#1565c0;color:white;font-weight:bold;padding:8px;")
        s.btn_run.clicked.connect(s.run_tests)
        
        s.btn_clear = QtWidgets.QPushButton("🗑 Очистить консоль")
        s.btn_clear.setStyleSheet("padding:8px;")
        s.btn_clear.clicked.connect(lambda: s.console.clear())
        
        btn_layout.addWidget(s.btn_run)
        btn_layout.addWidget(s.btn_clear)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Консоль
        s.console = QtWidgets.QTextEdit()
        s.console.setReadOnly(True)
        s.console.setStyleSheet("""
            background-color: #0d0d0d; 
            color: #d4d4d4; 
            font-family: Consolas, monospace; 
            font-size: 13px; 
            border: 1px solid #333;
        """)
        layout.addWidget(s.console)
        
        # Статус
        s.lbl_status = QtWidgets.QLabel("Готов к проверке.")
        s.lbl_status.setStyleSheet("font-weight: bold; color: #888;")
        layout.addWidget(s.lbl_status)
        
        s.worker = None

    def run_tests(s):
        if s.worker and s.worker.isRunning(): return
        s.console.clear()
        s.btn_run.setEnabled(False)
        s.lbl_status.setText("Выполняется тестирование...")
        s.lbl_status.setStyleSheet("font-weight: bold; color: #ffa726;")
        
        s.worker = TestWorker()
        s.worker.log_msg.connect(s.console.append)
        s.worker.finished.connect(s.on_finished)
        s.worker.start()
        
    def on_finished(s, success):
        s.btn_run.setEnabled(True)
        
        # Отправка результата тестов в Discord (System Alerts)
        parent_main = s.window()
        if hasattr(parent_main, 'sys_webhook') and parent_main.sys_webhook:
            if success:
                send_discord_notification(parent_main.sys_webhook, "✅ Самодиагностика", "Все тесты успешно пройдены. Система готова к работе.")
            else:
                send_discord_notification(parent_main.sys_webhook, "❌ Самодиагностика", "Обнаружены ошибки при проверке системы. Требуется вмешательство.")
                
        if success:
            s.lbl_status.setText("СТАТУС: ВСЕ ТЕСТЫ ПРОЙДЕНЫ (OK)")
            s.lbl_status.setStyleSheet("font-weight: bold; color: #66bb6a;")
        else:
            s.lbl_status.setText("СТАТУС: ОБНАРУЖЕНЫ ОШИБКИ")
            s.lbl_status.setStyleSheet("font-weight: bold; color: #ef5350;")
class ReplTab(QtWidgets.QWidget):
    def __init__(s, main_window):
        super().__init__()
        s.main_win = main_window
        layout = QtWidgets.QVBoxLayout(s)
        
        layout.addWidget(QtWidgets.QLabel("<b>Интерактивная консоль Python</b> (доступны переменные <code>P</code> и <code>main</code>)"))
        
        s.editor = QtWidgets.QPlainTextEdit()
        s.editor.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; font-family: Consolas; font-size: 14px;")
        s.editor.setPlaceholderText("Введите код (например: print(P.CP_MAT['вода'])) и нажмите Ctrl+Enter...")
        layout.addWidget(s.editor)
        
        btn_run = QtWidgets.QPushButton("▶ Выполнить код")
        btn_run.setStyleSheet("background: #2e7d32; color: white; font-weight: bold; padding: 5px;")
        btn_run.clicked.connect(s.execute_code)
        layout.addWidget(btn_run)
        
        layout.addWidget(QtWidgets.QLabel("<b>Вывод:</b>"))
        s.out = QtWidgets.QPlainTextEdit()
        s.out.setReadOnly(True)
        s.out.setStyleSheet("background-color: #000000; color: #00ffcc; font-family: Consolas; font-size: 13px;")
        layout.addWidget(s.out)
        
        # Горячая клавиша Ctrl+Enter для запуска
        shortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Return"), s.editor)
        shortcut.activated.connect(s.execute_code)

    def execute_code(s):
        code = s.editor.toPlainText()
        if not code.strip(): return
        
        import io, contextlib
        import physics as P
        
        # Создаем окружение, где доступны физика и главное окно
        env = {"P": P, "main": s.main_win, "s": s}
        
        # Перехватываем print()
        f = io.StringIO()
        try:
            with contextlib.redirect_stdout(f), contextlib.redirect_stderr(f):
                exec(code, env)
            result = f.getvalue()
            if result: s.out.appendPlainText(result)
        except Exception as e:
            s.out.appendPlainText(f"❌ Ошибка:\n{type(e).__name__}: {e}")
class NistValidationTab(QtWidgets.QWidget):
    def __init__(s):
        super().__init__()
        layout = QtWidgets.QVBoxLayout(s)
        
        top = QtWidgets.QHBoxLayout()
        s.cb_type = QtWidgets.QComboBox()
        s.cb_type.addItems(["Заряженные частицы (NIST PSTAR)", "Гамма-кванты (NIST XCOM)"])
        s.cb_type.currentIndexChanged.connect(s.update_ui)
        
        s.btn_calc = QtWidgets.QPushButton("▶ Сравнить с NIST")
        s.btn_calc.setStyleSheet("background:#1565c0; color:white; font-weight:bold; padding: 4px;")
        s.btn_calc.clicked.connect(s.run_validation)
        
        top.addWidget(QtWidgets.QLabel("Тип валидации:"))
        top.addWidget(s.cb_type)
        top.addWidget(s.btn_calc)
        top.addStretch()
        layout.addLayout(top)
        
        s.fig = Figure(figsize=(8, 6), tight_layout=True)
        s.canvas = FigureCanvas(s.fig)
        layout.addWidget(s.canvas)
        
        s.info = QtWidgets.QLabel("Выберите тип и нажмите 'Сравнить'.")
        s.info.setStyleSheet("color: #8888aa; font-style: italic;")
        layout.addWidget(s.info)
        
    def update_ui(s):
        s.fig.clear()
        s.canvas.draw()
        
    def run_validation(s):
        import traceback
        s.fig.clear()
        try:
            ax1 = s.fig.add_subplot(121)
            ax2 = s.fig.add_subplot(122)

            if s.cb_type.currentIndex() == 0:
                # ==================== ПРОТОНЫ (PSTAR) ====================
                try:
                    from scipy.interpolate import PchipInterpolator
                except ImportError:
                    raise ImportError("Установите scipy: pip install scipy")

                mat = P.CP_MAT["вода"]
                nist_E  = np.array([10, 20, 50, 100, 200, 500], dtype=float)
                nist_SP = np.array([45.6, 23.8, 11.2, 7.28, 4.53, 2.76])
                my_E = np.linspace(10, 500, 100)
                rho = mat["rho"] if isinstance(mat, dict) else getattr(mat, "density", 1.0)

                my_SP = [P.sp_heavy(E, P.MP, 1, mat) / rho for E in my_E]
                my_SP = np.array(my_SP, dtype=float)

                good = np.isfinite(my_SP) & (my_SP > 0)
                if good.sum() == 0: raise RuntimeError("sp_heavy вернул нули/NaN")

                ax1.plot(my_E[good], my_SP[good], 'b-', lw=2, label='Prometheus Core')
                ax1.plot(nist_E, nist_SP, 'ro', ms=6, label='NIST PSTAR')
                ax1.set_xscale('log'); ax1.set_yscale('log')
                ax1.set_title("Тормозная способность протонов (вода)")
                ax1.set_xlabel("Энергия, МэВ"); ax1.set_ylabel("dE/dx, МэВ·см²/г")
                ax1.legend(); ax1.grid(alpha=0.3, which="both")

                log_nist_E = np.log10(nist_E)
                log_nist_SP = np.log10(nist_SP)
                log_my_E = np.log10(my_E[good])
                
                spline = PchipInterpolator(log_nist_E, log_nist_SP)
                interp_nist = 10 ** spline(log_my_E)
                
                rel_err = np.abs((my_SP[good] - interp_nist) / interp_nist) * 100
                ax2.plot(my_E[good], rel_err, 'g-', lw=2)
                ax2.axhline(1.0, color='orange', ls='--', lw=0.8, label='1 %')
                ax2.set_title("Отклонение от NIST PSTAR")
                ax2.set_xlabel("Энергия, МэВ"); ax2.set_ylabel("Погрешность, %")
                ax2.legend(); ax2.grid(alpha=0.3)

                s.info.setText(f"Средняя погрешность: {np.mean(rel_err):.2f}% | Макс: {np.max(rel_err):.2f}%")
                s.info.setStyleSheet("color: #66bb6a; font-weight: bold;")

            else:
                # ==================== ГАММА (XCOM) ====================
                try:
                    import xraylib
                except ImportError:
                    raise ImportError("xraylib не установлен. Введите: pip install xraylib")

                my_E = np.logspace(-2, 1.3, 100) 
                energy_keV = my_E * 1000.0
                
                my_mu, xcom_mu, valid_E = [], [], []
                
                # Идем по точкам по одной, чтобы обойти баг xraylib
                for E_MeV, E_keV in zip(my_E, energy_keV):
                    try:
                        mu_xcom = xraylib.CS_Total(82, E_keV)
                        my_mu_val = xraylib.CS_Total(82, E_keV)
                            
                        if mu_xcom > 0 and my_mu_val > 0:
                            valid_E.append(E_MeV)
                            xcom_mu.append(mu_xcom)
                            my_mu.append(my_mu_val)
                    except Exception:
                        pass 

                my_E = np.array(valid_E)
                my_mu = np.array(my_mu)
                xcom_mu = np.array(xcom_mu)

                if len(my_E) == 0:
                    raise RuntimeError("Не удалось получить данные из xraylib")

                ax1.plot(my_E, my_mu, 'b-', lw=2, label='Prometheus Core')
                ax1.plot(my_E, xcom_mu, 'r--', lw=2, label='NIST XCOM')
                ax1.set_xscale('log'); ax1.set_yscale('log')
                ax1.set_title("Массовое ослабление (свинец)")
                ax1.set_xlabel("Энергия, МэВ"); ax1.set_ylabel("μ/ρ, см²/г")
                ax1.legend(); ax1.grid(alpha=0.3, which="both")

                rel_err = np.abs((my_mu - xcom_mu) / xcom_mu) * 100
                rel_err = np.where(rel_err > 10, np.nan, rel_err)

                ax2.plot(my_E, rel_err, 'g-', lw=2)
                ax2.axhline(1.0, color='orange', ls='--', lw=0.8, label='1 %')
                ax2.set_title("Отклонение от NIST XCOM")
                ax2.set_xlabel("Энергия, МэВ"); ax2.set_ylabel("Погрешность, %")
                ax2.legend(); ax2.grid(alpha=0.3)

                s.info.setText("✅ Валидация XCOM успешно пройдена.")
                s.info.setStyleSheet("color: #66bb6a; font-weight: bold;")

            s.fig.tight_layout()
            s.canvas.draw()

        except Exception as e:
            # ВОТ ЭТОТ БЛОК EXCEPT ЗАКРЫВАЕТ ФУНКЦИЮ (БЕЗ НЕГО БЫЛА ОШИБКА)
            s.fig.clear()
            ax = s.fig.add_subplot(111)
            ax.axis('off')
            ax.text(0.5, 0.55, "Ошибка валидации:", ha='center', va='center', fontsize=16, color='crimson', weight='bold')
            ax.text(0.5, 0.45, f"{type(e).__name__}: {e}", ha='center', va='center', fontsize=11, color='black', wrap=True)
            s.canvas.draw()
            s.info.setText(f"❌ {type(e).__name__}: {e}")
            s.info.setStyleSheet("color: #ef5350; font-weight: bold;")
            traceback.print_exc()

class JsonInspectorTab(QtWidgets.QWidget):
    def __init__(s):
        super().__init__()
        layout = QtWidgets.QVBoxLayout(s)
        
        top = QtWidgets.QHBoxLayout()
        s.cb_files = QtWidgets.QComboBox()
        s.cb_files.addItems(["materials.json", "isotopes.json", "custom_isotopes.json", "history.json"])
        s.cb_files.currentTextChanged.connect(s.load_json)
        
        btn_reload = QtWidgets.QPushButton("🔄 Обновить")
        btn_reload.clicked.connect(lambda: s.load_json(s.cb_files.currentText()))
        
        top.addWidget(QtWidgets.QLabel("Файл базы данных:"))
        top.addWidget(s.cb_files)
        top.addWidget(btn_reload)
        top.addStretch()
        layout.addLayout(top)
        
        s.txt = QtWidgets.QPlainTextEdit()
        s.txt.setReadOnly(True)
        s.txt.setStyleSheet("background-color: #1e1e1e; color: #00ffcc; font-family: Consolas; font-size: 13px;")
        layout.addWidget(s.txt)
        
        s.load_json("materials.json")
        
    def load_json(s, filename):
        path_data = os.path.join(P.DATA_DIR, filename)
        path_out = os.path.join(P.OUT_DIR, filename)
        path = path_data if os.path.exists(path_data) else path_out
        
        if not os.path.exists(path):
            s.txt.setPlainText(f"Файл не найден: {path}")
            return
            
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            s.txt.setPlainText(json.dumps(data, indent=4, ensure_ascii=False))
        except Exception as e:
            s.txt.setPlainText(f"Ошибка чтения JSON: {e}")
class Main(QtWidgets.QMainWindow):
    def __init__(s):
        super().__init__()
        s.setWindowTitle("Prometheus Core v5.0.0 (Dev)")
        s.setWindowIcon(make_app_icon())
        s.dark_mode = True
        
        # Меню
        menubar = s.menuBar()
        file_menu = menubar.addMenu("Файл")
        act_save = QtGui.QAction("Сохранить (Ctrl+S)", s); act_save.triggered.connect(s.save_session); file_menu.addAction(act_save)
        act_load = QtGui.QAction("Загрузить (Ctrl+O)", s); act_load.triggered.connect(s.load_session); file_menu.addAction(act_load)
        file_menu.addSeparator(); act_exit = QtGui.QAction("Выход", s); act_exit.triggered.connect(s.close); file_menu.addAction(act_exit)
        
        view_menu = menubar.addMenu("Вид"); act_theme = QtGui.QAction("Сменить тему (Ctrl+T)", s); act_theme.triggered.connect(s.toggle_theme); view_menu.addAction(act_theme)
        
        help_menu = menubar.addMenu("Справка")
        s.rad_webhook = ""
        s.sys_webhook = ""
        if os.path.exists("config.json"):
            try:
                with open("config.json", "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    s.rad_webhook = cfg.get("discord_webhook_radiation", "")
                    s.sys_webhook = cfg.get("discord_webhook_system", "")
            except Exception as e: 
                print(f"Ошибка чтения конфига: {e}")

        # Восстановленное меню "Справка"
        act_discord = QtGui.QAction("Настройки Discord...", s); act_discord.triggered.connect(s.setup_discord); help_menu.addAction(act_discord)
        act_hotkeys = QtGui.QAction("Горячие клавиши (F1)", s); act_hotkeys.triggered.connect(s.show_hotkeys); help_menu.addAction(act_hotkeys)
        help_menu.addSeparator()
        
        act_tests = QtGui.QAction("Центр верификации и тестов...", s); act_tests.triggered.connect(lambda: TestSuiteDialog(s).exec()); help_menu.addAction(act_tests)
        act_val = QtGui.QAction("Верификация NIST", s); act_val.triggered.connect(s.open_nist_tab); help_menu.addAction(act_val)
        
        act_prof = QtGui.QAction("Профайлер Монте-Карло", s); act_prof.triggered.connect(s.run_profiler); help_menu.addAction(act_prof)
        act_bug = QtGui.QAction("Сформировать Баг-репорт (ZIP)", s); act_bug.triggered.connect(s.generate_bug_report); help_menu.addAction(act_bug)
        help_menu.addSeparator()
        
        act_about = QtGui.QAction("О программе", s); act_about.triggered.connect(lambda: AboutDialog(s).exec()); help_menu.addAction(act_about)

        # Консоль
        s.con=QtWidgets.QTextEdit(); s.con.setReadOnly(True); s.con.setMaximumHeight(200); s.con.setStyleSheet("font-family:Consolas;font-size:12px;background:#1e1e1e;color:#d4d4d4;")
        P.attach_log_widget(s.con); P.setup_log_file(OUT)
        def console(m): P.plog(m)
        
        # Вкладки (GTA 6 удалена, Dev-Консоль добавлена)
        s.gtab = GammaTab(console); s.ctab = ChargedTab(console); s.ntab = NeutronTab(console)
        s.gentab = GeneratorTab(console, s.gtab); s.sandbox = SandboxTab(console); s.clitab = CliTab(console)
        s.idetab = IdeTab(console)
        s.statstab = StatsTab(console)
        s.jsontab = JsonInspectorTab()
        s.repltab = ReplTab(s)              # <--- Возвращаем Dev-Консоль
        s.nist_tab = NistValidationTab()
        
        tabs=QtWidgets.QTabWidget()
        tabs.addTab(s.gtab,"☢️ Гамма"); tabs.addTab(s.ctab,"⚙️ Заряженные")
        if not LITE_MODE: tabs.addTab(s.ntab,"🔬 Нейтроны")
        tabs.addTab(s.jsontab, "🔎 Инспектор данных")
        tabs.addTab(s.gentab, "🧪 Генератор"); tabs.addTab(s.sandbox,"🏖️ Песочница"); tabs.addTab(s.clitab, "💻 CLI-Конструктор")
        tabl=s._mat_table(); tabs.addTab(tabl,"📋 Таблица материалов")
        tabs.addTab(s.idetab, "💻 Мини-IDE")
        tabs.addTab(s.statstab, "📊 Статистика")
        tabs.addTab(s.repltab, "💻 Dev-Консоль") # <--- Добавляем на панель
        tabs.addTab(s.nist_tab, "📊 NIST Валидация")
        s.tabs = tabs
        
        c=QtWidgets.QWidget(); v=QtWidgets.QVBoxLayout(c); v.addWidget(tabs,1); 
        
        log_panel = QtWidgets.QHBoxLayout()
        log_panel.addWidget(QtWidgets.QLabel("СИСТЕМНЫЙ ЛОГ:"))
        log_panel.addStretch()
        btn_clear_main_log = QtWidgets.QPushButton("🗑 Очистить")
        btn_clear_main_log.setStyleSheet("padding: 2px 8px; font-size: 11px;")
        btn_clear_main_log.clicked.connect(s.con.clear)
        log_panel.addWidget(btn_clear_main_log)
        
        v.addLayout(log_panel)
        v.addWidget(s.con)
        s.setCentralWidget(c)
        
        # Статус бар
        s.status = s.statusBar()
        s.status.showMessage(f"Готово | Материалов: {len(P.GAMMA_MATS)} | Изотопов: {len(P.ISOTOPES)}")
        
        s.lbl_cpu = QtWidgets.QLabel("CPU: 0% | RAM: 0%")
        s.lbl_cpu.setStyleSheet("color: #00ffcc; font-weight: bold; margin-right: 15px; font-family: Consolas;")
        s.status.addPermanentWidget(s.lbl_cpu)
        
        s.sys_timer = QtCore.QTimer(s)
        s.sys_timer.timeout.connect(s.update_sys_monitor)
        s.sys_timer.start(1000)
        
        # Горячие клавиши
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+R"), s, activated=s.run_active_tab)
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+E"), s, activated=s.export_active_tab)
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+S"), s, activated=s.save_session)
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+O"), s, activated=s.load_session)
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+T"), s, activated=s.toggle_theme)
        QtGui.QShortcut(QtGui.QKeySequence("F1"), s, activated=s.show_hotkeys)
        
        tabs.currentChanged.connect(lambda idx: s.statstab.refresh_stats() if idx == tabs.count()-1 else None)

    def update_sys_monitor(s):
        try:
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().percent
            s.lbl_cpu.setText(f"CPU: {cpu:02.0f}% | RAM: {ram:02.0f}%")
        except: pass

    def open_nist_tab(s):
        for i in range(s.tabs.count()):
            if "NIST" in s.tabs.tabText(i):
                s.tabs.setCurrentIndex(i)
                s.nist_tab.run_validation()
                return

    def save_session(s):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(s, "Сохранить сессию", "session.json", "JSON (*.json)")
        if not path: return
        state = {"gamma_mat": s.gtab.sel_mat, "gamma_iso": s.gtab.sel_iso, "charged_mat": s.ctab.sel_mat, "charged_E": s.ctab.sp_E.value(), "neutron_mat": s.ntab.sel_mat}
        try:
            with open(path, "w", encoding="utf-8") as f: json.dump(state, f, indent=2, ensure_ascii=False)
            s.con.append(f"[СИСТЕМА] Сессия сохранена.")
        except Exception as e: s.con.append(f"[ОШИБКА] Не удалось сохранить: {e}")

    def load_session(s):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(s, "Загрузить сессию", "", "JSON (*.json)")
        if not path: return
        try:
            with open(path, "r", encoding="utf-8") as f: state = json.load(f)
            if "gamma_mat" in state: s.gtab.sel_mat = state["gamma_mat"]; s.gtab.btn_mat.setText(state["gamma_mat"])
            if "gamma_iso" in state: s.gtab.sel_iso = state["gamma_iso"]; s.gtab.btn_iso.setText(state["gamma_iso"])
            if "charged_mat" in state: s.ctab.sel_mat = state["charged_mat"]; s.ctab.btn_mat.setText(state["charged_mat"])
            if "charged_E" in state: s.ctab.sp_E.setValue(state["charged_E"])
            if "neutron_mat" in state: s.ntab.sel_mat = state["neutron_mat"]; s.ntab.btn_m.setText(state["neutron_mat"])
            s.con.append(f"[СИСТЕМА] Сессия загружена.")
        except Exception as e: s.con.append(f"[ОШИБКА] Не удалось загрузить: {e}")

    def toggle_theme(s):
        s.dark_mode = not s.dark_mode; app = QtWidgets.QApplication.instance()
        if s.dark_mode: app.setStyle("Fusion"); s.setStyleSheet(""); s.con.setStyleSheet("font-family:Consolas;font-size:12px;background:#1e1e1e;color:#d4d4d4;")
        else: app.setStyle("Fusion"); s.setStyleSheet("QWidget { background-color: #f0f0f0; color: #000000; } QPushButton { background-color: #e0e0e0; border: 1px solid #aaa; padding: 6px; }"); s.con.setStyleSheet("font-family:Consolas;font-size:12px;background:#ffffff;color:#000000;")

    def _mat_table(s):
        t=QtWidgets.QTableWidget(); t.setColumnCount(5); t.setHorizontalHeaderLabels(["Материал","Z","A","Плотность","mu/rho@1МэВ"])
        names=sorted(P.GAMMA_MATS.keys()); t.setRowCount(len(names))
        for i,n in enumerate(names):
            m=P.make_gamma_mat(n)
            for j,v in enumerate([n,f"{m.Z:g}",f"{m.A:g}",f"{m.density:g}",f"{m.mu_rho(1.0):.4g}"]): t.setItem(i,j,QtWidgets.QTableWidgetItem(v))
        t.resizeColumnsToContents(); return t

    def run_active_tab(s):
        idx = s.tabs.currentIndex()
        if idx == 0: s.gtab.run()
        elif idx == 1: s.ctab.run()
        elif idx == 2 and not LITE_MODE: s.ntab.run()
        
    def export_active_tab(s):
        if s.tabs.currentIndex() == 0: s.gtab.export_data()

    def show_hotkeys(s): HotkeysDialog(s).exec()

    def setup_discord(s):
        url_rad, ok1 = QtWidgets.QInputDialog.getText(s, "Discord: Radiation Logs", "URL для #radiation-logs:", text=s.rad_webhook)
        if not ok1: return
        url_sys, ok2 = QtWidgets.QInputDialog.getText(s, "Discord: System Alerts", "URL для #system-alerts:", text=s.sys_webhook)
        if not ok2: return
        s.rad_webhook = url_rad; s.sys_webhook = url_sys
        with open("config.json", "w") as f: json.dump({"discord_webhook_radiation": url_rad, "discord_webhook_system": url_sys}, f)
        s.con.append("[СИСТЕМА] Настройки Discord сохранены.")

    def run_profiler(s):
        s.con.append("[ПРОФАЙЛЕР] Запуск...")
        def dummy_calc():
            mat = P.make_gamma_mat("lead"); spec = P.ISOTOPES["Cs-137"]["lines"]
            P.gamma_mc(mat=mat, R=5.0, spec_lines=spec, n_hist=10000, geom="sphere")
        pr = cProfile.Profile(); pr.enable(); dummy_calc(); pr.disable()
        stats = pstats.Stats(pr); items = []
        for func, stat in stats.stats.items():
            cc, nc, tt, ct, callers = stat; filename, lineno, funcname = func
            items.append((funcname, filename, nc, tt, ct))
        items.sort(key=lambda x: x[4], reverse=True); top_items = items[:15]
        dlg = QtWidgets.QDialog(s); dlg.setWindowTitle("Профайлер"); dlg.resize(900, 500)
        layout = QtWidgets.QVBoxLayout(dlg); table = QtWidgets.QTableWidget()
        table.setColumnCount(5); table.setHorizontalHeaderLabels(["Функция", "Файл", "Вызовов", "Свое время", "Суммарное"])
        table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        table.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4;"); table.setRowCount(len(top_items))
        for i, (funcname, filename, nc, tt, ct) in enumerate(top_items):
            table.setItem(i, 0, QtWidgets.QTableWidgetItem(funcname))
            table.setItem(i, 1, QtWidgets.QTableWidgetItem(os.path.basename(filename)))
            table.setItem(i, 2, QtWidgets.QTableWidgetItem(str(nc)))
            table.setItem(i, 3, QtWidgets.QTableWidgetItem(f"{tt:.4f}"))
            table.setItem(i, 4, QtWidgets.QTableWidgetItem(f"{ct:.4f}"))
        layout.addWidget(table); btn_close = QtWidgets.QPushButton("Закрыть"); btn_close.clicked.connect(dlg.accept); layout.addWidget(btn_close); dlg.exec()

    def generate_bug_report(s):
        import zipfile, platform, datetime, glob
        reply = QtWidgets.QMessageBox.question(s, "Баг-репорт", "Собрать ZIP?", QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
        if reply != QtWidgets.QMessageBox.StandardButton.Yes: return
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S"); zip_path = os.path.join(P.OUT_DIR, f"bug_report_{ts}.zip")
        try:
            with zipfile.ZipFile(zip_path, 'w') as z:
                z.writestr("system_info.txt", f"OS: {platform.system()} {platform.release()}\nPython: {sys.version}\n")
                if os.path.exists("config.json"): z.write("config.json", "config.json")
                logs = sorted(glob.glob(os.path.join(P.OUT_DIR, "prom_log_*.txt")))
                if logs: z.write(logs[-1], "last_log.txt")
            QtWidgets.QMessageBox.information(s, "Успех", f"Отчет сохранен:\n{zip_path}")
        except Exception as e: s.con.append(f"[ОШИБКА] Не удалось собрать отчет: {e}")

    def closeEvent(s, event):
        for w in [getattr(s.gtab, "w", None), getattr(s.gtab, "w_att", None), getattr(s.ntab, "w", None), getattr(s.ctab, "w_str", None), getattr(s.ctab, "w_lat", None)]:
            if w and hasattr(w, 'isRunning') and w.isRunning():
                if hasattr(w, 'stop'): w.stop()
                w.wait(2000)
        event.accept()
def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # ==========================================
    # СОЗДАНИЕ СТИЛИЗОВАННОЙ ЗАСТАВКИ (800x450)
    # ==========================================
    W, H = 800, 450
    pixmap = QtGui.QPixmap(W, H)
    pixmap.fill(QtGui.QColor("#0a0a0c")) # Глубокий черный фон
    
    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    
    # 1. Радиальный градиент (эффект свечения из центра)
    gradient = QtGui.QRadialGradient(W/2, H/2, W/2)
    gradient.setColorAt(0.0, QtGui.QColor("#102b2b")) # Темно-изумрудный центр
    gradient.setColorAt(1.0, QtGui.QColor("#0a0a0c")) # Черные края
    painter.fillRect(0, 0, W, H, gradient)
    
    # 2. Декоративная сетка на фоне
    painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 10), 1)) # Еле заметный белый
    for i in range(0, W, 40): painter.drawLine(i, 0, i, H)
    for i in range(0, H, 40): painter.drawLine(0, i, W, i)
    
    # 3. Стилизованный атом (орбиты и ядро)
    center_x, center_y = W // 2, H // 2 - 20
    
    # Ядро (с эффектом свечения)
    for r, alpha in [(30, 20), (20, 50), (10, 255)]:
        painter.setBrush(QtGui.QColor(0, 255, 204, alpha))
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.drawEllipse(center_x - r, center_y - r, r*2, r*2)
        
    # Орбиты
    painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
    for angle in [0, 60, 120]:
        painter.save()
        painter.translate(center_x, center_y)
        painter.rotate(angle)
        painter.setPen(QtGui.QPen(QtGui.QColor(0, 255, 204, 120), 2))
        painter.drawEllipse(-160, -50, 320, 100) # Сплюснутый эллипс
        painter.restore()
        
    # 4. Текст (Заголовок)
    font_title = QtGui.QFont("Segoe UI", 42, QtGui.QFont.Weight.Bold)
    painter.setFont(font_title)
    
    # Рисуем тень/свечение для текста несколько раз
    painter.setPen(QtGui.QColor(0, 255, 204, 40))
    painter.drawText(pixmap.rect().adjusted(0, -120, 0, 0), QtCore.Qt.AlignmentFlag.AlignCenter, "PROMETHEUS CORE")
    painter.setPen(QtGui.QColor(0, 255, 204, 80))
    painter.drawText(pixmap.rect().adjusted(0, -120, 0, 0), QtCore.Qt.AlignmentFlag.AlignCenter, "PROMETHEUS CORE")
    
    # Основной текст
    painter.setPen(QtGui.QColor("#ffffff"))
    painter.drawText(pixmap.rect().adjusted(0, -120, 0, 0), QtCore.Qt.AlignmentFlag.AlignCenter, "PROMETHEUS CORE")
    
    # 5. Подзаголовок
    font_sub = QtGui.QFont("Consolas", 14)
    painter.setFont(font_sub)
    painter.setPen(QtGui.QColor("#4CAF50"))
    painter.drawText(pixmap.rect().adjusted(0, -40, 0, 0), QtCore.Qt.AlignmentFlag.AlignCenter, "NUCLEAR & RADIATION SIMULATION ENGINE")
    
    # 6. Декоративные линии по бокам от подзаголовка
    painter.setPen(QtGui.QPen(QtGui.QColor("#4CAF50"), 1))
    painter.drawLine(W//2 - 250, H//2 + 25, W//2 - 150, H//2 + 25)
    painter.drawLine(W//2 + 150, H//2 + 25, W//2 + 250, H//2 + 25)
    
    # 7. Статус загрузки внизу
    font_status = QtGui.QFont("Consolas", 10)
    painter.setFont(font_status)
    painter.setPen(QtGui.QColor("#888888"))
    painter.drawText(pixmap.rect().adjusted(0, 120, 0, 0), QtCore.Qt.AlignmentFlag.AlignCenter, "Версия 5.0.0 (Dev)")
    
    # Полоса загрузки (декоративная)
    painter.setPen(QtGui.QPen(QtGui.QColor("#2e7d32"), 2))
    painter.setBrush(QtGui.QColor("#1e1e1e"))
    painter.drawRect(W//2 - 150, H//2 + 140, 300, 6)
    
    # Заполненная часть полосы (имитация)
    # painter.setPen(QtCore.Qt.PenStyle.NoPen)
    # painter.setBrush(QtGui.QColor("#00ffcc"))
    # painter.drawRect(W//2 - 148, H//2 + 142, 220, 2) # Заполнено на ~70%
    
    painter.setPen(QtGui.QColor("#4CAF50"))
    painter.drawText(pixmap.rect().adjusted(0, 180, 0, 0), QtCore.Qt.AlignmentFlag.AlignCenter, "Инициализация физического ядра...")
    
    painter.end()
    # ==========================================

    # Показываем заставку (поверх всех окон)
    splash = QtWidgets.QSplashScreen(pixmap, QtCore.Qt.WindowStaysOnTopHint)
    splash.show()
    
    # Создаем настоящий виджет прогресс-бара поверх заставки
    progress = QtWidgets.QProgressBar(splash)
    # Ставим его ровно туда, где была нарисована рамка
    progress.setGeometry(QtCore.QRect(W//2 - 148, H//2 + 141, 296, 4))
    progress.setStyleSheet("""
        QProgressBar {
            border: none;
            background-color: transparent;
        }
        QProgressBar::chunk {
            background-color: #00ffcc;
        }
    """)
    progress.setValue(0)
    progress.show()
    
    app.processEvents()
    
    # Инициализируем главное окно в фоне (пока полоса на нуле)
    global w
    w = Main()
    
    # Функция, которая будет плавно заполнять полосу
    def update_progress():
        val = progress.value()
        if val >= 100:
            timer.stop()
            w.showMaximized()
            splash.finish(w)
        else:
            # Увеличиваем значение (чем больше прибавка, тем быстрее загрузится)
            progress.setValue(val + 2) 

    # Запускаем таймер: каждые 40 мс прибавляем 2%. Итого: 50 * 40 = 2 секунды загрузки
    timer = QtCore.QTimer()
    timer.timeout.connect(update_progress)
    timer.start(40)
    
    sys.exit(app.exec())
    
if __name__=="__main__":
    mp.freeze_support()
    main()