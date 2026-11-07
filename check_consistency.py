import json
import numpy as np

with open("data/materials.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print("Проверка согласованности mu_total = sum(mu_partial)...")
all_ok = True

for name, d in data.items():
    if name.startswith("_"): continue
    
    mu = np.array(d["mu"])
    mu_pe = np.array(d.get("mu_pe", np.zeros_like(mu)))
    mu_comp = np.array(d.get("mu_comp", np.zeros_like(mu)))
    mu_coh = np.array(d.get("mu_coh", np.zeros_like(mu)))
    mu_pair = np.array(d.get("mu_pair", np.zeros_like(mu)))
    
    mu_sum = mu_pe + mu_comp + mu_coh + mu_pair
    
    # Относительное расхождение
    diff = np.abs(mu - mu_sum) / np.where(mu > 0, mu, 1e-30)
    max_diff = np.max(diff)
    
    if max_diff > 1e-6:
        print(f"[ОШИБКА] {name}: максимальное расхождение {max_diff:.2e}")
        all_ok = False
    else:
        pass # print(f"[OK] {name}: расхождение {max_diff:.2e}")

if all_ok:
    print("=== УСПЕХ: Все 34 материала имеют согласованные сечения (расхождение < 1e-6) ===")
else:
    print("=== ВНИМАНИЕ: Обнаружены расхождения в сечениях! ===")