"""app.py — GUI Prometheus Core v3"""
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
    pixmap = QtGui.QPixmap(64, 64)
    pixmap.fill(QtCore.Qt.GlobalColor.transparent)
    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    painter.setBrush(QtGui.QColor("#2e7d32"))
    painter.setPen(QtCore.Qt.PenStyle.NoPen)
    painter.drawEllipse(2, 2, 60, 60)
    painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
    painter.setPen(QtGui.QPen(QtGui.QColor("white"), 2))
    painter.drawEllipse(12, 28, 40, 8); painter.drawEllipse(28, 12, 8, 40); painter.drawEllipse(18, 18, 28, 28)
    painter.setBrush(QtGui.QColor("white")); painter.setPen(QtCore.Qt.PenStyle.NoPen)
    painter.drawEllipse(28, 28, 8, 8)
    painter.end()
    return QtGui.QIcon(pixmap)

# ==========================================
# 1D-СРЕЗ (LINE PROFILE)
# ==========================================
class SliceDialog(QtWidgets.QDialog):
    def __init__(self, g2, R, geom, parent=None):
        super().__init__(parent)
        self.setWindowTitle("1D Срез (Линейный профиль)")
        self.resize(800, 700)
        
        layout = QtWidgets.QVBoxLayout(self)
        self.fig = Figure(figsize=(8, 7), tight_layout=True)
        self.canvas = FigureCanvas(self.fig)
        
        self.ax_map = self.fig.add_subplot(211)
        self.ax_slice = self.fig.add_subplot(212)
        
        pos = g2[g2 > 0]
        vmin = pos.min() if pos.size else 1e-12
        self.g2_disp = g2.copy()
        self.g2_disp[self.g2_disp <= 0] = vmin
        
        if geom == "slab":
            extent = [0, R, -R, R]
            self.ax_map.set_xlabel("X (глубина), см")
        else:
            extent = [-R, R, -R, R]
            self.ax_map.set_xlabel("X, см")
            
        self.im = self.ax_map.imshow(self.g2_disp, origin="lower", extent=extent, cmap="inferno", norm=LogNorm(vmin=vmin), interpolation='nearest')
        self.ax_map.set_title("2D Карта (двигай ползунок, чтобы выбрать срез)")
        
        self.ny, self.nx = g2.shape
        self.y_center = self.ny // 2
        self.red_line = self.ax_map.axhline(y=extent[2] + (self.y_center / self.ny) * (extent[3] - extent[2]), color='red', lw=2)
        
        layout.addWidget(self.canvas)
        
        self.slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.slider.setRange(0, self.ny - 1)
        self.slider.setValue(self.y_center)
        self.slider.valueChanged.connect(self.update_slice)
        layout.addWidget(QtWidgets.QLabel("Позиция среза (ось Y/Z):"))
        layout.addWidget(self.slider)
        
        self.update_slice(self.y_center)

    def update_slice(self, val):
        y_pos = self.ax_map.get_ylim()[0] + (val / self.ny) * (self.ax_map.get_ylim()[1] - self.ax_map.get_ylim()[0])
        self.red_line.set_ydata([y_pos, y_pos])
        
        self.ax_slice.clear()
        slice_data = self.g2_disp[val, :]
        x_axis = np.linspace(self.ax_map.get_xlim()[0], self.ax_map.get_xlim()[1], len(slice_data))
        
        self.ax_slice.plot(x_axis, slice_data, color="cyan", lw=2)
        self.ax_slice.set_yscale("log")
        self.ax_slice.set_title(f"Профиль вдоль оси X (срез Y={val})")
        self.ax_slice.set_xlabel("Координата X, см")
        self.ax_slice.set_ylabel("Интенсивность (лог. шкала)")
        self.ax_slice.grid(alpha=0.3)
        
        self.canvas.draw_idle()

# ==========================================
# ОКНО ДЛЯ РАЗВОРОТА ГРАФИКОВ (ЗУМ + ПАНОРАМИРОВАНИЕ)
# ==========================================
class PopOutDialog(QtWidgets.QDialog):
    def __init__(self, fig, title="Визуализация", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(1000, 800)
        
        self.fig = fig
        self.original_canvas = parent.canvas if parent and hasattr(parent, 'canvas') else None
        
        self.original_limits = []
        for ax in self.fig.axes:
            self.original_limits.append((ax.get_xlim(), ax.get_ylim()))
        
        layout = QtWidgets.QVBoxLayout(self)
        self.canvas = FigureCanvas(fig)
        self.toolbar = NavToolbar(self.canvas, self)
        
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        
        self.draw_timer = QtCore.QTimer()
        self.draw_timer.setSingleShot(True)
        self.draw_timer.setInterval(50)
        self.draw_timer.timeout.connect(self.canvas.draw_idle)
        
        self.cid_scroll = self.canvas.mpl_connect('scroll_event', self.on_scroll)
        self.cid_press = self.canvas.mpl_connect('button_press_event', self.on_press)
        self.cid_motion = self.canvas.mpl_connect('motion_notify_event', self.on_motion)
        self.cid_release = self.canvas.mpl_connect('button_release_event', self.on_release)
        
        self.fig.set_size_inches(self.canvas.width() / self.fig.dpi, self.canvas.height() / self.fig.dpi)
        self.fig.tight_layout()
        self.canvas.draw()

    def request_draw(self):
        if not self.draw_timer.isActive():
            self.draw_timer.start()

    def on_scroll(self, event):
        ax = event.inaxes
        if ax is None: return
        base_scale = 1.2
        cur_xlim = ax.get_xlim()
        cur_ylim = ax.get_ylim()
        
        if event.button == 'up': scale_factor = 1 / base_scale
        elif event.button == 'down': scale_factor = base_scale
        else: scale_factor = 1
        
        new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
        new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor
        
        relx = (cur_xlim[1] - event.xdata) / (cur_xlim[1] - cur_xlim[0])
        rely = (cur_ylim[1] - event.ydata) / (cur_ylim[1] - cur_ylim[0])
        
        ax.set_xlim([event.xdata - new_width * (1 - relx), event.xdata + new_width * relx])
        ax.set_ylim([event.ydata - new_height * (1 - rely), event.ydata + new_height * rely])
        
        self.request_draw()

    def on_press(self, event):
        if event.button == 1 and event.inaxes is not None:
            ax = event.inaxes
            ax._pan_start = (event.xdata, event.ydata, ax.get_xlim(), ax.get_ylim())
            if ax.get_xscale() == 'log' and event.xdata > 0: ax._pan_start_logx = np.log10(event.xdata)
            if ax.get_yscale() == 'log' and event.ydata > 0: ax._pan_start_logy = np.log10(event.ydata)
            self.canvas.setCursor(QtCore.Qt.CursorShape.ClosedHandCursor)

    def on_motion(self, event):
        if event.button == 1 and event.inaxes is not None and hasattr(event.inaxes, '_pan_start'):
            ax = event.inaxes
            start_x, start_y, xlim, ylim = ax._pan_start
            
            if ax.get_xscale() == 'log' and event.xdata > 0 and hasattr(ax, '_pan_start_logx'):
                dx = np.log10(event.xdata) - ax._pan_start_logx
                ax.set_xlim(10**(np.log10(xlim[0]) - dx), 10**(np.log10(xlim[1]) - dx))
            elif ax.get_xscale() != 'log':
                dx = event.xdata - start_x
                ax.set_xlim(xlim[0] - dx, xlim[1] - dx)
                
            if ax.get_yscale() == 'log' and event.ydata > 0 and hasattr(ax, '_pan_start_logy'):
                dy = np.log10(event.ydata) - ax._pan_start_logy
                ax.set_ylim(10**(np.log10(ylim[0]) - dy), 10**(np.log10(ylim[1]) - dy))
            elif ax.get_yscale() != 'log':
                dy = event.ydata - start_y
                ax.set_ylim(ylim[0] - dy, ylim[1] - dy)
                
            self.request_draw()

    def on_release(self, event):
        if event.button == 1:
            if event.inaxes is not None and hasattr(event.inaxes, '_pan_start'):
                del event.inaxes._pan_start
            self.canvas.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
            self.canvas.draw_idle()
            
    def closeEvent(self, event):
        try:
            self.draw_timer.stop()
            self.canvas.mpl_disconnect(self.cid_scroll)
            self.canvas.mpl_disconnect(self.cid_press)
            self.canvas.mpl_disconnect(self.cid_motion)
            self.canvas.mpl_disconnect(self.cid_release)
            
            if self.original_canvas:
                self.fig.set_canvas(self.original_canvas)
                w = self.original_canvas.width()
                h = self.original_canvas.height()
                if w > 0 and h > 0:
                    self.fig.set_size_inches(w / self.fig.dpi, h / self.fig.dpi)
                self.fig.tight_layout()
                
                for ax, (xlim, ylim) in zip(self.fig.axes, self.original_limits):
                    ax.set_xlim(xlim)
                    ax.set_ylim(ylim)
                self.original_canvas.draw()
        except Exception:
            pass
        super().closeEvent(event)

# ==========================================
# ОКНО ДЛЯ ВЫБОРА МАТЕРИАЛОВ И ИЗОТОПОВ
# ==========================================
class SelectorDialog(QtWidgets.QDialog):
    def __init__(s, title, data_dict, item_type, parent=None):
        super().__init__(parent)
        s.setWindowTitle(title); s.resize(700, 550)
        s.data_dict = data_dict; s.item_type = item_type
        
        layout = QtWidgets.QHBoxLayout(s)
        left_layout = QtWidgets.QVBoxLayout()
        s.search = QtWidgets.QLineEdit(); s.search.setPlaceholderText("🔍 Поиск...")
        s.search.textChanged.connect(s.filter_list); left_layout.addWidget(s.search)
        
        s.list_widget = QtWidgets.QListWidget()
        s.list_widget.itemDoubleClicked.connect(s.accept)  # <--- ДВОЙНОЙ КЛИК ДЛЯ ВЫБОРА
        
        for k in sorted(data_dict.keys()):
            if k.startswith("_"): continue
            s.list_widget.addItem(k)
        s.list_widget.currentTextChanged.connect(s.update_details); left_layout.addWidget(s.list_widget)
        
        right_layout = QtWidgets.QVBoxLayout()
        right_layout.addWidget(QtWidgets.QLabel("<b>Информация:</b>"))
        s.details = QtWidgets.QTextBrowser()
        s.details.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; font-family: Consolas; font-size: 13px;")
        right_layout.addWidget(s.details)
        
        layout.addLayout(left_layout, 1); layout.addLayout(right_layout, 1)
        
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(s.accept); btn_box.rejected.connect(s.reject)
        main_layout = QtWidgets.QVBoxLayout(); main_layout.addLayout(layout); main_layout.addWidget(btn_box); s.setLayout(main_layout)
        
        if s.list_widget.count() > 0: s.list_widget.setCurrentRow(0)

    def filter_list(s, text):
        for i in range(s.list_widget.count()):
            item = s.list_widget.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def update_details(s, name):
        if not name or name not in s.data_dict: return
        d = s.data_dict[name]
        text = ""
        if s.item_type == "isotope":
            text += f"Изотоп: {name}\n\nПериод полураспада: {d.get('half_life_s', 0):.3e} с\n\nГамма-линии (МэВ, выход):\n"
            for line in d.get("lines", []): text += f"  - {line[0]:.4f} МэВ ({line[1]*100:.1f}%)\n"
            if "_note" in d: text += f"\nПримечание: {d['_note']}"
        elif s.item_type.startswith("material"):
            text += f"Материал: {name}\n\nZ: {d.get('Z', 0):.2f}\nA: {d.get('A', 0):.2f}\nПлотность: {d.get('rho', 0)} г/см³\n"
            if "I" in d: text += f"I: {d['I']} эВ\n"
            if "ZA" in d: text += f"Z/A: {d['ZA']:.4f}\n"
            if "mu" in d and s.item_type == "material_gamma":
                try:
                    idx = d["E"].index(1.0)
                    text += f"\nμ/ρ при 1 МэВ: {d['mu'][idx]:.4f} см²/г"
                except ValueError: pass
        s.details.setText(text)
# ==========================================

class GammaWorker(QtCore.QThread):
    done=QtCore.Signal(dict); fail=QtCore.Signal(str); prog=QtCore.Signal(float)
    def __init__(s,p): super().__init__(); s.p=p; s._stop=False
    def stop(s): s._stop=True
    def run(s):
        try:
            t_start = time.perf_counter()
            r=P.gamma_mc(**s.p, progress=lambda f:s.prog.emit(f), should_stop=lambda:s._stop)
            t_end = time.perf_counter()
            if r is not None:
                r["elapsed_time"] = t_end - t_start
                s.done.emit(r)
        except Exception as e: s.fail.emit(f"{type(e).__name__}: {e}")

class AttenuationWorker(QtCore.QThread):
    done=QtCore.Signal(list); fail=QtCore.Signal(str)
    def __init__(s, mat, spec, n_hist, thick): 
        super().__init__(); s.mat=mat; s.spec=spec; s.n_hist=n_hist; s.thick=thick
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
            ranges = [P.csda(s.part, s.T0, s.mat, nstep=800, seed=i)[0] for i in range(50)]
            s.done.emit(ranges)
        except Exception as e: s.fail.emit(f"{type(e).__name__}: {e}")


class GammaTab(QtWidgets.QWidget):
    def __init__(s, console):
        super().__init__(); s.console=console; s.res=None; s.w=None; s.att_res=None
        s.sel_mat = "air"; s.sel_iso = "Am-241"
        
        root=QtWidgets.QHBoxLayout(s)
        p=QtWidgets.QWidget(); p.setFixedWidth(350); fl=QtWidgets.QFormLayout(p)
        s.cb_geom = QtWidgets.QComboBox(); s.cb_geom.addItems(["Сфера", "Плоский слой"])
        s.lbl_R = QtWidgets.QLabel("Радиус,см")
        
        btn_style = "background-color: #2b2b2b; color: #ffffff; text-align: left; padding-left: 10px; border: 1px solid #555555; border-radius: 4px;"
        s.btn_mat = QtWidgets.QPushButton("air"); s.btn_mat.setStyleSheet(btn_style); s.btn_mat.clicked.connect(s.select_material)
        s.btn_iso = QtWidgets.QPushButton("Am-241"); s.btn_iso.setStyleSheet(btn_style); s.btn_iso.clicked.connect(s.select_isotope)
        
        s.tbl_layers = QtWidgets.QTableWidget(3, 2); s.tbl_layers.setHorizontalHeaderLabels(["Материал", "Толщина,см"])
        s.tbl_layers.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        
        def update_total_thickness():
            total = sum(s.tbl_layers.cellWidget(i, 1).value() for i in range(3))
            s.sp_R.setValue(total); s.validate()

        for i in range(3):
            cb = QtWidgets.QComboBox(); cb.addItems(sorted(P.GAMMA_MATS.keys())); cb.setCurrentText("lead" if i==0 else ("polyethylene" if i==1 else "concrete"))
            s.tbl_layers.setCellWidget(i, 0, cb)
            sb = QtWidgets.QDoubleSpinBox(); sb.setRange(0, 1000); sb.setValue(2.0 if i==0 else (10.0 if i==1 else 0.0))
            sb.valueChanged.connect(update_total_thickness); s.tbl_layers.setCellWidget(i, 1, sb)
        s.tbl_layers.setVisible(False)
        
        s.sp_R=QtWidgets.QDoubleSpinBox(); s.sp_R.setRange(1,300); s.sp_R.setValue(10)
        s.sp_n=QtWidgets.QSpinBox(); s.sp_n.setRange(1000,5_000_000); s.sp_n.setValue(100000); s.sp_n.setGroupSeparatorShown(True)
        s.sp_seed=QtWidgets.QSpinBox(); s.sp_seed.setRange(0,999999); s.sp_seed.setValue(42)
        s.chk_abs=QtWidgets.QCheckBox("Абс. доза")
        s.sp_act=QtWidgets.QDoubleSpinBox(); s.sp_act.setRange(0,1e12); s.sp_act.setValue(1.0)
        s.cb_au=QtWidgets.QComboBox(); s.cb_au.addItems(P.ACTIVITY_U.keys()); s.cb_au.setCurrentText("МБк")
        s.sp_t=QtWidgets.QDoubleSpinBox(); s.sp_t.setRange(0,1e12); s.sp_t.setValue(1.0)
        s.cb_tu=QtWidgets.QComboBox(); s.cb_tu.addItems(P.TIME_U.keys()); s.cb_tu.setCurrentText("ч")
        
        s.btn=QtWidgets.QPushButton("▶ Рассчитать гамму"); s.btn.clicked.connect(s.run); s.btn.setStyleSheet("background:#2e7d32;color:white;font-weight:bold;padding:6px;")
        s.btn_export = QtWidgets.QPushButton("💾 Экспорт отчета"); s.btn_export.clicked.connect(s.export_data)
        
        s.btn_viz = QtWidgets.QToolButton(); s.btn_viz.setText("📊 Визуализации ▾")
        s.btn_viz.setStyleSheet("QToolButton { background:#455a64; color:white; padding:6px; border:none; }")
        s.btn_viz.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QtWidgets.QMenu(s.btn_viz)
        menu.addAction("📊 Гистограмма столкновений").triggered.connect(s.show_coll_hist)
        menu.addAction("📐 Угловое распределение").triggered.connect(s.show_polar_hist)
        menu.addAction("📉 Кривая ослабления").triggered.connect(s.run_attenuation)
        menu.addAction("📏 1D-срез (Line Profile)").triggered.connect(s.show_slice)
        s.btn_viz.setMenu(menu)
        
        s.sp_n.valueChanged.connect(s.validate); s.sp_R.valueChanged.connect(s.validate)
        
        def on_geom_change():
            if s.cb_geom.currentText() == "Сфера": 
                s.lbl_R.setText("Радиус,см"); s.tbl_layers.setVisible(False); s.btn_mat.setVisible(True); s.sp_R.setReadOnly(False)
            else: 
                s.lbl_R.setText("Общая толщина,см"); s.tbl_layers.setVisible(True); s.btn_mat.setVisible(False); s.sp_R.setReadOnly(True)
                update_total_thickness()
            s.validate()
        s.cb_geom.currentIndexChanged.connect(on_geom_change)
        
        fl.addRow("Геометрия", s.cb_geom); fl.addRow("Материал", s.btn_mat); fl.addRow(s.tbl_layers)
        fl.addRow("Изотоп", s.btn_iso); fl.addRow(s.lbl_R,s.sp_R)
        fl.addRow("Историй",s.sp_n); fl.addRow("Seed",s.sp_seed); fl.addRow("",s.chk_abs)
        fl.addRow("Активность",s.sp_act); fl.addRow("Ед.акт",s.cb_au); fl.addRow("Время",s.sp_t); fl.addRow("Ед.вр",s.cb_tu)
        fl.addRow(s.btn); fl.addRow(s.btn_export); fl.addRow(s.btn_viz)
        s.pbar=QtWidgets.QProgressBar(); fl.addRow(s.pbar)
        root.addWidget(p)
        
        s.fig=Figure(figsize=(10,10),tight_layout=True)
        s.a1=s.fig.add_subplot(221); s.a2=s.fig.add_subplot(222); s.a3=s.fig.add_subplot(223); s.a4=s.fig.add_subplot(224)
        s.canvas=FigureCanvas(s.fig)
        
        g=QtWidgets.QWidget(); gl=QtWidgets.QVBoxLayout(g)
        hl = QtWidgets.QHBoxLayout()
        s.toolbar_g = NavToolbar(s.canvas,s)
        hl.addWidget(s.toolbar_g)
        hl.addStretch()
        btn_pop = QtWidgets.QPushButton("🔍 Развернуть")
        btn_pop.setStyleSheet("background-color: #2b2b2b; color: white; border: 1px solid #555555; padding: 4px;")
        btn_pop.clicked.connect(lambda: PopOutDialog(s.fig, "Гамма-модуль: Визуализация", s).exec())
        hl.addWidget(btn_pop)
        gl.addLayout(hl); gl.addWidget(s.canvas); root.addWidget(g,1)
        
        s.validate()

    def select_material(s):
        dlg = SelectorDialog("Выбор материала (Гамма)", P.GAMMA_MATS, "material_gamma", s)
        if dlg.exec():
            sel = dlg.list_widget.currentItem()
            if sel: s.sel_mat = sel.text(); s.btn_mat.setText(s.sel_mat)

    def select_isotope(s):
        valid = {k:v for k,v in P.ISOTOPES.items() if k not in ["Sr-90", "Y-90"]}
        dlg = SelectorDialog("Выбор изотопа (Гамма)", valid, "isotope", s)
        if dlg.exec():
            sel = dlg.list_widget.currentItem()
            if sel: s.sel_iso = sel.text(); s.btn_iso.setText(s.sel_iso)

    def validate(s):
        ok = True
        if s.sp_n.value() < 1000: ok = False
        if s.sp_R.value() <= 0: ok = False
        if s.cb_geom.currentText() == "Плоский слой":
            if sum(s.tbl_layers.cellWidget(i, 1).value() for i in range(3)) <= 0: ok = False
        s.btn.setEnabled(ok)

    def run(s):
        if s.w and s.w.isRunning(): s.console("[ГАММА] Уже идёт расчёт."); return
        layers = []
        if s.cb_geom.currentText() == "Плоский слой":
            for i in range(3):
                thick = s.tbl_layers.cellWidget(i, 1).value()
                if thick > 0: layers.append((P.make_gamma_mat(s.tbl_layers.cellWidget(i, 0).currentText()), thick))
            if not layers: s.console("[ГАММА] ОШИБКА: Все слои нулевой толщины!"); return
            mat = layers[0][0]; R = sum(l[1] for l in layers)
        else:
            mat = P.make_gamma_mat(s.sel_mat); R = s.sp_R.value()
            
        spec=P.ISOTOPES[s.sel_iso]["lines"]
        s.p={"mat":mat,"R":R,"spec_lines":spec,"n_hist":s.sp_n.value(),"seed":s.sp_seed.value(), 
             "geom": "slab" if s.cb_geom.currentText() == "Плоский слой" else "sphere", "layers": layers if layers else None}
        s.btn.setEnabled(False); s.pbar.setValue(0)
        s.console(f"[ГАММА] старт: N={s.sp_n.value()}, геометрия={s.p['geom']}")
        s.w=GammaWorker(s.p); s.w.prog.connect(lambda f:s.pbar.setValue(int(f*100)))
        s.w.done.connect(s.ok); s.w.fail.connect(s.err); s.w.start()

    def err(s,m): s.btn.setEnabled(True); s.validate(); s.console("[ГАММА] ОШИБКА: "+m)
    
    def ok(s,r):
        s.res=r; s.btn.setEnabled(True); s.validate(); s.pbar.setValue(100)
        theor_escape = r.get("theor_escape", np.exp(-r["mu"] * r["R"]))
        sim_escape = r["nlk_uncoll"] / r["n"] if r["n"] > 0 else 0.0
        backscatter_pct = (r.get("backscatter_count", 0) / r["n"]) * 100 if r["n"] > 0 else 0.0
        
        s.console(f"[ГАММА] готово: доза={r['dose']:.3e} Гр/ч-ца | фото/комптон/пары={r['nph']}/{r['nco']}/{r['npa']}")
        
        if "elapsed_time" in r:
            s.console(f"  [ВРЕМЯ] Расчет и компиляция Numba заняли: {r['elapsed_time']:.3f} сек")
            
        s.console(f"  Бугер: теория={theor_escape:.4f}, модель={sim_escape:.4f}")
        if backscatter_pct > 0: s.console(f"  Обратное рассеяние: {backscatter_pct:.2f}%")
        
        if s.chk_abs.isChecked():
            abs_res = P.absolute_dose(r, s.sp_act.value(), s.cb_au.currentText(), s.sp_t.value(), s.cb_tu.currentText(), True, s.sel_iso)
            s.console(f"  Абсолютная доза: {abs_res['dose_abs']:.3e} Зв"); r.update(abs_res)

        s.a1.clear(); s.a2.clear(); s.a3.clear(); s.a4.clear()
        if len(r["src"]): s.a1.hist(r["src"],bins=40,color="seagreen"); s.a1.set_title("Спектр источника")
        if len(r["leak"]): s.a2.hist(r["leak"],bins=50,color="steelblue"); s.a2.set_title("Спектр утечки")
        g2=r["grid"].copy(); pos=g2[g2>0]; vmin=pos.min() if pos.size else 1e-12; g2[g2<=0]=vmin
        
        if r["geom"] == "slab": 
            s.a3.imshow(g2, origin="lower", extent=[0,r["R"],-r["R"],r["R"]], cmap="inferno", norm=LogNorm(vmin=vmin,vmax=g2.max()), interpolation='nearest'); s.a3.set_xlabel("X (глубина), см")
        else: 
            s.a3.imshow(g2, origin="lower", extent=[-r["R"],r["R"],-r["R"],r["R"]], cmap="inferno", norm=LogNorm(vmin=vmin,vmax=g2.max()), interpolation='nearest'); s.a3.set_xlabel("X,см")
            
        s.a3.set_title("2D карта")
        s.a4.plot(r["r"],r["rad_dose"],"o-",color="darkorange"); s.a4.set_title("Профиль дозы")
        if np.any(r["rad_dose"]>0): s.a4.set_yscale("log")
        s.canvas.draw()

    def show_coll_hist(s):
        if not s.res or "coll_hist" not in s.res: return s.console("[ВИЗУАЛИЗАЦИЯ] Нет данных")
        fig = Figure(figsize=(8, 6), tight_layout=True); ax = fig.add_subplot(111)
        ax.bar(np.arange(len(s.res["coll_hist"])), s.res["coll_hist"], color="teal", alpha=0.8)
        ax.set_xlabel("Число столкновений"); ax.set_ylabel("Кол-во фотонов"); ax.set_title("Гистограмма столкновений"); ax.grid(alpha=0.3)
        win = QtWidgets.QDialog(s); win.setWindowTitle("Гистограмма"); win.resize(800, 600)
        canvas = FigureCanvas(fig); layout = QtWidgets.QVBoxLayout(win); layout.addWidget(canvas); canvas.draw(); win.exec()

    def show_slice(s):
        if not s.res or "grid" not in s.res: 
            return s.console("[ВИЗУАЛИЗАЦИЯ] Сначала выполните расчет!")
        dlg = SliceDialog(s.res["grid"], s.res["R"], s.res["geom"], s)
        dlg.exec()

    def show_polar_hist(s):
        if not s.res or "theta_hist" not in s.res: return s.console("[ВИЗУАЛИЗАЦИЯ] Нет данных")
        fig = Figure(figsize=(8, 8), tight_layout=True); ax = fig.add_subplot(111, projection='polar')
        hist = s.res["theta_hist"]; cos_theta = (np.arange(90) + 0.5) / 45 - 1; angles = np.arccos(cos_theta)
        ax.bar(angles, hist, width=np.pi/90, color="darkred", alpha=0.7)
        ax.set_title("Угловое распределение рассеянных фотонов (0° = вперед)")
        win = QtWidgets.QDialog(s); win.setWindowTitle("Полярный график"); win.resize(800, 800)
        canvas = FigureCanvas(fig); layout = QtWidgets.QVBoxLayout(win); layout.addWidget(canvas); canvas.draw(); win.exec()

    def run_attenuation(s):
        s.att_res = None; mat = P.make_gamma_mat(s.sel_mat); spec = P.ISOTOPES[s.sel_iso]["lines"]; thick = np.linspace(0, 20, 11)
        s.console(f"[ГАММА] Запуск кривой ослабления для {s.sel_mat}...")
        s.w_att = AttenuationWorker(mat, spec, 10000, thick)
        s.w_att.done.connect(s.show_attenuation_plot); s.w_att.fail.connect(lambda m: s.console(f"[ОШИБКА] {m}")); s.w_att.start()

    def show_attenuation_plot(s, results):
        s.att_res = results; s.console("[ГАММА] Кривая ослабления готова!")
        fig = Figure(figsize=(8, 6), tight_layout=True); ax = fig.add_subplot(111)
        x = [r[0] for r in results]; y_model = [r[1] for r in results]; y_theory = [r[2] for r in results]
        ax.plot(x, y_model, 'o-', color='blue', label='Модель (МК)'); ax.plot(x, y_theory, '--', color='red', label='Теория (e^{-mu*x})')
        ax.set_yscale("log"); ax.set_xlabel("Толщина, см"); ax.set_ylabel("Доля выживших (Transmission)")
        ax.set_title(f"Кривая ослабления: {s.sel_mat}"); ax.legend(); ax.grid(alpha=0.3)
        win = QtWidgets.QDialog(s); win.setWindowTitle("Кривая ослабления"); win.resize(800, 600)
        canvas = FigureCanvas(fig); layout = QtWidgets.QVBoxLayout(win); layout.addWidget(canvas); canvas.draw(); win.exec()

    def export_data(s):
        if not s.res: return s.console("[ЭКСПОРТ] Нет данных!")
        path, _ = QtWidgets.QFileDialog.getSaveFileName(s, "Сохранить", "report", "HTML (*.html);;JSON (*.json);;CSV (*.csv);;NumPy Matrix (*.npy)")
        if not path: return
        try:
            if path.endswith('.csv'): 
                np.savetxt(path, np.column_stack((s.res["r"], s.res["rad_dose"])), delimiter=";", header="r;dose")
            elif path.endswith('.npy'):
                np.save(path, s.res["grid"])
                s.console(f"[ЭКСПОРТ] Матрица 2D-карты сохранена в формате NumPy (.npy)")
            elif path.endswith('.json'):
                with open(path, "w", encoding="utf-8") as f: 
                    json.dump(make_json_serializable(s.res), f)
            elif path.endswith('.html'):
                img_main = fig_to_base64(s.fig); img_coll = img_polar = img_att = None
                if "coll_hist" in s.res and s.res["coll_hist"].sum() > 0:
                    fig_c = Figure(figsize=(8, 5), tight_layout=True); ax_c = fig_c.add_subplot(111)
                    ax_c.bar(np.arange(len(s.res["coll_hist"])), s.res["coll_hist"], color="teal", alpha=0.8)
                    ax_c.set_xlabel("Число столкновений"); ax_c.set_ylabel("Кол-во фотонов"); ax_c.grid(alpha=0.3); img_coll = fig_to_base64(fig_c)
                if "theta_hist" in s.res and s.res["theta_hist"].sum() > 0:
                    fig_p = Figure(figsize=(7, 7), tight_layout=True); ax_p = fig_p.add_subplot(111, projection='polar')
                    cos_theta = (np.arange(90) + 0.5) / 45 - 1; angles = np.arccos(cos_theta)
                    ax_p.bar(angles, s.res["theta_hist"], width=np.pi/90, color="darkred", alpha=0.7); img_polar = fig_to_base64(fig_p)
                if s.att_res is not None:
                    fig_a = Figure(figsize=(8, 5), tight_layout=True); ax_a = fig_a.add_subplot(111)
                    x_att = [r[0] for r in s.att_res]; y_mod = [r[1] for r in s.att_res]; y_th = [r[2] for r in s.att_res]
                    ax_a.plot(x_att, y_mod, 'o-', color='blue', label='Модель'); ax_a.plot(x_att, y_th, '--', color='red', label='Теория')
                    ax_a.set_yscale("log"); ax_a.set_xlabel("Толщина, см"); ax_a.set_ylabel("Transmission")
                    ax_a.legend(); ax_a.grid(alpha=0.3); img_att = fig_to_base64(fig_a)

                html = f"""<html><head><meta charset="utf-8"><title>Prometheus Report</title>
<style>body {{ font-family: Arial; margin: 40px; background: #f4f4f9; }} h1 {{ color: #2e7d32; }} h2 {{ color: #1565c0; margin-top: 40px; }}
table {{ border-collapse: collapse; width: 60%; background: white; }} th, td {{ border: 1px solid #ddd; padding: 8px; }}
th {{ background-color: #2e7d32; color: white; }} img {{ max-width: 100%; border: 1px solid #ccc; margin-top: 10px; }}</style></head><body>
<h1>Prometheus Core: Отчет</h1><h2>Результаты</h2>
<table><tr><th>Параметр</th><th>Значение</th></tr>
<tr><td>Доза</td><td>{s.res['dose']:.4e} Гр/ч-ца</td></tr>
<tr><td>Фото/Комптон/Пары</td><td>{s.res['nph']} / {s.res['nco']} / {s.res['npa']}</td></tr>
<tr><td>Бугер (теория/модель)</td><td>{s.res.get('theor_escape', 0):.4f} / {(s.res['nlk_uncoll']/s.res['n']):.4f}</td></tr>
</table><h2>Графики</h2><img src="data:image/png;base64,{img_main}">"""
                if img_coll: html += f'<h2>Гистограмма столкновений</h2><img src="data:image/png;base64,{img_coll}">'
                if img_polar: html += f'<h2>Угловое распределение</h2><img src="data:image/png;base64,{img_polar}">'
                if img_att: html += f'<h2>Кривая ослабления</h2><img src="data:image/png;base64,{img_att}">'
                html += "</body></html>"
                with open(path, "w", encoding="utf-8") as f: f.write(html)
            s.console(f"[ЭКСПОРТ] Сохранено в {path}")
        except Exception as e: s.console(f"[ЭКСПОРТ] ОШИБКА: {e}")


class ChargedTab(QtWidgets.QWidget):
    def __init__(s, console):
        super().__init__(); s.console=console; s.res=None; s.sel_mat = "вода"
        
        root=QtWidgets.QHBoxLayout(s)
        p=QtWidgets.QWidget(); p.setFixedWidth(350); fl=QtWidgets.QFormLayout(p)
        s.cb_p=QtWidgets.QComboBox(); s.cb_p.addItems(P.PARTICLES.keys())
        
        s.cb_mode = QtWidgets.QComboBox()
        s.cb_mode.addItems(["База данных", "Ручной ввод"])
        s.cb_mode.currentIndexChanged.connect(s.toggle_mode)

        btn_style = "background-color: #2b2b2b; color: #ffffff; text-align: left; padding-left: 10px; border: 1px solid #555555; border-radius: 4px;"
        s.btn_mat = QtWidgets.QPushButton("вода"); s.btn_mat.setStyleSheet(btn_style); s.btn_mat.clicked.connect(s.select_material)
        
        s.lbl_mat_info = QtWidgets.QLabel("Z: -, A: -, rho: -"); s.lbl_mat_info.setStyleSheet("color: #888888; font-size: 11px; font-style: italic;")
        
        s.lbl_Z = QtWidgets.QLabel("Z (Ат. номер)"); s.lbl_A = QtWidgets.QLabel("A (Масса)")
        s.lbl_rho = QtWidgets.QLabel("rho (г/см³)"); s.lbl_I = QtWidgets.QLabel("I (эВ)")

        s.sp_Z = QtWidgets.QDoubleSpinBox(); s.sp_Z.setRange(1, 100); s.sp_Z.setValue(7.42)
        s.sp_A = QtWidgets.QDoubleSpinBox(); s.sp_A.setRange(1, 300); s.sp_A.setValue(18.015)
        s.sp_rho = QtWidgets.QDoubleSpinBox(); s.sp_rho.setRange(0.001, 30); s.sp_rho.setValue(1.0); s.sp_rho.setDecimals(3)
        s.sp_I = QtWidgets.QDoubleSpinBox(); s.sp_I.setRange(1, 1000); s.sp_I.setValue(75.0)

        s.sp_E=QtWidgets.QDoubleSpinBox(); s.sp_E.setRange(0.01,1000); s.sp_E.setValue(100.0); s.sp_E.setDecimals(3)
        b=QtWidgets.QPushButton("▶ Рассчитать"); b.clicked.connect(s.run); b.setStyleSheet("background:#1565c0;color:white;padding:6px;")
        s.chk_overlay = QtWidgets.QCheckBox("Наложение")
        s.btn_clear = QtWidgets.QPushButton("Очистить"); s.btn_clear.clicked.connect(s.clear_plots)
        
        fl.addRow("Частица",s.cb_p); fl.addRow("Режим", s.cb_mode)
        fl.addRow("Материал",s.btn_mat); fl.addRow("", s.lbl_mat_info)
        fl.addRow(s.lbl_Z, s.sp_Z); fl.addRow(s.lbl_A, s.sp_A)
        fl.addRow(s.lbl_rho, s.sp_rho); fl.addRow(s.lbl_I, s.sp_I)
        fl.addRow("Энергия (МэВ)",s.sp_E)
        fl.addRow(b); fl.addRow(s.chk_overlay); fl.addRow(s.btn_clear)
        
        root.addWidget(p)
        
        s.fig=Figure(figsize=(10,8),tight_layout=True)
        s.a1=s.fig.add_subplot(221); s.a2=s.fig.add_subplot(222)
        s.a3=s.fig.add_subplot(223); s.a4=s.fig.add_subplot(224)
        s.canvas=FigureCanvas(s.fig)
        
        g=QtWidgets.QWidget(); gl=QtWidgets.QVBoxLayout(g)
        hl = QtWidgets.QHBoxLayout()
        s.toolbar_g = NavToolbar(s.canvas,s)
        hl.addWidget(s.toolbar_g)
        hl.addStretch()
        btn_pop = QtWidgets.QPushButton("🔍 Развернуть")
        btn_pop.setStyleSheet("background-color: #2b2b2b; color: white; border: 1px solid #555555; padding: 4px;")
        btn_pop.clicked.connect(lambda: PopOutDialog(s.fig, "Заряженные частицы: Визуализация", s).exec())
        hl.addWidget(btn_pop)
        gl.addLayout(hl); gl.addWidget(s.canvas); root.addWidget(g,1)
        
        s.toggle_mode()
        s.update_mat_info()

    def toggle_mode(s):
        is_manual = (s.cb_mode.currentIndex() == 1)
        s.btn_mat.setVisible(not is_manual)
        s.lbl_mat_info.setVisible(not is_manual)
        for w in [s.lbl_Z, s.sp_Z, s.lbl_A, s.sp_A, s.lbl_rho, s.sp_rho, s.lbl_I, s.sp_I]:
            w.setVisible(is_manual)

    def select_material(s):
        dlg = SelectorDialog("Выбор материала (Заряженные)", P.CP_MAT, "material_charged", s)
        if dlg.exec():
            sel = dlg.list_widget.currentItem()
            if sel: s.sel_mat = sel.text(); s.btn_mat.setText(s.sel_mat); s.update_mat_info()

    def update_mat_info(s):
        if s.sel_mat in P.CP_MAT:
            m = P.CP_MAT[s.sel_mat]
            info = f"Z={m['Z']}, A={m['A']}, rho={m['rho']} г/см³"
            if "I" in m: info += f"\nI={m['I']} эВ"
            if "ZA" in m: info += f", Z/A={m['ZA']:.4f}"
            s.lbl_mat_info.setText(info)
        
    def run(s):
        pt=s.cb_p.currentText()
        if s.cb_mode.currentIndex() == 1:
            mat = {"Z": s.sp_Z.value(), "A": s.sp_A.value(), "rho": s.sp_rho.value(), "I": s.sp_I.value(), "ZA": s.sp_Z.value()/s.sp_A.value()}
            mat_name = "Ручной ввод"
        else:
            mat = P.CP_MAT[s.sel_mat]
            mat_name = s.sel_mat
            
        T0=s.sp_E.value(); R,dep,de=P.csda(pt,T0,mat)
        wr = {"протон": 2.0, "альфа": 20.0, "дейтрон": 2.0, "электрон": 1.0}.get(pt, 1.0)
        dE_dx = P.sp_elec(T0, mat)[0] if pt == "электрон" else P.sp_heavy(T0, *P.PARTICLES[pt], mat)
            
        s.console(f"[ЗАРЯЖ] {pt} {T0}МэВ в {mat_name}: dE/dx={dE_dx:.4g}МэВ/см, пробег={R:.4g}см (wR={wr:.0f})")
        
        if not s.chk_overlay.isChecked(): s.a1.clear(); s.a2.clear(); s.a3.clear(); s.a4.clear()
        color = {"протон": "crimson", "альфа": "darkgreen", "электрон": "blue", "дейтрон": "purple"}.get(pt, "black")
        
        s.a1.plot(dep,de,color=color,lw=2); s.a1.set_title("Тормозная способность (dE/dx)"); s.a1.set_xlabel("Глубина, см"); s.a1.set_ylabel("МэВ/см")
        Es,Rs=P.range_vs_energy(pt,mat); s.a2.plot(Es,Rs,color=color,lw=2); s.a2.set_title("Пробег (CSDA)"); s.a2.set_xlabel("Энергия, МэВ"); s.a2.set_ylabel("Пробег, см")
        
        s.a3.plot(dep, de, color=color, lw=2); s.a3.fill_between(dep, de, color=color, alpha=0.3)
        s.a3.set_title("Кривая Брэгга (Пик энерговыделения)"); s.a3.set_xlabel("Глубина, см"); s.a3.set_ylabel("Удельные потери (МэВ/см)")
        
        s.a4.set_title("Страгглинг (разброс пробегов)"); s.a4.set_xlabel("Пробег, см"); s.a4.set_ylabel("Частота")
        s.w_str = StragglingWorker(pt, T0, mat)
        s.w_str.done.connect(lambda ranges: s.draw_straggling(ranges, color))
        s.w_str.start()
        
        s.canvas.draw()

    def draw_straggling(s, ranges, color):
        s.a4.clear()
        s.a4.hist(ranges, bins=15, color=color, alpha=0.7, edgecolor='black')
        s.a4.set_title("Страгглинг (разброс пробегов)")
        s.a4.set_xlabel("Пробег, см"); s.a4.set_ylabel("Частота")
        s.canvas.draw()
        
    def clear_plots(s): s.a1.clear(); s.a2.clear(); s.a3.clear(); s.a4.clear(); s.canvas.draw()


class NeutronTab(QtWidgets.QWidget):
    def __init__(s, console):
        super().__init__(); s.console=console; s.w=None
        root=QtWidgets.QHBoxLayout(s); p=QtWidgets.QWidget(); p.setFixedWidth(350); fl=QtWidgets.QFormLayout(p)
        s.cb_m=QtWidgets.QComboBox(); s.cb_m.addItems(["water","polyethylene","concrete","iron","lead","graphite","b4c","uranium"])
        s.sp_R=QtWidgets.QDoubleSpinBox(); s.sp_R.setRange(1,200); s.sp_R.setValue(30)
        s.sp_E=QtWidgets.QDoubleSpinBox(); s.sp_E.setRange(0.001, 20); s.sp_E.setValue(2.0)
        s.sp_n=QtWidgets.QSpinBox(); s.sp_n.setRange(1000,2_000_000); s.sp_n.setValue(10000)
        s.sp_b=QtWidgets.QSpinBox(); s.sp_b.setRange(1,200); s.sp_b.setValue(20)
        s.btn=QtWidgets.QPushButton("▶ Запустить OpenMC"); s.btn.clicked.connect(s.run); s.btn.setStyleSheet("background:#00695c;color:white;padding:6px;")
        for lab,wg in [("Материал",s.cb_m),("Радиус",s.sp_R),("Энергия",s.sp_E),("Частиц/батч",s.sp_n),("Батчей",s.sp_b)]: fl.addRow(lab,wg)
        fl.addRow(s.btn); root.addWidget(p)
        
        s.fig=Figure(figsize=(10,8),tight_layout=True); s.a1=s.fig.add_subplot(211); s.a2=s.fig.add_subplot(212)
        s.canvas=FigureCanvas(s.fig)
        
        g=QtWidgets.QWidget(); gl=QtWidgets.QVBoxLayout(g)
        hl = QtWidgets.QHBoxLayout()
        s.toolbar_g = NavToolbar(s.canvas,s)
        hl.addWidget(s.toolbar_g)
        hl.addStretch()
        btn_pop = QtWidgets.QPushButton("🔍 Развернуть")
        btn_pop.setStyleSheet("background-color: #2b2b2b; color: white; border: 1px solid #555555; padding: 4px;")
        btn_pop.clicked.connect(lambda: PopOutDialog(s.fig, "Нейтроны: Визуализация", s).exec())
        hl.addWidget(btn_pop)
        gl.addLayout(hl); gl.addWidget(s.canvas); root.addWidget(g,1)
    
    def run(s):
        if s.w and s.w.isRunning(): s.console("[НЕЙТРОНЫ] Уже идёт расчёт."); return
        cfg={"material":s.cb_m.currentText(),"radius":s.sp_R.value(),"energy_MeV":s.sp_E.value(),"particles":s.sp_n.value(),"batches":s.sp_b.value(),"mesh_n":80}
        s.btn.setEnabled(False); s.console("[НЕЙТРОНЫ] запуск...")
        s.w=NeutronWorker(cfg); s.w.msg.connect(s.console); s.w.done.connect(s.ok); s.w.fail.connect(lambda m: s.console("[ОШИБКА] "+m)); s.w.start()
        
    def ok(s,r):
        s.btn.setEnabled(True); st=r["stats"]; 
        s.console(f"[НЕЙТРОНЫ] рассеяние={st['scatter']:.4e} поглощение={st['absorption']:.4e}")
        
        if "dose" in st: 
            s.console(f"[НЕЙТРОНЫ] Эквивалентная доза (ICRP-74): {st['dose']:.4e} Зв·см²/источник")
        
        if "groups" in st and len(st["groups"]) == 3:
            g_flux = st["groups"]
            s.console(f"[НЕЙТРОНЫ] Многогрупповой поток: Тепловые={g_flux[0]:.3e}, Резонансные={g_flux[1]:.3e}, Быстрые={g_flux[2]:.3e}")

        import matplotlib.image as mpimg
        s.a1.clear(); s.a2.clear(); 
        s.a1.imshow(mpimg.imread(r["spec_img"])); s.a1.axis("off"); 
        s.a2.imshow(mpimg.imread(r["map_img"])); s.a2.axis("off"); 
        s.canvas.draw()

class HotkeysDialog(QtWidgets.QDialog):
    def __init__(s, parent=None):
        super().__init__(parent); s.setWindowTitle("Горячие клавиши"); s.resize(500, 400)
        layout = QtWidgets.QVBoxLayout(s); layout.addWidget(QtWidgets.QLabel("<h2>Горячие клавиши Prometheus Core</h2>"))
        table = QtWidgets.QTableWidget(); table.setColumnCount(2); table.setHorizontalHeaderLabels(["Клавиша", "Действие"])
        table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        hotkeys = [("Ctrl+R", "Рассчитать"), ("Ctrl+E", "Экспорт"), ("Ctrl+S", "Сохранить"), ("Ctrl+O", "Загрузить"), ("Ctrl+T", "Сменить тему"), ("F1", "Справка")]
        table.setRowCount(len(hotkeys))
        for i, (key, desc) in enumerate(hotkeys):
            table.setItem(i, 0, QtWidgets.QTableWidgetItem(key)); table.setItem(i, 1, QtWidgets.QTableWidgetItem(desc))
        layout.addWidget(table); btn = QtWidgets.QPushButton("Закрыть"); btn.clicked.connect(s.close); layout.addWidget(btn)

class Main(QtWidgets.QMainWindow):
    def __init__(s):
        super().__init__()
        s.setWindowTitle("Prometheus Core v3.1.0 (Dev)"); s.setWindowIcon(make_app_icon()); s.dark_mode = True
        
        menubar = s.menuBar(); file_menu = menubar.addMenu("Файл")
        act_save = QtGui.QAction("Сохранить проект (Ctrl+S)", s); act_save.triggered.connect(s.save_session); file_menu.addAction(act_save)
        act_load = QtGui.QAction("Загрузить проект (Ctrl+O)", s); act_load.triggered.connect(s.load_session); file_menu.addAction(act_load)
        file_menu.addSeparator(); act_exit = QtGui.QAction("Выход", s); act_exit.triggered.connect(s.close); file_menu.addAction(act_exit)
        view_menu = menubar.addMenu("Вид"); act_theme = QtGui.QAction("Сменить тему (Ctrl+T)", s); act_theme.triggered.connect(s.toggle_theme); view_menu.addAction(act_theme)
        
        help_menu = menubar.addMenu("Справка")
        act_hotkeys = QtGui.QAction("Горячие клавиши (F1)", s); act_hotkeys.triggered.connect(s.show_hotkeys); help_menu.addAction(act_hotkeys)
        help_menu.addSeparator()
        act_val = QtGui.QAction("Запустить верификацию NIST", s); act_val.triggered.connect(s.run_validation); help_menu.addAction(act_val)

        s.con=QtWidgets.QPlainTextEdit(); s.con.setReadOnly(True); s.con.setMaximumHeight(200)
        s.con.setStyleSheet("font-family:Consolas;font-size:12px;background:#1e1e1e;color:#d4d4d4;")
        P.attach_log_widget(s.con); P.setup_log_file(OUT)
        
        def console(m): P.plog(m)
        s.gtab = GammaTab(console); s.ctab = ChargedTab(console); s.ntab = NeutronTab(console)
        
        tabs=QtWidgets.QTabWidget()
        tabs.addTab(s.gtab,"☢️ Гамма"); tabs.addTab(s.ctab,"⚙️ Заряженные"); tabs.addTab(s.ntab,"🔬 Нейтроны")
        tabl=s._mat_table(); tabs.addTab(tabl,"📋 Таблица материалов")
        
        c=QtWidgets.QWidget(); v=QtWidgets.QVBoxLayout(c); v.addWidget(tabs,1); v.addWidget(QtWidgets.QLabel("ЛОГ:")); v.addWidget(s.con); s.setCentralWidget(c)
        s.status = s.statusBar(); s.status.showMessage(f"Готово | Материалов: {len(P.GAMMA_MATS)} | Изотопов: {len(P.ISOTOPES)}")
        
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+R"), s, activated=s.run_active_tab)
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+E"), s, activated=s.export_active_tab)
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+S"), s, activated=s.save_session)
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+O"), s, activated=s.load_session)
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+T"), s, activated=s.toggle_theme)
        QtGui.QShortcut(QtGui.QKeySequence("F1"), s, activated=s.show_hotkeys)
        s.tabs = tabs

    def run_active_tab(s):
        idx = s.tabs.currentIndex()
        if idx == 0: s.gtab.run()
        elif idx == 1: s.ctab.run()
        elif idx == 2: s.ntab.run()

    def export_active_tab(s):
        if s.tabs.currentIndex() == 0: s.gtab.export_data()
        else: P.plog("[ЭКСПОРТ] Экспорт доступен только для вкладки 'Гамма'")

    def show_hotkeys(s): HotkeysDialog(s).exec()

    def run_validation(s):
        report = validator.run_validation(log_cb=lambda msg, level="info": P.plog(msg, level))
        dlg = QtWidgets.QDialog(s); dlg.setWindowTitle("Отчет о верификации NIST"); dlg.resize(800, 500)
        layout = QtWidgets.QVBoxLayout(dlg)
        text = QtWidgets.QPlainTextEdit(); text.setPlainText(report); text.setReadOnly(True); text.setStyleSheet("font-family: Consolas; font-size: 13px;")
        layout.addWidget(text)
        btn = QtWidgets.QPushButton("Закрыть"); btn.clicked.connect(dlg.accept); layout.addWidget(btn)
        dlg.exec()

    def toggle_theme(s):
        s.dark_mode = not s.dark_mode; app = QtWidgets.QApplication.instance()
        if s.dark_mode:
            app.setStyle("Fusion"); s.setStyleSheet("")
            s.con.setStyleSheet("font-family:Consolas;font-size:12px;background:#1e1e1e;color:#d4d4d4;")
        else:
            app.setStyle("Fusion"); s.setStyleSheet("QWidget { background-color: #f0f0f0; color: #000000; } QPushButton { background-color: #e0e0e0; border: 1px solid #aaa; padding: 6px; } QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox { background: white; }")
            s.con.setStyleSheet("font-family:Consolas;font-size:12px;background:#ffffff;color:#000000;")
        P.plog(f"[ТЕМА] Переключено на {'тёмную' if s.dark_mode else 'светлую'}")

    def save_session(s):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(s, "Сохранить", "project.json", "JSON (*.json)")
        if not path: return
        data = {
            "gamma": {"geom": s.gtab.cb_geom.currentText(), "mat": s.gtab.sel_mat, "iso": s.gtab.sel_iso, "R": s.gtab.sp_R.value(), "N": s.gtab.sp_n.value(), "layers": [(s.gtab.tbl_layers.cellWidget(i,0).currentText(), s.gtab.tbl_layers.cellWidget(i,1).value()) for i in range(3)]},
            "charged": {"pt": s.ctab.cb_p.currentText(), "mat": s.ctab.sel_mat, "mode": s.ctab.cb_mode.currentIndex(), "E": s.ctab.sp_E.value(),
                        "custom_Z": s.ctab.sp_Z.value(), "custom_A": s.ctab.sp_A.value(), "custom_rho": s.ctab.sp_rho.value(), "custom_I": s.ctab.sp_I.value()}
        }
        with open(path, "w", encoding="utf-8") as f: json.dump(data, f, indent=2)
        P.plog(f"[СЕССИЯ] Сохранено в {path}")

    def load_session(s):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(s, "Загрузить", "", "JSON (*.json)")
        if not path: return
        try:
            with open(path, "r", encoding="utf-8") as f: data = json.load(f)
            if "gamma" in data:
                g = data["gamma"]
                s.gtab.cb_geom.setCurrentText(g.get("geom", "Сфера")); 
                s.gtab.sel_mat = g.get("mat", "air"); s.gtab.btn_mat.setText(s.gtab.sel_mat)
                s.gtab.sel_iso = g.get("iso", "Am-241"); s.gtab.btn_iso.setText(s.gtab.sel_iso)
                s.gtab.sp_R.setValue(g.get("R", 10)); s.gtab.sp_n.setValue(g.get("N", 100000))
                if "layers" in g:
                    for i, (m, t) in enumerate(g["layers"]):
                        s.gtab.tbl_layers.cellWidget(i, 0).setCurrentText(m); s.gtab.tbl_layers.cellWidget(i, 1).setValue(t)
            if "charged" in data:
                c = data["charged"]; 
                s.ctab.cb_p.setCurrentText(c.get("pt", "протон")); 
                s.ctab.cb_mode.setCurrentIndex(c.get("mode", 0))
                s.ctab.sel_mat = c.get("mat", "вода"); s.ctab.btn_mat.setText(s.ctab.sel_mat); s.ctab.update_mat_info()
                s.ctab.sp_E.setValue(c.get("E", 100))
                s.ctab.sp_Z.setValue(c.get("custom_Z", 7.42)); s.ctab.sp_A.setValue(c.get("custom_A", 18.015))
                s.ctab.sp_rho.setValue(c.get("custom_rho", 1.0)); s.ctab.sp_I.setValue(c.get("custom_I", 75.0))
            P.plog(f"[СЕССИЯ] Загружено из {path}")
        except Exception as e: P.plog(f"[СЕССИЯ] Ошибка загрузки: {e}")

    def _mat_table(s):
        t=QtWidgets.QTableWidget(); t.setColumnCount(5); t.setHorizontalHeaderLabels(["Материал","Z","A","Плотность","mu/rho@1МэВ"])
        names=sorted(P.GAMMA_MATS.keys()); t.setRowCount(len(names))
        for i,n in enumerate(names):
            m=P.make_gamma_mat(n)
            for j,v in enumerate([n,f"{m.Z:g}",f"{m.A:g}",f"{m.density:g}",f"{m.mu_rho(1.0):.4g}"]):
                t.setItem(i,j,QtWidgets.QTableWidgetItem(v))
        t.resizeColumnsToContents(); return t

    def closeEvent(s, event):
        for tab in [s.gtab, s.ctab, s.ntab]:
            try:
                if hasattr(tab, 'canvas') and hasattr(tab, 'toolbar_g'):
                    tab.canvas.mpl_disconnect(tab.toolbar_g._id_drag)
                    tab.canvas.mpl_disconnect(tab.toolbar_g._id_press)
                    tab.canvas.mpl_disconnect(tab.toolbar_g._id_release)
            except Exception:
                pass

        for w in [getattr(s.gtab, "w", None), getattr(s.gtab, "w_att", None), getattr(s.ntab, "w", None), getattr(s.ctab, "w_str", None)]:
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