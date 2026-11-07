import json
import numpy as np

with open("data/materials.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for name in ["pmma", "paraffin", "nai", "water_heavy", "soil"]:
    d = data[name]
    mu = np.array(d["mu"])
    mu_pe = np.array(d.get("mu_pe", np.zeros_like(mu)))
    mu_comp = np.array(d.get("mu_comp", np.zeros_like(mu)))
    mu_coh = np.array(d.get("mu_coh", np.zeros_like(mu)))
    mu_pair = np.array(d.get("mu_pair", np.zeros_like(mu)))
    
    mu_sum = mu_pe + mu_comp + mu_coh + mu_pair
    diff = np.abs(mu - mu_sum) / np.where(mu > 0, mu, 1e-30)
    
    for i in range(len(mu)):
        if diff[i] > 1e-6:
            print(f"{name}: Ошибка на индексе {i}, E={d['E'][i]} МэВ")
            print(f"  mu={mu[i]}, mu_sum={mu_sum[i]}")
            print(f"  mu_pe={mu_pe[i]}, mu_comp={mu_comp[i]}, mu_coh={mu_coh[i]}, mu_pair={mu_pair[i]}")