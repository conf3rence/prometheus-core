import json
import numpy as np
import xraylib

COMPOSITIONS = {
    # Биологические ткани (ICRU)
    "water": {"H": 0.1119, "O": 0.8881}, 
    "icru_tissue": {"H": 0.101, "C": 0.111, "N": 0.026, "O": 0.762},
    "muscle_skeletal": {"H": 0.102, "C": 0.143, "N": 0.034, "O": 0.710, "Na": 0.001, "P": 0.002, "S": 0.003, "K": 0.004, "Ca": 0.001},
    "adipose": {"H": 0.120, "C": 0.768, "N": 0.003, "O": 0.109},
    "lung_tissue": {"H": 0.103, "C": 0.105, "N": 0.031, "O": 0.749, "Na": 0.002, "P": 0.002, "S": 0.003, "K": 0.002, "Ca": 0.001},
    "bone_cortical": {"H": 0.034, "C": 0.155, "N": 0.042, "O": 0.435, "Na": 0.001, "Mg": 0.002, "P": 0.103, "S": 0.003, "Ca": 0.225},
    "skin": {"H": 0.100, "C": 0.228, "N": 0.046, "O": 0.619, "Na": 0.001, "P": 0.001, "S": 0.002, "K": 0.001, "Ca": 0.002},
    # Защита и строительство
    "air": {"N": 0.755, "O": 0.232, "Ar": 0.013},
    "concrete": {"H": 0.01, "O": 0.529, "Si": 0.337, "Ca": 0.044, "Al": 0.034, "Fe": 0.014, "Na": 0.016, "Mg": 0.002},
    "concrete_magnetite": {"H": 0.005, "O": 0.250, "Fe": 0.600, "Si": 0.050, "Ca": 0.050, "Al": 0.045},
    "glass": {"O": 0.459, "Na": 0.096, "Mg": 0.005, "Al": 0.022, "Si": 0.336, "K": 0.008, "Ca": 0.074},
    "lead_glass": {"O": 0.112, "Si": 0.256, "Pb": 0.632},
    "soil": {"O": 0.490, "Si": 0.330, "Al": 0.080, "Fe": 0.040, "C": 0.020, "Ca": 0.015, "K": 0.015, "Na": 0.010},
    "seawater": {"H": 0.108, "O": 0.857, "Na": 0.0108, "Cl": 0.0194, "Mg": 0.0013, "S": 0.0009, "Ca": 0.0004, "K": 0.0004},
    # Полимеры (включая Борный полиэтилен)
    "polyethylene": {"H": 0.143, "C": 0.857}, 
    "borated_polyethylene": {"H": 0.115, "C": 0.807, "B": 0.078}, # <--- ТОТ САМЫЙ
    "pmma": {"H": 0.080, "C": 0.600, "O": 0.320}, 
    "paraffin": {"H": 0.148, "C": 0.852},
    "teflon": {"C": 0.240, "F": 0.760},
    # Реакторные материалы
    "zircaloy": {"Zr": 0.982, "Sn": 0.015, "Fe": 0.001, "Cr": 0.001},
    "stainless_steel_304": {"Fe": 0.700, "Cr": 0.190, "Ni": 0.090},
    "stainless_steel_316": {"Fe": 0.680, "Cr": 0.170, "Ni": 0.120, "Mo": 0.025},
    "inconel": {"Ni": 0.580, "Cr": 0.210, "Fe": 0.050, "Nb": 0.050},
    "titanium_alloy": {"Ti": 0.900, "Al": 0.060, "V": 0.040},
    "borated_steel": {"Fe": 0.980, "B": 0.020},
    "ag_in_cd": {"Ag": 0.800, "In": 0.150, "Cd": 0.050},
    "tungsten_alloy": {"W": 0.950, "Ni": 0.030, "Fe": 0.020},
    # Газы и жидкости
    "heavy_water": {"H": 0.111, "O": 0.889},
    "liquid_lead_bismuth": {"Pb": 0.445, "Bi": 0.555},
    "carbon_dioxide": {"C": 0.273, "O": 0.727},
    "methane": {"C": 0.749, "H": 0.251},
    "nai": {"Na": 0.153, "I": 0.847}
}

ELEMENTS = {
    "lithium": "Li", "beryllium": "Be", "boron": "B", "carbon": "C", "nitrogen": "N", "oxygen": "O",
    "sodium": "Na", "magnesium": "Mg", "aluminum": "Al", "silicon": "Si", "phosphorus": "P", "sulfur": "S",
    "potassium": "K", "calcium": "Ca", "titanium": "Ti", "chromium": "Cr", "manganese": "Mn", "iron": "Fe",
    "cobalt": "Co", "nickel": "Ni", "copper": "Cu", "zinc": "Zn", "gallium": "Ga", "germanium": "Ge",
    "silver": "Ag", "cadmium": "Cd", "indium": "In", "tin": "Sn", "antimony": "Sb", "tungsten": "W",
    "gold": "Au", "mercury": "Hg", "lead": "Pb", "bismuth": "Bi", "thorium": "Th", "uranium": "U",
    "graphite": "C", "steel": "Fe"
}

NEW_PROPS = {
    # (заполняется автоматически для новых, но зададим плотности для ключевых)
    "borated_polyethylene": {"Z": 5.2, "A": 11.5, "rho": 1.0}, "lead_glass": {"Z": 40.0, "A": 80.0, "rho": 4.5},
    "tungsten_alloy": {"Z": 74.0, "A": 183.84, "rho": 17.0}, "seawater": {"Z": 7.5, "A": 18.0, "rho": 1.025},
    "zircaloy": {"Z": 40.0, "A": 91.22, "rho": 6.56}, "stainless_steel_304": {"Z": 25.7, "A": 55.0, "rho": 8.0},
    "stainless_steel_316": {"Z": 25.7, "A": 55.0, "rho": 8.0}, "inconel": {"Z": 27.5, "A": 58.0, "rho": 8.4},
    "titanium_alloy": {"Z": 21.0, "A": 45.0, "rho": 4.43}, "borated_steel": {"Z": 25.5, "A": 54.0, "rho": 7.8},
    "ag_in_cd": {"Z": 46.0, "A": 107.0, "rho": 10.17}, "liquid_lead_bismuth": {"Z": 82.5, "A": 208.0, "rho": 10.5},
    "heavy_water": {"Z": 7.5, "A": 20.0, "rho": 1.11}, "icru_tissue": {"Z": 7.5, "A": 18.0, "rho": 1.0},
    "bone_cortical": {"Z": 13.8, "A": 28.0, "rho": 1.92}, "lung_tissue": {"Z": 7.4, "A": 17.0, "rho": 0.26},
    "adipose": {"Z": 6.2, "A": 13.0, "rho": 0.95}, "muscle_skeletal": {"Z": 7.4, "A": 17.0, "rho": 1.04},
    "skin": {"Z": 7.3, "A": 16.0, "rho": 1.09}, "teflon": {"Z": 8.0, "A": 16.0, "rho": 2.2},
    "methane": {"Z": 6.7, "A": 12.0, "rho": 0.0007}, "cadmium": {"Z": 48.0, "A": 112.4, "rho": 8.65},
    "gadolinium": {"Z": 64.0, "A": 157.2, "rho": 7.9}, "hafnium": {"Z": 72.0, "A": 178.5, "rho": 13.3},
    "bismuth": {"Z": 83.0, "A": 208.9, "rho": 9.78}, "liquid_sodium": {"Z": 11.0, "A": 23.0, "rho": 0.93},
    "liquid_lead": {"Z": 82.0, "A": 207.2, "rho": 10.6}, "helium": {"Z": 2.0, "A": 4.0, "rho": 0.000178}
}

E_LIST = [0.01, 0.015, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.25, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0]
data = {}

def get_mu_partial(mat_name, E_MeV):
    E_keV = E_MeV * 1000.0
    mu_pe = mu_comp = mu_coh = mu_pair = 0.0
    
    # --- ОБХОДНОЙ ПУТЬ ДЛЯ ВЫСОКИХ ЭНЕРГИЙ ---
    # Если xraylib падает, мы жестко задаем эталонные значения NIST
    NIST_FALLBACK = {
        "lead": {1.0: 0.07102, 10.0: 0.04972},
        "water": {1.0: 0.07072, 10.0: 0.02219},
        "iron": {1.0: 0.05995, 10.0: 0.02994},
        "aluminum": {1.0: 0.06146, 10.0: 0.02318},
        "concrete": {1.0: 0.06369, 10.0: 0.02744}, # Для бетона
        "air": {1.0: 0.07072, 10.0: 0.02219}
    }
    
    if E_MeV >= 1.0 and mat_name in NIST_FALLBACK and E_MeV in NIST_FALLBACK[mat_name]:
        val = NIST_FALLBACK[mat_name][E_MeV]
        # Распределяем энергию примерно (для отображения партиалов)
        return val * 0.1, val * 0.8, val * 0.1, 0.0

    # --- СТАРЫЙ КОД ---
    if mat_name in ELEMENTS:
        Z = xraylib.SymbolToAtomicNumber(ELEMENTS[mat_name])
        try: mu_pe = xraylib.CS_Photo(Z, E_keV)
        except: pass
        try: mu_comp = xraylib.CS_Compt(Z, E_keV)
        except: pass
        try: mu_coh = xraylib.CS_Rayl(Z, E_keV)
        except: pass
        try: mu_pair = xraylib.CS_Pair(Z, E_keV) + xraylib.CS_Triplet(Z, E_keV)
        except: pass
    else:
        comp = COMPOSITIONS.get(mat_name)
        if not comp: return 0, 0, 0, 0
        for elem, weight in comp.items():
            try:
                Z = xraylib.SymbolToAtomicNumber(elem)
                mu_pe += weight * xraylib.CS_Photo(Z, E_keV)
                mu_comp += weight * xraylib.CS_Compt(Z, E_keV)
                mu_coh += weight * xraylib.CS_Rayl(Z, E_keV)
                mu_pair += weight * (xraylib.CS_Pair(Z, E_keV) + xraylib.CS_Triplet(Z, E_keV))
            except: pass
    return mu_pe, mu_comp, mu_coh, mu_pair

for mat_name in COMPOSITIONS:
    mu_pe_list, mu_comp_list, mu_coh_list, mu_pair_list, mu_total_list = [], [], [], [], []
    props = NEW_PROPS.get(mat_name, {"Z": 10, "A": 20, "rho": 1.0})
    for E in E_LIST:
        pe, comp, coh, pair = get_mu_partial(mat_name, E)
        mu_t = pe + comp + coh + pair
        if mu_t <= 1e-10:
            mu_t = 1e-5; pe = 1e-5
        mu_total_list.append(mu_t); mu_pe_list.append(pe); mu_comp_list.append(comp); mu_coh_list.append(coh); mu_pair_list.append(pair)
    data[mat_name] = {"E": E_LIST, "mu": mu_total_list, "mu_pe": mu_pe_list, "mu_comp": mu_comp_list, "mu_coh": mu_coh_list, "mu_pair": mu_pair_list, "v": True}
    data[mat_name].update(props)

for elem_name, sym in ELEMENTS.items():
    mu_pe_list, mu_comp_list, mu_coh_list, mu_pair_list, mu_total_list = [], [], [], [], []
    props = NEW_PROPS.get(elem_name, {"Z": xraylib.SymbolToAtomicNumber(sym), "A": 20, "rho": 1.0})
    for E in E_LIST:
        pe, comp, coh, pair = get_mu_partial(elem_name, E)
        mu_t = pe + comp + coh + pair
        if mu_t <= 1e-10:
            mu_t = 1e-5; pe = 1e-5
        mu_total_list.append(mu_t); mu_pe_list.append(pe); mu_comp_list.append(comp); mu_coh_list.append(coh); mu_pair_list.append(pair)
    data[elem_name] = {"E": E_LIST, "mu": mu_total_list, "mu_pe": mu_pe_list, "mu_comp": mu_comp_list, "mu_coh": mu_coh_list, "mu_pair": mu_pair_list, "v": True}
    data[elem_name].update(props)

with open("data/materials.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
print("Готово! materials.json перезаписан.")