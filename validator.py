import physics as P
import numpy as np

# Эталонные значения NIST XCOM (массовый коэффициент ослабления, см2/г)
# Формат: материал -> {энергия (МэВ): mu/rho}
NIST_REF = {
    "lead": {0.1: 5.549, 1.0: 0.07102, 10.0: 0.04972},
    "water": {0.1: 0.1707, 1.0: 0.07072, 10.0: 0.02219},
    "iron": {0.1: 0.3717, 1.0: 0.05995, 10.0: 0.02994},
    "aluminum": {0.1: 0.1704, 1.0: 0.06146, 10.0: 0.02318}
}

def run_validation(log_cb):
    """Запускает проверку данных и возвращает текстовый отчет."""
    report_lines = []
    report_lines.append("="*50)
    report_lines.append("ТЕСТ ВЕРИФИКАЦИИ ДАННЫХ (NIST XCOM)")
    report_lines.append("="*50)
    
    log_cb("[ВАЛИДАЦИЯ] Запуск проверки точности данных NIST...", "info")
    
    total_tests = 0
    passed_tests = 0
    max_error = 0.0
    
    for mat_name, points in NIST_REF.items():
        if mat_name not in P.GAMMA_MATS:
            continue
            
        mat_obj = P.make_gamma_mat(mat_name)
        
        for E, ref_val in points.items():
            calc_val = mat_obj.mu_rho(E)
            
            # Считаем относительную ошибку в %
            if ref_val > 0:
                error_pct = abs(calc_val - ref_val) / ref_val * 100.0
            else:
                error_pct = 0.0
                
            total_tests += 1
            if error_pct < 1.0:  # Если ошибка меньше 1%, тест пройден
                passed_tests += 1
                status = "OK"
            else:
                status = "ОШИБКА"
                
            max_error = max(max_error, error_pct)
            
            # Формируем строку для отчета
            line = f"{mat_name:10} | E={E:4.1f} МэВ | NIST={ref_val:.5f} | Calc={calc_val:.5f} | Err={error_pct:.3f}% | {status}"
            report_lines.append(line)
            
            # Пишем лог
            log_level = "info" if error_pct < 1.0 else "warning"
            log_cb(f"[ВАЛИДАЦИЯ] {mat_name:10} @ {E:4.1f} МэВ: точность {100-error_pct:.2f}% (расхождение {error_pct:.3f}%)", log_level)

    report_lines.append("-"*50)
    report_lines.append(f"Всего тестов: {total_tests}")
    report_lines.append(f"Пройдено: {passed_tests}")
    report_lines.append(f"Максимальное расхождение: {max_error:.3f}%")
    
    if max_error < 1.0:
        report_lines.append("ИТОГ: СИСТЕМА ВЕРИФИЦИРОВАНА (Отлично)")
        log_cb("[ВАЛИДАЦИЯ] ИТОГ: Все тесты пройдены! База данных корректна.", "info")
    else:
        report_lines.append("ИТОГ: ЕСТЬ ОШИБКИ (Требуется проверка)")
        log_cb("[ВАЛИДАЦИЯ] ИТОГ: Обнаружены расхождения > 1%.", "error")
        
    report_lines.append("="*50)
    
    return "\n".join(report_lines)