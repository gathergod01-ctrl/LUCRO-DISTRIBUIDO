import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gestão de Lucros - Gabriel", layout="wide", page_icon="💰")

DB_FILE = "dados_sistema.db"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS usuarios 
                     (nome TEXT, cpf TEXT PRIMARY KEY, empresa TEXT, cnpj TEXT, senha TEXT, tipo TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS lancamentos 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, cpf_socio TEXT, data TEXT, valor REAL, banco TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS bancos (nome_banco TEXT PRIMARY KEY)''')
        conn.commit()

init_db()

def run_query(query, params=(), fetch=False):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        if fetch: return cursor.fetchall()
        conn.commit()

# --- LÓGICA DE SESSÃO ---
if 'logado' not in st.session_state:
    st.session_state.update({'logado': False, 'user_type': None, 'user_cpf': None})

# --- TELAS ---
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
                user = run_query("SELECT tipo, cpf FROM usuarios WHERE cpf=? AND senha=?", (u_in, p_in), fetch=True)
                if user:
                    st.session_state.update({'logado': True, 'user_type': user[0][0], 'user_cpf': user[0][1]})
                    st.rerun()
                else:
                    st.error("Usuário ou senha inválidos.")

    with t_cad:
        with st.form("form_cad"):
            n = st.text_input("Nome")
            c = st.text_input("CPF")
            e = st.text_input("Razão Social")
            cj = st.text_input("CNPJ")
            s = st.text_input("Senha", type="password")
            if st.form_submit_button("Finalizar Cadastro"):
                try:
                    run_query("INSERT INTO usuarios VALUES (?,?,?,?,?,?)", (n, c, e, cj, s, 'socio'))
                    st.success("Cadastrado! Vá para a aba de Login.")
                except: st.error("Erro: CPF já cadastrado.")

elif st.session_state.user_type == "admin":
    # --- ÁREA ADM (GABRIEL) ---
    st.sidebar.button("Sair", on_click=lambda: st.session_state.update({'logado': False}))
    st.header("📊 Painel Geral de Retiradas")
    
    query_adm = """
        SELECT u.cpf, u.cnpj, u.nome, u.empresa, l.data, l.valor, l.banco 
        FROM lancamentos l 
        JOIN usuarios u ON l.cpf_socio = u.cpf
    """
    df_adm = pd.read_sql_query(query_adm, sqlite3.connect(DB_FILE))
    
    if not df_adm.empty:
        # Tratamento robusto de datas para evitar o ValueError
        df_adm['data'] = pd.to_datetime(df_adm['data'], errors='coerce').dt.date
        df_adm = df_adm.dropna(subset=['data']) # Remove registros com data inválida

        with st.expander("🔍 Filtros de Relatório", expanded=True):
            col1, col2, col3 = st.columns(3)
            f_cpf = col1.text_input("Filtrar por CPF")
            f_cnpj = col2.text_input("Filtrar por CNPJ")
            periodo = col3.date_input("Período", [date.today().replace(day=1), date.today()])

        # Aplicação dos Filtros
        if f_cpf: df_adm = df_adm[df_adm['cpf'].astype(str).str.contains(f_cpf)]
        if f_cnpj: df_adm = df_adm[df_adm['cnpj'].astype(str).str.contains(f_cnpj)]
        if len(periodo) == 2:
            df_adm = df_adm[(df_adm['data'] >= periodo[0]) & (df_adm['data'] <= periodo[1])]

        st.dataframe(df_adm, use_container_width=True)
        st.metric("Total Distribuído no Período", f"R$ {df_adm['valor'].sum():,.2f}")
    else:
        st.info("Nenhum lançamento registrado.")

else:
    # --- ÁREA DO SÓCIO ---
    st.sidebar.button("Sair", on_click=lambda: st.session_state.update({'logado': False}))
    st.header("💸 Lançar Retirada")
    
    bancos_db = run_query("SELECT nome_banco FROM bancos", fetch=True)
    lista_bancos = ["Novo..."] + [b[0] for b in bancos_db]
    
    with st.form("form_ret", clear_on_submit=True):
        c1, c2 = st.columns(2)
        dt = c1.date_input("Data do Recebimento", date.today())
        vl = c2.number_input("Valor (R$)", min_value=0.0)
        b_sel = c1.selectbox("Banco PJ de Origem", lista_bancos)
        b_new = c2.text_input("Se novo, digite o nome")
        
        if st.form_submit_button("Registrar Retirada"):
            final_b = b_new.upper() if b_sel == "Novo..." else b_sel
            if final_b and vl > 0:
                if b_sel == "Novo...":
                    try: run_query("INSERT INTO bancos VALUES (?)", (final_b,))
                    except: pass
                
                # Salva no formato ISO para facilitar filtros (YYYY-MM-DD)
                run_query("INSERT INTO lancamentos (cpf_socio, data, valor, banco) VALUES (?,?,?,?)",
                          (st.session_state.user_cpf, dt.strftime('%Y-%m-%d'), vl, final_b))
                st.success("Lançamento realizado!")
                st.rerun()

    st.divider()
    st.subheader("📜 Meu Histórico de Retiradas")
    query_socio = "SELECT data, valor, banco FROM lancamentos WHERE cpf_socio=? ORDER BY data DESC"
    df_socio = pd.read_sql_query(query_socio, sqlite3.connect(DB_FILE), params=(st.session_state.user_cpf,))
    
    if not df_socio.empty:
        # Tratamento seguro de exibição de data para o sócio
        df_socio['data'] = pd.to_datetime(df_socio['data'], errors='coerce').dt.strftime('%d/%m/%Y')
        st.table(df_socio)
        st.metric("Minha Retirada Total", f"R$ {df_socio['valor'].sum():,.2f}")
    else:
        st.info("Você ainda não possui lançamentos registrados.")
