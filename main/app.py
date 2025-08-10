import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import plotly.express as px
import folium
from streamlit_folium import st_folium
from folium.plugins import HeatMap

st.set_page_config(page_title="Dashboard AIH - RIDE", layout="wide")

st.markdown("""
<style>
    .main .block-container {
        padding-top: 1rem;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .header-container {
        background-color: #1D355B;
        padding: 2rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
    }
    .kpi-card {
        background-color: rgba(255, 255, 255, 0.1);
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    .kpi-card .stMetricValue {
        color: white;
        font-size: 2.2em;
    }
    .kpi-card .stMetricLabel {
        color: rgba(255, 255, 255, 0.7);
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

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

@st.cache_data
def carregar_dados_geo(caminho_arquivo):
    try:
        df_geo = pd.read_csv(caminho_arquivo)
        rename_map = {'codigo_ibge': 'codigo_municipio', 'latitude': 'lat', 'longitude': 'lon'}
        df_geo = df_geo.rename(columns=rename_map)
        df_geo['codigo_municipio'] = df_geo['codigo_municipio'].astype(str).str[:6]
        return df_geo[['codigo_municipio', 'lat', 'lon']]
    except FileNotFoundError:
        return None
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo de coordenadas: {e}")
        return None

engine = init_connection()

if engine:
    minha_query = 'SELECT * FROM public.sus_ride_df_aih;'
    df = run_query(minha_query, engine)

    df_geo = carregar_dados_geo('main/municipios_brasileiros.csv')
    if df_geo is not None and df is not None:
        df['codigo_municipio'] = df['codigo_municipio'].astype(str)
        df = pd.merge(df, df_geo, on='codigo_municipio', how='left')
    
    if df is not None and not df.empty:
        with st.container():
            st.markdown('<div class="header-container">', unsafe_allow_html=True)
            st.title("🏥 Análise de Internações (AIH) na RIDE-DF")
            st.markdown("Dashboard interativo para exploração de dados de Autorizações de Internação Hospitalar do DATASUS.")
            st.markdown("---")
            kpi1, kpi2, kpi3 = st.columns(3)
            with kpi1:
                st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
                st.metric("Valor Total (R$)", f"{df['vl_total'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                st.markdown('</div>', unsafe_allow_html=True)
            with kpi2:
                st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
                st.metric("Quantidade Total", f"{df['qtd_total'].sum():,.0f}")
                st.markdown('</div>', unsafe_allow_html=True)
            with kpi3:
                st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
                st.metric("Nº de Registros", f"{len(df):,}")
                st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        col_filtros, col_conteudo = st.columns([1, 3])
        df_filtrado = df

        with col_filtros:
            st.header("Filtros")
            ufs_disponiveis = sorted(df['uf_nome'].unique())
            ufs_selecionadas = st.multiselect('Selecione a(s) UF(s):', ufs_disponiveis, placeholder="Todas as UFs")
            if ufs_selecionadas:
                df_filtrado = df_filtrado[df_filtrado['uf_nome'].isin(ufs_selecionadas)]
            
            municipios_disponiveis = sorted(df_filtrado['nome_municipio'].unique())
            municipios_selecionados = st.multiselect('Selecione o(s) município(s):', municipios_disponiveis, placeholder="Todos")
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
            tab1, tab2, tab3, tab4 = st.tabs(["Visão Geral", "Análise Temporal", "Mapa Geográfico", "Dados Brutos"])

            with tab1:
                st.subheader("Análise para a seleção atual")
                st.markdown("##### Valor Total por Município")
                soma_por_municipio = df_filtrado.groupby('nome_municipio')['vl_total'].sum().sort_values(ascending=False)
                st.bar_chart(soma_por_municipio)
                st.markdown("##### Quantidade Total por Município")
                qtd_por_municipio = df_filtrado.groupby('nome_municipio')['qtd_total'].sum().sort_values(ascending=False)
                st.bar_chart(qtd_por_municipio, color="#D13F42")
                
            with tab2:
                st.subheader("Evolução Mensal do Valor Total")
                df_temporal = df_filtrado.copy()
                if not df_temporal.empty:
                    df_temporal['data'] = pd.to_datetime(df_temporal['ano_aih'].astype(str) + '-' + df_temporal['mes_aih'].astype(str))
                    soma_mensal = df_temporal.groupby('data')['vl_total'].sum()
                    st.line_chart(soma_mensal)
                else:
                    st.warning("Não há dados para exibir com os filtros selecionados.")
            
            with tab3:
                st.subheader("Análise Geográfica por Município (Mapa de Calor)")
                
                df_mapa = df_filtrado.dropna(subset=['lat', 'lon'])

                if not df_mapa.empty:
                    mapa_calor = folium.Map(location=[df_mapa['lat'].mean(), df_mapa['lon'].mean()], zoom_start=8, tiles="cartodbdark_matter")

                    dados_calor = df_mapa[['lat', 'lon', 'vl_total']].values.tolist()

                    HeatMap(dados_calor, radius=15).add_to(mapa_calor)

                    st_folium(mapa_calor, use_container_width=True, height=500)
                else:
                    st.warning("Não há dados geográficos para exibir com os filtros selecionados.")

            with tab4:
                st.subheader("Amostra dos Dados Filtrados")
                st.dataframe(df_filtrado.head(100))
    else:
        st.warning("A consulta não retornou dados.")
else:
    st.error("A conexão com o banco de dados falhou.")