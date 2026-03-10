import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gestão de Lucros - Gabriel", layout="wide", page_icon="💰")

# Customização de Layout (CSS)
st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .stButton>button { width: 100%; border-radius: 8px; background-color: #0047AB; color: white; font-weight: bold; }
    h1 { color: #0047AB; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO COM GOOGLE SHEETS ---
# Certifique-se de configurar o arquivo .streamlit/secrets.toml com a URL da sua planilha
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(worksheet):
    return conn.read(worksheet=worksheet, ttl=0)

# --- LÓGICA DE SESSÃO ---
if 'logado' not in st.session_state:
    st.session_state.logado = False
    st.session_state.user_type = None
    st.session_state.user_cpf = None

# --- TELAS ---

if not st.session_state.logado:
    st.title("🏦 Sistema de Distribuição de Lucros")
    tab_login, tab_cad = st.tabs(["Acessar Sistema", "Novo Cadastro de Sócio"])

    with tab_login:
        user_input = st.text_input("Usuário (CPF ou Nome ADM)")
        pass_input = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            # Verificação ADM (Gabriel Lopes)
            if user_input.upper() == "GABRIEL" and pass_input == "@Lopes2019":
                st.session_state.logado = True
                st.session_state.user_type = "admin"
                st.rerun()
            else:
                # Busca na aba de usuários da planilha
                df_users = get_data("usuarios")
                user = df_users[(df_users['cpf'] == user_input) & (df_users['senha'] == pass_input)]
                if not user.empty:
                    st.session_state.logado = True
                    st.session_state.user_type = "socio"
                    st.session_state.user_cpf = user_input
                    st.rerun()
                else:
                    st.error("Credenciais inválidas.")

    with tab_cad:
        st.subheader("📝 Cadastro de Novo Sócio")
        with st.form("form_cadastro"):
            c1, c2 = st.columns(2)
            nome = c1.text_input("Nome Completo")
            cpf = c2.text_input("CPF")
            emp = c1.text_input("Razão Social")
            cnpj = c2.text_input("CNPJ")
            senha_cad = st.text_input("Senha", type="password")
            
            if st.form_submit_button("Finalizar Cadastro"):
                df_users = get_data("usuarios")
                if cpf in df_users['cpf'].values:
                    st.error("CPF já cadastrado.")
                else:
                    new_user = pd.DataFrame([{"nome": nome, "cpf": cpf, "empresa": emp, "cnpj": cnpj, "senha": senha_cad, "tipo": "socio"}])
                    updated_users = pd.concat([df_users, new_user], ignore_index=True)
                    conn.update(worksheet="usuarios", data=updated_users)
                    st.success("Cadastrado! Faça login.")

elif st.session_state.user_type == "admin":
    st.sidebar.title("Painel ADM")
    st.sidebar.write("Olá, **Gabriel**")
    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    st.header("📊 Relatório de Retiradas")
    df_lanc = get_data("lancamentos")
    df_users = get_data("usuarios")
    
    # Cruzamento de dados para o relatório do Gabriel
    if not df_lanc.empty:
        df_final = df_lanc.merge(df_users, left_on='cpf_socio', right_on='cpf')
        st.dataframe(df_final[['nome', 'empresa', 'data', 'valor', 'banco']], use_container_width=True)
        st.metric("Total Distribuído", f"R$ {df_final['valor'].sum():,.2f}")
        
        st.divider()
        st.subheader("🔐 Resetar Senha")
        user_sel = st.selectbox("Sócio:", df_users['nome'].unique())
        if st.button("Resetar para 'abcd1234'"):
            df_users.loc[df_users['nome'] == user_sel, 'senha'] = "abcd1234"
            conn.update(worksheet="usuarios", data=df_users)
            st.success("Senha resetada!")
    else:
        st.info("Nenhum lançamento encontrado.")

else:
    # --- ÁREA DO SÓCIO ---
    st.sidebar.write(f"Sócio: {st.session_state.user_cpf}")
    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    st.header("💸 Lançar Retirada")
    df_bancos = get_data("bancos")
    
    with st.form("form_retirada"):
        data_ret = st.date_input("Data", datetime.now())
        valor_ret = st.number_input("Valor (R$)", min_value=0.0)
        banco_sel = st.selectbox("Banco PJ:", ["Novo..."] + list(df_bancos['nome_banco'].unique()))
        novo_banco = st.text_input("Se novo, qual?")
        
        if st.form_submit_button("Registrar"):
            b_final = novo_banco.upper() if banco_sel == "Novo..." else banco_sel
            
            # Atualiza lista de bancos se for novo
            if banco_sel == "Novo..." and novo_banco:
                new_b = pd.DataFrame([{"nome_banco": b_final}])
                conn.update(worksheet="bancos", data=pd.concat([df_bancos, new_b]))

            # Salva o lançamento
            df_lanc = get_data("lancamentos")
            new_l = pd.DataFrame([{"cpf_socio": st.session_state.user_cpf, "data": data_ret.strftime("%d/%m/%Y"), "valor": valor_ret, "banco": b_final}])
            conn.update(worksheet="lancamentos", data=pd.concat([df_lanc, new_l]))
            st.success("Lançamento concluído!")
