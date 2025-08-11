import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import plotly.express as px
import folium
from streamlit_folium import st_folium
from folium.plugins import HeatMap

# ========== CONFIGURAÇÃO DA PÁGINA (DO NOVO MODELO) ==========
st.set_page_config(
    page_title="Dashboard AIH - RIDE",
    layout="wide",
    initial_sidebar_state="auto",
    page_icon="🏥"
)

# --- FUNÇÕES DE BANCO DE DADOS E CARREGAMENTO DE DADOS ---
@st.cache_resource
def init_connection():
    try:
        db_credentials = st.secrets["postgres"]
        connection_string = (f"postgresql+psycopg2://{db_credentials['user']}:{db_credentials['password']}@{db_credentials['host']}:{db_credentials['port']}/{db_credentials['database']}")
        return create_engine(connection_string)
    except Exception as e:
        st.error(f"Não foi possível conectar ao banco de dados: {e}")
        return None

@st.cache_data(ttl=600)
def run_query(query, _engine):
    try:
        with _engine.connect() as connection:
            df = pd.read_sql(text(query), connection)
        return df
    except Exception as e:
        st.error(f"Erro ao executar a consulta: {e}")
        return None

def footer():
    st.markdown("""
    <div style='text-align:center; color:#888; margin-top:40px;'>
        Desenvolvido por Pedro e Mateus Lima para o Projeto de Análise de Dados | Fonte: DATASUS / AIH
    </div>
    """, unsafe_allow_html=True)

# --- Início da Aplicação ---
engine = init_connection()

if engine:
    minha_query = 'SELECT * FROM public.sus_ride_df_aih;'
    df = run_query(minha_query, engine)

    if df is not None and not df.empty:
        if 'latitude' in df.columns and 'longitude' in df.columns:
            df = df.rename(columns={'latitude': 'lat', 'longitude': 'lon'})
        
        # ========== HEADER PERSONALIZADO (DO NOVO MODELO) ==========
        with st.container():
            st.markdown("""
                <div style="
                    background-color: #2C225F;
                    padding: 1.5rem 2rem;
                    border-radius: 10px;
                    color: white;
                    text-align: left;
                    font-size: 1.5rem;
                    font-weight: bold;
                    margin-bottom: 1rem;
                ">
                    🏥 Análise de Internações (AIH) na RIDE-DF
                    <p style="font-size: 1rem; font-weight: normal; margin-top: 0.5rem;">
                        Este painel apresenta análises interativas com dados de Autorizações de Internação Hospitalar do DATASUS.
                    </p>
                </div>
            """ , unsafe_allow_html=True)

            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            with kpi1:
                st.metric("Período Analisado", f"{df['ano_aih'].min()} - {df['ano_aih'].max()}")
            with kpi2:
                st.metric("Fonte dos Dados", "DATASUS")
            with kpi3:
                st.metric("Nº de Registros Totais", f"{len(df):,}")
            with kpi4:
                st.metric("Atualização", "Ago 2025")

        col_filtros, col_conteudo = st.columns([1, 3])
        df_filtrado = df

        with col_filtros:
            st.header("Filtros")
            
            ufs_disponiveis = sorted(df['uf_nome'].unique())
            ufs_selecionadas = st.multiselect('Selecione a(s) UF(s):', ufs_disponiveis, placeholder="Todas as UFs")
            if ufs_selecionadas:
                df_filtrado = df_filtrado[df_filtrado['uf_nome'].isin(ufs_selecionadas)]
            
            municipios_disponiveis = sorted(df_filtrado['nome_municipio'].unique())
            municipios_selecionados = st.multiselect('Selecione o(s) município(s):', municipios_disponiveis, placeholder="Todos os Municípios")
            if municipios_selecionados:
                df_filtrado = df_filtrado[df_filtrado['nome_municipio'].isin(municipios_selecionados)]

            st.markdown("---")
            anos_disponiveis = sorted(df_filtrado['ano_aih'].unique(), reverse=True)
            anos_selecionados = st.multiselect('Selecione o(s) ano(s):', anos_disponiveis, placeholder="Todos os Anos")
            if anos_selecionados:
                df_filtrado = df_filtrado[df_filtrado['ano_aih'].isin(anos_selecionados)]

            meses_disponiveis = sorted(df_filtrado['mes_aih'].unique())
            meses_selecionados = st.multiselect('Selecione o(s) mes(es):', meses_disponiveis, placeholder="Todos os Meses")
            if meses_selecionados:
                df_filtrado = df_filtrado[df_filtrado['mes_aih'].isin(meses_selecionados)]

        with col_conteudo:
            if df_filtrado.empty:
                st.warning("Nenhum registro encontrado para a combinação de filtros selecionada.")
            else:
                tab1, tab2, tab3, tab4, tab5 = st.tabs(["Visão Geral", "Por Região", "Análise Temporal", "Mapa Geográfico", "Dados Brutos"])

                with tab1:
                    st.subheader(f"Análise de Ranking por Município")
                    st.markdown("##### Valor Total por Município (R$)")
                    soma_por_municipio = df_filtrado.groupby('nome_municipio')['vl_total'].sum().sort_values(ascending=False)
                    st.bar_chart(soma_por_municipio)
                    if 'numero_habitantes' in df_filtrado.columns and df_filtrado['numero_habitantes'].sum() > 0:
                        st.markdown("##### Top 15 Municípios por Valor Gasto por Habitante (R$)")
                        df_per_capita = df_filtrado.groupby('nome_municipio').agg(
                            vl_total_sum=('vl_total', 'sum'),
                            populacao_sum=('numero_habitantes', 'first')
                        ).dropna()
                        df_per_capita['valor_por_habitante'] = df_per_capita['vl_total_sum'] / df_per_capita['populacao_sum']
                        st.bar_chart(df_per_capita['valor_por_habitante'].sort_values(ascending=False).head(15), color="#D13F42")

                with tab2:
                    st.subheader("Análise de Ranking por Região")
                    if 'regiao_nome' in df_filtrado.columns:
                        st.markdown("##### Valor Total por Região (R$)")
                        soma_por_regiao = df_filtrado.groupby('regiao_nome')['vl_total'].sum().sort_values(ascending=False)
                        st.bar_chart(soma_por_regiao)
                        st.markdown("##### Quantidade Total por Região")
                        qtd_por_regiao = df_filtrado.groupby('regiao_nome')['qtd_total'].sum().sort_values(ascending=False)
                        st.bar_chart(qtd_por_regiao, color="#D13F42")
                    
                with tab3:
                    st.subheader("Evolução Mensal do Valor Total")
                    df_temporal = df_filtrado.copy()
                    df_temporal['data'] = pd.to_datetime(df_filtrado['ano_aih'].astype(str) + '-' + df_filtrado['mes_aih'].astype(str))
                    soma_mensal = df_temporal.groupby('data')['vl_total'].sum().sort_index()
                    st.line_chart(soma_mensal)
                
                with tab4:
                    st.subheader("Análise Geográfica por Município (Mapa de Calor)")
                    if 'lat' in df_filtrado.columns:
                        df_mapa = df_filtrado.dropna(subset=['lat', 'lon', 'vl_total'])
                        if not df_mapa.empty:
                            mapa_calor = folium.Map(location=[df_mapa['lat'].mean(), df_mapa['lon'].mean()], zoom_start=8, tiles="cartodbdark_matter")
                            dados_calor = df_mapa[['lat', 'lon', 'vl_total']].values.tolist()
                            HeatMap(dados_calor, radius=15).add_to(mapa_calor)
                            st_folium(mapa_calor, use_container_width=True, height=500)
                        else:
                            st.warning("Não há dados geográficos para exibir com os filtros selecionados.")
                    else:
                        st.warning("Colunas 'latitude' e 'longitude' não encontradas nos dados do banco.")

                with tab5:
                    st.subheader("Amostra dos Dados Filtrados")
                    st.dataframe(df_filtrado.head(100))
                
                footer()
    else:
        st.warning("A consulta não retornou dados.")
else:
    st.error("A conexão com o banco de dados falhou.")