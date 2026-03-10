import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gestão de Lucros - Gabriel", layout="wide", page_icon="💰")

DB_FILE = "dados_sistema.db"
BANCOS_PADRAO = ["001 - BANCO DO BRASIL", "033 - SANTANDER", "104 - CAIXA ECONOMICA", "237 - BRADESCO", "341 - ITAU", "077 - INTER", "260 - NUBANK", "336 - C6 BANK", "OUTRO"]

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS usuarios (nome TEXT, cpf TEXT PRIMARY KEY, empresa TEXT, cnpj TEXT, senha TEXT, tipo TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS lancamentos (id INTEGER PRIMARY KEY AUTOINCREMENT, cpf_socio TEXT, data TEXT, valor REAL, banco TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS bancos_custom (nome_banco TEXT PRIMARY KEY)')
        conn.commit()

init_db()

def run_query(query, params=(), fetch=False):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        if fetch: return cursor.fetchall()
        conn.commit()

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
                else: st.error("Credenciais inválidas.")
    with t_cad:
        with st.form("cad"):
            n, c = st.columns(2)
            nome = n.text_input("Nome")
            cpf = c.text_input("CPF")
            emp = n.text_input("Empresa")
            cnpj = c.text_input("CNPJ")
            pw = st.text_input("Senha", type="password")
            if st.form_submit_button("Cadastrar"):
                try:
                    run_query("INSERT INTO usuarios VALUES (?,?,?,?,?,?)", (nome, cpf, emp, cnpj, pw, 'socio'))
                    st.success("Cadastrado!")
                except: st.error("CPF já existe.")

elif st.session_state.user_type == "admin":
    st.sidebar.button("Sair", on_click=lambda: st.session_state.update({'logado': False}))
    st.header("📊 Painel Administrativo")
    
    t_relatorio, t_bancos = st.tabs(["Relatório Consolidado", "Gerenciar Bancos"])
    
    with t_relatorio:
        df_adm = pd.read_sql_query("SELECT u.cpf, u.cnpj, u.nome, u.empresa, l.data, l.valor, l.banco FROM lancamentos l JOIN usuarios u ON l.cpf_socio = u.cpf", sqlite3.connect(DB_FILE))
        if not df_adm.empty:
            df_adm['data'] = pd.to_datetime(df_adm['data']).dt.date
            with st.expander("🔍 Filtros Avançados", expanded=True):
                c1, c2, c3 = st.columns(3)
                f_cpf = c1.text_input("CPF")
                f_cnpj = c2.text_input("CNPJ")
                periodo = c3.date_input("Filtrar Período", [date.today().replace(day=1), date.today()])
            
            if f_cpf: df_adm = df_adm[df_adm['cpf'].str.contains(f_cpf)]
            if f_cnpj: df_adm = df_adm[df_adm['cnpj'].str.contains(f_cnpj)]
            if len(periodo) == 2:
                df_adm = df_adm[(df_adm['data'] >= periodo[0]) & (df_adm['data'] <= periodo[1])]
            
            st.dataframe(df_adm, use_container_width=True)
            st.metric("Total Distribuído", f"R$ {df_adm['valor'].sum():,.2f}")
        else: st.info("Sem dados.")

    with t_bancos:
        st.subheader("Bancos Cadastrados pelos Sócios")
        b_cust = run_query("SELECT nome_banco FROM bancos_custom", fetch=True)
        if b_cust:
            for b in b_cust:
                col_b1, col_b2 = st.columns([3, 1])
                novo_nome = col_b1.text_input(f"Editar {b[0]}", b[0], key=f"edit_{b[0]}")
                if col_b2.button("Salvar", key=f"save_{b[0]}"):
                    run_query("UPDATE bancos_custom SET nome_banco=? WHERE nome_banco=?", (novo_nome.upper(), b[0]))
                    run_query("UPDATE lancamentos SET banco=? WHERE banco=?", (novo_nome.upper(), b[0]))
                    st.rerun()
                if col_b2.button("Excluir", key=f"del_{b[0]}"):
                    run_query("DELETE FROM bancos_custom WHERE nome_banco=?", (b[0],))
                    st.rerun()
        else: st.write("Nenhum banco personalizado cadastrado.")

else:
    # --- PAINEL DO SÓCIO ---
    st.sidebar.button("Sair", on_click=lambda: st.session_state.update({'logado': False}))
    st.header("💸 Lançamentos e Edição")
    
    t_novo, t_meus = st.tabs(["Novo Lançamento", "Meus Lançamentos (Editar)"])
    
    with t_novo:
        bancos_db = [b[0] for b in run_query("SELECT nome_banco FROM bancos_custom", fetch=True)]
        lista_bancos = sorted(list(set(BANCOS_PADRAO + bancos_db)))
        with st.form("novo_l"):
            d, v = st.columns(2)
            data_l = d.date_input("Data", date.today())
            valor_l = v.number_input("Valor", min_value=0.0)
            b_sel = st.selectbox("Banco", lista_bancos)
            b_txt = st.text_input("Se outro, qual?")
            if st.form_submit_button("Lançar"):
                final_b = b_txt.upper() if b_sel == "OUTRO" else b_sel
                if b_sel == "OUTRO": run_query("INSERT OR IGNORE INTO bancos_custom VALUES (?)", (final_b,))
                run_query("INSERT INTO lancamentos (cpf_socio, data, valor, banco) VALUES (?,?,?,?)", (st.session_state.user_cpf, data_l.isoformat(), valor_l, final_b))
                st.success("Sucesso!")
                st.rerun()

    with t_meus:
        df_my = pd.read_sql_query("SELECT id, data, valor, banco FROM lancamentos WHERE cpf_socio=?", sqlite3.connect(DB_FILE), params=(st.session_state.user_cpf,))
        if not df_my.empty:
            for _, row in df_my.iterrows():
                with st.expander(f"Lançamento: {row['data']} - R$ {row['valor']}"):
                    c1, c2, c3 = st.columns(3)
                    nova_dt = c1.date_input("Data", datetime.strptime(row['data'], '%Y-%m-%d'), key=f"dt_{row['id']}")
                    novo_vl = c2.number_input("Valor", value=row['valor'], key=f"vl_{row['id']}")
                    novo_bc = c3.text_input("Banco", value=row['banco'], key=f"bc_{row['id']}")
                    if st.button("Salvar Alteração", key=f"btn_{row['id']}"):
                        run_query("UPDATE lancamentos SET data=?, valor=?, banco=? WHERE id=?", (nova_dt.isoformat(), novo_vl, novo_bc.upper(), row['id']))
                        st.success("Atualizado!")
                        st.rerun()
                    if st.button("Excluir Lançamento", key=f"del_l_{row['id']}"):
                        run_query("DELETE FROM lancamentos WHERE id=?", (row['id'],))
                        st.rerun()
        else: st.info("Nenhum lançamento.")
