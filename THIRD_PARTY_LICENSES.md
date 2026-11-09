# Сторонние источники данных и лицензии

Проект **Prometheus Core** использует данные и программные библиотеки из открытых источников.

## 1. NIST XCOM (Photon Cross Sections Database)
*   **Использование:** Парциальные массовые коэффициенты ослабления для 39 материалов.
*   **Цитирование:** *Berger, M.J., Hubbell, J.H., Seltzer, S.M., et al. (2010), XCOM: Photon Cross Section Database (version 1.5). NIST, Gaithersburg, MD.*
*   **Лицензия:** Public Domain.

## 2. NIST PSTAR / ASTAR
*   **Использование:** Эталонные значения пробега и тормозной способности протонов и альфа-частиц.
*   **Цитирование:** *Berger, M.J., Coursey, J.S., Zucker, M.A., and Chang, J. (2005), ESTAR, PSTAR, and ASTAR. NIST, Gaithersburg, MD.*
*   **Лицензия:** Public Domain.

## 3. ICRP Publication 74
*   **Использование:** Коэффициенты качества излучения \(w_R\) для перевода Гр в Зв.
*   **Цитирование:** *ICRP Publication 74. Conversion Coefficients for use in Radiological Protection Against External Radiation. Ann. ICRP 26 (3-4), 1996.*
*   **Примечание:** Используются только широко опубликованные табличные значения, текст публикации не воспроизводится.

## 4. ENDF/B (Evaluated Nuclear Data File)
*   **Использование:** Оценённые ядерные данные для OpenMC.
*   **Цитирование:** *D.A. Brown et al., "ENDF/B-VIII.0...", Nuclear Data Sheets, vol. 148, pp. 1-142, 2018.*
*   **Лицензия:** Открытые данные (US DOE Data Policy).

## 5. OpenMC
*   **Использование:** Движок для моделирования переноса нейтронов.
*   **Цитирование:** *Paul K. Romano, et al., "OpenMC: A State-of-the-Art Monte Carlo Code...", Ann. Nucl. Energy, 82, 90–97 (2015).*
*   **Лицензия:** MIT License.

## 6. xraylib
*   **Использование:** Источник парциальных сечений взаимодействия (включая NIST XCOM).
*   **Цитирование:** *Tom Schoonjans, et al., "The xraylib library...", Spectrochimica Acta Part B, 66(11), 776-784 (2011).*
*   **Лицензия:** BSD 3-Clause License.

## 7. PySide6 (Qt for Python)
*   **Использование:** Графический интерфейс пользователя (GUI).
*   **Лицензия:** LGPL v3. Это позволяет распространять сам проект Prometheus Core под лицензией MIT.

## 8. Numba / llvmlite
*   **Использование:** JIT-компиляция ядра Монте-Карло.
*   **Лицензия:** BSD 2-Clause License.

## 9. NumPy
*   **Использование:** Массивы и линейная алгебра.
*   **Лицензия:** BSD 3-Clause.

## 10. Matplotlib
*   **Использование:** Графики и визуализации.
*   **Лицензия:** PSF-based (BSD-совместимая).

## 11. PyInstaller
*   **Использование:** Сборка standalone-исполняемых файлов.
*   **Лицензия:** GPL v2 с исключением для сборки приложений (сам PyInstaller остается GPL, ваше приложение — нет).

## 13. PyVista
* **Использование:** 3D-визуализация (облака нейтронов, 3D-сферы, треки).
* **Лицензия:** MIT License.
* **Ссылка:** https://pyvista.org/

## 14. VTK (Visualization Toolkit)
* **Использование:** Движок рендеринга для PyVista.
* **Лицензия:** BSD 3-Clause License.
* **Ссылка:** https://vtk.org/