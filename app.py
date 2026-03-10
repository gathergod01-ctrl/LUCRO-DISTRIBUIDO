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

def safe_parse_date(date_str):
    if not date_str: return date.today()
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%Y/%m/%d'):
        try:
            return datetime.strptime(str(date_str), fmt).date()
        except (ValueError, TypeError):
            continue
    return date.today()

if 'logado' not in st.session_state:
    st.session_state.update({'logado': False, 'user_type': None, 'user_cpf': None})

# --- INTERFACE DE ACESSO ---
if not st.session_state.logado:
    st.title("🏦 Sistema de Distribuição de Lucros")
    t_login, t_cad = st.tabs(["Acessar", "Novo Cadastro"])
    
    with t_login:
        u_in = st.text_input("Usuário")
        p_in = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            # Lógica Automática para o ADM Gabriel
            if u_in == "GABRIEL" and p_in == "@Lopes2019":
                st.session_state.update({'logado': True, 'user_type': 'admin', 'user_cpf': 'ADM'})
                st.rerun()
            else:
                user = run_query("SELECT tipo, cpf FROM usuarios WHERE cpf=? AND senha=?", (u_in, p_in), fetch=True)
                if user:
                    st.session_state.update({'logado': True, 'user_type': user[0][0], 'user_cpf': user[0][1]})
                    st.rerun()
                else: st.error("Usuário ou senha inválidos.")
    
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
                except: st.error("Erro: CPF já cadastrado.")

elif st.session_state.user_type == "admin":
    # --- PAINEL GABRIEL (ADM) ---
    st.sidebar.button("Sair", on_click=lambda: st.session_state.update({'logado': False}))
    st.header("📊 Painel Administrativo - Visão Geral")
    
    df_adm = pd.read_sql_query("""
        SELECT u.cpf, u.cnpj, u.nome, u.empresa, l.data, l.valor, l.banco 
        FROM lancamentos l JOIN usuarios u ON l.cpf_socio = u.cpf
    """, sqlite3.connect(DB_FILE))
    
    if not df_adm.empty:
        df_adm['data_obj'] = df_adm['data'].apply(safe_parse_date)
        
        with st.expander("🔍 Filtros de Relatório", expanded=True):
            c1, c2, c3 = st.columns(3)
            f_cpf = c1.text_input("Filtrar CPF")
            f_cnpj = c2.text_input("Filtrar CNPJ")
            periodo = c3.date_input("Período", [date.today().replace(day=1), date.today()])

        if f_cpf: df_adm = df_adm[df_adm['cpf'].astype(str).str.contains(f_cpf)]
        if f_cnpj: df_adm = df_adm[df_adm['cnpj'].astype(str).str.contains(f_cnpj)]
        if len(periodo) == 2:
            df_adm = df_adm[(df_adm['data_obj'] >= periodo[0]) & (df_adm['data_obj'] <= periodo[1])]

        st.dataframe(df_adm[['cpf', 'cnpj', 'nome', 'empresa', 'data', 'valor', 'banco']], use_container_width=True)
        
        col_res1, col_res2 = st.columns([2, 1])
        col_res1.metric("Total Distribuído no Período", f"R$ {df_adm['valor'].sum():,.2f}")
        
        # --- BOTÃO DE EXPORTAÇÃO CSV ---
        csv = df_adm[['cpf', 'cnpj', 'nome', 'empresa', 'data', 'valor', 'banco']].to_csv(index=False).encode('utf-8')
        col_res2.download_button(
            label="📥 Exportar Relatório (CSV)",
            data=csv,
            file_name=f"relatorio_lucros_{date.today()}.csv",
            mime='text/csv',
        )
    else: st.info("Nenhum dado encontrado.")

else:
    # --- PAINEL DO SÓCIO ---
    st.sidebar.button("Sair", on_click=lambda: st.session_state.update({'logado': False}))
    st.header("💸 Central do Sócio")
    
    tab_novo, tab_filtro, tab_edicao = st.tabs(["Novo Lançamento", "🔍 Consultar por Período", "⚙️ Editar/Excluir"])
    
    with tab_novo:
        bancos_db = [b[0] for b in run_query("SELECT nome_banco FROM bancos_custom", fetch=True)]
        lista_bancos = sorted(list(set(BANCOS_PADRAO + bancos_db)))
        with st.form("form_novo", clear_on_submit=True):
            col1, col2 = st.columns(2)
            data_l = col1.date_input("Data", date.today())
            valor_l = col2.number_input("Valor", min_value=0.0)
            b_sel = st.selectbox("Banco", lista_bancos)
            b_txt = st.text_input("Novo Banco?")
            if st.form_submit_button("Registrar"):
                final_b = b_txt.upper() if b_sel == "OUTRO" else b_sel
                if b_sel == "OUTRO": run_query("INSERT OR IGNORE INTO bancos_custom VALUES (?)", (final_b,))
                run_query("INSERT INTO lancamentos (cpf_socio, data, valor, banco) VALUES (?,?,?,?)", 
                          (st.session_state.user_cpf, data_l.strftime('%d/%m/%Y'), valor_l, final_b))
                st.success("Lançado!")
                st.rerun()

    with tab_filtro:
        df_f = pd.read_sql_query("SELECT data, valor, banco FROM lancamentos WHERE cpf_socio=?", 
                                 sqlite3.connect(DB_FILE), params=(st.session_state.user_cpf,))
        if not df_f.empty:
            df_f['data_obj'] = df_f['data'].apply(safe_parse_date)
            p_socio = st.date_input("Intervalo", [date.today().replace(day=1), date.today()], key="p_socio")
            if len(p_socio) == 2:
                df_filtrado = df_f[(df_f['data_obj'] >= p_socio[0]) & (df_f['data_obj'] <= p_socio[1])]
                st.metric("Total no Período", f"R$ {df_filtrado['valor'].sum():,.2f}")
                st.table(df_filtrado[['data', 'valor', 'banco']])
        else: st.info("Sem lançamentos.")

    with tab_edicao:
        df_edit = pd.read_sql_query("SELECT id, data, valor, banco FROM lancamentos WHERE cpf_socio=?", 
                                    sqlite3.connect(DB_FILE), params=(st.session_state.user_cpf,))
        for _, row in df_edit.iterrows():
            with st.expander(f"Lançamento: {row['data']} - R$ {row['valor']}"):
                c1, c2, c3 = st.columns(3)
                n_dt = c1.date_input("Data", safe_parse_date(row['data']), key=f"e_dt_{row['id']}")
                n_vl = c2.number_input("Valor", value=float(row['valor']), key=f"e_vl_{row['id']}")
                n_bc = c3.text_input("Banco", value=str(row['banco']), key=f"e_bc_{row['id']}")
                if st.button("Salvar", key=f"s_{row['id']}"):
                    run_query("UPDATE lancamentos SET data=?, valor=?, banco=? WHERE id=?", 
                              (n_dt.strftime('%d/%m/%Y'), n_vl, n_bc.upper(), row['id']))
                    st.rerun()
                if st.button("Excluir", key=f"d_{row['id']}"):
                    run_query("DELETE FROM lancamentos WHERE id=?", (row['id'],))
                    st.rerun()
