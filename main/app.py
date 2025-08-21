# Financial Summary Data
# Valor Total (R$): 2,245,405,043.13
# Quantidade Total: 87,273,506
# Nº de Registros: 2,618

import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import plotly.express as px
import folium
from streamlit_folium import st_folium
from folium.plugins import HeatMap
import boto3
import json

# Add specific CSS protection for canvas-based maps
st.markdown("""
<style>
/* Protect all canvas elements and their containers from button styling */
canvas,
canvas *,
[class*="canvas"],
[class*="canvas"] *,
[id*="canvas"],
[id*="canvas"] *,
.stIframe,
.stIframe *,
[data-testid="stIframe"],
[data-testid="stIframe"] *,
.leaflet-container,
.leaflet-container *,
.folium-map,
.folium-map *,
div[data-testid="stIframe"] canvas,
div[data-testid="stIframe"] canvas * {
    all: revert !important;
    background: initial !important;
    color: initial !important;
    border: initial !important;
    border-radius: initial !important;
}

/* Specifically target streamlit-folium iframe content */
iframe[src*="folium"],
iframe[src*="folium"] *,
iframe[title*="folium"],
iframe[title*="folium"] * {
    all: revert !important;
}

/* ===== Placeholder branco nos Select/MultiSelect do Streamlit ===== */
.stMultiSelect div[data-baseweb="select"] input::placeholder,
.stSelectbox  div[data-baseweb="select"] input::placeholder {
    color: white !important;
    opacity: 1 !important;
}

.stMultiSelect div[data-baseweb="select"] span,
.stSelectbox  div[data-baseweb="select"] span,
.stMultiSelect div[data-baseweb="select"] div,
.stSelectbox  div[data-baseweb="select"] div {
    color: white !important;
}
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_secret(secret_name, region_name="us-east-1"):
    """
    Retrieve secret from AWS Secrets Manager
    """
    try:
        # Create a Secrets Manager client
        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name=region_name
        )
        
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
        
        # Parse the secret string
        secret_string = get_secret_value_response['SecretString']
        secret = json.loads(secret_string)
        
        return secret
        
    except json.JSONDecodeError as e:
        st.error(f"Erro ao fazer parse do JSON do secret: {e}")
        return None
    except Exception as e:
        st.error(f"Erro ao recuperar secret do AWS Secrets Manager: {e}")
        return None

@st.cache_resource
def init_connection():
    try:
        # Get database credentials from AWS Secrets Manager
        db_credentials = get_secret("rds-secret")
        
        if db_credentials is None:
            st.error("Não foi possível recuperar as credenciais do banco de dados do AWS Secrets Manager")
            return None
        
        # Check for required keys
        required_keys = ['username', 'password', 'host', 'db_name']
        missing_keys = [key for key in required_keys if key not in db_credentials]
        
        if missing_keys:
            st.error(f"Credenciais incompletas no banco de dados")
            return None
            
        # Build connection string using the actual secret structure
        connection_string = (f"postgresql+psycopg2://{db_credentials['username']}:{db_credentials['password']}@"
                             f"{db_credentials['host']}:{db_credentials.get('port', 5432)}/{db_credentials['db_name']}")
        
        engine = create_engine(connection_string)
        
        # Test the connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        return engine
        
    except KeyError as e:
        st.error(f"Configuração de banco de dados incompleta")
        return None
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

engine = init_connection()

if engine:
    minha_query = 'SELECT * FROM public.sus_ride_df_aih;'
    df = run_query(minha_query, engine)

    if df is not None and not df.empty:

        if 'latitude' in df.columns and 'longitude' in df.columns:
            df = df.rename(columns={'latitude': 'lat', 'longitude': 'lon'})

        valor_total_fmt = f"{df['vl_total'].sum():,.2f}".replace(',','X').replace('.',',').replace('X','.')
        qtd_total_fmt = f"{df['qtd_total'].sum():,.0f}".replace(',','.')
        n_reg_fmt = f"{len(df):,}".replace(',','.')

        # Display metrics horizontally using columns
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(label="Valor Total (R$)", value=valor_total_fmt)
        
        with col2:
            st.metric(label="Quantidade Total", value=qtd_total_fmt)
        
        with col3:
            st.metric(label="Nº de Registros", value=n_reg_fmt)

        col_filtros, col_conteudo = st.columns([1, 3])
        df_filtrado = df.copy()

        with col_filtros:
            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
            st.header("Filtros")

            ufs_disponiveis = sorted(df['uf_nome'].unique())
            ufs_selecionadas = st.multiselect('Unidade da Federação:', ufs_disponiveis, placeholder='Opções')
            if ufs_selecionadas:
                df_filtrado = df_filtrado[df_filtrado['uf_nome'].isin(ufs_selecionadas)]

            municipios_disponiveis = sorted(df_filtrado['nome_municipio'].unique())
            municipios_selecionados = st.multiselect('Municípios:', municipios_disponiveis, placeholder='Opções')
            if municipios_selecionados:
                df_filtrado = df_filtrado[df_filtrado['nome_municipio'].isin(municipios_selecionados)]

            anos_disponiveis = sorted(df_filtrado['ano_aih'].unique(), reverse=True)
            anos_selecionados = st.multiselect('Anos:', anos_disponiveis, placeholder='Opções')
            if anos_selecionados:
                df_filtrado = df_filtrado[df_filtrado['ano_aih'].isin(anos_selecionados)]

            meses_disponiveis = sorted(df_filtrado['mes_aih'].unique())
            meses_selecionados = st.multiselect('Meses:', meses_disponiveis, placeholder='Opções')
            if meses_selecionados:
                df_filtrado = df_filtrado[df_filtrado['mes_aih'].isin(meses_selecionados)]
            st.markdown("</div>", unsafe_allow_html=True)

        with col_conteudo:
            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
            if df_filtrado.empty:
                st.warning("Nenhum registro encontrado para a combinação de filtros selecionada.")
            else:
                abas = st.tabs(["Visão Geral", "Por Região", "Análise Temporal", "Mapa Geográfico", "Dados Brutos", "Gráfico de Pizza"])

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
                            # Calculate proper center and bounds
                            center_lat = df_mapa['lat'].mean()
                            center_lon = df_mapa['lon'].mean()
                            
                            # Calculate zoom level based on data spread
                            lat_range = df_mapa['lat'].max() - df_mapa['lat'].min()
                            lon_range = df_mapa['lon'].max() - df_mapa['lon'].min()
                            max_range = max(lat_range, lon_range)
                            
                            # Determine appropriate zoom level
                            if max_range > 10:
                                zoom_level = 5
                            elif max_range > 5:
                                zoom_level = 6
                            elif max_range > 2:
                                zoom_level = 7
                            elif max_range > 1:
                                zoom_level = 8
                            else:
                                zoom_level = 9
                            
                            # Create map with proper centering
                            mapa_calor = folium.Map(
                                location=[center_lat, center_lon],
                                zoom_start=zoom_level,
                                tiles="cartodbdark_matter"
                            )
                            
                            # Add heatmap
                            HeatMap(
                                df_mapa[['lat', 'lon', 'vl_total']].values.tolist(), 
                                radius=15,
                                blur=10,
                                max_zoom=18
                            ).add_to(mapa_calor)
                            
                            # Display the map with canvas protection
                            st_folium(mapa_calor, use_container_width=True, height=500, key="protected_map")
                        else:
                            st.warning("Não há dados geográficos para exibir.")
                    else:
                        st.warning("Colunas de latitude e longitude não encontradas.")

                with abas[4]:
                    st.subheader("Amostra dos Dados")
                    st.dataframe(df_filtrado.head(100))
                
                with abas[5]:
                    st.subheader("Análise por Tipo de Procedimento")

                    # Mapeamento dos nomes das colunas para nomes legíveis
                    mapeamento_grupos = {
                        'vl_02': 'Diagnósticos',
                        'vl_03': 'Clínicos',
                        'vl_04': 'Cirúrgicos',
                        'vl_05': 'Transplantes',
                        'vl_06': 'Medicamentos',
                        'vl_07': 'Órteses e Próteses',
                        'vl_08': 'Ações Complementares'
                    }
                    colunas_grupos = list(mapeamento_grupos.keys())
                    soma_grupos = df_filtrado[colunas_grupos].sum().rename(index=mapeamento_grupos).sort_values(ascending=False)
                    soma_grupos = soma_grupos[soma_grupos > 0]

                    if not soma_grupos.empty:
                        st.markdown("##### Proporção de Gasto por Grupo de Procedimento")
                        fig_pizza = px.pie(soma_grupos, values=soma_grupos.values, names=soma_grupos.index, hole=0.4)
                        st.plotly_chart(fig_pizza, use_container_width=True)
                    
                    st.markdown("---")

                    mapeamento_cirurgias = {
                        'vl_0401': 'Pele e Mucosa', 'vl_0403': 'Sistema Nervoso', 'vl_0404': 'Cabeça e Pescoço',
                        'vl_0405': 'Visão', 'vl_0406': 'Aparelho Circulatório', 'vl_0407': 'Aparelho Digestivo',
                        'vl_0408': 'Osteomuscular', 'vl_0409': 'Geniturinário', 'vl_0411': 'Obstétrica',
                        'vl_0416': 'Oncologia'
                    }
                    colunas_cirurgias = list(mapeamento_cirurgias.keys())
                    soma_cirurgias = df_filtrado[colunas_cirurgias].sum().rename(index=mapeamento_cirurgias).sort_values(ascending=False)
                    soma_cirurgias = soma_cirurgias[soma_cirurgias > 0]

                    if not soma_cirurgias.empty:
                        st.markdown("##### Valor Gasto nos Principais Tipos de Cirurgia (R$)")
                        st.bar_chart(soma_cirurgias)
                
            st.markdown("</div>", unsafe_allow_html=True)

    else:
        st.warning("A consulta não retornou dados.")
else:
    st.error("A conexão com o banco de dados falhou.")