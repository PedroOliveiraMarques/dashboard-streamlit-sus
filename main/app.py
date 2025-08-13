import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import plotly.express as px
import folium
from streamlit_folium import st_folium
from folium.plugins import HeatMap

# ===================== CONFIGURAÇÃO PÁGINA =====================
st.set_page_config(
    page_title="Dashboard AIH - RIDE",
    layout="wide",
    initial_sidebar_state="auto",
    page_icon="🏥"
)

# ===================== CSS PADRÃO PROFESSOR =====================
st.markdown("""
<style>
    /* Geral */
    body, .main {
        background-color: #F5F6FA;
        font-family: 'Arial', sans-serif;
    }

    /* Cabeçalho */
    .header-box {
        background-color: #2C225F;
        padding: 2rem;
        color: white;
        margin-bottom: 1.5rem;
        border-radius: 10px;
    }

    .header-title {
        font-size: 1.8rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }

    .header-desc {
        font-size: 1rem;
        opacity: 0.9;
    }

    /* Métricas */
    .metric-container {
        display: flex;
        gap: 1rem;
        margin-top: 1.5rem;
    }
    .metric-card {
        background-color: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        text-align: center;
        flex: 1;
    }
    .metric-card h3 {
        font-size: 1.2rem;
        color: #333;
        margin-bottom: 0.3rem;
    }
    .metric-card p {
        font-size: 1.4rem;
        font-weight: bold;
        margin: 0;
    }

    /* Caixa branca de conteúdo */
    .content-box {
        background-color: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        margin-bottom: 1rem;
    }

    /* Filtros */
    .stSelectbox, .stMultiselect, .stSlider {
        background-color: white !important;
    }

    /* Rodapé */
    .footer {
        text-align: center; 
        color: #888; 
        margin-top: 40px;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# ===================== FUNÇÕES BANCO DE DADOS =====================
@st.cache_resource
def init_connection():
    try:
        db_credentials = st.secrets["postgres"]
        connection_string = (f"postgresql+psycopg2://{db_credentials['user']}:{db_credentials['password']}@"
                             f"{db_credentials['host']}:{db_credentials['port']}/{db_credentials['database']}")
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
    st.markdown(
        "<div class='footer'>Desenvolvido por Pedro e Mateus Lima para o Projeto de Análise de Dados | Fonte: DATASUS / AIH</div>",
        unsafe_allow_html=True
    )

# ===================== CONEXÃO E QUERY =====================
engine = init_connection()

if engine:
    minha_query = 'SELECT * FROM public.sus_ride_df_aih;'
    df = run_query(minha_query, engine)

    if df is not None and not df.empty:
        if 'latitude' in df.columns and 'longitude' in df.columns:
            df = df.rename(columns={'latitude': 'lat', 'longitude': 'lon'})

        # ===================== HEADER =====================
        st.markdown('<div class="header-box">', unsafe_allow_html=True)
        st.markdown('<div class="header-title">🏥 Análise de Internações (AIH) na RIDE-DF</div>', unsafe_allow_html=True)
        st.markdown('<div class="header-desc">Este painel apresenta análises interativas com dados de Autorizações de Internação Hospitalar do DATASUS. É possível filtrar por UF, município, faixa populacional, ano e mês para personalizar a análise.</div>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"<div class='metric-card'><h3>Valor Total (R$)</h3><p>{df['vl_total'].sum():,.2f}</p></div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div class='metric-card'><h3>Quantidade Total</h3><p>{df['qtd_total'].sum():,.0f}</p></div>", unsafe_allow_html=True)
        with col3:
            st.markdown(f"<div class='metric-card'><h3>Nº de Registros</h3><p>{len(df):,}</p></div>", unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

        # ===================== LAYOUT PRINCIPAL =====================
        col_filtros, col_conteudo = st.columns([1, 3])
        df_filtrado = df.copy()

        # ===== COLUNA DE FILTROS =====
        with col_filtros:
            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
            st.header("Filtros")
            
            ufs_disponiveis = sorted(df['uf_nome'].unique())
            ufs_selecionadas = st.multiselect('UF(s):', ufs_disponiveis)
            if ufs_selecionadas:
                df_filtrado = df_filtrado[df_filtrado['uf_nome'].isin(ufs_selecionadas)]
            
            municipios_disponiveis = sorted(df_filtrado['nome_municipio'].unique())
            municipios_selecionados = st.multiselect('Município(s):', municipios_disponiveis)
            if municipios_selecionados:
                df_filtrado = df_filtrado[df_filtrado['nome_municipio'].isin(municipios_selecionados)]

            if 'faixa_populacao' in df_filtrado.columns:
                faixas_disponiveis = sorted(df_filtrado['faixa_populacao'].unique())
                faixas_selecionadas = st.multiselect('Faixa populacional:', faixas_disponiveis)
                if faixas_selecionadas:
                    df_filtrado = df_filtrado[df_filtrado['faixa_populacao'].isin(faixas_selecionadas)]

            anos_disponiveis = sorted(df_filtrado['ano_aih'].unique(), reverse=True)
            anos_selecionados = st.multiselect('Ano(s):', anos_disponiveis)
            if anos_selecionados:
                df_filtrado = df_filtrado[df_filtrado['ano_aih'].isin(anos_selecionados)]

            meses_disponiveis = sorted(df_filtrado['mes_aih'].unique())
            meses_selecionados = st.multiselect('Mês(es):', meses_disponiveis)
            if meses_selecionados:
                df_filtrado = df_filtrado[df_filtrado['mes_aih'].isin(meses_selecionados)]
            st.markdown("</div>", unsafe_allow_html=True)

        # ===== COLUNA DE CONTEÚDO =====
        with col_conteudo:
            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
            if df_filtrado.empty:
                st.warning("Nenhum registro encontrado para a combinação de filtros selecionada.")
            else:
                abas = st.tabs(["Visão Geral", "Por Região", "Análise Temporal", "Mapa Geográfico", "Dados Brutos"])

                with abas[0]:
                    st.subheader("Ranking por Município")
                    soma_por_municipio = df_filtrado.groupby('nome_municipio')['vl_total'].sum().sort_values(ascending=False)
                    st.bar_chart(soma_por_municipio)

                    if 'numero_habitantes' in df_filtrado.columns and df_filtrado['numero_habitantes'].sum() > 0:
                        st.subheader("Top 15 Municípios por Valor Gasto por Habitante (R$)")
                        df_per_capita = df_filtrado.groupby('nome_municipio').agg(
                            vl_total_sum=('vl_total', 'sum'),
                            populacao_sum=('numero_habitantes', 'first')
                        ).dropna()
                        df_per_capita['valor_por_habitante'] = df_per_capita['vl_total_sum'] / df_per_capita['populacao_sum']
                        st.bar_chart(df_per_capita['valor_por_habitante'].sort_values(ascending=False).head(15), color="#D13F42")

                with abas[1]:
                    st.subheader("Ranking por Região")
                    if 'regiao_nome' in df_filtrado.columns:
                        soma_por_regiao = df_filtrado.groupby('regiao_nome')['vl_total'].sum().sort_values(ascending=False)
                        st.bar_chart(soma_por_regiao)
                        qtd_por_regiao = df_filtrado.groupby('regiao_nome')['qtd_total'].sum().sort_values(ascending=False)
                        st.bar_chart(qtd_por_regiao, color="#D13F42")

                with abas[2]:
                    st.subheader("Evolução Mensal do Valor Total")
                    df_temporal = df_filtrado.copy()
                    df_temporal['data'] = pd.to_datetime(df_filtrado['ano_aih'].astype(str) + '-' + df_filtrado['mes_aih'].astype(str))
                    soma_mensal = df_temporal.groupby('data')['vl_total'].sum().sort_index()
                    st.line_chart(soma_mensal)

                with abas[3]:
                    st.subheader("Mapa de Calor")
                    if 'lat' in df_filtrado.columns:
                        df_mapa = df_filtrado.dropna(subset=['lat', 'lon', 'vl_total'])
                        if not df_mapa.empty:
                            mapa_calor = folium.Map(location=[df_mapa['lat'].mean(), df_mapa['lon'].mean()],
                                                    zoom_start=8, tiles="cartodbdark_matter")
                            HeatMap(df_mapa[['lat', 'lon', 'vl_total']].values.tolist(), radius=15).add_to(mapa_calor)
                            st_folium(mapa_calor, use_container_width=True, height=500)
                        else:
                            st.warning("Não há dados geográficos para exibir.")
                    else:
                        st.warning("Colunas de latitude e longitude não encontradas.")

                with abas[4]:
                    st.subheader("Amostra dos Dados")
                    st.dataframe(df_filtrado.head(100))

            st.markdown("</div>", unsafe_allow_html=True)
            footer()

    else:
        st.warning("A consulta não retornou dados.")
else:
    st.error("A conexão com o banco de dados falhou.")
