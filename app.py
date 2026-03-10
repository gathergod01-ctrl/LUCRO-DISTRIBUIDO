import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gestão de Lucros - Gabriel", layout="wide", page_icon="💰")

# --- BANCO DE DADOS LOCAL (SIMPLES E DIRETO) ---
DB_FILE = "dados_sistema.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Tabela de Usuários
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios 
                 (nome TEXT, cpf TEXT PRIMARY KEY, empresa TEXT, cnpj TEXT, senha TEXT, tipo TEXT)''')
    # Tabela de Lançamentos
    c.execute('''CREATE TABLE IF NOT EXISTS lancamentos 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, cpf_socio TEXT, data TEXT, valor REAL, banco TEXT)''')
    # Tabela de Bancos
    c.execute('''CREATE TABLE IF NOT EXISTS bancos (nome_banco TEXT PRIMARY KEY)''')
    conn.commit()
    conn.close()

init_db()

# --- FUNÇÕES DE ACESSO ---
def run_query(query, params=(), fetch=False):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        if fetch:
            return cursor.fetchall()
        conn.commit()

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
            e = st.text_input("Empresa")
            cj = st.text_input("CNPJ")
            s = st.text_input("Senha", type="password")
            if st.form_submit_button("Finalizar Cadastro"):
                try:
                    run_query("INSERT INTO usuarios VALUES (?,?,?,?,?,?)", (n, c, e, cj, s, 'socio'))
                    st.success("Cadastrado! Vá para a aba de Login.")
                except:
                    st.error("Erro: CPF já cadastrado.")

elif st.session_state.user_type == "admin":
    st.sidebar.button("Sair", on_click=lambda: st.session_state.update({'logado': False}))
    st.header("📊 Painel ADM - Gabriel")
    
    # Query de Relatório
    df_res = pd.read_sql_query("""
        SELECT u.nome, u.empresa, l.data, l.valor, l.banco 
        FROM lancamentos l JOIN usuarios u ON l.cpf_socio = u.cpf
    """, sqlite3.connect(DB_FILE))
    
    if not df_res.empty:
        st.dataframe(df_res, use_container_width=True)
        st.metric("Total Acumulado", f"R$ {df_res['valor'].sum():,.2f}")
    else:
        st.info("Nenhum lançamento registrado.")

    st.divider()
    st.subheader("🔐 Gestão de Sócios")
    df_u = pd.read_sql_query("SELECT nome, cpf FROM usuarios", sqlite3.connect(DB_FILE))
    if not df_u.empty:
        u_sel = st.selectbox("Sócio:", df_u['nome'].tolist())
        if st.button("Resetar Senha para abcd1234"):
            run_query("UPDATE usuarios SET senha='abcd1234' WHERE nome=?", (u_sel,))
            st.success(f"Senha de {u_sel} resetada!")

else:
    # --- ÁREA DO SÓCIO ---
    st.sidebar.button("Sair", on_click=lambda: st.session_state.update({'logado': False}))
    st.header("💸 Registrar Retirada")
    
    bancos_db = run_query("SELECT nome_banco FROM bancos", fetch=True)
    lista_bancos = ["Novo..."] + [b[0] for b in bancos_db]
    
    with st.form("form_ret"):
        dt = st.date_input("Data", datetime.now())
        vl = st.number_input("Valor", min_value=0.0)
        b_sel = st.selectbox("Banco PJ", lista_bancos)
        b_new = st.text_input("Se novo, qual?")
        
        if st.form_submit_button("Lançar"):
            final_b = b_new.upper() if b_sel == "Novo..." else b_sel
            if final_b and vl > 0:
                if b_sel == "Novo...":
                    try: run_query("INSERT INTO bancos VALUES (?)", (final_b,))
                    except: pass
                
                run_query("INSERT INTO lancamentos (cpf_socio, data, valor, banco) VALUES (?,?,?,?)",
                          (st.session_state.user_cpf, dt.strftime("%d/%m/%Y"), vl, final_b))
                st.success("Lançado com sucesso!")
