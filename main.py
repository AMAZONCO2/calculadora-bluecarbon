import streamlit as st
import pandas as pd
from sqlalchemy.sql import text
import uuid
import altair as alt
from modules.calcular_reducao import calcula_estoque, resultados_completos



# Carregar projetos salvos do banco de dados
def load_projects():
    conn = st.connection('postgresql', type="sql")
    df = conn.query('SELECT * FROM carbono.projetos', ttl="30s")
    print("pesquisa no banco")
    project = pd.DataFrame(df)
    return project

def load_select_project(id):
    conn = st.connection('postgresql', type="sql")
    projetos_selecionado = conn.query("SELECT * FROM carbono.projetos WHERE id = :id", ttl="3360", params={"id":id})
    resultados_selecionado = conn.query("SELECT * FROM carbono.resultados WHERE projeto_id = :project_id", ttl="3360", params={"project_id":id})
    projetos = pd.DataFrame(projetos_selecionado)
    resultados = pd.DataFrame(resultados_selecionado)
    return projetos,resultados

# Salvar projeto no banco de dados
def save_project(project_data):
    conn = st.connection('postgresql', type="sql")
    project_id = str(uuid.uuid4())
    
    query = text("""
        INSERT INTO carbono.projetos (Nome_do_Projeto, Area, Delta_C_AB, Delta_C_BGB, Delta_C_SOC, Periodo_Projeto, Fator_de_Risco, Taxa_Desmatamento)
        VALUES (:nome_projeto, :area, :delta_c_ab, :delta_c_bgb, :delta_c_soc, :periodo_projeto, :fator_de_risco, :taxa_desmatamento)
        RETURNING ID;
    """)
    
    with conn.session as session:
        result = session.execute(query, {
            "id": project_id,
            "nome_projeto": project_data["Nome do Projeto"],
            "area": project_data["Área"],
            "delta_c_ab": project_data["ΔC_AB"],
            "delta_c_bgb": project_data["ΔC_BGB"],
            "delta_c_soc": project_data["ΔC_SOC"],
            "periodo_projeto": project_data["Período do Projeto"],
            "fator_de_risco": project_data["Fator de risco"],
            "taxa_desmatamento": project_data["Taxa desmatamento"]
        })
        session.commit()
        project_id = result.fetchone()[0]
    return project_id

# Atualizar nome do projeto no banco de dados
def update_project_name(project_id, new_name):
    conn = st.connection('postgresql', type="sql")
    
    query = text("""
        UPDATE carbono.projetos
        SET Nome_do_Projeto = :new_name
        WHERE id = :project_id
    """)
    
    with conn.session as session:
        session.execute(query, {"new_name": new_name, "project_id": project_id})
        session.commit()
    
# Inicializar estado da sessão
if 'projects' not in st.session_state:
    st.session_state.projects = load_projects()
    
# Salvar dados anuais no banco de dados
def save_annual_data(project_id, annual_data: pd.DataFrame):
    try:
        conn = st.connection('postgresql', type="sql")
        #print(annual_data)
        query = text("""
            INSERT INTO carbono.resultados (Projeto_ID, Ano, Taxa_Desmatamento_Projetada, Linha_Base, Projeto_tco2, Vazamento, Buffer, Reducao_Liquida, VCUs_Acumulados)
            VALUES (:projeto_id, :ano, :taxa_desmatamento_projetada, :linha_base, :projeto_tco2, :vazamento, :buffer, :reducao_liquida, :vcus_acumulados)
        """)
        
        with conn.session as session:
            for _, data in annual_data.iterrows():
                session.execute(query, {
                    "projeto_id": project_id,
                    "ano": int(data["Ano"]),
                    "taxa_desmatamento_projetada": float(data["Taxa de Desmatamento Projetada (%)"]),
                    "linha_base": float(data["Linha Base (t CO2e)"]),
                    "projeto_tco2": float(data["Projeto (t CO2e)"]),
                    "vazamento": float(data["Vazamento (t CO2e)"]),
                    "buffer": float(data["Buffer (t CO2e)"]),
                    "reducao_liquida": float(data["Redução Líquida (t CO2e)"]),
                    "vcus_acumulados": float(data["VCUs Acumulados (t CO2e)"])
                })
            session.commit()
        print("ok - Enviado id: "+project_id)
    except Exception as e:
        print(f"Erro ao salvar dados anuais para o projeto {project_id}: {e}")
    
# Função para exibir a página de cadastro de projetos
def cadastro_projeto():
    st.subheader("LINHA DE BASE")
    with st.expander("Mostrar informações completas"):
        st.header("Dados Iniciais")
        project_name = st.text_input("Nome do Projeto de Linha de Base")
        agb_inicial = st.number_input("AGB Inicial (tC/ha)")
        bgb_inicial = st.number_input("BGB Inicial (tC/ha)")
        soc_inicial = st.number_input("SOC Inicial (tC/ha)")

    st.subheader("BUFFER")
    with st.expander("Mostrar informações completas"):
        st.header("Dados de Buffer")
        fator_risco = st.number_input("Fator de risco")

    taxa_desmatamento = st.number_input("Taxa de desmatamento (%)")
    area = st.number_input("Área do projeto (ha)")
    periodo_projeto = st.number_input("Período do projeto (anos)")

    if st.button("Calcular e Salvar Linha de Base e Projeto"):
        # Calcular o estoque total inicial
        delta_c_bsl = calcula_estoque(area, agb_inicial, bgb_inicial, soc_inicial)
        estoque_total_inicial = delta_c_bsl
        
        # Calcular as reduções completas
        reducoes = resultados_completos(int(periodo_projeto),estoque_total_inicial, fator_risco, )
        
        # Dados do projeto
        project_data = {
            "Nome do Projeto": project_name,
            "ΔC_AB": agb_inicial,
            "ΔC_BGB": bgb_inicial,
            "ΔC_SOC": soc_inicial,
            "Área": area,
            "Período do Projeto": periodo_projeto,
            "Fator de risco": fator_risco,
            "Taxa desmatamento": taxa_desmatamento,
            "Média VCUs": reducoes["VCUs Acumulados (t CO2e)"].sum()/len(reducoes["VCUs Acumulados (t CO2e)"]),
            "VCUs Acumulados (t CO2e)": reducoes["VCUs Acumulados (t CO2e)"].max(),
            "Redução Líquida (t CO2e)": reducoes["Redução Líquida (t CO2e)"].max()
        }
     
        # Salvar projeto e obter o ID
        project_id = save_project(project_data)
     
        # Salvar dados anuais
        save_annual_data(project_id, reducoes)

        # Atualizar lista de projetos no estado da sessão
        st.session_state.projects = load_projects()
        
        # Mostrar resultados
        st.header("Resultados")
        st.write(reducoes)
        
        
def relatorio():
    st.header("Relatório de Projetos")

    projects = st.session_state.projects
    resultados_lista = []
    if not projects.empty:
        # Utilizar uma combinação de nome e ID para selecionar os projetos
        project_options = {f"{row['nome_do_projeto']} (ID: {row['id']})": row['id'] for _, row in projects.iterrows()}
        selected_project_keys = st.multiselect(
            "Selecione os projetos para visualizar no gráfico:",
            project_options.keys(), placeholder="Selecione uma opção"
        )
     
        if selected_project_keys:
            selected_project_ids = [project_options[key] for key in selected_project_keys]
            filtered_projects = projects[projects['id'].isin(selected_project_ids)]
            
            for _, project in filtered_projects.iterrows():
                #st.subheader(f"Projeto: {project['nome_do_projeto']}")
                #st.write(project['nome_do_projeto'])
                projetos,resultados = load_select_project(project['id'])
                # Adicionar chave única para text_input e button

                if not resultados.empty:   
                    st.subheader(f"Estimativa de 30 Anos para o Projeto: {project['nome_do_projeto']}")
                    key_prefix = str(project['id'])
                    
                    with st.expander(f"Editar nome do projeto"):
                        new_name = st.text_input(f"Novo nome do projeto (ID: {project['nome_do_projeto']})", value=project['nome_do_projeto'], key=f"name_{key_prefix}")
                        if st.button(f"Atualizar nome (ID: {project['id']})", key=f"button_{key_prefix}"):
                            update_project_name(project['id'], new_name)
                            st.session_state.projects = load_projects()
                            st.success("Nome do projeto atualizado!")
                    
                    media_vcu_anual = resultados['reducao_liquida'].sum() / len(resultados['reducao_liquida'])
                    total_vcu = resultados['vcus_acumulados'].max()
                    buffer = resultados['buffer'].max()
                    vazamento = resultados['vazamento'].sum()
                    anos = len(resultados['ano']) 
                    linha_base = resultados['linha_base'].sum()
                    projeto = resultados['projeto_tco2'].sum()
                    
                    with st.expander("Mostrar resumo"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"ΔC_AB: {project['delta_c_ab']:.2f} tC/ha")
                            st.write(f"ΔC_BGB: {project['delta_c_bgb']:.2f} tC/ha")
                            st.write(f"ΔC_SOC: {project['delta_c_soc']:.2f} tC/ha")
                            st.write(f"Área: {project['area']:.2f} ha")
                            st.write(f"Período do Projeto: {project['periodo_projeto']} anos")
                            st.write(f"Total de emissão (Vazamento) {anos} anos: {vazamento:.2f} tCO2e")
                            st.write(f"Total de emissão (Linha de base) {anos} anos: {linha_base:.2f} tCO2e")
                            st.write(f"Total de emissão (Projeto) {anos} anos: {projeto:.2f} tCO2e")

                        with col2:
                            st.write(f"Fator de risco: {project['fator_de_risco']:.2f}")
                            st.write(f"Taxa de desmatamento: {project['taxa_desmatamento']:.2f}%")
                            st.write(f"Buffer: {buffer:.2f} tCO2e")

                            st.write(f"Total de VCU: {total_vcu:.2f} tCO2e")
                            st.write(f"Média de VCU: {media_vcu_anual:.2f} tCO2e")
                       
                    # Separa informações
                    max_vcus = resultados['vcus_acumulados'].max()
                    # Criar um DataFrame temporário com o nome do projeto e o valor máximo de VCUs Acumulados (t CO2e)
                    df_temp = pd.DataFrame({
                        "Nome do Projeto": [project['nome_do_projeto']],
                        "VCUs Acumulados Máximo (t CO2e)": [max_vcus],
                        "Area": [project['area']]
                        })
                    # Adicionar o DataFrame temporário à lista de resultados
                    resultados_lista.append(df_temp)
                    # Combinar todos os resultados para gráficos
                    df_resultados_final = pd.concat(resultados_lista, ignore_index=True)
                    st.write(resultados)
                    #--------------------
                    
                    # Gráfico de VCUs Acumulados (t CO2e)
                    chart_vcus_acumulados = alt.Chart(resultados).mark_bar().encode(
                        x=alt.X('ano:O', title='Ano'),
                        y=alt.Y('vcus_acumulados:Q', title='VCUs Acumulados (t CO2e)'),
                        tooltip=['ano', 'vcus_acumulados']
                    ).properties(
                        title='Progressão dos VCUs Acumulados (t CO2e)'
                    ).encode(
                        text='vcus_acumulados:Q'
                    )
                    
                    chart_vcus_acumulados = chart_vcus_acumulados.mark_bar() + chart_vcus_acumulados.mark_text(
                        align='center',
                        baseline='bottom',
                        color='white',
                        fontSize=9
                    ).encode(
                        text=alt.Text('vcus_acumulados:Q', format='.2f')
                    )
                    st.altair_chart(chart_vcus_acumulados, use_container_width=True)
                    

            st.write("---")
            
            # # Gráfico de Créditos de Carbono Anuais por Projeto
            chart_creditos = alt.Chart(df_resultados_final).mark_bar().encode(
                x=alt.X('Nome do Projeto:N', sort=None, title='Projeto'),
                y=alt.Y('VCUs Acumulados Máximo (t CO2e):Q', title='Créditos de Carbono Totais (tCO2e)'),
                tooltip=['Nome do Projeto', 'VCUs Acumulados Máximo (t CO2e)']
            ).properties(
                title='Créditos de Carbono por Projeto'
            )
            chart_creditos = chart_creditos + chart_creditos.mark_text(
                align='center',
                baseline='bottom',
                color="white"
            ).encode(
                text='VCUs Acumulados Máximo (t CO2e):Q'
            )
            st.altair_chart(chart_creditos, use_container_width=True)

            # Gráfico de Área por Projeto
            chart_area = alt.Chart(df_resultados_final).mark_bar().encode(
                x=alt.X('Nome do Projeto:N', sort=None, title='Projeto'),
                y=alt.Y('Area:Q', title='Área (ha)'),
                tooltip=['Nome do Projeto', 'Area']
            ).properties(
                title='Àrea por Projeto'
            )
            chart_area = chart_area + chart_area.mark_text(
                align='center',
                baseline='bottom',
                color="white"
            ).encode(
                text='Area:Q'
            )
            st.altair_chart(chart_area, use_container_width=True)

            # Gráfico de Pizza para a Distribuição dos Créditos de Carbono
            chart_pie = alt.Chart(df_resultados_final).mark_arc().encode(
                theta=alt.Theta(field="VCUs Acumulados Máximo (t CO2e)", type="quantitative"),
                color=alt.Color(field="Nome do Projeto", type="nominal"),
                tooltip=[alt.Tooltip("Nome do Projeto", title="Projeto"),
                         alt.Tooltip("VCUs Acumulados Máximo (t CO2e)", title="Créditos (tCO2e)")]
            ).properties(
                title='Distribuição dos VCUs Acumulados'
            )
            st.altair_chart(chart_pie, use_container_width=True)

        else:
            st.write("Nenhum projeto selecionado.")
    else:
        st.write("Nenhum projeto encontrado.")


# Interface do usuário
st.title("Estimativa de Créditos de Carbono Anuais - Blue Carbon")
logo_url = "./logo_acc.svg"
st.sidebar.image(logo_url, width=100)
# Menu de navegação
menu = st.sidebar.selectbox("Menu", ["Cadastro de Projeto", "Relatório"])

if menu == "Cadastro de Projeto":
    cadastro_projeto()
elif menu == "Relatório":
    relatorio()

# # Mostrar projetos salvos
# st.sidebar.header("Projetos Salvos")
# st.session_state.projects['Projeto Display'] =  st.session_state.projects['nome_do_projeto']
# selected_project = st.sidebar.selectbox("Selecione um projeto", [""] + st.session_state.projects['Projeto Display'].tolist())

# if selected_project:
#     selected_id = (selected_project.split(" - ")[0])
#     project_data = st.session_state.projects[st.session_state.projects["id"] == selected_id]
#     st.write(selected_project)
#     # Campo para editar o nome do projeto
#     new_name = st.sidebar.text_input("Novo nome do projeto", value=selected_project)
#     if st.sidebar.button("Atualizar nome"):
#         update_project_name(selected_id, new_name)
#         st.session_state.projects = load_projects()
#         st.sidebar.success("Nome do projeto atualizado!")

#     st.sidebar.write("Resultados")
#     st.sidebar.write(f"Emissões na Linha de Base (delta_c_bsl): {project_data['delta_c_bsl'].values[0]:.2f} tCO2e")
#    # st.sidebar.write(f"Emissões no Projeto (delta_c_ps): {project_data['delta_c_ps'].values[0]:.2f} tCO2e")
#     st.sidebar.write(f"Emissões de Fuga (delta_c_lk): {project_data['delta_c_lk'].values[0]::.2f} tCO2e")
#     st.sidebar.write(f"Reduções Líquidas de Emissões (NER_REDD): {project_data['NER_REDD'].values[0]:.2f} tCO2e")
#     st.sidebar.write(f"Buffer: {project_data['Buffer'].values[0]:.2f} tCO2e")
#     st.sidebar.write(f"Total CO2e: {project_data['Total_CO2e'].values[0]:.2f} tCO2e")
#     st.sidebar.write(f"Créditos de Carbono Anuais: {project_data['Créditos_Carbono_Anuais'].values[0]:.2f} tCO2e/ano")
#     st.sidebar.write(f"Total do Valor dos Créditos Gerados ($): {project_data['Total_Valor_dos_Creditos_($)'].values[0]:.2f}")

st.sidebar.markdown('<p style="font-size=3px">Desenvolvido por ACC © 2024 Amazon Connection Carbon. Todos os direitos reservados.</p>', unsafe_allow_html=True)
