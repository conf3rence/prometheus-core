import json
import os

DATA_DIR = "data"
FILE_PATH = os.path.join(DATA_DIR, "materials.json")

with open(FILE_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

# Правильные плотности для всех материалов (г/см³)
correct_rho = {
    "water": 1.0, "icru_tissue": 1.0, "muscle_skeletal": 1.04, "adipose": 0.95,
    "lung_tissue": 0.26, "bone_cortical": 1.92, "skin": 1.09, "air": 0.001205,
    "concrete": 2.3, "concrete_magnetite": 4.0, "glass": 2.5, "lead_glass": 4.5,
    "soil": 1.5, "seawater": 1.025, "polyethylene": 0.94, "borated_polyethylene": 1.0,
    "pmma": 1.18, "paraffin": 0.9, "teflon": 2.2, "zircaloy": 6.56,
    "lead": 11.35, "iron": 7.87, "aluminum": 2.70, "copper": 8.96, 
    "tungsten": 19.3, "uranium": 18.95, "steel_304": 8.0, "titanium": 4.43
}

for mat_name, mat_data in data.items():
    if mat_name.startswith("_"): continue
    if mat_name.lower() in correct_rho:
        mat_data["rho"] = correct_rho[mat_name.lower()]
        print(f"[OK] {mat_name}: плотность обновлена до {mat_data['rho']} г/см³")

with open(FILE_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("\nГотово! Плотности исправлены. Теперь свинец будет ослаблять гамму как свинец.")