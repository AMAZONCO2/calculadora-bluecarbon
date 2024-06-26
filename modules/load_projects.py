import pandas as pd
import os

SAVE_FILE = "projects/projects.csv"
columns = ["ID", "Nome do Projeto", "AGB Inicial", "SOC Inicial", "AGB Final", "SOC Final", "Área", "Taxa de Desmatamento", "Total Inicial", "Total Final", "ΔC", "ΔCO2e", "Total CO2e", "Créditos de Carbono Anuais"]
# Carregar projetos salvos
def load_projects():
    if os.path.exists(SAVE_FILE):
        return pd.read_csv(SAVE_FILE)
    else:
        return pd.DataFrame(columns=columns)
