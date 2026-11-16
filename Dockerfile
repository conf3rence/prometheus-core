# Используем официальный образ OpenMC с Docker Hub
FROM openmc/openmc:latest

# Создаем рабочую директорию
WORKDIR /data

# По умолчанию запускаем bash (скрипт будет вызываться вручную)
CMD ["/bin/bash"]docker build -t prometheus-openmc .