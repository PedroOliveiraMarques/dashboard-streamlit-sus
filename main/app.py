import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import plotly.express as px

# Define o layout da página para ser "wide" (largo) e o título da aba do navegador
st.set_page_config(page_title="Dashboard SUS", layout="wide")

# --- Funções de Conexão e Preparação de Dados ---
@st.cache_resource
def init_connection():
    """Inicializa a conexão com o banco de dados."""
    try:
        db_credentials = st.secrets["postgres"]
        connection_string = (f"postgresql+psycopg2://{db_credentials['user']}:{db_credentials['password']}@{db_credentials['host']}:{db_credentials['port']}/{db_credentials['database']}")
        return create_engine(connection_string)
    except Exception as e:
        st.error(f"Não foi possível conectar ao banco de dados: {e}")
        return None

@st.cache_data(ttl=600)
def run_query(query, _engine):
    """Executa uma consulta no banco de dados e retorna um DataFrame."""
    try:
        with _engine.connect() as connection:
            df = pd.read_sql(text(query), connection)
        return df
    except Exception as e:
        st.error(f"Erro ao executar a consulta: {e}")
        return None

@st.cache_data
def carregar_dados_geo(caminho_arquivo):
    """Carrega o arquivo CSV com dados geográficos dos municípios."""
    try:
        try:
            df_geo = pd.read_csv(caminho_arquivo, sep=',')
        except:
            df_geo = pd.read_csv(caminho_arquivo, sep=';')
        
        rename_map = {}
        possible_names = {
            'codigo_municipio': ['codigo_ibge', 'Codigo IBGE'],
            'lat': ['latitude', 'Latitude'],
            'lon': ['longitude', 'Longitude'],
            'UF': ['uf', 'UF', 'estado_sigla', 'codigo_uf'],
            'capital': ['capital', 'Capital']
        }
        for standard_name, possible_list in possible_names.items():
            for possible_name in possible_list:
                if possible_name in df_geo.columns:
                    rename_map[possible_name] = standard_name
                    break
        
        df_geo = df_geo.rename(columns=rename_map)
        df_geo['codigo_municipio'] = df_geo['codigo_municipio'].astype(str).str[:6]
        colunas_essenciais = ['codigo_municipio', 'lat', 'lon', 'UF', 'capital']
        if not all(col in df_geo.columns for col in colunas_essenciais):
            st.error(f"O arquivo de coordenadas não contém todas as colunas necessárias.")
            return None
        return df_geo[colunas_essenciais]
    except FileNotFoundError:
        return None
    except Exception as e:
        st.error(f"Ocorreu um erro ao carregar o arquivo de coordenadas: {e}")
        return None

# --- Início da Aplicação ---
engine = init_connection()
st.title("🗺️ Dashboard Geo-Analítico de Dados de AIH (SUS)")

if engine:
    minha_query = 'SELECT * FROM "Projeto_Integrador"."SUS_AIH_PI_HMDC679A";'
    df_principal = run_query(minha_query, engine)
    
    df_geo = carregar_dados_geo('main/municipios_brasileiros.csv')

    if df_principal is not None and not df_principal.empty:
        df = df_principal.copy()
        if df_geo is not None:
            df['codigo_municipio'] = df['codigo_municipio'].astype(str)
            df = pd.merge(df, df_geo, on='codigo_municipio', how='left')
            st.success("Dados geográficos carregados e combinados com sucesso!")
        else:
            st.warning("Arquivo 'municipios_brasileiros.csv' não encontrado. O mapa não será exibido.")

        # --- BARRA LATERAL COM FILTROS ---
        st.sidebar.header('Filtros Interativos')
        anos_disponiveis = sorted(df['ano_aih'].unique(), reverse=True)
        anos_disponiveis.insert(0, "Todos")
        ano_selecionado = st.sidebar.selectbox('Selecione o Ano:', anos_disponiveis)
        if ano_selecionado != "Todos":
            df_filtrado_por_ano = df[df['ano_aih'] == ano_selecionado]
        else:
            df_filtrado_por_ano = df

        meses_disponiveis = sorted(df_filtrado_por_ano['mes_aih'].unique())
        meses_disponiveis.insert(0, "Todos")
        mes_selecionado = st.sidebar.selectbox('Selecione o Mês:', meses_disponiveis)
        if mes_selecionado != "Todos":
            df_filtrado_final = df_filtrado_por_ano[df_filtrado_por_ano['mes_aih'] == mes_selecionado]
        else:
            df_filtrado_final = df_filtrado_por_ano
            
        st.sidebar.write("---")
        if 'nome_municipio' in df_filtrado_final.columns:
            municipios_disponiveis = sorted(df_filtrado_final['nome_municipio'].unique())
            municipios_selecionados = st.sidebar.multiselect('Selecione um ou mais municípios:', municipios_disponiveis, placeholder="Deixe em branco para ver todos")
            if municipios_selecionados:
                df_filtrado_final = df_filtrado_final[df_filtrado_final['nome_municipio'].isin(municipios_selecionados)]
        
        # --- EXIBIÇÃO PRINCIPAL ---
        st.header("Análise de Dados Filtrados")
        
        kpi1, kpi2, kpi3 = st.columns(3)
        valor_total = df_filtrado_final['vl_total'].sum()
        qtd_total = df_filtrado_final['qtd_total'].sum()
        num_registros = len(df_filtrado_final)
        kpi1.metric("Valor Total (R$)", f"{valor_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        kpi2.metric("Quantidade Total", f"{qtd_total:,.0f}")
        kpi3.metric("Nº de Registros", f"{num_registros:,}")
        
        st.dataframe(df_filtrado_final.head(200))
        st.caption(f"Mostrando uma prévia de 200 de {len(df_filtrado_final)} linhas.")
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            tab1, tab2, tab3 = st.tabs(["Por Município (Valor)", "Por Município (Qtd)", "Maiores Registros"])
            with tab1:
                st.subheader("Top 15 Municípios por Valor Total")
                soma_por_municipio = df_filtrado_final.groupby('nome_municipio')['vl_total'].sum().sort_values(ascending=False).head(15)
                st.bar_chart(soma_por_municipio)
            with tab2:
                st.subheader("Top 15 Municípios por Quantidade de Registros")
                contagem_municipios = df_filtrado_final['nome_municipio'].value_counts().head(15)
                st.bar_chart(contagem_municipios)
            with tab3:
                st.subheader("Top 10 Registros Individuais")
                colunas_necessarias = ['nome_municipio', 'ano_aih', 'mes_aih', 'qtd_total', 'vl_total']
                if all(coluna in df_filtrado_final.columns for coluna in colunas_necessarias):
                    st.write("**Maiores Registros por Valor Total (R$)**")
                    df_top_valor = df_filtrado_final.sort_values(by="vl_total", ascending=False).head(10)
                    st.dataframe(df_top_valor[colunas_necessarias])
                    st.write("**Maiores Registros por Quantidade Total**")
                    df_top_qtd = df_filtrado_final.sort_values(by="qtd_total", ascending=False).head(10)
                    st.dataframe(df_top_qtd[colunas_necessarias])
        with col2:
            st.header("Estatísticas Descritivas")
            st.write(df_filtrado_final.describe())
            st.write("---")
            st.subheader("Correlação: Quantidade vs. Valor Total")
            if not df_filtrado_final.empty:
                df_scatter = df_filtrado_final.sample(min(len(df_filtrado_final), 2000))
                st.caption(f"Gráfico de dispersão gerado com uma amostra de {len(df_scatter)} pontos.")
                fig_scatter = px.scatter(df_scatter, x="qtd_total", y="vl_total", hover_name="nome_municipio")
                st.plotly_chart(fig_scatter, use_container_width=True)
                
        # Gráfico de Tendência no final
        st.markdown("---")
        st.header("Análise de Tendência Temporal")
        if not df_filtrado_final.empty:
            df_tendencia = df_filtrado_final.copy()
            df_tendencia['data'] = pd.to_datetime(dict(year=df_tendencia['ano_aih'], month=df_tendencia['mes_aih'], day=1))
            soma_mensal = df_tendencia.groupby('data')['vl_total'].sum()
            st.line_chart(soma_mensal, height=400)
            
        # MAPA OTIMIZADO POR ESTADO COM ESCALA AJUSTADA
        st.markdown("---")
        st.header("Mapa de Valor Total por Estado")

        if 'lat' in df_filtrado_final.columns and 'UF' in df_filtrado_final.columns and 'capital' in df_filtrado_final.columns:
            dados_por_estado = df_filtrado_final.groupby('UF')['vl_total'].sum().reset_index()
            capitais_geo = df_geo[df_geo['capital'] == 1]
            dados_mapa_estado = pd.merge(dados_por_estado, capitais_geo, on='UF', how='left')
            dados_mapa_estado.dropna(subset=['lat', 'lon'], inplace=True)
            
            if not dados_mapa_estado.empty:
                valor_maximo = dados_mapa_estado['vl_total'].max()
                raio_minimo_em_metros = 20000
                raio_maximo_em_metros = 300000
                
                if valor_maximo > 0:
                    dados_mapa_estado['raio_proporcional'] = (dados_mapa_estado['vl_total'] / valor_maximo) * (raio_maximo_em_metros - raio_minimo_em_metros)
                    dados_mapa_estado['raio_bolha'] = raio_minimo_em_metros + dados_mapa_estado['raio_proporcional']
                else:
                    dados_mapa_estado['raio_bolha'] = raio_minimo_em_metros

                st.map(
                    dados_mapa_estado,
                    size='raio_bolha',
                    color='#FF4B4B88',
                    zoom=3
                )
            else:
                st.warning("Não há dados para exibir no mapa com os filtros atuais.")
        else:
            st.info("O mapa não pode ser exibido. Verifique se as colunas 'lat', 'UF' e 'capital' foram carregadas.")

    else:
        st.warning("A consulta ao banco não retornou dados.")
else:
    st.error("A conexão com o banco de dados falhou.")