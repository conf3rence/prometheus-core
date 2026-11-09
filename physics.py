"""
physics.py — физическое ядро Prometheus Core v3
Многослойность, Поляризация, Backscatter + мост в wsl/openmc.
"""
import os, sys, math, json, subprocess, tempfile, datetime, logging, shutil
import numpy as np
try:
    from numba import njit
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False
    def njit(*args, **kwargs):
        if len(args) == 1 and callable(args[0]) and not kwargs:
            return args[0]
        def decorator(f): return f
        return decorator

if getattr(sys, 'frozen', False):
    if hasattr(sys, '_MEIPASS'): BASE_DIR = sys._MEIPASS
    else: BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, "data")
if getattr(sys, 'frozen', False): OUT_DIR = os.path.join(os.path.dirname(sys.executable), "output")
else: OUT_DIR = os.path.join(BASE_DIR, "output")

MEC2=0.510998950; RE=2.8179403262e-13; MEV_TO_J=1.602176634e-13
ME=0.510998950; MP=938.272089; MALPHA=3727.379; K_BB=0.307075
_Y=365.25*24*3600; _D=86400; _H=3600

def _load(fname):
    p = os.path.join(DATA_DIR, fname)
    if not os.path.isfile(p): raise FileNotFoundError(f"Не найден файл: {p}")
    with open(p, encoding="utf-8") as f: return json.load(f)

_MAT_RAW = _load("materials.json")
_ISO_RAW = _load("isotopes.json")
GAMMA_MATS = {k: v for k, v in _MAT_RAW.items() if not k.startswith("_")}
ISOTOPES   = {k: v for k, v in _ISO_RAW.items() if not k.startswith("_")}

ACTIVITY_U = {
    # СИ (Беккерель)
    "мкБк": 1e-6, "мБк": 1e-3, "Бк": 1.0, "кБк": 1e3, "МБк": 1e6, 
    "ГБк": 1e9, "ТБк": 1e12, "ПБк": 1e15, "ЭБк": 1e18,
    # Внесистемные (Кюри)
    "нКи": 37.0, "мкКи": 3.7e4, "мКи": 3.7e7, "Ки": 3.7e10, 
    "кКи": 3.7e13, "МКи": 3.7e16, "ГКи": 3.7e19
}

TIME_U     = {"с":1.0,"мин":60.0,"ч":3600.0,"сут":86400.0,"год":_Y}

CP_MAT = {
    "вода": {"Z": 7.42, "A": 18.015, "rho": 1.0, "I": 75.0, "ZA": 0.5551},
    "воздух": {"Z": 7.64, "A": 14.4, "rho": 0.001205, "I": 85.7},
    "ткань": {"Z": 7.5, "A": 18.0, "rho": 1.06, "I": 74.9},
    "кость": {"Z": 13.8, "A": 28.0, "rho": 1.92, "I": 91.9},
    "мышца": {"Z": 7.4, "A": 17.0, "rho": 1.04, "I": 74.0},
    "кожа": {"Z": 7.3, "A": 16.0, "rho": 1.09, "I": 72.0},
    "алюминий": {"Z": 13, "A": 26.98, "rho": 2.70, "I": 166.0},
    "кремний": {"Z": 14, "A": 28.09, "rho": 2.33, "I": 173.0},
    "титан": {"Z": 22, "A": 47.87, "rho": 4.54, "I": 233.0},
    "железо": {"Z": 26, "A": 55.845, "rho": 7.874, "I": 286.0},
    "сталь": {"Z": 26, "A": 55.8, "rho": 7.85, "I": 286.0},
    "медь": {"Z": 29, "A": 63.55, "rho": 8.96, "I": 322.0},
    "цинк": {"Z": 30, "A": 65.38, "rho": 7.14, "I": 330.0},
    "серебро": {"Z": 47, "A": 107.87, "rho": 10.49, "I": 470.0},
    "вольфрам": {"Z": 74, "A": 183.84, "rho": 19.30, "I": 727.0},
    "золото": {"Z": 79, "A": 196.97, "rho": 19.32, "I": 790.0},
    "свинец": {"Z": 82, "A": 207.2, "rho": 11.35, "I": 823.0},
    "уран": {"Z": 92, "A": 238.03, "rho": 18.95, "I": 890.0},
    "полиэтилен": {"Z": 5.53, "A": 13.0, "rho": 0.94, "I": 57.4},
    "графит": {"Z": 6, "A": 12.011, "rho": 1.70, "I": 78.0},
    "бетон": {"Z": 11.0, "A": 22.0, "rho": 2.30, "I": 135.0},
    "литий": {"Z": 3, "A": 6.94, "rho": 0.534, "I": 40.0},
    "бериллий": {"Z": 4, "A": 9.012, "rho": 1.85, "I": 63.7},
    "бор": {"Z": 5, "A": 10.81, "rho": 2.34, "I": 76.0},
    "боркарбид": {"Z": 5.3, "A": 11.2, "rho": 2.52, "I": 78.0},
}
PARTICLES = {"протон": (MP,1), "альфа": (MALPHA, 2), "дейтрон": (2*MP, 1), "электрон": (ME, 1)}

class GammaMaterial:
    NT = 20000
    def __init__(self, name, d):
        self.name, self.Z, self.A, self.density = name, float(d["Z"]), float(d["A"]), float(d["rho"])
        E= np.asarray(d["E"],float); mu = np.asarray(d["mu"], float)
        mu_pe = np.asarray(d.get("mu_pe", np.zeros_like(mu)), float)
        mu_comp = np.asarray(d.get("mu_comp", np.zeros_like(mu)), float)
        mu_pair = np.asarray(d.get("mu_pair", np.zeros_like(mu)), float)
        mu_coh = np.asarray(d.get("mu_coh", np.zeros_like(mu)), float)
        
        self._lE= np.log(E); self._lMu = np.log(mu)
        self._lMu_pe = np.log(np.maximum(mu_pe, 1e-15)); self._lMu_comp = np.log(np.maximum(mu_comp, 1e-15))
        self._lMu_pair = np.log(np.maximum(mu_pair, 1e-15)); self._lMu_coh = np.log(np.maximum(mu_coh, 1e-15))
        self.Emin, self.Emax = float(E[0]), float(E[-1])
        self._build()

    def _build(self):
        lo, hi = math.log(self.Emin), math.log(self.Emax)
        lE = np.linspace(lo, hi, self.NT)
        mu_total = np.exp(np.interp(lE, self._lE, self._lMu))
        mu_pe = np.exp(np.interp(lE, self._lE, self._lMu_pe))
        mu_comp = np.exp(np.interp(lE, self._lE, self._lMu_comp))
        mu_coh = np.exp(np.interp(lE, self._lE, self._lMu_coh))
        
        self._tm = mu_total * self.density
        safe_mu = np.where(mu_total > 0, mu_total, 1e-30)
        self._c1 = mu_pe / safe_mu
        self._c2 = np.minimum((mu_pe + mu_comp + mu_coh) / safe_mu, 1.0)
        self._t0, self._sc = lo, (self.NT - 1) / (hi - lo)

    def xs(self, E):
        x = (math.log(E) - self._t0) * self._sc
        if x <= 0: return self._tm[0], self._c1[0], self._c2[0]
        n = self.NT - 1
        if x >= n: return self._tm[n], self._c1[n], self._c2[n]
        i = int(x); f = x - i
        m, a, b = self._tm, self._c1, self._c2
        return (m[i]+(m[i+1]-m[i])*f, a[i]+(a[i+1]-a[i])*f, b[i]+(b[i+1]-b[i])*f)

    def mu_rho(self, E): return float(np.exp(np.interp(math.log(E), self._lE, self._lMu)))
    def macro(self, E): return self.mu_rho(E) * self.density

from functools import lru_cache

@lru_cache(maxsize=128)
def make_gamma_mat(name): return GammaMaterial(name, GAMMA_MATS[name])


class RandBuf:
    def __init__(self, rng, size=1 << 16):
        self.rng = rng; self.size = size; self.buf = rng.random(size); self.i = 0
    def __call__(self):
        if self.i >= self.size: self.buf = self.rng.random(self.size); self.i = 0
        v = self.buf[self.i]; self.i += 1
        return v

def _rotate(d, mu, phi):
    st = math.sqrt(max(0.0, 1 - mu*mu))
    dx, dy, dz = d
    perp = math.sqrt(max(1e-12, 1 - dz*dz))
    cp, sp = math.cos(phi), math.sin(phi)
    nx = dx*mu + st*(dx*dz*cp - dy*sp)/perp; ny = dy*mu + st*(dy*dz*cp + dx*sp)/perp
    nz = dz*mu - st*perp*cp; n= math.sqrt(nx*nx + ny*ny + nz*nz)
    return np.array([nx/n, ny/n, nz/n])

@njit(cache=False)
def _interp_log_nb(E, t0, sc, tm, c1, c2):
    x = (np.log(E) - t0) * sc
    n = len(tm) - 1
    if x <= 0: return tm[0], c1[0], c2[0]
    if x >= n: return tm[n], c1[n], c2[n]
    i = int(x); f = x - i
    return (tm[i] + (tm[i+1] - tm[i]) * f,
            c1[i] + (c1[i+1] - c1[i]) * f,
            c2[i] + (c2[i+1] - c2[i]) * f)

@njit(cache=False)
def _mc_core_numba(n_hist, seed, is_slab, R,
                   tm_sph, c1_sph, c2_sph, t0_sph, sc_sph,
                   n_layers, tm_L, c1_L, c2_L, t0_L, sc_L,
                   layer_starts, layer_ends, total_thick,
                   Es, cdf, ngrid, gsc, rad_n, dr, e_cut):
    np.random.seed(seed)
    MEC2 = 0.510998950
    coll_hist = np.zeros(30)
    theta_hist = np.zeros(90)  # cos(theta) от -1 до 1 (90 бинов)
    g2 = np.zeros((ngrid, ngrid))
    rad_dep = np.zeros(rad_n)
    leak = np.zeros(n_hist)
    leak_count = 0
    edep = edepsq = 0.0
    nph = nco = npa = nlk = nlk_uncoll = n_colls = backscatter_count = 0

    for h in range(n_hist):
        r = np.random.random()
        idx = 0
        for j in range(len(cdf)):
            if r <= cdf[j]: idx = j; break
        E0 = Es[idx]
        px, py, pz = 0.0, 0.0, 0.0
        
        if is_slab: dx, dy, dz = 1.0, 0.0, 0.0
        else:
            ct = 2.0 * np.random.random() - 1.0
            st = np.sqrt(max(0.0, 1.0 - ct*ct))
            phi = 2.0 * np.pi * np.random.random()
            dx = st * np.cos(phi); dy = st * np.sin(phi); dz = ct
        
        E = E0; eh = 0.0; is_uncollided = True; local_colls = 0
        
        while True:
            if is_slab:
                li = 0
                for l in range(n_layers):
                    if px >= layer_starts[l] and px < layer_ends[l]: li = l; break
                else: li = n_layers - 1
                mac, c1, c2 = _interp_log_nb(E, t0_L[li], sc_L[li], tm_L[li], c1_L[li], c2_L[li])
            else:
                mac, c1, c2 = _interp_log_nb(E, t0_sph, sc_sph, tm_sph, c1_sph, c2_sph)
            
            if E < 2.0 * MEC2: c2 = 1.0
            fp = -np.log(np.random.random()) / mac
            
            if is_slab:
                if dx > 1e-9:
                    db = (layer_ends[li] - px) / dx
                elif dx < -1e-9:
                    db = (layer_starts[li] - px) / dx
                else: 
                    db = 1e12
            else:
                b = px*dx + py*dy + pz*dz
                c = px*px + py*py + pz*pz - R*R
                disc = b*b - c
                db = -b + np.sqrt(disc) if disc >= 0 else 1e12
            
            if fp >= db:
                px += db * dx; py += db * dy; pz += db * dz
                if is_slab:
                    if px >= total_thick - 1e-9 or px <= 1e-9:
                        if px <= 1e-9 and dx < 0: backscatter_count += 1
                        leak[leak_count] = E; leak_count += 1; nlk += 1
                        if is_uncollided: nlk_uncoll += 1
                        break
                    else:
                        px += 1e-10 * dx; continue
                else:
                    leak[leak_count] = E; leak_count += 1; nlk += 1
                    if is_uncollided: nlk_uncoll += 1
                    break
            
            px += fp * dx; py += fp * dy; pz += fp * dz
            n_colls += 1; is_uncollided = False; local_colls += 1
            r = np.random.random()
            
            if r < c1:
                dep = E; eh += dep; nph += 1; final = True
            elif r < c2:
                a = E / MEC2
                while True:
                    r1 = np.random.random()
                    if r1 < (1.0 + 2.0*a) / (9.0 + 2.0*a): eps = 1.0 + 2.0*a*np.random.random()
                    else: eps = (1.0 + 2.0*a) / (1.0 + 2.0*a*np.random.random())
                    mu_c = 1.0 - (eps - 1.0) / a
                    if np.random.random() < 1.0 - eps*(1.0 - mu_c*mu_c)/(1.0 + eps*eps): break
                
                theta_idx = int((mu_c + 1.0) * 45.0)
                if theta_idx < 0: theta_idx = 0
                elif theta_idx > 89: theta_idx = 89
                theta_hist[theta_idx] += 1

                En = E / eps; dep = E - En; eh += dep; nco += 1
                st = np.sqrt(max(0.0, 1.0 - mu_c*mu_c))
                perp = np.sqrt(max(1e-12, 1.0 - dz*dz))
                phi_c = 2.0 * np.pi * np.random.random()
                cp = np.cos(phi_c); sp = np.sin(phi_c)
                nx = dx*mu_c + st*(dx*dz*cp - dy*sp)/perp
                ny = dy*mu_c + st*(dy*dz*cp + dx*sp)/perp
                nz = dz*mu_c - st*perp*cp
                nn = np.sqrt(nx*nx + ny*ny + nz*nz)
                dx = nx/nn; dy = ny/nn; dz = nz/nn
                E = En
                final = E < e_cut
                if final: eh += E; dep += E
            else:
                dep = E - 2.0 * MEC2; eh += dep; npa += 1; final = True
            
            if is_slab:
                ix = int(px * gsc); iz = int((pz + total_thick) * gsc / 2.0)
                ri = min(int(px / dr), rad_n - 1)
            else:
                ix = int((px + R) * gsc); iz = int((pz + R) * gsc)
                r_pos = np.sqrt(px*px + py*py + pz*pz)
                ri = min(int(r_pos / dr), rad_n - 1)
            
            if 0 <= ix < ngrid and 0 <= iz < ngrid: g2[iz, ix] += dep
            rad_dep[ri] += dep
            if final: break
        
        edep += eh; edepsq += eh * eh
        if local_colls < 30: coll_hist[local_colls] += 1
    
    return (edep, edepsq, nph, nco, npa, nlk, nlk_uncoll, n_colls, g2, rad_dep, leak[:leak_count], coll_hist, theta_hist, backscatter_count)

import multiprocessing as mp

def _mc_worker(args):
    (n_hist, seed, is_slab, R,
     tm_sph, c1_sph, c2_sph, t0_sph, sc_sph,
     n_layers, tm_L, c1_L, c2_L, t0_L, sc_L,
     layer_starts, layer_ends, total_thick,
     Es, cdf, ngrid, gsc, rad_n, dr, e_cut) = args
    return _mc_core_numba(
        n_hist, seed, is_slab, R, tm_sph, c1_sph, c2_sph, t0_sph, sc_sph,
        n_layers, tm_L, c1_L, c2_L, t0_L, sc_L, layer_starts, layer_ends, total_thick,
        Es, cdf, ngrid, gsc, rad_n, dr, e_cut
    )

def gamma_mc(mat, R, spec_lines, n_hist, seed=42, ngrid=64, e_cut=0.001,
             n_tracks=50, progress=None, should_stop=None, geom="sphere", layers=None):
    if layers is None: layers = [(mat, R)]
    total_thick = sum(l[1] for l in layers)
    Es = np.array([l[0] for l in spec_lines], dtype=np.float64)
    ws = np.array([l[1] for l in spec_lines], dtype=np.float64)
    cdf = np.cumsum(ws / ws.sum()); cdf[-1] = 1.0
    
    n_layers = len(layers)
    tm_L = np.zeros((n_layers, mat.NT)); c1_L = np.zeros((n_layers, mat.NT)); c2_L = np.zeros((n_layers, mat.NT))
    t0_L = np.zeros(n_layers); sc_L = np.zeros(n_layers)
    layer_starts = np.zeros(n_layers); layer_ends = np.zeros(n_layers)
    cur = 0.0
    for i, (l_mat, l_thick) in enumerate(layers):
        tm_L[i] = l_mat._tm; c1_L[i] = l_mat._c1; c2_L[i] = l_mat._c2
        t0_L[i] = l_mat._t0; sc_L[i] = l_mat._sc
        layer_starts[i] = cur; cur += l_thick; layer_ends[i] = cur
    
    if geom == "slab": gsc = (ngrid - 1) / total_thick; rad_n = 40; dr = total_thick / rad_n
    else: gsc = (ngrid - 1) / (2 * R); rad_n = 40; dr = R / rad_n
    
    n_procs = 1  # <--- ПРИНУДИТЕЛЬНО 1 ПРОЦЕСС ДЛЯ GUI
    
    if n_hist < 100000 or n_procs == 1:
        edep, edepsq, nph, nco, npa, nlk, nlk_uncoll, n_colls, g2, rad_dep, leak_arr, coll_hist, theta_hist, backscatter_count = _mc_worker((
            n_hist, seed, geom == "slab", R, mat._tm, mat._c1, mat._c2, mat._t0, mat._sc,
            n_layers, tm_L, c1_L, c2_L, t0_L, sc_L, layer_starts, layer_ends, total_thick,
            Es, cdf, ngrid, gsc, rad_n, dr, e_cut
        ))
    else:
        # БАТЧЕВЫЙ РАСЧЕТ: прогресс + возможность остановки
        n_chunks = 10
        hist_per_chunk = n_hist // n_chunks
        chunk_tasks = []
        for i in range(n_chunks):
            count = hist_per_chunk if i < n_chunks - 1 else n_hist - (hist_per_chunk * (n_chunks - 1))
            chunk_tasks.append((count, seed + i, geom == "slab", R, mat._tm, mat._c1, mat._c2, mat._t0, mat._sc,
                                n_layers, tm_L, c1_L, c2_L, t0_L, sc_L, layer_starts, layer_ends, total_thick,
                                Es, cdf, ngrid, gsc, rad_n, dr, e_cut))
        
        results = []
        with mp.Pool(processes=n_procs) as pool:
            for i, task in enumerate(chunk_tasks):
                if should_stop and should_stop():
                    pool.terminate()
                    break
                results.append(pool.apply(_mc_worker, (task,)))
                if progress: progress((i + 1) / n_chunks)
        
        if not results:
            return None  # расчёт отменён пользователем
        
        edep = sum(r[0] for r in results); edepsq = sum(r[1] for r in results)
        nph = sum(r[2] for r in results); nco = sum(r[3] for r in results); npa = sum(r[4] for r in results)
        nlk = sum(r[5] for r in results); nlk_uncoll = sum(r[6] for r in results); n_colls = sum(r[7] for r in results)
        g2 = sum(r[8] for r in results); rad_dep = sum(r[9] for r in results)
        leak_arr = np.concatenate([r[10] for r in results])
        coll_hist = sum(r[11] for r in results)
        theta_hist = sum(r[12] for r in results)
        backscatter_count = sum(r[13] for r in results)
    
    n = max(n_hist, 1); mean = edep / n; var = (edepsq/n - mean*mean) / n
    rel = math.sqrt(max(var, 0)) / mean if mean > 0 else 0.0
    
    if geom == "slab": mass = sum(l[1] * l[0].density for l in layers) / 1000.0
    else: mass = (4/3*math.pi*R**3) * mat.density / 1000.0
    dose = mean * MEV_TO_J / mass if mass > 0 else 0.0
    
    meanE = float(np.mean(Es)) if len(Es) > 0 else 0.0
    mu_v = layers[0][0].macro(max(meanE, layers[0][0].Emin))
    
    if geom == "slab":
        theor_escape = 1.0
        for l_mat, l_thick in layers: theor_escape *= np.exp(-l_mat.macro(max(meanE, l_mat.Emin)) * l_thick)
    else: theor_escape = np.exp(-mu_v * R)
    
    r_c = (np.arange(rad_n) + 0.5) * dr
    if geom == "slab": smass = np.full(rad_n, dr * sum(l[0].density for l in layers)) / 1000.0
    else: smass = (4/3*np.pi*((np.arange(1,rad_n+1)*dr)**3-(np.arange(rad_n)*dr)**3)) * mat.density / 1000.0
    
    with np.errstate(divide="ignore", invalid="ignore"): rad_dose = np.where(smass>0, rad_dep*MEV_TO_J/smass/n, 0.0)
    src_e_plot = np.random.choice(Es, size=min(n_hist, 10000), p=ws/ws.sum())
    
    return {
        "mean":mean, "rel":rel, "dose":dose, "dose_eq":dose,
        "meanE":meanE, "abs":mean/meanE if meanE>0 else 0,
        "nph":nph, "nco":nco, "npa":npa, "nlk":nlk, "n":n,
        "nlk_uncoll":nlk_uncoll, "n_colls":n_colls, "backscatter_count":backscatter_count,
        "leak":leak_arr, "src":src_e_plot, "grid":g2/n, "R": total_thick, "geom": geom,
        "coll_hist": coll_hist, "theta_hist": theta_hist,
        "r":r_c, "rad_dose":rad_dose, "mu":mu_v, "theor_escape": theor_escape, 
        "mfp":1/mu_v if mu_v>0 else 0, "hvl":math.log(2)/mu_v if mu_v>0 else 0,
        "mu_rho": mat.mu_rho(max(meanE, mat.Emin)),
    }
def attenuation_curve(mat, spec_lines, n_hist, thicknesses, seed=42):
    """Возвращает [(thickness, transmission_model, transmission_theory)] для построения кривой ослабления"""
    results = []
    mean_E = float(np.mean([l[0] for l in spec_lines])) if spec_lines else mat.Emin
    mu_macro = mat.macro(max(mean_E, mat.Emin))
    for thickness in thicknesses:
        if thickness <= 0: 
            results.append((thickness, 1.0, 1.0)); continue
        res = gamma_mc(mat=mat, R=thickness, spec_lines=spec_lines, n_hist=n_hist, seed=seed, geom="slab", layers=[(mat, thickness)])
        trans = res["nlk_uncoll"] / res["n"] if res["n"] > 0 else 0.0
        theor = float(np.exp(-mu_macro * thickness))
        results.append((thickness, trans, theor))
    return results

def absolute_dose(res, activity, act_unit, time, time_unit, use_decay, iso_name):
    A0= activity * ACTIVITY_U[act_unit]; T = time * TIME_U[time_unit]
    if iso_name in ISOTOPES:
        iso = ISOTOPES[iso_name]
        gpd = sum(l[1] for l in iso["lines"])
        hl = iso.get("half_life_s", 0.0)
        lam = math.log(2) / hl if hl > 0 else 0.0
    else: 
        gpd = 1.0
        lam = 0.0
        
    if use_decay and lam > 0:
        decays = A0 / lam * (1 - math.exp(-lam * T))
    else:
        decays = A0 * T
    return {"dose_abs":res["dose"]*(decays*gpd)}

def sp_heavy(T, mass, z, mat):
    if T <= 0: return 0.0
    g = 1 + T/mass; b2 = 1 - 1/g**2
    if b2 <= 1e-9: return 0.0
    bg2 = b2*g**2; I = mat["I"]*1e-6; ZA = mat.get("ZA", 0.5)
    Tmax = 2*ME*bg2/(1 + 2*g*ME/mass + (ME/mass)**2)
    arg = 2*ME*bg2*Tmax/I**2
    return max(K_BB*z**2*ZA/b2*(0.5*math.log(arg)-b2), 0.0)*mat["rho"] if arg > 1 else 0.0

def sp_elec(T, mat):
    if T <= 0: return 0.0, 0.0, 0.0
    tau = T/ME; g = 1+tau; b2 = 1-1/g**2
    if b2 <= 1e-9: return 0.0, 0.0, 0.0
    I= mat["I"] * 1e-6; F = 1-b2 + (tau**2/8-(2*tau+1)*math.log(2))/(tau+1)**2
    coll = max(0.153536/b2*(mat["Z"]/mat["A"]) *(math.log(tau**2*(tau+2)/(2*(I/ME)**2)) + F), 0.0)
    # Феноменологическое ограничение сверху, чтобы тормозные потери не превышали столкновительные
    rad_factor = min(1.0, mat["Z"] * T / 800.0)
    return (coll + coll * rad_factor) * mat["rho"], coll * mat["rho"], coll * rad_factor * mat["rho"]

def csda(part, T0, mat, nstep=2000, straggling=True, seed=None):
    """CSDA с расчетом среднего пробега. Дисперсия (страгглинг) считается отдельно."""
    mass, z = PARTICLES[part]
    dT = T0 / nstep
    x = 0.0; T = T0
    dep = [0.0]; de = []
    
    while T > 0.01:
        # s_val в МэВ/см (полная тормозная способность)
        s_val = (sp_elec(T, mat)[0] if part == "электрон" else sp_heavy(T, mass, z, mat)) * mat["rho"]
        if s_val <= 0: break
        
        dx = dT / s_val
        dep.append(dep[-1] + dx)
        de.append(s_val)
        x += dx
        T -= dT
        
    de.append(de[-1] if de else 0.0)
    return x, np.array(dep), np.array(de) # <--- ВОЗВРАЩАЕМ ПРОБЕГ (x)!

def straggling_sigma(part, T0, mat, nstep=2000):
    """Стандартное отклонение пробега по Бору (интеграл дисперсии вдоль трека)."""
    mass, z = PARTICLES[part]
    dT = T0 / nstep
    T = T0
    sigma_R_sq = 0.0
    while T > 0.1:  # <-- Обрываем при T=0.1 МэВ, ниже формула Бора неприменима
        s_val = (sp_elec(T, mat)[0] if part == "электрон" else sp_heavy(T, mass, z, mat)) * mat["rho"]
        if s_val <= 0: break
        dx = dT / s_val
        p = np.sqrt(T * (T + 2 * mass))
        beta = max(p / (T + mass), 0.01)  # <-- Кап на beta, чтобы не было деления на 0
        dOmega2_dx = 0.307 * (mat["Z"] / mat["A"]) * mat["rho"] / beta**2 * (1 - beta**2 / 2.0)
        sigma_R_sq += dOmega2_dx * dx / (s_val**2)
        T -= dT
    return np.sqrt(sigma_R_sq)

def lateral_straggling_2d(part, T0, mat, n_particles=2000, n_steps=300):
    """2D-карта латерального рассеяния (Highland formula с учетом 1/beta^2)."""
    mass, z = PARTICLES[part]
    dT = T0 / n_steps
    X0 = 36.08 # Радиационная длина воды (см)
    rng = np.random.default_rng()
    
    R_est, _, _ = csda(part, T0, mat, nstep=100, straggling=False)
    x_bins = np.linspace(0, R_est * 1.05, 100)
    y_bins = np.linspace(-3.0, 3.0, 100) # Возвращаем широкий диапазон для наглядности
    grid, _, _ = np.histogram2d([], [], bins=[x_bins, y_bins])
    
    for _ in range(n_particles):
        x, y = 0.0, 0.0
        theta = 0.0
        T = T0
        
        for i in range(n_steps):
            s_val = (sp_heavy(T, mass, z, mat) if part != "электрон" else sp_elec(T, mat)[0]) * mat["rho"]
            if s_val <= 0: break
            
            dx = dT / s_val 
            
            p = np.sqrt(T * (T + 2 * mass))
            beta = p / (T + mass)
            
            if p > 0 and beta > 1e-6:
                # Формула Хайленда с точным 1/beta^2
                theta0 = (13.6 / (beta * p)) * z * np.sqrt(dx / X0) * (1 + 0.038 * np.log(dx / X0 + 1e-12))
                theta += rng.normal(0, abs(theta0))
            
            x += dx * np.cos(theta)
            y += dx * np.sin(theta)
            T -= dT
            
            if 0 <= x < x_bins[-1] and y_bins[0] <= y <= y_bins[-1]:
                ix = np.searchsorted(x_bins, x) - 1
                iy = np.searchsorted(y_bins, y) - 1
                if 0 <= ix < 99 and 0 <= iy < 99:
                    grid[ix, iy] += 1

    return grid.T, x_bins, y_bins

def lateral_straggling_2d(part, T0, mat, n_particles=2000, n_steps=400):
    """2D-карта латерального рассеяния с корректным учетом 1/beta^2."""
    mass, z = PARTICLES[part]
    dT = T0 / n_steps
    X0 = 36.08 # Радиационная длина воды (см)
    rng = np.random.default_rng()
    
    R_est, _, _ = csda(part, T0, mat, nstep=100, straggling=False)
    x_bins = np.linspace(0, R_est * 1.05, 100)
    y_bins = np.linspace(-1.5, 1.5, 100) # Сузили диапазон Y для наглядности
    grid, _, _ = np.histogram2d([], [], bins=[x_bins, y_bins])
    
    for _ in range(n_particles):
        x, y = 0.0, 0.0
        theta = 0.0
        T = T0
        
        for i in range(n_steps):
            s_val = sp_heavy(T, mass, z, mat) if part != "электрон" else sp_elec(T, mat)[0]
            if s_val <= 0: break
            
            dx = dT / s_val 
            
            p = np.sqrt(T * (T + 2 * mass))
            beta = p / (T + mass)
            
            if p > 0 and beta > 0:
                # Формула Хайленда
                theta0 = (13.6 / (beta * p)) * z * np.sqrt(dx / X0) * (1 + 0.038 * np.log(dx / X0 + 1e-12))
                theta += rng.normal(0, theta0)
            
            x += dx * np.cos(theta)
            y += dx * np.sin(theta)
            T -= dT
            
            if 0 <= x < x_bins[-1] and y_bins[0] <= y <= y_bins[-1]:
                ix = np.searchsorted(x_bins, x) - 1
                iy = np.searchsorted(y_bins, y) - 1
                if 0 <= ix < 99 and 0 <= iy < 99:
                    grid[ix, iy] += 1

    return grid.T, x_bins, y_bins

def range_vs_energy(part, mat, nE=60, seed=None):
    Emin, Emax = (0.5, 500.0) if part in ("протон", "альфа", "дейтрон") else (0.05, 50.0)
    Es = np.linspace(Emin, Emax, nE)
    # Берем средний пробег (индекс 1 - это dep, и из него [-1])
    return Es, np.array([csda(part, e, mat, nstep=800, seed=seed)[1][-1] for e in Es])

#  НЕЙТРОНЫ — мост в WSL (запускает OpenMC в Linux)
NEUTRON_SCRIPT = r'''
import os, json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import openmc

C = json.loads(os.environ["PROM_CFG"])

def build_mat(name):
    if name == "water":
        m = openmc.Material()
        m.add_nuclide("H1", 2); m.add_nuclide("O16", 1)
        m.set_density("g/cm3", 1.0)
        m.add_s_alpha_beta("c_H_in_H2O")
    elif name == "polyethylene":
        m = openmc.Material()
        m.add_nuclide("H1", 2); m.add_nuclide("C0", 1)
        m.set_density("g/cm3", 0.94)
        m.add_s_alpha_beta("c_H_in_CH2")
    elif name == "concrete":
        m = openmc.Material()
        for el, w in [("H",0.01),("O",0.529),("Si",0.337),("Ca",0.044),("Al",0.034),("Fe",0.014),("Na",0.016),("Mg",0.002)]:
            m.add_element(el, w, "wo")
        m.set_density("g/cm3", 2.3)
    elif name == "iron":
        m = openmc.Material()
        m.add_element("Fe", 1.0); m.set_density("g/cm3", 7.874)
    elif name == "lead":
        m = openmc.Material()
        m.add_element("Pb", 1.0); m.set_density("g/cm3", 11.35)
    elif name == "graphite":
        m = openmc.Material()
        m.add_nuclide("C0", 1.0); m.set_density("g/cm3", 1.7)
        m.add_s_alpha_beta("c_Graphite")
    elif name == "uranium":
        m = openmc.Material()
        m.add_nuclide("U235", 0.05); m.add_nuclide("U238", 0.95)
        m.set_density("g/cm3", 19.0)
    elif name == "b4c":
        m = openmc.Material()
        m.add_nuclide("B10", 4.0); m.add_nuclide("B11", 16.0)
        m.add_nuclide("C0", 5.0); m.set_density("g/cm3", 2.52)
    else:
        m = openmc.Material()
        m.add_element("Fe", 1.0); m.set_density("g/cm3", 7.874)
    return m

mat = build_mat(C["material"])
materials = openmc.Materials([mat])
R = float(C["radius"])
sph = openmc.Sphere(r=R, boundary_type="vacuum")
cell = openmc.Cell(fill=mat, region=-sph)
geom = openmc.Geometry([cell])

src = openmc.IndependentSource()
src.space= openmc.stats.Point((0,0,0))
src.angle  = openmc.stats.Isotropic()

spec_type = C.get("spectrum", "mono")
if spec_type == "u235":
    # Стандартный спектр деления U-235 (Watt)
    src.energy = openmc.stats.Watt(a=0.988, b=2.249)
elif spec_type == "cf252":
    # Спектр спонтанного деления Cf-252 (Watt)
    src.energy = openmc.stats.Watt(a=1.18, b=1.034)
else:
    # Моноэнергетический
    src.energy = openmc.stats.Discrete([C["energy_MeV"]*1e6], [1.0])
src.particle = "neutron"

st = openmc.Settings()
st.run_mode = "fixed source"
st.source   = src
st.particles = int(C["particles"])
st.batches   = int(C["batches"])

tals= openmc.Tallies()
ebins = np.logspace(-3, 7, 100)
ef= openmc.EnergyFilter(ebins)
tsp   = openmc.Tally(name="spectrum")
tsp.filters = [ef]; tsp.scores = ["flux"]
tals.append(tsp)

n = int(C["mesh_n"])
mesh = openmc.RegularMesh()
mesh.dimension= [n, 1, n]
mesh.lower_left  = [-R, -R/n, -R]
mesh.upper_right = [ R,  R/n,  R]
tm = openmc.Tally(name="mesh")
tm.filters = [openmc.MeshFilter(mesh)]; tm.scores = ["flux"]
tals.append(tm)

tg = openmc.Tally(name="glob")
tg.scores = ["absorption","fission","scatter","(n,gamma)"]
tals.append(tg)

# --- Многогрупповой анализ (Тепловые, Резонансные, Быстрые) ---
# 0 - 0.625 эВ (тепловые), 0.625 - 100 кэВ (резонансные), > 100 кэВ (быстрые)
group_bins = [0.0, 0.625, 100000.0, 20000000.0] 
gf = openmc.EnergyFilter(group_bins)
tgrp = openmc.Tally(name="groups")
tgrp.filters = [gf]; tgrp.scores = ["flux", "absorption", "fission"]
tals.append(tgrp)

model = openmc.Model(geom, materials, st, tals)
sp_path = model.run(output=True)

with openmc.StatePoint(sp_path) as sp:
    flux = sp.get_tally(name="spectrum").mean.flatten()
    mm= sp.get_tally(name="mesh").mean.reshape((n,1,n))[:,0,:].T
    df   = sp.get_tally(name="glob").get_pandas_dataframe()
    def gv(s):
        r = df[df["score"]==s]["mean"].values
        return float(r[0]) if len(r) else 0.0
    absb = gv("absorption"); fiss = gv("fission")
    scat = gv("scatter");ng   = gv("(n,gamma)")
    
    # РАСЧЕТ ДОЗЫ ЧЕРЕЗ КОЭФФИЦИЕНТЫ (OpenMC 0.15.3)
    # Добавляем расчет ec здесь, чтобы он был доступен для дозы
    ec = np.sqrt(ebins[:-1]*ebins[1:])
    
    # РАСЧЕТ ДОЗЫ ЧЕРЕЗ КОЭФФИЦИЕНТЫ (OpenMC >= 0.15.3)
    try:
        # Получаем энергии (в эВ) и коэффициенты (в пЗв·см²) для нейтронов
        dose_energies, dose_coeffs = openmc.data.dose_coefficients(particle='neutron', geometry='AP', data_source='icrp74')
        
        # Интерполируем коэффициенты на наш энергетический спектр (ec - это середины бинов)
        interp_coeffs = np.interp(ec, dose_energies, dose_coeffs) / 1e12
        
        # Считаем дозу: сумма (поток * коэффициент)
        # Поток из OpenMC уже проинтегрирован по бину, поэтому умножать на ширину не нужно
        dose_val = float(np.sum(flux * interp_coeffs))
    except Exception as e:
        print(f"Ошибка расчета дозы: {e}")
        dose_val = 0.0

    # Извлечение группового потока
    try:
        grp_df = sp.get_tally(name="groups").get_pandas_dataframe()
        # Усредняем по всем ячейкам, если их несколько
        grp_flux = grp_df[grp_df["score"]=="flux"]["mean"].values.tolist()
        if not grp_flux: grp_flux = [0.0, 0.0, 0.0]
    except Exception:
        grp_flux = [0.0, 0.0, 0.0]

ec = np.sqrt(ebins[:-1]*ebins[1:])

plt.figure(figsize=(8,5))
plt.step(ec, flux, where="mid", color="teal", lw=1.5)
plt.xscale("log"); plt.yscale("log")
plt.xlabel("Энергия нейтронов, эВ"); plt.ylabel("Поток (усл. ед.)")
plt.title("Спектр нейтронов: " + C["material"] +f", источник {C['energy_MeV']} МэВ")
plt.axvline(0.025,color="red",ls="--", alpha=.6, label="тепловые 0.025 эВ")
plt.axvline(C["energy_MeV"]*1e6, color="orange", ls="--", alpha=.6, label="источник")
plt.legend(); plt.grid(alpha=.3, which="both"); plt.tight_layout()
plt.savefig(C["out_spec"], dpi=120); plt.close()

mm2 = mm.copy(); pos = mm2[mm2>0]
vmin = pos.min() if pos.size else 1e-12; mm2[mm2<=0] = vmin
plt.figure(figsize=(7,6))
im = plt.imshow(mm2, origin="lower", extent=[-R,R,-R,R], cmap="inferno", norm=LogNorm(vmin=vmin, vmax=mm2.max()))
plt.colorbar(im, label="Поток нейтронов")
plt.xlabel("X, см"); plt.ylabel("Z, см")
plt.title("2D карта потока нейтронов: " + C["material"])
plt.tight_layout(); plt.savefig(C["out_map"], dpi=120); plt.close()

json.dump({
    "absorption": absb, "fission": fiss, "scatter": scat, "ngamma": ng, 
    "dose": dose_val, "groups": grp_flux,
    "spectrum_E": ec.tolist(), "spectrum_flux": flux.tolist()
}, open(C["out_json"], "w"))
print("NEUTRON_DONE")
'''
def run_neutrons_wsl(cfg, log_cb):
    tmp = tempfile.mkdtemp(prefix="prom_")
    def to_wsl(p):
        p = os.path.abspath(p).replace("\\", "/")
        if len(p) > 1 and p[1] == ":": p = "/mnt/" + p[0].lower() + p[2:]
        return p
    try:
        script_path = os.path.join(tmp, "neu.py")
        with open(script_path, "w", encoding="utf-8") as f: f.write(NEUTRON_SCRIPT)
        cfg = dict(cfg)
        cfg["out_spec"] = to_wsl(os.path.join(tmp, "spec.png"))
        cfg["out_map"]  = to_wsl(os.path.join(tmp, "map.png"))
        cfg["out_json"] = to_wsl(os.path.join(tmp, "res.json"))
        
        cfg_json = json.dumps(cfg)
        wsl_script = to_wsl(script_path)
        wsl_dir = os.path.dirname(wsl_script)
        
        inner = (f"export PROM_CFG='{cfg_json}'; source ~/.bashrc > /dev/null 2>&1; "
                 f"conda activate openmc && cd {wsl_dir} && python {wsl_script}")
        log_cb(f"[WSL] запуск OpenMC: материал={cfg['material']}, R={cfg['radius']} см, E={cfg['energy_MeV']} МэВ")
        log_cb("[WSL] подождите, первый запуск может занять минуту...")
        
        try:
            proc = subprocess.run(["wsl", "bash", "-lc", inner], capture_output=True, text=True, timeout=3600)
        except FileNotFoundError: 
            raise RuntimeError("Команда 'wsl' не найдена.\nУбедись, что WSL установлен (wsl --install).")
            
        if proc.stdout: log_cb(proc.stdout[-3000:])
        if proc.returncode != 0 and proc.stderr: log_cb("[WSL stderr] " + proc.stderr[-1000:])
        if "NEUTRON_DONE" not in (proc.stdout or ""): 
            raise RuntimeError("OpenMC не завершился успешно.\n" + (proc.stderr or "")[-2000:])
            
        res_path = os.path.join(tmp, "res.json")
        with open(res_path, encoding="utf-8") as f: stats = json.load(f)
        
        return {"spec_img": os.path.join(tmp, "spec.png"),
                "map_img":  os.path.join(tmp, "map.png"),
                "stats":    stats}
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    # ЛОГИ
_logger  = logging.getLogger("prometheus")
_logger.setLevel(logging.DEBUG)
_log_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S")

def setup_log_file(out_dir):
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(out_dir, f"prom_log_{ts}.txt")
    fh = logging.FileHandler(path, encoding="utf-8"); fh.setFormatter(_log_fmt); _logger.addHandler(fh)
    return path

def attach_log_widget(widget):
    class _QH(logging.Handler):
        def __init__(self, w): super().__init__(); self.w = w
        def emit(self, r):
            try: self.w.appendPlainText(self.format(r))
            except Exception: pass
    qh = _QH(widget); qh.setFormatter(_log_fmt); _logger.addHandler(qh)

def plog(msg, level="info"): getattr(_logger, level)(msg)

def fmt_hl(s):
    if s >= _Y: return f"{s/_Y:.3g} лет"
    if s >= _D: return f"{s/_D:.3g} сут"
    if s >= _H: return f"{s/_H:.3g} ч"
    if s >= 60: return f"{s/60:.3g} мин"
    return f"{s:.3g} с"
def lateral_straggling_2d(part, T0, mat, n_particles=2000, n_steps=300):
    """Симуляция 2D-карты латерального (бокового) рассеяния пучка частиц."""
    mass, z = PARTICLES[part]
    dT = T0 / n_steps
    X0 = 36.08 # Радиационная длина для воды (см)
    
    R_est, _, _ = csda(part, T0, mat, nstep=100) 
    x_bins = np.linspace(0, R_est * 1.1, 100)
    y_bins = np.linspace(-3, 3, 100)
    grid, _, _ = np.histogram2d([], [], bins=[x_bins, y_bins])
    
    for _ in range(n_particles):
        x, y = 0.0, 0.0
        theta = 0.0
        T = T0
        
        for i in range(n_steps):
            s_val = sp_heavy(T, mass, z, mat) if part != "электрон" else sp_elec(T, mat)[0]
            if s_val <= 0: break
            
            dx = dT / s_val 
            
            p = np.sqrt(T * (T + 2*mass))
            beta = p / (T + mass)
            if p > 0:
                theta0 = (13.6 / (beta * p)) * z * np.sqrt(dx / X0) * (1 + 0.038 * np.log(dx / X0))
                theta += np.random.normal(0, theta0) 
            
            x += dx * np.cos(theta)
            y += dx * np.sin(theta)
            T -= dT
            
            if 0 <= x < x_bins[-1] and -3 <= y <= 3:
                ix = np.searchsorted(x_bins, x) - 1
                iy = np.searchsorted(y_bins, y) - 1
                if 0 <= ix < 99 and 0 <= iy < 99:
                    grid[ix, iy] += 1

    return grid.T, x_bins, y_bins

if __name__ == "__main__":
    print("=== Самопроверка physics.py ===")
    print(f"Материалов: {len(GAMMA_MATS)}, Изотопов: {len(ISOTOPES)}")
    m = make_gamma_mat("water"); print(f"Вода: mu/rho @ 1 МэВ = {m.mu_rho(1.0):.4f}")
    R_p, _, _ = csda("протон", 100.0, CP_MAT["вода"]); print(f"Протон 100 МэВ: пробег = {R_p:.3f} см")
    print("=== Всё OK ===")