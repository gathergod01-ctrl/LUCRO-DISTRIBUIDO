import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gestão de Lucros - Gabriel", layout="wide", page_icon="💰")

# --- CONEXÃO COM GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(worksheet_name):
    try:
        df = conn.read(worksheet=worksheet_name, ttl=0)
        # Limpeza de nomes de colunas (removendo caracteres das imagens anteriores)
        df.columns = df.columns.str.replace(':', '').str.replace(',', '').str.strip()
        return df
    except:
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
    t_login, t_cad = st.tabs(["Acessar", "Novo Cadastro"])

    with t_login:
        u_in = st.text_input("Usuário (CPF ou GABRIEL)")
        p_in = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            if u_in.upper() == "GABRIEL" and p_in == "@Lopes2019":
                st.session_state.update({'logado': True, 'user_type': 'admin'})
                st.rerun()
            else:
                df_u = get_data("usuarios")
                if not df_u.empty:
                    df_u['cpf'] = df_u['cpf'].astype(str)
                    df_u['senha'] = df_u['senha'].astype(str)
                    user = df_u[(df_u['cpf'] == u_in) & (df_u['senha'] == p_in)]
                    if not user.empty:
                        st.session_state.update({'logado': True, 'user_type': 'socio', 'user_cpf': u_in})
                        st.rerun()
                st.error("Credenciais inválidas.")

    with t_cad:
        with st.form("form_cad"):
            n = st.text_input("Nome")
            c = st.text_input("CPF")
            e = st.text_input("Empresa")
            cj = st.text_input("CNPJ")
            s = st.text_input("Senha", type="password")
            if st.form_submit_button("Cadastrar Sócio"):
                df_u = get_data("usuarios")
                # Garante que as colunas existam antes de concatenar
                new_row = pd.DataFrame([{"nome": n, "cpf": str(c), "empresa": e, "cnpj": cj, "senha": str(s), "tipo": "socio"}])
                df_updated = pd.concat([df_u, new_row], ignore_index=True)
                # O método update precisa encontrar as colunas exatas
                conn.update(worksheet="usuarios", data=df_updated)
                st.success("Cadastrado com sucesso! Volte para a aba de login.")

elif st.session_state.user_type == "admin":
    st.sidebar.button("Sair", on_click=lambda: st.session_state.update({'logado': False}))
    st.header("📊 Painel ADM - Gabriel")
    
    df_l = get_data("lancamentos")
    df_u = get_data("usuarios")
    
    if not df_l.empty and not df_u.empty:
        df_l['cpf_socio'] = df_l['cpf_socio'].astype(str)
        df_u['cpf'] = df_u['cpf'].astype(str)
        df_res = df_l.merge(df_u, left_on='cpf_socio', right_on='cpf')
        st.dataframe(df_res[['nome', 'empresa', 'data', 'valor', 'banco']], use_container_width=True)
        st.metric("Total Acumulado", f"R$ {df_res['valor'].sum():,.2f}")
    else:
        st.info("Aguardando lançamentos.")

else:
    # --- ÁREA DO SÓCIO ---
    st.sidebar.button("Sair", on_click=lambda: st.session_state.update({'logado': False}))
    st.header("💸 Registrar Retirada")
    df_b = get_data("bancos")
    
    with st.form("form_ret"):
        dt = st.date_input("Data", datetime.now())
        vl = st.number_input("Valor", min_value=0.0)
        b_list = ["Novo..."] + list(df_b['nome_banco'].unique()) if not df_b.empty else ["Novo..."]
        b_sel = st.selectbox("Banco PJ", b_list)
        b_new = st.text_input("Se novo, qual?")
        
        if st.form_submit_button("Lançar"):
            final_b = b_new.upper() if b_sel == "Novo..." else b_sel
            # Salvar novo banco
            if b_sel == "Novo..." and b_new:
                new_b_df = pd.DataFrame([{"nome_banco": final_b}])
                conn.update(worksheet="bancos", data=pd.concat([df_b, new_b_df]).drop_duplicates())
            
            # Salvar lançamento
            df_l = get_data("lancamentos")
            new_l_df = pd.DataFrame([{"cpf_socio": str(st.session_state.user_cpf), "data": dt.strftime("%d/%m/%Y"), "valor": vl, "banco": final_b}])
            conn.update(worksheet="lancamentos", data=pd.concat([df_l, new_l_df], ignore_index=True))
            st.success("Lançamento realizado!")
