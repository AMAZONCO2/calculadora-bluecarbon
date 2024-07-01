import pandas as pd
from statsmodels.tsa.api import ExponentialSmoothing
from datetime import datetime

# Dados históricos da coluna "Taxa de Desmatamento Acumulativa por Ano (%)"
data_acumulativa = {
    "Ano": [
        2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015,
        2016, 2017, 2018, 2019, 2020, 2021, 2022
    ],
    "Taxa de Desmatamento Acumulativa (%)": [
        0.97, 1.13, 1.13, 1.17, 1.17, 1.17, 1.70, 1.74,
        1.83, 1.92, 1.92, 1.95, 1.98, 1.98, 1.98
    ]
}

# Criar DataFrame
df_taxa_acumulativa = pd.DataFrame(data_acumulativa)

def treinar_modelo(anos):
    # Ajustar a suavização exponencial
    model = ExponentialSmoothing(df_taxa_acumulativa['Taxa de Desmatamento Acumulativa (%)'], trend='add', seasonal=None)
    fit = model.fit()

    # Calcular o ano inicial (ano atual + 2)
    ano_atual = datetime.now().year
    ano_inicial = ano_atual + 2
    projection_years = list(range(ano_inicial, ano_inicial + anos))
    
    # Projetar para os próximos anos
    projection = fit.forecast(len(projection_years))

    return projection_years, projection

# Função para calcular o estoque inicial
def calcula_estoque(area, agb=0, bgb=0, dw=0, l=0, soc=0):
    estoque_total_inicial = (agb + bgb + dw + l + soc) * area  # t C
    return estoque_total_inicial

# Função para calcular as emissões e reduções com base na taxa de desmatamento anual projetada
def calcular_reducoes(taxa_desmatamento, estoque_total_inicial, fator_risco):
    conversao_para_CO2e = 3.6667  # Fator de conversão de carbono para CO2e

    perda_carbono_anual = estoque_total_inicial * (taxa_desmatamento / 100)  # t C/ano
    perda_carbono_anual_CO2e = perda_carbono_anual * conversao_para_CO2e  # t CO2e/ano

    vazamento_anual = perda_carbono_anual_CO2e * 0.2  # t CO2e/ano

    projeto_conservacao = (perda_carbono_anual_CO2e - vazamento_anual) * 0.95  # t CO2e/ano

    buffer_anual = projeto_conservacao * fator_risco  # t CO2e/ano

    reducao_anual_ajustada = projeto_conservacao - buffer_anual  # t CO2e/ano

    return perda_carbono_anual_CO2e, projeto_conservacao, vazamento_anual, buffer_anual, reducao_anual_ajustada

# Função principal para calcular e retornar os resultados completos
def resultados_completos(anos, estoque_inicial, fator_risco):
    projection_years, projection = treinar_modelo(int(anos))

    resultados = []
    vcus_acumulados = 0
    
    for ano, taxa in zip(projection_years, projection):
        
        perda, conservacao, vazamento, buffer, reducao = calcular_reducoes(
            taxa, estoque_inicial, fator_risco
        )
        vcus_acumulados += reducao
        
        resultados.append(
            {
                "Ano": int(ano),
                "Taxa de Desmatamento Projetada (%)": taxa,
                "Linha Base (t CO2e)": perda,
                "Projeto (t CO2e)": conservacao,
                "Vazamento (t CO2e)": vazamento,
                "Buffer (t CO2e)": buffer,
                "Redução Líquida (t CO2e)": reducao,
                "VCUs Acumulados (t CO2e)": round(vcus_acumulados,3),
            }
        )

    df_resultados_completos = pd.DataFrame(resultados)
    return df_resultados_completos
