import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gestão de Lucros - Gabriel", layout="wide", page_icon="💰")

# --- CONEXÃO COM GOOGLE SHEETS ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("Erro nos Secrets do Streamlit. Verifique a URL da planilha.")
    st.stop()

def get_data(worksheet_name):
    try:
        # ttl=0 força o Streamlit a buscar dados novos sempre
        df = conn.read(worksheet=worksheet_name, ttl=0)
        # Limpa espaços em branco nos nomes das colunas caso existam
        df.columns = df.columns.str.replace(':', '').str.replace(',', '').str.strip()
        return df
    except Exception:
        cols = {
            "usuarios": ["nome", "cpf", "empresa", "cnpj", "senha", "tipo"],
            "lancamentos": ["cpf_socio", "data", "valor", "banco"],
            "bancos": ["nome_banco"]
        }
        return pd.DataFrame(columns=cols.get(worksheet_name, []))

# --- LÓGICA DE SESSÃO ---
if 'logado' not in st.session_state:
    st.session_state.update({'logado': False, 'user_type': None, 'user_cpf': None})

# --- INTERFACE ---
if not st.session_state.logado:
    st.title("🏦 Sistema de Distribuição de Lucros")
    tab_login, tab_cad = st.tabs(["Acessar", "Novo Cadastro"])

    with tab_login:
        user_in = st.text_input("Usuário (CPF ou GABRIEL)")
        pass_in = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            if user_in.upper() == "GABRIEL" and pass_in == "@Lopes2019":
                st.session_state.update({'logado': True, 'user_type': 'admin'})
                st.rerun()
            else:
                df_u = get_data("usuarios")
                if not df_u.empty:
                    df_u['cpf'] = df_u['cpf'].astype(str)
                    df_u['senha'] = df_u['senha'].astype(str)
                    user = df_u[(df_u['cpf'] == user_in) & (df_u['senha'] == pass_in)]
                    if not user.empty:
                        st.session_state.update({'logado': True, 'user_type': 'socio', 'user_cpf': user_in})
                        st.rerun()
                st.error("Credenciais inválidas.")

    with tab_cad:
        with st.form("cad"):
            n = st.text_input("Nome")
            c = st.text_input("CPF")
            e = st.text_input("Empresa")
            cj = st.text_input("CNPJ")
            s = st.text_input("Senha", type="password")
            if st.form_submit_button("Finalizar"):
                df_u = get_data("usuarios")
                new_u = pd.DataFrame([{"nome": n, "cpf": str(c), "empresa": e, "cnpj": cj, "senha": str(s), "tipo": "socio"}])
                conn.update(worksheet="usuarios", data=pd.concat([df_u, new_u], ignore_index=True))
                st.success("Cadastrado!")

elif st.session_state.user_type == "admin":
    st.sidebar.button("Sair", on_click=lambda: st.session_state.update({'logado': False}))
    st.header("📊 Painel ADM")
    df_l = get_data("lancamentos")
    df_u = get_data("usuarios")
    if not df_l.empty and not df_u.empty:
        df_l['cpf_socio'] = df_l['cpf_socio'].astype(str)
        df_u['cpf'] = df_u['cpf'].astype(str)
        df_res = df_l.merge(df_u, left_on='cpf_socio', right_on='cpf')
        st.dataframe(df_res[['nome', 'empresa', 'data', 'valor', 'banco']], use_container_width=True)
        st.metric("Total Acumulado", f"R$ {df_res['valor'].sum():,.2f}")
    
    st.divider()
    st.subheader("🔐 Resetar Senha")
    if not df_u.empty:
        u_sel = st.selectbox("Sócio:", df_u['nome'].unique())
        if st.button("Resetar"):
            df_u.loc[df_u['nome'] == u_sel, 'senha'] = "abcd1234"
            conn.update(worksheet="usuarios", data=df_u)
            st.success("Senha resetada para abcd1234")

else:
    st.sidebar.button("Sair", on_click=lambda: st.session_state.update({'logado': False}))
    st.header("💸 Lançar Retirada")
    df_b = get_data("bancos")
    with st.form("ret"):
        data_v = st.date_input("Data", datetime.now())
        valor_v = st.number_input("Valor", min_value=0.0)
        b_sel = st.selectbox("Banco PJ", ["Novo..."] + list(df_b['nome_banco'].unique()))
        b_novo = st.text_input("Se novo, qual?")
        if st.form_submit_button("Lançar"):
            b_final = b_novo.upper() if b_sel == "Novo..." else b_sel
            if b_sel == "Novo...":
                new_b = pd.DataFrame([{"nome_banco": b_final}])
                conn.update(worksheet="bancos", data=pd.concat([df_b, new_b]).drop_duplicates())
            df_l = get_data("lancamentos")
            new_l = pd.DataFrame([{"cpf_socio": st.session_state.user_cpf, "data": data_v.strftime("%d/%m/%Y"), "valor": valor_v, "banco": b_final}])
            conn.update(worksheet="lancamentos", data=pd.concat([df_l, new_l], ignore_index=True))
            st.success("Lançado com sucesso!")
