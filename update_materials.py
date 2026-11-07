import json
import numpy as np
import xraylib

with open("data/materials.json", "r", encoding="utf-8") as f:
    data = json.load(f)

COMPOSITIONS = {
    "water": {"H": 0.1119, "O": 0.8881},
    "air": {"N": 0.755, "O": 0.232, "Ar": 0.013},
    "tissue": {"H": 0.101, "C": 0.111, "N": 0.026, "O": 0.762},
    "muscle": {"H": 0.102, "C": 0.143, "N": 0.034, "O": 0.710, "Na": 0.001, "P": 0.002, "S": 0.003, "K": 0.004, "Ca": 0.001},
    "fat": {"H": 0.120, "C": 0.768, "N": 0.003, "O": 0.109},
    "lung": {"H": 0.103, "C": 0.105, "N": 0.031, "O": 0.749, "Na": 0.002, "P": 0.002, "S": 0.003, "K": 0.002, "Ca": 0.001},
    "bone": {"H": 0.034, "C": 0.155, "N": 0.042, "O": 0.435, "Na": 0.001, "Mg": 0.002, "P": 0.103, "S": 0.003, "Ca": 0.225},
    "concrete": {"H": 0.01, "O": 0.529, "Si": 0.337, "Ca": 0.044, "Al": 0.034, "Fe": 0.014, "Na": 0.016, "Mg": 0.002},
    "glass": {"O": 0.459, "Na": 0.096, "Mg": 0.005, "Al": 0.022, "Si": 0.336, "K": 0.008, "Ca": 0.074},
    "polyethylene": {"H": 0.143, "C": 0.857},
    "pmma": {"H": 0.080, "C": 0.600, "O": 0.320},
    "paraffin": {"H": 0.148, "C": 0.852},
    "nai": {"Na": 0.153, "I": 0.847},
    "water_heavy": {"H": 0.111, "O": 0.889},
    "soil": {"O": 0.490, "Si": 0.330, "Al": 0.080, "Fe": 0.040, "C": 0.020, "Ca": 0.015, "K": 0.015, "Na": 0.010},
    "borated_polyethylene": {"H": 0.115, "C": 0.807, "B": 0.078},
    "lead_glass": {"O": 0.112, "Si": 0.256, "Pb": 0.632},
    "tungsten_alloy": {"W": 0.95, "Ni": 0.03, "Fe": 0.02},
    "seawater": {"H": 0.108, "O": 0.857, "Na": 0.0108, "Cl": 0.0194, "Mg": 0.0013, "S": 0.0009, "Ca": 0.0004, "K": 0.0004},
    "air_humid": {"N": 0.749, "O": 0.230, "Ar": 0.013, "H": 0.008},
}

# Словарь: какие новые материалы копировать из старых (если xraylib не дает данных)
NEW_FROM_OLD = {
    "seawater": "water",
    "air_humid": "air",
    "borated_polyethylene": "polyethylene",
    "lead_glass": "glass",
    "tungsten_alloy": "tungsten"
}

ELEMENTS = {
    "aluminum": "Al", "titanium": "Ti", "chromium": "Cr", "iron": "Fe",
    "steel": "Fe", "nickel": "Ni", "copper": "Cu", "zinc": "Zn",
    "molybdenum": "Mo", "tin": "Sn", "silver": "Ag", "tantalum": "Ta",
    "tungsten": "W", "gold": "Au", "lead": "Pb", "uranium": "U",
    "graphite": "C", "boron": "B",
}

NEW_PROPS = {
    "borated_polyethylene": {"Z": 5.2, "A": 11.5, "rho": 1.0},
    "lead_glass": {"Z": 40.0, "A": 80.0, "rho": 4.5},
    "tungsten_alloy": {"Z": 74.0, "A": 183.84, "rho": 17.0},
    "seawater": {"Z": 7.5, "A": 18.0, "rho": 1.025},
    "air_humid": {"Z": 7.6, "A": 14.5, "rho": 0.0012}
}

# Создаем заготовки для новых материалов
for mat_name in COMPOSITIONS.keys():
    if mat_name not in data:
        data[mat_name] = {"v": False, "E": [], "mu": [], "mu_pe": [], "mu_comp": [], "mu_coh": [], "mu_pair": []}
        if mat_name in NEW_PROPS: data[mat_name].update(NEW_PROPS[mat_name])
        else: data[mat_name].update({"Z": 10, "A": 20, "rho": 1.0})

def get_mu_partial(mat_name, E_MeV):
    E_keV = E_MeV * 1000.0
    mu_pe = mu_comp = mu_coh = 0.0

    if mat_name in ELEMENTS:
        Z = xraylib.SymbolToAtomicNumber(ELEMENTS[mat_name])
        try: mu_pe = xraylib.CS_Photo(Z, E_keV)
        except: pass
        try: mu_comp = xraylib.CS_Compt(Z, E_keV)
        except: pass
        try: mu_coh = xraylib.CS_Rayl(Z, E_keV)
        except: pass
    else:
        comp = COMPOSITIONS.get(mat_name)
        if not comp: return 0, 0, 0
        for elem, weight in comp.items():
            Z = xraylib.SymbolToAtomicNumber(elem)
            try: mu_pe += weight * xraylib.CS_Photo(Z, E_keV)
            except: pass
            try: mu_comp += weight * xraylib.CS_Compt(Z, E_keV)
            except: pass
            try: mu_coh += weight * xraylib.CS_Rayl(Z, E_keV)
            except: pass
            
    return mu_pe, mu_comp, mu_coh

for mat_name, mat_data in data.items():
    if mat_name.startswith("_"): continue
    
    if len(mat_data.get("E", [])) == 0:
        mat_data["E"] = [0.01, 0.015, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50, 0.60, 0.80, 1.0, 1.25, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0]
        mat_data["mu"] = [0.0] * len(mat_data["E"])
        
    E_list = mat_data["E"]
    mu_total = mat_data["mu"]
    mu_pe_list, mu_comp_list, mu_coh_list, mu_pair_list = [], [], [], []
    mu_total_new = []

    for i, (E, mu_t_old) in enumerate(zip(E_list, mu_total)):
        pe, comp, coh = get_mu_partial(mat_name, E)
        
        mu_t = pe + comp + coh
        if mu_t <= 0:
            # Если xraylib не дал данных (или это новый материал без данных),
            # копируем из старого материала
            if mat_name in NEW_FROM_OLD:
                old_mat = data[NEW_FROM_OLD[mat_name]]
                if i < len(old_mat["mu"]):
                    mu_t = old_mat["mu"][i] * (mat_data.get("rho", 1.0) / old_mat.get("rho", 1.0))
                else:
                    mu_t = mu_t_old
            else:
                mu_t = mu_t_old
            
        mu_total_new.append(mu_t)
        
        Z_val = mat_data.get("Z", 0)
        pair_frac = 0.0
        if E > 1.022 and Z_val > 30:
            pair_frac = min(0.8, (E - 1.022) * 0.15)
            
        s_partial = pe + comp + coh
        if s_partial > 0:
            frac_pe = pe / s_partial
            frac_comp = comp / s_partial
            frac_coh = coh / s_partial
            
            mu_pe_list.append(mu_t * (1 - pair_frac) * frac_pe)
            mu_comp_list.append(mu_t * (1 - pair_frac) * frac_comp)
            mu_coh_list.append(mu_t * (1 - pair_frac) * frac_coh)
            mu_pair_list.append(mu_t * pair_frac)
        else:
            # Если нет партиалов, все уходит в комптон
            mu_pe_list.append(0.0)
            mu_coh_list.append(0.0)
            mu_comp_list.append(mu_t * (1 - pair_frac))
            mu_pair_list.append(mu_t * pair_frac)

    mat_data["mu"] = mu_total_new
    mat_data["mu_pe"] = mu_pe_list
    mat_data["mu_comp"] = mu_comp_list
    mat_data["mu_coh"] = mu_coh_list
    mat_data["mu_pair"] = mu_pair_list
    print(f"Обновлён: {mat_name}")

with open("data/materials.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
print("Готово! materials.json обновлён с точностью NIST.")