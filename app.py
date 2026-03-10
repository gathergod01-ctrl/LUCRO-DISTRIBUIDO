import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gestão de Lucros - Gabriel", layout="wide", page_icon="💰")

st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .stButton>button { width: 100%; border-radius: 8px; background-color: #0047AB; color: white; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO COM GOOGLE SHEETS ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("Erro ao conectar com o Google Sheets. Verifique os Secrets.")
    st.stop()

def get_data(worksheet_name):
    try:
        # ttl=0 evita cache para dados financeiros
        return conn.read(worksheet=worksheet_name, ttl=0)
    except Exception:
        # Cria dataframe vazio com colunas caso a aba não exista ou esteja inacessível
        cols = {
            "usuarios": ["nome", "cpf", "empresa", "cnpj", "senha", "tipo"],
            "lancamentos": ["cpf_socio", "data", "valor", "banco"],
            "bancos": ["nome_banco"]
        }
        return pd.DataFrame(columns=cols.get(worksheet_name, []))

# --- LÓGICA DE SESSÃO ---
if 'logado' not in st.session_state:
    st.session_state.logado = False
    st.session_state.user_type = None
    st.session_state.user_cpf = None

# --- TELAS ---

if not st.session_state.logado:
    st.title("🏦 Sistema de Distribuição de Lucros")
    tab_login, tab_cad = st.tabs(["Acessar", "Novo Sócio"])

    with tab_login:
        user_in = st.text_input("Usuário (CPF ou Nome ADM)")
        pass_in = st.text_input("Senha", type="password")
        
        if st.button("Entrar"):
            if user_in.upper() == "GABRIEL" and pass_in == "@Lopes2019":
                st.session_state.logado = True
                st.session_state.user_type = "admin"
                st.rerun()
            else:
                df_u = get_data("usuarios")
                if not df_u.empty:
                    # Garantindo que CPF e Senha sejam comparados como strings
                    df_u['cpf'] = df_u['cpf'].astype(str)
                    df_u['senha'] = df_u['senha'].astype(str)
                    user_match = df_u[(df_u['cpf'] == user_in) & (df_u['senha'] == pass_in)]
                    
                    if not user_match.empty:
                        st.session_state.logado = True
                        st.session_state.user_type = "socio"
                        st.session_state.user_cpf = user_in
                        st.rerun()
                    else:
                        st.error("Usuário ou senha inválidos.")

    with tab_cad:
        with st.form("cad"):
            c1, c2 = st.columns(2)
            n = c1.text_input("Nome")
            c = c2.text_input("CPF (Login)")
            e = c1.text_input("Empresa")
            cj = c2.text_input("CNPJ")
            s = st.text_input("Senha", type="password")
            if st.form_submit_button("Cadastrar"):
                df_u = get_data("usuarios")
                if c in df_u['cpf'].astype(str).values:
                    st.error("CPF já existe.")
                else:
                    new_u = pd.DataFrame([{"nome": n, "cpf": c, "empresa": e, "cnpj": cj, "senha": s, "tipo": "socio"}])
                    conn.update(worksheet="usuarios", data=pd.concat([df_u, new_u], ignore_index=True))
                    st.success("Cadastrado! Use a aba de login.")

elif st.session_state.user_type == "admin":
    # --- ÁREA ADM (GABRIEL) ---
    st.sidebar.button("Sair", on_click=lambda: st.session_state.update({"logado": False}))
    st.header("📊 Painel ADM - Gabriel")
    
    df_l = get_data("lancamentos")
    df_u = get_data("usuarios")
    
    if not df_l.empty and not df_u.empty:
        df_u['cpf'] = df_u['cpf'].astype(str)
        df_l['cpf_socio'] = df_l['cpf_socio'].astype(str)
        df_res = df_l.merge(df_u, left_on='cpf_socio', right_on='cpf')
        
        socio_f = st.multiselect("Filtrar Sócio", df_res['nome'].unique())
        if socio_f: df_res = df_res[df_res['nome'].isin(socio_f)]
        
        st.dataframe(df_res[['nome', 'empresa', 'data', 'valor', 'banco']], use_container_width=True)
        st.metric("Total GERAL", f"R$ {df_res['valor'].sum():,.2f}")
    else:
        st.info("Sem dados para exibir.")

    st.divider()
    st.subheader("🔧 Reset de Senha")
    if not df_u.empty:
        u_reset = st.selectbox("Sócio:", df_u['nome'].unique())
        if st.button("Resetar p/ abcd1234"):
            df_u.loc[df_u['nome'] == u_reset, 'senha'] = "abcd1234"
            conn.update(worksheet="usuarios", data=df_u)
            st.success("Senha resetada!")

else:
    # --- ÁREA DO SÓCIO ---
    st.sidebar.button("Sair", on_click=lambda: st.session_state.update({"logado": False}))
    st.header("💸 Lançar Retirada")
    
    df_b = get_data("bancos")
    with st.form("ret"):
        data_v = st.date_input("Data", datetime.now())
        valor_v = st.number_input("Valor", min_value=0.0)
        b_sel = st.selectbox("Banco PJ", ["Novo..."] + list(df_b['nome_banco'].unique()))
        b_novo = st.text_input("Qual o novo banco?")
        
        if st.form_submit_button("Lançar"):
            b_final = b_novo.upper() if b_sel == "Novo..." else b_sel
            if b_final and valor_v > 0:
                # Salvar banco se for novo
                if b_sel == "Novo...":
                    new_b = pd.DataFrame([{"nome_banco": b_final}])
                    conn.update(worksheet="bancos", data=pd.concat([df_b, new_b]).drop_duplicates())
                
                # Salvar lançamento
                df_l = get_data("lancamentos")
                new_l = pd.DataFrame([{"cpf_socio": st.session_state.user_cpf, "data": data_v.strftime("%d/%m/%Y"), "valor": valor_v, "banco": b_final}])
                conn.update(worksheet="lancamentos", data=pd.concat([df_l, new_l], ignore_index=True))
                st.success("Lançado!")
