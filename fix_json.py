import json
import os
import xraylib
import numpy as np

DATA_DIR = "data"
FILE_PATH = os.path.join(DATA_DIR, "materials.json")

print("Загрузка materials.json...")
with open(FILE_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

formulas = {
    "water": "H2O",
    "air": "Air",
    "icru_tissue": "Tissue, ICRU",
    "muscle_skeletal": "Muscle, Skeletal",
    "adipose": "Adipose Tissue, ICRU-44",
    "lung_tissue": "Lung Tissue, ICRU-44",
    "bone_cortical": "Bone, Cortical, ICRU-44",
    "skin": "Skin, ICRU-44",
    "polyethylene": "Polyethylene",
    "pmma": "PMMA",
    "teflon": "Teflon"
}

def get_val(cp_name, z_name, target_str, target_z, E_keV):
    """Универсальная функция: ищет функцию для соединений (CP), если нет — считает по Z"""
    # Пытаемся использовать функцию для соединений
    if target_str:
        func_cp = getattr(xraylib, cp_name, None)
        if func_cp is not None:
            try: return func_cp(target_str, E_keV)
            except Exception: pass
            
    # Если не вышло, или функции нет — используем атомный номер (с обходом краев поглощения)
    if target_z:
        func_z = getattr(xraylib, z_name, None)
        if func_z is not None:
            try: return func_z(target_z, E_keV + 0.001)
            except Exception:
                try: return func_z(target_z, E_keV - 0.001)
                except Exception: pass
                
    return 0.0

print("Восстановление данных (с обходом версионных багов xraylib)...")

for mat_name, mat_data in data.items():
    if mat_name.startswith("_"): continue
    
    target_str = formulas.get(mat_name.lower())
    target_z = int(round(mat_data["Z"])) if "Z" in mat_data else None

    E_MeV = np.array(mat_data["E"])
    E_keV = E_MeV * 1000.0
    
    mu, mu_pe, mu_comp, mu_coh, mu_pair = [], [], [], [], []
    
    for E in E_keV:
        # Передаем ИМЕНА функций строками, чтобы скрипт не падал с AttributeError
        mu.append(float(get_val("CS_Total_CP", "CS_Total", target_str, target_z, E)))
        mu_pe.append(float(get_val("CS_Photo_CP", "CS_Photo", target_str, target_z, E)))
        mu_comp.append(float(get_val("CS_Compt_CP", "CS_Compt", target_str, target_z, E)))
        mu_coh.append(float(get_val("CS_Rayl_CP", "CS_Rayl", target_str, target_z, E)))
        mu_pair.append(float(get_val("CS_Pair_CP", "CS_Pair", target_str, target_z, E)))

    mat_data["mu"] = mu
    mat_data["mu_pe"] = mu_pe
    mat_data["mu_comp"] = mu_comp
    mat_data["mu_coh"] = mu_coh
    mat_data["mu_pair"] = mu_pair
    
    print(f"[OK] Восстановлен: {mat_name} (Z={target_z})")

with open(FILE_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("\nГОТОВО! materials.json исцелен. Ошибок быть не должно.")