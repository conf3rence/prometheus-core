# Сторонние источники данных и лицензии

Проект **Prometheus Core** использует данные и программные библиотеки из открытых источников.

## 1. NIST XCOM (Photon Cross Sections Database)
*   **Использование:** Парциальные массовые коэффициенты ослабления для 39 материалов.
*   **Цитирование:** *Berger, M.J., Hubbell, J.H., Seltzer, S.M., Chang, J., Coursey, J.S., Sukumar, R., Zucker, D.S., and Olsen, K. (2010), XCOM: Photon Cross Section Database (version 1.5). NIST, Gaithersburg, MD.*
*   **Лицензия:** Public Domain.

## 2. NIST PSTAR (Stopping Power for Protons)
*   **Использование:** Эталонные значения пробега и тормозной способности протонов.
*   **Цитирование:** *Berger, M.J., Coursey, J.S., Zucker, M.A., and Chang, J. (2005), ESTAR, PSTAR, and ASTAR. NIST, Gaithersburg, MD.*
*   **Лицензия:** Public Domain.

## 3. ICRP Publication 74
*   **Использование:** Коэффициенты качества излучения \(w_R\) для перевода Гр в Зв.
*   **Цитирование:** *International Commission on Radiological Protection. Conversion Coefficients for use in Radiological Protection Against External Radiation. ICRP Publication 74. Ann. ICRP 26 (3-4), 1996.*
*   **Лицензия:** Материалы ICRP защищены авторским правом. Разрешено цитирование с указанием источника.

## 4. ENDF/B (Evaluated Nuclear Data File)
*   **Использование:** Оценённые ядерные данные для OpenMC (NNDC HDF5).
*   **Цитирование:** *D.A. Brown et al., "ENDF/B-VIII.0: The 8th Major Release of the Nuclear Reaction Data Library...", Nuclear Data Sheets, vol. 148, pp. 1-142, 2018.*
*   **Лицензия:** Открытые данные для научных и инженерных целей (NNDC Brookhaven National Laboratory).

## 5. OpenMC (Monte Carlo Particle Transport Code)
*   **Использование:** Движок для моделирования переноса нейтронов.
*   **Цитирование:** *Paul K. Romano, et al., "OpenMC: A State-of-the-Art Monte Carlo Code for Research and Development," Ann. Nucl. Energy, 82, 90–97 (2015).*
*   **Лицензия:** MIT License.

## 6. xraylib
*   **Использование:** Python-интерфейс для извлечения парциальных сечений из NIST XCOM.
*   **Цитирование:** *Tom Schoonjans, et al., "The xraylib library for X-ray–matter interactions. Recent developments," Spectrochimica Acta Part B, 66(11), 776-784 (2011).*
*   **Лицензия:** BSD 3-Clause License.

## 7. PySide6 (Qt for Python)
*   **Использование:** Графический интерфейс пользователя (GUI).
*   **Цитирование:** The Qt Company.
*   **Лицензия:** LGPL v3. Это позволяет распространять сам проект Prometheus Core под лицензией MIT.

## 8. Numba (JIT Compiler for Python)
*   **Использование:** JIT-компиляция ядра Монте-Карло для ускорения в 5-10 раз.
*   **Цитирование:** *Siu Kwan Lam, Antoine Pitrou, and Stanley Seibert. "Numba: A LLVM-based Python JIT Compiler." Proceedings of the Second Workshop on the LLVM Compiler Infrastructure in HPC, 2015.*
*   **Лицензия:** BSD 2-Clause License.

## 9. llvmlite
*   **Использование:** Транспортный слой для Numba (компиляция в LLVM IR).
*   **Цитирование:** *Siu Kwan Lam. "llvmlite: A lightweight LLVM binding for Python." GitHub repository, 2014-2024.*
*   **Лицензия:** BSD 2-Clause License.

---
**Примечание:** При публикации результатов, полученных с помощью Prometheus Core, просьба ссылаться на оригинальные источники данных (NIST, ICRP, ENDF/B) и используемые библиотеки.