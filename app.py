import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gestão de Lucros - Gabriel", layout="wide", page_icon="💰")

DB_FILE = "dados_sistema.db"
BANCOS_PADRAO = ["001 - BANCO DO BRASIL", "033 - SANTANDER", "104 - CAIXA ECONOMICA", "237 - BRADESCO", "341 - ITAU", "077 - INTER", "260 - NUBANK", "336 - C6 BANK"]

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
        try: return datetime.strptime(str(date_str), fmt).date()
        except: continue
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
    st.header("📊 Painel Administrativo")
    
    tab_rel, tab_bc = st.tabs(["Relatório Consolidado", "Gestão de Bancos"])
    
    with tab_rel:
        df_adm = pd.read_sql_query("SELECT u.cpf, u.cnpj, u.nome, u.empresa, l.data, l.valor, l.banco FROM lancamentos l JOIN usuarios u ON l.cpf_socio = u.cpf", sqlite3.connect(DB_FILE))
        if not df_adm.empty:
            df_adm['data_obj'] = df_adm['data'].apply(safe_parse_date)
            with st.expander("🔍 Filtros", expanded=True):
                c1, c2, c3 = st.columns(3)
                f_cpf = c1.text_input("CPF")
                f_cnpj = c2.text_input("CNPJ")
                periodo = c3.date_input("Período", [date.today().replace(day=1), date.today()])
            
            if f_cpf: df_adm = df_adm[df_adm['cpf'].astype(str).str.contains(f_cpf)]
            if f_cnpj: df_adm = df_adm[df_adm['cnpj'].astype(str).str.contains(f_cnpj)]
            if len(periodo) == 2:
                df_adm = df_adm[(df_adm['data_obj'] >= periodo[0]) & (df_adm['data_obj'] <= periodo[1])]
            
            st.dataframe(df_adm[['cpf', 'cnpj', 'nome', 'empresa', 'data', 'valor', 'banco']], use_container_width=True)
            
            c_res1, c_res2 = st.columns([2, 1])
            c_res1.metric("Total Distribuído", f"R$ {df_adm['valor'].sum():,.2f}")
            csv = df_adm.to_csv(index=False).encode('utf-8')
            c_res2.download_button("📥 Exportar CSV", csv, "relatorio.csv", "text/csv")
        else: st.info("Sem dados.")

    with tab_bc:
        st.subheader("Configuração de Bancos")
        nb = st.text_input("Novo banco: digite o nome do novo banco:")
        if st.button("➕ Adicionar Banco"):
            if nb:
                run_query("INSERT OR IGNORE INTO bancos_custom VALUES (?)", (nb.upper().strip(),))
                st.rerun()
        
        st.divider()
        b_c = [b[0] for b in run_query("SELECT nome_banco FROM bancos_custom", fetch=True)]
        if b_c:
            ex = st.selectbox("Excluir banco: selecione o nome:", ["Selecione..."] + b_c)
            if st.button("❌ Excluir Banco"):
                run_query("DELETE FROM bancos_custom WHERE nome_banco=?", (ex,))
                st.rerun()

else:
    # --- PAINEL DO SÓCIO ---
    st.sidebar.button("Sair", on_click=lambda: st.session_state.update({'logado': False}))
    st.header("💸 Área do Sócio")
    
    t_lan, t_banco, t_cons, t_edit = st.tabs(["Lançamento", "🏦 Cadastrar Banco", "🔍 Consultar", "⚙️ Editar"])
    
    # 1. ABA: CADASTRO DE BANCO (PRIMEIRO PASSO)
    with t_banco:
        st.subheader("Gestão de Bancos")
        col_nb1, col_nb2 = st.columns([3, 1])
        novo_b = col_nb1.text_input("Novo banco: digite o nome do novo banco:")
        if col_nb2.button("➕ Adicionar"):
            if novo_b:
                run_query("INSERT OR IGNORE INTO bancos_custom VALUES (?)", (novo_b.upper().strip(),))
                st.success("Banco cadastrado!")
                st.rerun()
        
        st.divider()
        lista_c = [b[0] for b in run_query("SELECT nome_banco FROM bancos_custom", fetch=True)]
        if lista_c:
            col_eb1, col_eb2 = st.columns([3, 1])
            excluir_b = col_eb1.selectbox("Excluir banco: selecione o nome:", ["Selecione..."] + lista_c)
            if col_eb2.button("❌ Excluir"):
                run_query("DELETE FROM bancos_custom WHERE nome_banco=?", (excluir_b,))
                st.rerun()

    # 2. ABA: LANÇAMENTO
    with t_lan:
        b_db = [b[0] for b in run_query("SELECT nome_banco FROM bancos_custom", fetch=True)]
        final_list = sorted(list(set(BANCOS_PADRAO + b_db)))
        
        with st.form("f_lan", clear_on_submit=True):
            c1, c2 = st.columns(2)
            d_l = c1.date_input("Data do Recebimento", date.today())
            v_l = c2.number_input("Valor (R$)", min_value=0.0)
            b_pg = st.selectbox("Banco que Efetuou o pagamento", final_list)
            if st.form_submit_button("Confirmar Lançamento"):
                if v_l > 0:
                    run_query("INSERT INTO lancamentos (cpf_socio, data, valor, banco) VALUES (?,?,?,?)", 
                              (st.session_state.user_cpf, d_l.strftime('%d/%m/%Y'), v_l, b_pg))
                    st.success("Registrado com sucesso!")
                else: st.warning("Informe um valor válido.")

    # 3. ABA: CONSULTA (SOMATÓRIO POR PERÍODO)
    with t_cons:
        df_c = pd.read_sql_query("SELECT data, valor, banco FROM lancamentos WHERE cpf_socio=?", 
                                 sqlite3.connect(DB_FILE), params=(st.session_state.user_cpf,))
        if not df_c.empty:
            df_c['data_obj'] = df_c['data'].apply(safe_parse_date)
            p_s = st.date_input("Filtrar período para somar:", [date.today().replace(day=1), date.today()])
            if len(p_s) == 2:
                df_fil = df_c[(df_c['data_obj'] >= p_s[0]) & (df_c['data_obj'] <= p_s[1])]
                st.metric("Total de Distribuições no Período", f"R$ {df_fil['valor'].sum():,.2f}")
                st.table(df_fil[['data', 'valor', 'banco']])

    # 4. ABA: EDIÇÃO/EXCLUSÃO
    with t_edit:
        df_e = pd.read_sql_query("SELECT id, data, valor, banco FROM lancamentos WHERE cpf_socio=?", 
                                 sqlite3.connect(DB_FILE), params=(st.session_state.user_cpf,))
        for _, r in df_e.iterrows():
            with st.expander(f"Registro {r['data']} - R$ {r['valor']}"):
                nc1, nc2, nc3 = st.columns(3)
                edt = nc1.date_input("Nova Data", safe_parse_date(r['data']), key=f"d{r['id']}")
                evl = nc2.number_input("Novo Valor", value=float(r['valor']), key=f"v{r['id']}")
                ebc = nc3.selectbox("Novo Banco", final_list, index=final_list.index(r['banco']) if r['banco'] in final_list else 0, key=f"b{r['id']}")
                if st.button("Salvar Alteração", key=f"s{r['id']}"):
                    run_query("UPDATE lancamentos SET data=?, valor=?, banco=? WHERE id=?", (edt.strftime('%d/%m/%Y'), evl, ebc, r['id']))
                    st.rerun()
                if st.button("Excluir Lançamento", key=f"x{r['id']}"):
                    run_query("DELETE FROM lancamentos WHERE id=?", (r['id'],))
                    st.rerun()
