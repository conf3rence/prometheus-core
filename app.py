"""app.py — GUI Prometheus Core v3.1.0 (Dev)"""
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

OUT = P.OUT_DIR
os.makedirs(OUT, exist_ok=True)

CUSTOM_ISO_FILE = os.path.join(P.OUT_DIR, "custom_isotopes.json")
if os.path.exists(CUSTOM_ISO_FILE):
    try:
        with open(CUSTOM_ISO_FILE, "r", encoding="utf-8") as f:
            P.ISOTOPES.update(json.load(f))
    except Exception: pass

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

def launch_3d_view(log_cb, mode="gamma", R=10.0, data=None):
    try:
        import pyvista as pv
    except ImportError:
        return log_cb("[ОШИБКА] Установите: pip install pyvista")
        
    log_cb(f"[3D] Генерация 3D сцены: {mode}...")
    plotter = pv.Plotter(); plotter.set_background('#1e1e1e')
    
    if mode == "gamma":
        plotter.add_mesh(pv.Sphere(radius=R), color='#455a64', opacity=0.2, style='wireframe')
        plotter.add_mesh(pv.Sphere(radius=R*0.05), color='red')
        for _ in range(200):
            theta, phi = np.random.uniform(0, np.pi), np.random.uniform(0, 2*np.pi)
            end = [R * np.sin(theta) * np.cos(phi), R * np.sin(theta) * np.sin(phi), R * np.cos(theta)]
            plotter.add_mesh(pv.Line((0,0,0), end), color='yellow', opacity=0.1)
        plotter.show(title=f"3D Гамма: R={R}")
        
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
        plotter.add_volume(grid, cmap="plasma", opacity="sigmoid", show_scalar_bar=True, scalar_bar_args={'title': 'Поток нейтронов'})
        plotter.add_mesh(pv.Sphere(radius=R*0.05), color='red')
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
        self.red_line.set_ydata([y_pos, y_pos]); self.ax_slice.clear(); slice_data = self.g2_disp[val, :]
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
    def __init__(s, title, data_dict, item_type, parent=None):
        super().__init__(parent); s.setWindowTitle(title); s.resize(700, 550); s.data_dict = data_dict; s.item_type = item_type
        layout = QtWidgets.QHBoxLayout(s); left = QtWidgets.QVBoxLayout()
        s.search = QtWidgets.QLineEdit(); s.search.setPlaceholderText("🔍 Поиск..."); s.search.textChanged.connect(s.filter_list); left.addWidget(s.search)
        s.list_widget = QtWidgets.QListWidget(); s.list_widget.itemDoubleClicked.connect(s.accept)
        for k in sorted(data_dict.keys()):
            if not k.startswith("_"): s.list_widget.addItem(k)
        s.list_widget.currentTextChanged.connect(s.update_details); left.addWidget(s.list_widget)
        right = QtWidgets.QVBoxLayout(); right.addWidget(QtWidgets.QLabel("<b>Информация:</b>"))
        s.details = QtWidgets.QTextBrowser(); s.details.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; font-family: Consolas; font-size: 13px;")
        right.addWidget(s.details); layout.addLayout(left, 1); layout.addLayout(right, 1)
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(s.accept); btn_box.rejected.connect(s.reject)
        main = QtWidgets.QVBoxLayout(); main.addLayout(layout); main.addWidget(btn_box); s.setLayout(main)
        if s.list_widget.count() > 0: s.list_widget.setCurrentRow(0)
    def filter_list(s, text):
        for i in range(s.list_widget.count()): s.list_widget.item(i).setHidden(text.lower() not in s.list_widget.item(i).text().lower())
    def update_details(s, name):
        if not name or name not in s.data_dict: return
        d = s.data_dict[name]; text = ""
        if s.item_type == "isotope":
            text += f"Изотоп: {name}\n\nГамма-линии:\n"
            for line in d.get("lines", []): text += f"  - {line[0]:.4f} МэВ ({line[1]*100:.1f}%)\n"
        elif s.item_type.startswith("material"):
            text += f"Материал: {name}\n\nZ: {d.get('Z', 0):.2f}\nA: {d.get('A', 0):.2f}\nПлотность: {d.get('rho', 0)} г/см³\n"
        s.details.setText(text)

# ==========================================
# РАБОЧИЕ ПОТОКИ
# ==========================================
class GammaWorker(QtCore.QThread):
    done=QtCore.Signal(dict); fail=QtCore.Signal(str); prog=QtCore.Signal(float)
    def __init__(s,p): super().__init__(); s.p=p; s._stop=False
    def stop(s): s._stop=True
    def run(s):
        try:
            t_start = time.perf_counter(); r=P.gamma_mc(**s.p, progress=lambda f:s.prog.emit(f), should_stop=lambda:s._stop); t_end = time.perf_counter()
            if r is not None: r["elapsed_time"] = t_end - t_start; s.done.emit(r)
        except Exception as e: s.fail.emit(f"{type(e).__name__}: {e}")
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
    done=QtCore.Signal(np.ndarray, np.ndarray, np.ndarray); fail=QtCore.Signal(str)
    def __init__(s, part, T0, mat): super().__init__(); s.part=part; s.T0=T0; s.mat=mat
    def run(s):
        try: grid, xb, yb = P.lateral_straggling_2d(s.part, s.T0, s.mat); s.done.emit(grid, xb, yb)
        except Exception as e: s.fail.emit(f"{type(e).__name__}: {e}")

# ==========================================
# ОСНОВНЫЕ МОДУЛИ
# ==========================================
class GammaTab(QtWidgets.QWidget):
    def __init__(s, console):
        super().__init__(); s.console=console; s.res=None; s.w=None; s.att_res=None; s.sel_mat = "air"; s.sel_iso = "Am-241"
        root=QtWidgets.QHBoxLayout(s); p=QtWidgets.QWidget(); p.setFixedWidth(350); fl=QtWidgets.QFormLayout(p)
        s.cb_geom = QtWidgets.QComboBox(); s.cb_geom.addItems(["Сфера", "Плоский слой"]); s.lbl_R = QtWidgets.QLabel("Радиус,см")
        btn_style = "background-color: #2b2b2b; color: #ffffff; text-align: left; padding-left: 10px; border: 1px solid #555555; border-radius: 4px;"
        s.btn_mat = QtWidgets.QPushButton("air"); s.btn_mat.setStyleSheet(btn_style); s.btn_mat.clicked.connect(s.select_material)
        s.btn_iso = QtWidgets.QPushButton("Am-241"); s.btn_iso.setStyleSheet(btn_style); s.btn_iso.clicked.connect(s.select_isotope)
        s.tbl_layers = QtWidgets.QTableWidget(3, 2); s.tbl_layers.setHorizontalHeaderLabels(["Материал", "Толщина,см"])
        s.tbl_layers.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        def update_total_thickness(): s.sp_R.setValue(sum(s.tbl_layers.cellWidget(i, 1).value() for i in range(3))); s.validate()
        for i in range(3):
            cb = QtWidgets.QComboBox(); cb.addItems(sorted(P.GAMMA_MATS.keys())); cb.setCurrentText("lead" if i==0 else ("polyethylene" if i==1 else "concrete")); s.tbl_layers.setCellWidget(i, 0, cb)
            sb = QtWidgets.QDoubleSpinBox(); sb.setRange(0, 1000); sb.setValue(2.0 if i==0 else (10.0 if i==1 else 0.0)); sb.valueChanged.connect(update_total_thickness); s.tbl_layers.setCellWidget(i, 1, sb)
        s.tbl_layers.setVisible(False)
        s.sp_R=QtWidgets.QDoubleSpinBox(); s.sp_R.setRange(1,300); s.sp_R.setValue(10); s.sp_n=QtWidgets.QSpinBox(); s.sp_n.setRange(1000,5_000_000); s.sp_n.setValue(100000); s.sp_n.setGroupSeparatorShown(True)
        s.sp_seed=QtWidgets.QSpinBox(); s.sp_seed.setRange(0,999999); s.sp_seed.setValue(42); s.chk_abs=QtWidgets.QCheckBox("Абс. доза")
        s.sp_act=QtWidgets.QDoubleSpinBox(); s.sp_act.setRange(0,1e18); s.sp_act.setValue(1.0); s.cb_au=QtWidgets.QComboBox(); s.cb_au.addItems(P.ACTIVITY_U.keys()); s.cb_au.setCurrentText("МБк")
        s.sp_t=QtWidgets.QDoubleSpinBox(); s.sp_t.setRange(0,1e12); s.sp_t.setValue(1.0); s.cb_tu=QtWidgets.QComboBox(); s.cb_tu.addItems(P.TIME_U.keys()); s.cb_tu.setCurrentText("ч")
        s.btn=QtWidgets.QPushButton("▶ Рассчитать"); s.btn.clicked.connect(s.run); s.btn.setStyleSheet("background:#2e7d32;color:white;font-weight:bold;padding:6px;")
        s.btn_export = QtWidgets.QPushButton("💾 Экспорт"); s.btn_export.clicked.connect(s.export_data)
        s.sp_n.valueChanged.connect(s.validate); s.sp_R.valueChanged.connect(s.validate)
        def on_geom_change():
            if s.cb_geom.currentText() == "Сфера": s.lbl_R.setText("Радиус,см"); s.tbl_layers.setVisible(False); s.btn_mat.setVisible(True); s.sp_R.setReadOnly(False)
            else: s.lbl_R.setText("Общая толщина,см"); s.tbl_layers.setVisible(True); s.btn_mat.setVisible(False); s.sp_R.setReadOnly(True); update_total_thickness()
            s.validate()
        s.cb_geom.currentIndexChanged.connect(on_geom_change)
        fl.addRow("Геометрия", s.cb_geom); fl.addRow("Материал", s.btn_mat); fl.addRow(s.tbl_layers); fl.addRow("Изотоп", s.btn_iso); fl.addRow(s.lbl_R,s.sp_R); fl.addRow("Историй",s.sp_n); fl.addRow("Seed",s.sp_seed); fl.addRow("",s.chk_abs); fl.addRow("Активность",s.sp_act); fl.addRow("Ед.акт",s.cb_au); fl.addRow("Время",s.sp_t); fl.addRow("Ед.вр",s.cb_tu); fl.addRow(s.btn); fl.addRow(s.btn_export)
        btn_grid = QtWidgets.QGridLayout(); b_style = "background-color: #2b2b2b; color: white; border: 1px solid #555555; padding: 4px; border-radius: 4px;"
        b_hist = QtWidgets.QPushButton("📊 Гистограмма"); b_hist.setStyleSheet(b_style); b_hist.clicked.connect(s.show_coll_hist)
        b_polar = QtWidgets.QPushButton("📐 Полярный"); b_polar.setStyleSheet(b_style); b_polar.clicked.connect(s.show_polar_hist)
        b_att = QtWidgets.QPushButton("📉 Ослабление"); b_att.setStyleSheet(b_style); b_att.clicked.connect(s.run_attenuation)
        b_slice = QtWidgets.QPushButton("📏 1D-срез"); b_slice.setStyleSheet(b_style); b_slice.clicked.connect(s.show_slice)
        btn_3d = QtWidgets.QPushButton("🚀 3D"); btn_3d.setStyleSheet(b_style); btn_3d.clicked.connect(lambda: launch_3d_view(s.console, mode="gamma", R=s.sp_R.value()))
        btn_pop = QtWidgets.QPushButton("🔍 Развернуть"); btn_pop.setStyleSheet(b_style); btn_pop.clicked.connect(lambda: PopOutDialog(s.fig, "Гамма-модуль", s).exec())
        btn_grid.addWidget(b_hist, 0, 0); btn_grid.addWidget(b_polar, 0, 1); btn_grid.addWidget(b_att, 1, 0); btn_grid.addWidget(b_slice, 1, 1); btn_grid.addWidget(btn_3d, 2, 0); btn_grid.addWidget(btn_pop, 2, 1)
        fl.addRow(btn_grid)
        s.pbar=QtWidgets.QProgressBar(); fl.addRow(s.pbar); root.addWidget(p)
        s.fig=Figure(figsize=(10,10),tight_layout=True); s.a1=s.fig.add_subplot(221); s.a2=s.fig.add_subplot(222); s.a3=s.fig.add_subplot(223); s.a4=s.fig.add_subplot(224)
        s.canvas=FigureCanvas(s.fig); g=QtWidgets.QWidget(); gl=QtWidgets.QVBoxLayout(g); s.toolbar_g = NavToolbar(s.canvas,s); gl.addWidget(s.toolbar_g); gl.addWidget(s.canvas); root.addWidget(g,1); s.validate()
    def select_material(s):
        dlg = SelectorDialog("Материал", P.GAMMA_MATS, "material_gamma", s)
        if dlg.exec(): s.sel_mat = dlg.list_widget.currentItem().text(); s.btn_mat.setText(s.sel_mat)
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
                if thick > 0: layers.append((P.make_gamma_mat(s.tbl_layers.cellWidget(i, 0).currentText()), thick))
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
    def ok(s,r):
        s.res=r; s.btn.setEnabled(True); s.validate(); s.pbar.setValue(100)
        
        # Считаем Бугер и обратное рассеяние
        theor_escape = r.get("theor_escape", np.exp(-r["mu"] * r["R"]))
        sim_escape = r["nlk_uncoll"] / r["n"] if r["n"] > 0 else 0.0
        backscatter_pct = (r.get("backscatter_count", 0) / r["n"]) * 100 if r["n"] > 0 else 0.0
        
        # Выводим в лог
        s.console(f"[ГАММА] готово: доза={r['dose']:.3e} Гр/ч-ца | фото/комптон/пары={r['nph']}/{r['nco']}/{r['npa']}")
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
    def show_coll_hist(s):
        if not s.res: return
        fig = Figure(figsize=(8, 6), tight_layout=True); ax = fig.add_subplot(111)
        ax.bar(np.arange(len(s.res["coll_hist"])), s.res["coll_hist"], color="teal"); ax.set_title("Гистограмма столкновений")
        win = QtWidgets.QDialog(s); win.resize(800, 600); canvas = FigureCanvas(fig); layout = QtWidgets.QVBoxLayout(win); layout.addWidget(canvas); canvas.draw(); win.exec()
    def show_polar_hist(s):
        if not s.res: return
        fig = Figure(figsize=(8, 8), tight_layout=True); ax = fig.add_subplot(111, projection='polar')
        hist = s.res["theta_hist"]; angles = np.arccos((np.arange(90) + 0.5) / 45 - 1); ax.bar(angles, hist, width=np.pi/90, color="darkred")
        win = QtWidgets.QDialog(s); win.resize(800, 800); canvas = FigureCanvas(fig); layout = QtWidgets.QVBoxLayout(win); layout.addWidget(canvas); canvas.draw(); win.exec()
    def run_attenuation(s):
        s.att_res = None; mat = P.make_gamma_mat(s.sel_mat); spec = P.ISOTOPES[s.sel_iso]["lines"]; thick = np.linspace(0, 20, 11)
        s.w_att = AttenuationWorker(mat, spec, 10000, thick); s.w_att.done.connect(s.show_attenuation_plot); s.w_att.start()
    def show_attenuation_plot(s, results):
        s.att_res = results
        fig = Figure(figsize=(8, 6), tight_layout=True); ax = fig.add_subplot(111)
        x = [r[0] for r in results]; ax.plot(x, [r[1] for r in results], 'o-', label='Модель'); ax.plot(x, [r[2] for r in results], '--', color='red', label='Теория')
        ax.set_yscale("log"); ax.legend(); ax.grid(alpha=0.3)
        win = QtWidgets.QDialog(s); win.resize(800, 600); canvas = FigureCanvas(fig); layout = QtWidgets.QVBoxLayout(win); layout.addWidget(canvas); canvas.draw(); win.exec()
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

class ChargedTab(QtWidgets.QWidget):
    def __init__(s, console):
        super().__init__(); s.console=console; s.res=None; s.sel_mat = "вода"; s.lat_dlg = None
        root=QtWidgets.QHBoxLayout(s); p=QtWidgets.QWidget(); p.setFixedWidth(350); fl=QtWidgets.QFormLayout(p)
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
        
        btn_layout = QtWidgets.QHBoxLayout()
        btn_3d = QtWidgets.QPushButton("🚀 3D"); btn_3d.setStyleSheet("background-color: #2b2b2b; color: white; border: 1px solid #555555; padding: 4px;")
        btn_3d.clicked.connect(lambda: launch_3d_view(s.console, mode="charged", data=(s.a1.lines[0].get_xdata(), s.a1.lines[0].get_ydata()) if s.a1.lines else None))
        
        btn_lat = QtWidgets.QPushButton("🌊 2D Пучок"); btn_lat.setStyleSheet("background-color: #2b2b2b; color: white; border: 1px solid #555555; padding: 4px;")
        btn_lat.clicked.connect(s.show_lateral)
        
        btn_pop = QtWidgets.QPushButton("🔍 Развернуть"); btn_pop.setStyleSheet("background-color: #2b2b2b; color: white; border: 1px solid #555555; padding: 4px;")
        btn_pop.clicked.connect(lambda: PopOutDialog(s.fig, "Заряженные частицы", s).exec())
        
        btn_layout.addWidget(btn_3d); btn_layout.addWidget(btn_lat); btn_layout.addWidget(btn_pop)
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
        R, dep, de = P.csda(pt, T0, mat) # <--- Теперь csda возвращает пробег (x)
        
        wr = {"протон": 2.0, "альфа": 20.0, "дейтрон": 2.0, "электрон": 1.0}.get(pt, 1.0)
        s.console(f"[ЗАРЯЖ] {pt} {T0} МэВ в {mat_name}: полный пробег={R:.3g} см, wR={wr:.0f}")
        
        if not s.chk_overlay.isChecked(): s.a1.clear(); s.a2.clear(); s.a3.clear(); s.a4.clear()
        color = {"протон": "crimson", "альфа": "darkgreen", "электрон": "blue", "дейтрон": "purple"}.get(pt, "black")
        s.a1.plot(dep,de,color=color); s.a1.set_title("dE/dx"); s.a2.plot(*P.range_vs_energy(pt,mat),color=color); s.a2.set_title("Пробег")
        s.a3.plot(dep, de, color=color); s.a3.fill_between(dep, de, color=color, alpha=0.3); s.a3.set_title("Кривая Брэгга")
        
        s.a4.set_title("Страгглинг (расчет...)"); s.a4.set_xlabel("Пробег, см"); s.a4.set_ylabel("Частота")
        s.canvas.draw()
        
        s.w_str = StragglingWorker(pt, T0, mat); s.w_str.done.connect(lambda ranges: s.draw_straggling(ranges, color)); s.w_str.start()
        
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

class NeutronTab(QtWidgets.QWidget):
    def __init__(s, console):
        super().__init__(); s.console=console; s.w=None
        root=QtWidgets.QHBoxLayout(s); p=QtWidgets.QWidget(); p.setFixedWidth(350); fl=QtWidgets.QFormLayout(p)
        
        # 1. СОЗДАЕМ ВСЕ ЭЛЕМЕНТЫ ИНТЕРФЕЙСА
        s.cb_m=QtWidgets.QComboBox(); s.cb_m.addItems(["water","polyethylene","concrete","iron","lead","graphite","b4c","uranium"])
        
        s.cb_spec = QtWidgets.QComboBox()
        s.cb_spec.addItems(["Моноэнергетический", "Спектр U-235", "Спектр Cf-252"])
        
        s.sp_R=QtWidgets.QDoubleSpinBox(); s.sp_R.setRange(1,200); s.sp_R.setValue(30)
        s.sp_E=QtWidgets.QDoubleSpinBox(); s.sp_E.setRange(0.001, 20); s.sp_E.setValue(2.0)
        s.sp_n=QtWidgets.QSpinBox(); s.sp_n.setRange(1000,2_000_000); s.sp_n.setValue(10000)
        s.sp_b=QtWidgets.QSpinBox(); s.sp_b.setRange(1,200); s.sp_b.setValue(20)
        s.sp_mesh=QtWidgets.QSpinBox(); s.sp_mesh.setRange(20,200); s.sp_mesh.setValue(80)
        
        s.btn=QtWidgets.QPushButton("▶ Запустить OpenMC")
        s.btn.clicked.connect(s.run) # Привязка кнопки к методу run
        s.btn.setStyleSheet("background:#00695c;color:white;padding:6px;")
        
        # 2. ДОБАВЛЯЕМ ИХ В ЛЕВУЮ ПАНЕЛЬ
        fl.addRow("Материал", s.cb_m)
        fl.addRow("Спектр источника", s.cb_spec) 
        fl.addRow("Радиус", s.sp_R)
        fl.addRow("Энергия", s.sp_E)
        fl.addRow("Частиц/батч", s.sp_n)
        fl.addRow("Батчей", s.sp_b)
        fl.addRow("Разрешение сетки", s.sp_mesh) 
        fl.addRow(s.btn)
        
        btn_layout = QtWidgets.QHBoxLayout()
        btn_3d = QtWidgets.QPushButton("🚀 3D"); btn_3d.setStyleSheet("background-color: #2b2b2b; color: white; border: 1px solid #555555; padding: 4px;")
        btn_3d.clicked.connect(lambda: launch_3d_view(s.console, mode="neutron", R=s.sp_R.value()))
        btn_pop = QtWidgets.QPushButton("🔍 Развернуть"); btn_pop.setStyleSheet("background-color: #2b2b2b; color: white; border: 1px solid #555555; padding: 4px;")
        btn_pop.clicked.connect(lambda: PopOutDialog(s.fig, "Нейтроны", s).exec())
        btn_layout.addWidget(btn_3d); btn_layout.addWidget(btn_pop); fl.addRow(btn_layout)
        
        root.addWidget(p)
        
        # 3. СОЗДАЕМ ГРАФИКИ
        s.fig=Figure(figsize=(10,8),tight_layout=True); s.a1=s.fig.add_subplot(211); s.a2=s.fig.add_subplot(212)
        s.canvas=FigureCanvas(s.fig); g=QtWidgets.QWidget(); gl=QtWidgets.QVBoxLayout(g); s.toolbar_g = NavToolbar(s.canvas,s); gl.addWidget(s.toolbar_g); gl.addWidget(s.canvas); root.addWidget(g,1)
    
    # 4. МЕТОД ЗАПУСКА РАСЧЕТА (ВЫНЕСЕН ИЗ __init__)
    def run(s):
        if s.w and s.w.isRunning(): return
        
        # Определяем тип спектра по тексту из выпадающего списка
        spec = "mono"
        if s.cb_spec.currentText() == "Спектр U-235": spec = "u235"
        elif s.cb_spec.currentText() == "Спектр Cf-252": spec = "cf252"
            
        cfg={
            "material": s.cb_m.currentText(),
            "radius": s.sp_R.value(),
            "energy_MeV": s.sp_E.value(),
            "particles": s.sp_n.value(),
            "batches": s.sp_b.value(),
            "mesh_n": s.sp_mesh.value(), 
            "spectrum": spec            
        }
        s.btn.setEnabled(False); s.console("[НЕЙТРОНЫ] запуск..."); s.w=NeutronWorker(cfg); s.w.msg.connect(s.console); s.w.done.connect(s.ok); s.w.fail.connect(lambda m: s.console("[ОШИБКА] "+m)); s.w.start()
    
    # 5. МЕТОД ОТРИСОВКИ РЕЗУЛЬТАТОВ
    def ok(s,r):
        s.btn.setEnabled(True); st=r["stats"]; s.console(f"[НЕЙТРОНЫ] доза: {st.get('dose', 0):.4e} Зв")
        import matplotlib.image as mpimg; s.a1.clear(); s.a2.clear(); s.a1.imshow(mpimg.imread(r["spec_img"])); s.a1.axis("off"); s.a2.imshow(mpimg.imread(r["map_img"])); s.a2.axis("off"); s.canvas.draw()

class HotkeysDialog(QtWidgets.QDialog):
    def __init__(s, parent=None):
        super().__init__(parent); s.setWindowTitle("Горячие клавиши"); s.resize(500, 400)
        layout = QtWidgets.QVBoxLayout(s); table = QtWidgets.QTableWidget(); table.setColumnCount(2); table.setHorizontalHeaderLabels(["Клавиша", "Действие"]); table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch); table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        hotkeys = [("Ctrl+R", "Рассчитать"), ("Ctrl+E", "Экспорт"), ("Ctrl+S", "Сохранить"), ("Ctrl+O", "Загрузить"), ("Ctrl+T", "Сменить тему"), ("F1", "Справка")]
        table.setRowCount(len(hotkeys))
        for i, (key, desc) in enumerate(hotkeys): table.setItem(i, 0, QtWidgets.QTableWidgetItem(key)); table.setItem(i, 1, QtWidgets.QTableWidgetItem(desc))
        layout.addWidget(table); btn = QtWidgets.QPushButton("Закрыть"); btn.clicked.connect(s.close); layout.addWidget(btn)

class Main(QtWidgets.QMainWindow):
    def __init__(s):
        super().__init__()
        s.setWindowTitle("Prometheus Core v3.1.0 (Dev)"); s.setWindowIcon(make_app_icon()); s.dark_mode = True
        menubar = s.menuBar(); file_menu = menubar.addMenu("Файл")
        act_save = QtGui.QAction("Сохранить (Ctrl+S)", s); act_save.triggered.connect(s.save_session); file_menu.addAction(act_save)
        act_load = QtGui.QAction("Загрузить (Ctrl+O)", s); act_load.triggered.connect(s.load_session); file_menu.addAction(act_load)
        file_menu.addSeparator(); act_exit = QtGui.QAction("Выход", s); act_exit.triggered.connect(s.close); file_menu.addAction(act_exit)
        view_menu = menubar.addMenu("Вид"); act_theme = QtGui.QAction("Сменить тему (Ctrl+T)", s); act_theme.triggered.connect(s.toggle_theme); view_menu.addAction(act_theme)
        help_menu = menubar.addMenu("Справка"); act_hotkeys = QtGui.QAction("Горячие клавиши (F1)", s); act_hotkeys.triggered.connect(s.show_hotkeys); help_menu.addAction(act_hotkeys); help_menu.addSeparator(); act_val = QtGui.QAction("Верификация NIST", s); act_val.triggered.connect(s.run_validation); help_menu.addAction(act_val)
        
        s.con=QtWidgets.QPlainTextEdit(); s.con.setReadOnly(True); s.con.setMaximumHeight(200); s.con.setStyleSheet("font-family:Consolas;font-size:12px;background:#1e1e1e;color:#d4d4d4;")
        P.attach_log_widget(s.con); P.setup_log_file(OUT)
        def console(m): P.plog(m)
        
        s.gtab = GammaTab(console); s.ctab = ChargedTab(console); s.ntab = NeutronTab(console)
        s.gentab = GeneratorTab(console, s.gtab); s.sandbox = SandboxTab(console); s.clitab = CliTab(console)
        
        tabs=QtWidgets.QTabWidget()
        tabs.addTab(s.gtab,"☢️ Гамма"); tabs.addTab(s.ctab,"⚙️ Заряженные"); tabs.addTab(s.ntab,"🔬 Нейтроны")
        tabs.addTab(s.gentab, "🧪 Генератор"); tabs.addTab(s.sandbox,"🏖️ Песочница"); tabs.addTab(s.clitab, "💻 CLI-Конструктор")
        tabl=s._mat_table(); tabs.addTab(tabl,"📋 Таблица материалов")
        
        c=QtWidgets.QWidget(); v=QtWidgets.QVBoxLayout(c); v.addWidget(tabs,1); v.addWidget(QtWidgets.QLabel("ЛОГ:")); v.addWidget(s.con); s.setCentralWidget(c)
        s.status = s.statusBar(); s.status.showMessage(f"Готово | Материалов: {len(P.GAMMA_MATS)} | Изотопов: {len(P.ISOTOPES)}")
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+R"), s, activated=s.run_active_tab); QtGui.QShortcut(QtGui.QKeySequence("Ctrl+E"), s, activated=s.export_active_tab); QtGui.QShortcut(QtGui.QKeySequence("Ctrl+S"), s, activated=s.save_session); QtGui.QShortcut(QtGui.QKeySequence("Ctrl+O"), s, activated=s.load_session); QtGui.QShortcut(QtGui.QKeySequence("Ctrl+T"), s, activated=s.toggle_theme); QtGui.QShortcut(QtGui.QKeySequence("F1"), s, activated=s.show_hotkeys)
        s.tabs = tabs
    def run_active_tab(s):
        idx = s.tabs.currentIndex()
        if idx == 0: s.gtab.run()
        elif idx == 1: s.ctab.run()
        elif idx == 2: s.ntab.run()
    def export_active_tab(s):
        if s.tabs.currentIndex() == 0: s.gtab.export_data()
    def show_hotkeys(s): HotkeysDialog(s).exec()
    def run_validation(s):
        report = validator.run_validation(log_cb=lambda msg, level="info": P.plog(msg, level))
        dlg = QtWidgets.QDialog(s); dlg.setWindowTitle("Верификация NIST"); dlg.resize(800, 500)
        layout = QtWidgets.QVBoxLayout(dlg); text = QtWidgets.QPlainTextEdit(); text.setPlainText(report); text.setReadOnly(True); layout.addWidget(text)
        btn = QtWidgets.QPushButton("Закрыть"); btn.clicked.connect(dlg.accept); layout.addWidget(btn); dlg.exec()
    def toggle_theme(s):
        s.dark_mode = not s.dark_mode; app = QtWidgets.QApplication.instance()
        if s.dark_mode: app.setStyle("Fusion"); s.setStyleSheet(""); s.con.setStyleSheet("font-family:Consolas;font-size:12px;background:#1e1e1e;color:#d4d4d4;")
        else: app.setStyle("Fusion"); s.setStyleSheet("QWidget { background-color: #f0f0f0; color: #000000; } QPushButton { background-color: #e0e0e0; border: 1px solid #aaa; padding: 6px; }"); s.con.setStyleSheet("font-family:Consolas;font-size:12px;background:#ffffff;color:#000000;")
    def save_session(s):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(s, "Сохранить", "project.json", "JSON (*.json)")
        if not path: return
        data = {"gamma": {"geom": s.gtab.cb_geom.currentText(), "mat": s.gtab.sel_mat, "iso": s.gtab.sel_iso, "R": s.gtab.sp_R.value(), "N": s.gtab.sp_n.value()}, "charged": {"pt": s.ctab.cb_p.currentText(), "mat": s.ctab.sel_mat, "E": s.ctab.sp_E.value()}}
        with open(path, "w", encoding="utf-8") as f: json.dump(data, f, indent=2)
    def load_session(s):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(s, "Загрузить", "", "JSON (*.json)")
        if not path: return
        try:
            with open(path, "r", encoding="utf-8") as f: data = json.load(f)
            if "gamma" in data:
                g = data["gamma"]; s.gtab.cb_geom.setCurrentText(g.get("geom", "Сфера")); s.gtab.sel_mat = g.get("mat", "air"); s.gtab.btn_mat.setText(s.gtab.sel_mat); s.gtab.sel_iso = g.get("iso", "Am-241"); s.gtab.btn_iso.setText(s.gtab.sel_iso); s.gtab.sp_R.setValue(g.get("R", 10)); s.gtab.sp_n.setValue(g.get("N", 100000))
            if "charged" in data:
                c = data["charged"]; s.ctab.cb_p.setCurrentText(c.get("pt", "протон")); s.ctab.sel_mat = c.get("mat", "вода"); s.ctab.btn_mat.setText(s.ctab.sel_mat); s.ctab.sp_E.setValue(c.get("E", 100))
        except Exception: pass
    def _mat_table(s):
        t=QtWidgets.QTableWidget(); t.setColumnCount(5); t.setHorizontalHeaderLabels(["Материал","Z","A","Плотность","mu/rho@1МэВ"])
        names=sorted(P.GAMMA_MATS.keys()); t.setRowCount(len(names))
        for i,n in enumerate(names):
            m=P.make_gamma_mat(n)
            for j,v in enumerate([n,f"{m.Z:g}",f"{m.A:g}",f"{m.density:g}",f"{m.mu_rho(1.0):.4g}"]): t.setItem(i,j,QtWidgets.QTableWidgetItem(v))
        t.resizeColumnsToContents(); return t
    def closeEvent(s, event):
        for w in [getattr(s.gtab, "w", None), getattr(s.gtab, "w_att", None), getattr(s.ntab, "w", None), getattr(s.ctab, "w_str", None), getattr(s.ctab, "w_lat", None)]:
            if w and hasattr(w, 'isRunning') and w.isRunning():
                if hasattr(w, 'stop'): w.stop()
                w.wait(2000)
        event.accept()

def main():
    app=QtWidgets.QApplication(sys.argv); app.setStyle("Fusion")
    app.setStyleSheet("""
        QComboBox { background-color: #2b2b2b; color: #ffffff; border: 1px solid #555555; border-radius: 4px; padding: 4px 8px; }
        QComboBox:hover { border: 1px solid #2e7d32; }
        QComboBox QAbstractItemView { background-color: #2b2b2b; color: #ffffff; selection-background-color: #2e7d32; selection-color: white; border: 1px solid #555555; outline: none; }
        QTableWidget { background-color: #2b2b2b; color: #ffffff; gridline-color: #444444; selection-background-color: #2e7d32; }
        QHeaderView::section { background-color: #1e1e1e; color: #ffffff; padding: 4px; border: 1px solid #444444; }
        QToolTip { background-color: #2b2b2b; color: #ffffff; border: 1px solid #2e7d32; }
    """)
    w=Main(); w.showMaximized(); sys.exit(app.exec())

if __name__=="__main__":
    mp.freeze_support()
    main()