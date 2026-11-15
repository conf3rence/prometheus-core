import json
import sys
import numpy as np

with open("data/materials.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print("Проверка материалов на наличие нулей и ошибок...")
all_ok = True
n_checked = 0

for name, d in data.items():
    if name.startswith("_"): continue
    n_checked += 1
    
    mu = np.array(d.get("mu", []))
    mu_pe = np.array(d.get("mu_pe", np.zeros_like(mu)))
    mu_comp = np.array(d.get("mu_comp", np.zeros_like(mu)))
    mu_coh = np.array(d.get("mu_coh", np.zeros_like(mu)))
    mu_pair = np.array(d.get("mu_pair", np.zeros_like(mu)))
    
    # 1. Проверка на пустые данные
    if len(mu) == 0:
        print(f"[ОШИБКА] {name:20}: массив mu пуст!")
        all_ok = False
        continue
        
    # 2. Проверка на наличие нулей (деление на ноль в логарифме)
    if np.any(mu <= 0):
        print(f"[ОШИБКА] {name:20}: содержит нули или отрицательные значения в mu!")
        all_ok = False
        
    # 3. Проверка на NaN (Not a Number)
    if np.any(np.isnan(mu)):
        print(f"[ОШИБКА] {name:20}: содержит NaN!")
        all_ok = False

    # 4. Проверка согласованности (сумма партиалов = тотал)
    mu_sum = mu_pe + mu_comp + mu_coh + mu_pair
    diff = np.abs(mu - mu_sum) / np.where(mu > 0, mu, 1e-30)
    max_diff = np.max(diff) if len(diff) > 0 else 0.0
    
    if max_diff > 1e-6:
        print(f"[ОШИБКА] {name:20}: партиалы не сходятся с общим (расхождение {max_diff:.2e})")
        all_ok = False

if all_ok:
    print(f"\n=== УСПЕХ: Все {n_checked} материалов имеют корректные данные! ===")
    sys.exit(0)
else:
    print(f"\n=== ВНИМАНИЕ: Найдены проблемные материалы (всего проверено {n_checked}) ===")
    sys.exit(1)