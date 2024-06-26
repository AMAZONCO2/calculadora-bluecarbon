import pandas as pd
# Dados históricos da coluna "Taxa de Desmatamento Acumulativa por Ano (%)"
data_acumulativa = {
    "Ano": [2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022],
    "Taxa de Desmatamento Acumulativa (%)": [0.97, 1.13, 1.13, 1.17, 1.17, 1.17, 1.70, 1.74, 1.83, 1.92, 1.92, 1.95, 1.98, 1.98, 1.98]
}

# Criar DataFrame
df_taxa_acumulativa = pd.DataFrame(data_acumulativa)

# Aplicar suavização exponencial
#model = ExponentialSmoothing(df_taxa_acumulativa['Taxa de Desmatamento Acumulativa (%)'], trend='add', seasonal=None)
#fit = model.fit()

# Projetar para os próximos 30 anos
projection_years = list(range(2026, 2056 + 1))
#projection = fit.forecast(len(projection_years))
projection = [2.00,2.01,2.02,2.03,2.03,2.04,2.05,2.06,2.07,2.08,2.09,2.10,2.11,2.12,2.13,2.14,2.15,2.16,2.17,2.18,2.19,2.20,2.21,2.22,2.23,2.24,2.25,2.26,2.27,2.28,2.29]
# Parâmetros utilizados


def calcula_estoque(area,agb=0,bgb=0,dw=0,l=0,soc=0):
    
    # Estoque total inicial
    estoque_total_inicial = (agb+bgb+dw+l + soc) * area  # t C
    return estoque_total_inicial
    
# Função para calcular as emissões e reduções com base na taxa de desmatamento anual projetada
def calcular_reducoes(taxa_desmatamento, estoque_total_inicial, fator_risco ):

    conversao_para_CO2e = 3.6667  # Fator de conversão de carbono para CO2e

    # Cálculo da perda anual de carbono
   
    perda_carbono_anual = estoque_total_inicial * (taxa_desmatamento / 100)  # t C/ano
    perda_carbono_anual_CO2e = perda_carbono_anual * conversao_para_CO2e  # t CO2e/ano
    
    # Cálculo do vazamento
    vazamento_anual = perda_carbono_anual_CO2e * 0.2 # t CO2e/ano
    
    # Cálculo do projeto de conservação
    projeto_conservacao = (perda_carbono_anual_CO2e - vazamento_anual) * 0.95  # t CO2e/ano
    
    # Cálculo do buffer
    buffer_anual = projeto_conservacao * fator_risco  # t CO2e/ano
    
    # Cálculo da redução anual ajustada
    reducao_anual_ajustada = projeto_conservacao - buffer_anual  # t CO2e/ano
    
    return perda_carbono_anual_CO2e, projeto_conservacao, vazamento_anual, buffer_anual, reducao_anual_ajustada

def resultados_completos(estoque_inicial,fator_risco,):
    # Calculando as reduções para os próximos 30 anos
    resultados = []
    vcus_acumulados = 0

    for ano, taxa in zip(projection_years, projection):
        perda, conservacao, vazamento, buffer, reducao = calcular_reducoes(taxa, estoque_inicial, fator_risco)
        vcus_acumulados += reducao
        resultados.append({
            "Ano": int(ano),
            "Taxa de Desmatamento Projetada (%)": taxa,
            "Linha Base (t CO2e)": perda,
            "Projeto (t CO2e)": conservacao,
            "Vazamento (t CO2e)": vazamento,
            "Buffer (t CO2e)": buffer,
            "Redução Líquida (t CO2e)": reducao,
            "VCUs Acumulados (t CO2e)": vcus_acumulados
        })

    # Criar DataFrame com os resultados
    df_resultados_completos = pd.DataFrame(resultados)
    print(df_resultados_completos.dtypes)
    # Exibir os resultados
    #import ace_tools as tools; tools.display_dataframe_to_user(name="Tabela de VCU Completa com Projeção de Taxa de Desmatamento", dataframe=df_resultados_completos)
    return(df_resultados_completos)
