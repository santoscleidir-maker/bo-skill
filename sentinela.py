import streamlit as st
import google.generativeai as genai
from PIL import Image
import io, datetime, time, re

st.set_page_config(page_title="Sentinela Bravo", page_icon="🛡️", layout="centered")
st.markdown("""
<style>
  .block-container{padding-top:1rem}
  h1{font-size:1.9rem!important;font-weight:800!important;color:#1e3d59}
  h3{color:#1e3d59;font-size:1.05rem!important}
  .stTextArea textarea{font-family:'Courier New',monospace;font-size:.88rem}
  .stButton>button[kind="primary"]{background-color:#1e3d59;color:white;font-weight:700;
    font-size:1rem;border:none;padding:.75rem;border-radius:6px;width:100%}
  .stButton>button[kind="primary"]:hover{background-color:#17b978}
  .pend{background:#fff3cd;border-left:4px solid #e0a800;padding:.7rem 1rem;
    border-radius:4px;margin:.3rem 0;font-size:.88rem}
  .info-modelo{background:#e8f4fd;border-left:4px solid #1e3d59;padding:.5rem 1rem;
    border-radius:4px;margin-bottom:.6rem;font-size:.88rem}
  .aviso-local{background:#fff8e1;border-left:4px solid #ff9800;padding:.5rem 1rem;
    border-radius:4px;margin-bottom:.6rem;font-size:.88rem}
</style>""", unsafe_allow_html=True)

st.markdown("# 🛡️ Sentinela Bravo")
st.caption("Boletinista Técnico — Stellantis Betim | Grupo Souza Lima")
st.markdown("---")

for k in ["bo_final","arq"]:
    if k not in st.session_state:
        st.session_state[k] = None

api_key = st.secrets.get("GOOGLE_API_KEY") or st.secrets.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# ══════════════════════════════════════════════════════════════════
#  CATÁLOGO DOS 39 MODELOS
# ══════════════════════════════════════════════════════════════════
MODELOS = {
  "overtime":       {"nome":"EXCESSO DE CARGA HORÁRIA — OVERTIME",
    "kw":["overtime","excesso de carga","carga horária","5 horas","jornada excessiva"],
    "t3":True,"placa":True,
    "ext":[("mvm",r'mvm[\s:\-]*[\d\.]{5,}',"MVM"),("transp",r'transportadora\s+\w+',"Transportadora"),
           ("h_ent",r'(adentrou|acessou|chegou).{0,30}\d{1,2}h',"Hora de entrada"),
           ("h_sai",r'(saiu|deixou).{0,30}\d{1,2}h',"Hora de saída")]},
  "abalroamento":   {"nome":"ABALROAMENTO",
    "kw":["abalroamento","abalroou","abalroado"],"t3":True,"placa":True,
    "ext":[("danos",r'amassad|riscad|quebrad|arranhad|empenad|trincad|deformad',"Danos técnicos"),
           ("tst",r'(técnico|tecnico).{0,20}segurança|tst\b',"TST ciente"),
           ("cso",r'\bcso\b|centro.{0,20}saúde',"Encaminhamento CSO")]},
  "colisao":        {"nome":"COLISÃO","kw":["colisão","colisao","colidiu"],"t3":False,"placa":True,
    "ext":[("danos",r'amassad|riscad|quebrad|arranhad|empenad|trincad',"Danos técnicos"),
           ("tst",r'(técnico|tecnico).{0,20}segurança|tst\b',"TST ciente")]},
  "choque":         {"nome":"CHOQUE","kw":["choque","chocou"],"t3":False,"placa":True,
    "ext":[("danos",r'amassad|riscad|quebrad|arranhad|empenad|trincad',"Danos técnicos")]},
  "empilhadeira_col":{"nome":"COLISÃO EMPILHADEIRA",
    "kw":["empilhadeira","hyster","operador de veículo logístico","ovl"],"t3":False,"placa":True,
    "ext":[("n_empi",r'(hyster|empilhadeira)\s*[\,]?\s*\w{2,}',"Número da empilhadeira"),
           ("tst",r'(técnico|tecnico).{0,20}segurança|tst\b',"TST ciente"),
           ("cso",r'\bcso\b',"Encaminhamento CSO")]},
  "queda_pecas":    {"nome":"QUEDA DE PEÇAS DA EMPILHADEIRA",
    "kw":["queda de peças","peças caíram","tubular","alocar sobre"],"t3":False,"placa":False,
    "ext":[("danfe",r'danfe[\s:\-]*\w+',"DANFE"),("desenho",r'desenho[\s:\-]*\w+',"Desenho")]},
  "carga_tombada":  {"nome":"CARGA TOMBADA / PEÇAS DANIFICADAS",
    "kw":["carga tombada","tombado","tombaram","peças danificadas","avaria"],"t3":True,"placa":True,
    "ext":[("mvm",r'mvm[\s:\-]*[\d\.]{5,}',"MVM"),("danfe",r'danfe[\s:\-]*\w+',"DANFE"),
           ("qtd",r'\d+\s*(peças|paletes|caixas)',"Qtd peças"),
           ("forn",r'fornecedor\s+\w+',"Fornecedor")]},
  "pecas_molhadas": {"nome":"PEÇAS MOLHADAS",
    "kw":["peças molhadas","molhado","umidade nas peças"],"t3":True,"placa":True,
    "ext":[("mvm",r'mvm[\s:\-]*[\d\.]{5,}',"MVM"),("danfe",r'danfe[\s:\-]*\w+',"DANFE")]},
  "container":      {"nome":"CONTAINER DANIFICADO",
    "kw":["container","contêiner"],"t3":True,"placa":True,
    "ext":[("cod",r'\b[a-z]{3,4}\s*\d{6,}',"Código container"),
           ("mvm",r'mvm[\s:\-]*[\d\.]{5,}',"MVM")]},
  "deem_maior":     {"nome":"DEEM MAIOR","kw":["deem maior","deem a maior","peças excedentes"],"t3":True,"placa":True,
    "ext":[("deem",r'deem.{0,10}n[°º]?\s*\d+',"Nº DEEM"),("danfe",r'danfe[\s:\-]*\w+',"DANFE")]},
  "deem_menor":     {"nome":"DEEM MENOR","kw":["deem menor","deem a menor","peças faltando"],"t3":True,"placa":True,
    "ext":[("deem",r'deem.{0,10}n[°º]?\s*\d+',"Nº DEEM"),("danfe",r'danfe[\s:\-]*\w+',"DANFE")]},
  "caminhao_def":   {"nome":"CAMINHÃO COM DEFEITO NO INTERIOR DA PLANTA",
    "kw":["defeito","pane","não ligou","bateria descarregou","problema mecânico","válvula","falha mecânica"],"t3":True,"placa":True,
    "ext":[("mvm",r'mvm[\s:\-]*[\d\.]{5,}',"MVM"),("transp",r'transportadora\s+\w+',"Transportadora"),
           ("forn",r'fornecedor\s+\w+',"Fornecedor")]},
  "prototipo":      {"nome":"PROTÓTIPO SEM LACRES",
    "kw":["protótipo","prototipo","sem lacres","sigilo industrial"],"t3":True,"placa":True,
    "ext":[("chassi",r'chassi[\s:\-]*\w+',"Chassi"),("mvm",r'mvm[\s:\-]*[\d\.]{5,}',"MVM")]},
  "sider":          {"nome":"SIDER ABERTO","kw":["sider aberto","sider","lona aberta"],"t3":True,"placa":True,
    "ext":[("mvm",r'mvm[\s:\-]*[\d\.]{5,}',"MVM")]},
  "recusa_carg":    {"nome":"RECUSA DE CARREGAMENTO","kw":["recusa","recusou","não quis carregar","saiu vazio"],"t3":True,"placa":True,
    "ext":[("mvm",r'mvm[\s:\-]*[\d\.]{5,}',"MVM")]},
  "ckd":            {"nome":"CARGA COM DESTINO AO CKD","kw":["ckd","entrou erroneamente","destino errado"],"t3":True,"placa":True,
    "ext":[("mvm",r'mvm[\s:\-]*[\d\.]{5,}',"MVM"),("danfe",r'danfe[\s:\-]*\w+',"DANFE")]},
  "conservacao":    {"nome":"ESTADO DE CONSERVAÇÃO DE VEÍCULOS — P1",
    "kw":["estado de conservação","lâmpada queimada","farol quebrado","irregularidades no veículo"],"t3":True,"placa":True,
    "ext":[("mvm",r'mvm[\s:\-]*[\d\.]{5,}',"MVM")]},
  "os_empi":        {"nome":"O.S COM AUXÍLIO DE EMPILHADEIRA — P1",
    "kw":["o.s com auxílio","os de trânsito","revista de caminhão"],"t3":True,"placa":True,
    "ext":[("mvm",r'mvm[\s:\-]*[\d\.]{5,}',"MVM"),("danfe",r'danfe[\s:\-]*\w+',"DANFE")]},
  "reboque":        {"nome":"VEÍCULO REBOCADO","kw":["rebocado","reboque","guincho","customer care","oficina assistencial"],"t3":True,"placa":True,
    "ext":[("cc",r'customer\s+care\s*n[°º]?\s*\d+',"Nº Customer Care")]},
  "vazilhames":     {"nome":"PEÇAS EM VASILHAMES — GALPÃO 89","kw":["vasilhame","galpão 89","peças no vasilhame"],"t3":False,"placa":False,
    "ext":[("cod",r'(cód|código)[\s:\-]*\w+',"Cód vasilhame"),("danfe",r'danfe[\s:\-]*\w+',"DANFE")]},
  "estacionamento": {"nome":"ESTACIONAMENTO IRREGULAR",
    "kw":["estacionamento irregular","vaga de idoso","vaga proibida","trava rodas","trava-rodas"],"t3":False,"placa":True,
    "ext":[("trava",r'trava[\s\-]?rodas',"Trava-rodas")]},
  "moto_irr":       {"nome":"ESTACIONAMENTO IRREGULAR — MOTOCICLETA",
    "kw":["motocicleta irregular","moto em local proibido","moto em vaga"],"t3":False,"placa":True,
    "ext":[("trava",r'trava[\s\-]?rodas',"Trava-rodas")]},
  "notebook_rev":   {"nome":"RECOLHIMENTO DE NOTEBOOK EM REVISTA",
    "kw":["notebook em revista","abrbe","patrimônio","qrcode","etiqueta danificada"],"t3":False,"placa":False,
    "ext":[("patr",r'(patrimônio|abrbe)[\s:\-]*\w+',"ABRBE/Patrimônio"),
           ("guarda",r'guarda\s+de\s+objetos\s+n[°º]?\s*\d+',"Nº guarda objetos")]},
  "objeto_rev":     {"nome":"RECOLHIMENTO DE OBJETOS EM REVISTA",
    "kw":["objeto recolhido","sala de revista","sem documentação","carta de próprio punho"],"t3":False,"placa":False,
    "ext":[("guarda",r'guarda\s+de\s+objetos\s+n[°º]?\s*\d+',"Nº guarda objetos"),
           ("carta",r'carta.{0,20}próprio\s+punho',"Carta próprio punho")]},
  "cracha":         {"nome":"CONFECÇÃO DE CRACHÁ MANUAL","kw":["crachá manual","ronda inoperante","crachá provisório"],"t3":False,"placa":False,"ext":[]},
  "visitantes":     {"nome":"SAÍDA DE VISITANTES FORA DO HORÁRIO","kw":["visitante fora do horário","saída de visitante"],"t3":False,"placa":False,
    "ext":[("empresa",r'empresa\s+\w+',"Empresa do visitante")]},
  "fisc_transito":  {"nome":"FISCALIZAÇÃO DE TRÂNSITO","kw":["fiscalização de trânsito","o.s de trânsito","sem habilitação","sem cnh"],"t3":False,"placa":True,
    "ext":[("insp",r'inspetor.{0,30}(reg\.?|sr\.)',"Inspetor responsável")]},
  "radar":          {"nome":"FISCALIZAÇÃO COM AUXÍLIO DE RADAR","kw":["radar","excesso de velocidade","km/h superior"],"t3":False,"placa":True,
    "ext":[("vel",r'\d+\s*km\s*/?\s*h',"Velocidade registrada")]},
  "uso_indevido":   {"nome":"UTILIZAÇÃO INDEVIDA DE VEÍCULOS","kw":["utilização indevida","uso indevido","fins particulares","rebocador"],"t3":False,"placa":True,"ext":[]},
  "mau_proc":       {"nome":"MAU PROCEDIMENTO — RECUSA DE REVISTA","kw":["mau procedimento","se recusou a passar","se negou","recusou a revista"],"t3":False,"placa":False,
    "ext":[("carta",r'carta.{0,20}próprio\s+punho',"Carta próprio punho")]},
  "embriaguez":     {"nome":"SINAIS DE EMBRIAGUEZ","kw":["embriaguez","hálito etílico","etílico","coordenação motora"],"t3":False,"placa":False,"ext":[]},
  "bermuda":        {"nome":"TRAJANDO BERMUDA / TRAJE IMPRÓPRIO","kw":["bermuda","short","traje impróprio","trajando"],"t3":False,"placa":False,"ext":[]},
  "sem_epi":        {"nome":"MOTORISTA SEM EPIs","kw":["sem epi","epis","sem calçado","calçado apropriado"],"t3":True,"placa":True,
    "ext":[("aut",r'autorizou.{0,30}entrada|autorizado',"Autorização entrada")]},
  "med":            {"nome":"ATENDIMENTO MÉDICO","kw":["atendimento médico","se sentiu mal","mal súbito","ambulância","enfermeiro","médico"],"t3":False,"placa":False,
    "ext":[("amb",r'ambulância.{0,20}placa|placa.{0,20}(qmu|ambulância)',"Placa ambulância"),
           ("cso",r'\bcso\b',"Atendimento CSO"),
           ("prof",r'(enfermeiro|enfermeira|médico|médica|técnico.{0,15}enfermagem)',"Profissional saúde")]},
  "transp_fred":    {"nome":"PERDA DO TRANSPORTE FRETADO","kw":["perda do transporte","perdeu o ônibus","transporte fretado","hands on"],"t3":False,"placa":False,
    "ext":[("linha",r'linha\s+\w+|box\s+n[°º]?\s*\d+',"Linha/box")]},
  "km_errado":      {"nome":"KM LANÇADO ERRONEAMENTE — P4","kw":["km lançado","quilometragem errada","lançamento errôneo"],"t3":False,"placa":True,
    "ext":[("km",r'km\s*\d{3,}',"Valores de KM")]},
  "mvm_portaria":   {"nome":"MVM EXTRAVIADO NA PORTARIA","kw":["mvm extraviado","mvm em aberto","saída em aberto no sistema"],"t3":False,"placa":False,
    "ext":[("mvm",r'mvm[\s:\-]*[\d\.]{5,}',"Nº MVM")]},
  "mvm_guiche":     {"nome":"MVM EXTRAVIADO NO GUICHÊ","kw":["guichê de recebimento","entregou o mvm no guichê","extravio do mvm no guichê"],"t3":True,"placa":True,
    "ext":[("mvm",r'mvm[\s:\-]*[\d\.]{5,}',"Nº MVM")]},
  "carteira":       {"nome":"CARTEIRA DEIXADA NA PORTARIA","kw":["carteira encontrada","carteira com documentos","carteira deixada"],"t3":False,"placa":False,
    "ext":[("cont",r'(cartão|cnh|rg|identidade|título|cpf|crvl)',"Conteúdo")]},
  "celular":        {"nome":"CELULAR DEIXADO NA PORTARIA","kw":["celular encontrado","aparelho celular","celular deixado"],"t3":False,"placa":False,
    "ext":[("marca",r'marca\s+\w+|modelo\s+\w+',"Marca/modelo")]},
  "ronda_nb":       {"nome":"RONDA — RECOLHIMENTO DE NOTEBOOK","kw":["ronda","notebook sobre","sem cabo de segurança","notebook abandonado"],"t3":False,"placa":False,
    "ext":[("abrbe",r'abrbe[\s:\-]*\w+',"ABRBE")]},
  "ronda_porta":    {"nome":"RONDA — PORTAS DESTRANCADAS","kw":["porta aberta","porta destrancada","sala aberta"],"t3":False,"placa":False,
    "ext":[("aviso",r'aviso.{0,20}(recolhimento|local)',"Aviso deixado")]},
  "ronda_vaz":      {"nome":"RONDA — VAZAMENTO DE LÍQUIDO","kw":["vazamento","vazando","água industrial","tubulação","líquido"],"t3":False,"placa":False,
    "ext":[("manu",r'(mecânico|manutenção).{0,30}(reg\.?|compareceu)',"Manutenção acionada")]},
  "ronda_cerca":    {"nome":"RONDA — CERCAS DANIFICADAS","kw":["cerca","cercas","limítrofe","grade caída"],"t3":False,"placa":False,
    "ext":[("hd",r'help\s+desk|chamado\s+n[°º]?\s*\d+|om\d+',"Chamado Help Desk")]},
  "instab_ronda":   {"nome":"INSTABILIDADE NO SISTEMA RONDA","kw":["instabilidade","sistema ronda instável","fichas manuais"],"t3":False,"placa":False,"ext":[]},
}

# ══════════════════════════════════════════════════════════════════
#  FUNÇÃO 1: Identificar modelo pelo scoring de keywords
# ══════════════════════════════════════════════════════════════════
def identificar_modelo(texto):
    t = texto.lower()
    melhor, best_score, best_id = None, 0, None
    for mid, m in MODELOS.items():
        score = sum(1 for kw in m["kw"] if kw in t)
        if score > best_score:
            best_score, best_id, melhor = score, mid, m
    return best_id, melhor

# ══════════════════════════════════════════════════════════════════
#  FUNÇÃO 2: Detectar se texto já é um BO estruturado
# ══════════════════════════════════════════════════════════════════
def ja_formatado(texto):
    t = texto.lower()
    score = sum(1 for p in [
        r"relatório de ocorrência", r"boletim de ocorrência",
        r"histórico.{0,20}(fatos|constatação)", r"dados logísticos",
        r"providências adotadas", r"\d+\.\s*(histórico|dados|qualificação|providências|diagnóstico)",
        r"horário de (início|término)", r"data do registro", r"setor/local:",
        r"qualificação dos envolvidos", r"emissão:\s*\d{2}/\d{2}/\d{4}",
    ] if re.search(p, t))
    return score >= 3

# ══════════════════════════════════════════════════════════════════
#  FUNÇÃO 3: Extrai entidades do texto (nomes, REs, placas etc.)
# ══════════════════════════════════════════════════════════════════
def extrair(texto):
    t = texto
    return {
        "nomes":   re.findall(r'(?:sr\.?|sra\.?)\s+[A-ZÁÀÂÃÉÊÍÓÔÕÚÜÇ][a-záàâãéêíóôõúüç]+(?:\s+[A-ZÁÀÂÃÉÊÍÓÔÕÚÜÇ][a-záàâãéêíóôõúüç]+)*', t),
        "regs":    re.findall(r'(?:re|reg\.?|matrícula|matricula|idsap)\s*[\:\-]?\s*(\d{4,})', t, re.I),
        "tels":    re.findall(r'\+?(?:55\s*)?\(?\d{2}\)?\s*\d{4,5}[\s\-]?\d{4}', t),
        "placas":  re.findall(r'\b[A-Z]{3}[\s\-]?\d{4}\b|\b[A-Z]{3}\d[A-Z]\d{2}\b', t),
        "mvms":    re.findall(r'(?:mvm)[\s:\-]*([\d\.]{5,})', t, re.I),
        "locais":  re.findall(r'(?:galpão|portaria|sala|coluna|pátio|estacionamento)\s*[\d\w]+', t, re.I),
        "horas":   re.findall(r'\d{1,2}h\d{0,2}|\d{2}:\d{2}', t),
        "empresas":re.findall(r'(?:transportadora|empresa)\s+([A-ZÁÀÂÃÉÊÍÓÔÕÚÜÇ][^\n,\.]{3,30})', t),
    }

# ══════════════════════════════════════════════════════════════════
#  FUNÇÃO 4: Auditoria Python — valida o relato ANTES de qualquer API
# ══════════════════════════════════════════════════════════════════
def auditar(texto, local):
    p, t = [], texto.lower()

    # Local
    local_ok = (local and len(local.strip()) >= 5) or bool(re.search(
        r'\b(galpão|galpao|portaria|coluna|sala|pátio|patio|baia|portão'
        r'|recebimento|almoxarifado|estacionamento|cso|ckd|oficina|guarita'
        r'|p1|p2|p3|p4|p5|p6|p7|p8)\b', t))
    if not local_ok:
        p.append(("Local do Fato", "Informe o galpão, portaria, coluna ou sala no campo ou no relato."))

    # Nome
    if not re.search(r'\b(sr\.?|sra\.?)\s+[a-záàâãéêíóôõúüç]', t):
        p.append(("Nome do Envolvido", "Identifique os envolvidos: Sr./Sra. + nome completo."))

    # Telefone
    if not re.search(r'\+?(?:55\s*)?\(?\d{2}\)?\s*\d{4,5}[\s\-]?\d{4}|\btel\.?\b|\bcelular\b', t):
        p.append(("Telefone", "Inclua o telefone de contato: (DDD) XXXXX-XXXX."))

    # Liderança
    if not re.search(r'\b(lider|líder|supervisor|gerente|inspetor|técnico|tst|coordenador|team\s+leader|orientou|autorizou|solicitou|determinou|cientificou)\b', t):
        p.append(("Liderança Ciente", "Identifique o Líder, Supervisor, Inspetor ou TST ciente."))

    # Alegação/dinâmica
    if not re.search(r'\b(disse|alegou|declarou|informou|relatou|orientou|constatou|solicitou'
                     r'|autorizou|ausência|impossibilitando|não foi possível|falha|vazamento|defeito)\b', t):
        p.append(("Alegação / Dinâmica", "Inclua o que o envolvido disse ou a restrição técnica da liderança."))

    # Desfecho
    if not re.search(
        r'\b(encaminh|liber|recolh|orient|retir|acion|notific|saiu|regulariz'
        r'|remov|trancad|gerado|solicit|previs|contato|acompanhou|encerr|devolv'
        r'|aberto chamado|deixou aviso|será desloc|foi para|foi embora|chamar'
        r'|providência|será regulariz|manutenção foi|help desk)\w*\b', t):
        p.append(("Desfecho / Providências", "Informe como a ocorrência foi encerrada ou direcionada."))

    # Termo proibido
    if re.search(r'\bdanificad[ao]\b', t):
        p.append(("Terminologia", "Substitua 'danificado/a' por: amassado, riscado, quebrado, empenado, trincado, furado."))

    # Tamanho mínimo
    if len(texto.split()) < 20:
        p.append(("Extensão", f"Relato muito curto ({len(texto.split())} palavras). Mínimo: 20 palavras."))

    return [{"campo": c, "mensagem": m} for c, m in p]

# ══════════════════════════════════════════════════════════════════
#  FUNÇÃO 5: Monta BO em Python puro — fallback sem API
# ══════════════════════════════════════════════════════════════════
def montar_bo_python(texto, modelo_id, modelo, data, hora, local):
    ent = extrair(texto)
    nome = modelo["nome"] if modelo else "OCORRÊNCIA OPERACIONAL"
    local_final = local.strip() or (ent["locais"][0].title() if ent["locais"] else "Declarado no histórico")

    env_linhas = []
    for n in ent["nomes"]:    env_linhas.append(f"  - {n}")
    for r in ent["regs"]:     env_linhas.append(f"  - RE/Matrícula/IDSAP: {r}")
    for t in ent["tels"]:     env_linhas.append(f"  - Tel: {t}")
    for e in ent["empresas"]: env_linhas.append(f"  - Empresa: {e}")
    for p in ent["placas"]:   env_linhas.append(f"  - Placa: {p}")
    for m in ent["mvms"]:     env_linhas.append(f"  - MVM: {m}")
    envolvidos = "\n".join(env_linhas) if env_linhas else "  - Dados conforme relato abaixo"

    # Texto do histórico: limpa espaços extras
    historico = re.sub(r'\n{3,}', '\n\n', texto.strip())

    ts = datetime.datetime.now().strftime('%d/%m/%Y às %H:%M')
    bo = f"""{nome}
{'─'*70}

1. DADOS LOGÍSTICOS E CLASSIFICAÇÃO
   Data do Fato : {data}
   Hora do Fato : {hora}
   Local Exato  : {local_final}
   Natureza     : {nome}

2. QUALIFICAÇÃO DOS ENVOLVIDOS / SOLICITANTES / LIDERANÇAS
{envolvidos}

3. HISTÓRICO DOS FATOS / NARRATIVA CRONOLÓGICA
{historico}

4. PROVIDÊNCIAS ADOTADAS / DESFECHO
   [Conforme narrado no histórico acima]

{'─'*70}
Emissão : {ts}
Relator : Vigilante Cleidir Alves dos Santos
⚠️  Gerado em modo Python local (API indisponível).
    Revise e complemente antes do envio oficial ao sistema.
"""
    return bo

# ══════════════════════════════════════════════════════════════════
#  INTERFACE
# ══════════════════════════════════════════════════════════════════
st.markdown("### 📋 Dados da Ocorrência")
col1, col2 = st.columns(2)
with col1:
    data_fato = st.date_input("Data do Fato", value=datetime.date.today())
with col2:
    hora_fato = st.selectbox("Hora do Fato (24h)",
        [f"{h:02d}:{m:02d}" for h in range(24) for m in range(0,60,5)], index=144)

local_txt = st.text_input("Local Exato",
    placeholder="Galpão 24, adjacente à Sala 28 / Portaria 03, baia 02…")

relato = st.text_area("Relato Bruto do Plantão",
    placeholder=(
        "Cole aqui o texto do WhatsApp ou anotações de campo.\n\n"
        "Para motoristas/terceiros inclua:\n"
        "  • Nome, CNH, telefone, empresa, endereço e filiação (pai/mãe)\n"
        "  • Número do MVM\n\n"
        "Para todos os casos inclua:\n"
        "  • O que o envolvido DISSE (alegação)\n"
        "  • Nome e RE da liderança ciente\n"
        "  • Como foi RESOLVIDO (desfecho)\n\n"
        "Se o BO já estiver formatado, cole-o aqui — o sistema reconhece\n"
        "e consolida sem gastar cota de API."
    ), height=260)

st.markdown("### 📷 Evidências Visuais / Documentos (CNH, MVM) — Opcional")
fotos = st.file_uploader("Fotos", type=["jpg","jpeg","png","webp"],
    accept_multiple_files=True, label_visibility="collapsed")

imgs = []
if fotos:
    for f in fotos:
        try:
            f.seek(0)
            img = Image.open(io.BytesIO(f.read()))
            img.thumbnail((1024,1024))
            buf = io.BytesIO()
            if img.mode in ("RGBA","P"): img = img.convert("RGB")
            img.save(buf, format="JPEG", quality=70, optimize=True)
            buf.seek(0)
            imgs.append(Image.open(buf))
        except Exception: pass
    if imgs:
        st.success(f"✅ {len(imgs)} imagem(ns) carregada(s).")

st.markdown("---")

if st.button("🛡️ Auditar e Gerar Boletim", type="primary"):
    if not relato.strip():
        st.warning("⚠️ O campo de relato não pode estar vazio.")
        st.stop()

    # Evita re-processar o mesmo texto já gerado
    if st.session_state.bo_final and st.session_state.get("ultimo_relato") == relato:
        st.info("ℹ️ Boletim já gerado para este relato. Role para baixo para visualizá-lo.")
        st.stop()

    mid, modelo = identificar_modelo(relato)

    # Exibe modelo identificado
    if modelo:
        terceiro_badge = " &nbsp;|&nbsp; 🚛 Envolve terceiro" if modelo["t3"] else ""
        st.markdown(
            f"<div class='info-modelo'>📌 <strong>{modelo['nome']}</strong>{terceiro_badge}</div>",
            unsafe_allow_html=True)
    else:
        st.markdown(
            "<div class='aviso-local'>📌 Natureza não identificada — aplicando validação base.</div>",
            unsafe_allow_html=True)

    # ── ROTA A: Texto já formatado → Python consolida (ZERO custo API) ────────
    if ja_formatado(relato):
        st.info("📋 BO já estruturado detectado — consolidando sem consumir cota de API…")
        ts = datetime.datetime.now().strftime('%d/%m/%Y às %H:%M')
        bo_txt = relato.strip()
        if "emissão" not in bo_txt.lower():
            bo_txt += f"\n\n{'─'*70}\nEmissão: {ts}\nRelator: Vigilante Cleidir Alves dos Santos"
        st.session_state.bo_final = bo_txt
        st.session_state.arq = f"BO_{data_fato.strftime('%Y%m%d')}_{hora_fato.replace(':','')}.txt"
        st.session_state["ultimo_relato"] = relato
        st.rerun()

    # ── ROTA B: Texto bruto → auditar → tentar Gemini → fallback Python ───────
    else:
        pends = auditar(relato, local_txt)

        if pends:
            st.error(f"⛔ **PRÉ-AUDITORIA: {len(pends)} pendência(s)**")
            st.markdown("Corrija antes de gerar. O Gemini só é acionado após aprovação:")
            for p in pends:
                st.markdown(
                    f"<div class='pend'>❌ <strong>{p['campo']}</strong><br>{p['mensagem']}</div>",
                    unsafe_allow_html=True)
            st.info("💡 Cada pendência corrigida aqui evita uma chamada desnecessária à API.")

        else:
            # Aprovado — tenta Gemini; se indisponível, Python resolve
            with st.spinner("🔄 Pré-auditoria OK! Gerando boletim…"):
                bo_gerado = None
                modo = "python"  # padrão: fallback

                if api_key:
                    try:
                        time.sleep(2)  # pausa preventiva anti-429
                        ia = genai.GenerativeModel("gemini-2.0-flash")
                        nome_m = modelo["nome"] if modelo else "OCORRÊNCIA OPERACIONAL"
                        instr_t3 = (
                            "\nATENÇÃO — Terceiro sem vínculo: inclua na seção 'Dados Complementares' "
                            "todos os dados disponíveis: filiação (pai/mãe), endereço completo, CNH, "
                            "empresa/transportadora e telefone." if (modelo and modelo["t3"]) else ""
                        )
                        prompt = f"""Você é o Boletinista Técnico da Segurança Patrimonial da Stellantis Betim.
Estruture o relato abaixo como BO Interno formal, conforme padrão da empresa.

DADOS:
- Data: {data_fato.strftime('%d/%m/%Y')} | Hora: {hora_fato}
- Local: {local_txt.strip() or 'Declarado no relato'}
- Natureza: {nome_m}
{instr_t3}

RELATO APROVADO:
\"\"\"
{relato}
\"\"\"

REGRAS: Título MAIÚSCULAS. "Registramos…" (3ª pessoa plural). Nunca "danificado".
Preservar exatamente: nomes, REs, placas, MVMs, CNH, telefones, DANFE, ABRBE.
Alegações: "O Sr. X disse que…". Texto com início, meio e desfecho.

ESTRUTURA:
[TÍTULO EM MAIÚSCULAS]
1. DADOS LOGÍSTICOS E CLASSIFICAÇÃO
2. QUALIFICAÇÃO DOS ENVOLVIDOS / SOLICITANTES / LIDERANÇAS
3. HISTÓRICO DOS FATOS
4. ALEGAÇÃO DOS ENVOLVIDOS / RESTRIÇÕES OPERACIONAIS
5. PROVIDÊNCIAS ADOTADAS / DESFECHO
{"Dados Complementares do Condutor: Filiação / Endereço / Tel / CNH" if modelo and modelo['t3'] else ""}
----------------------------------------------------------------------
Emissão: {datetime.datetime.now().strftime('%d/%m/%Y às %H:%M')}
Relator: Vigilante Cleidir Alves dos Santos"""

                        conteudo = [prompt]
                        if imgs:
                            conteudo.append("\n[Evidências para análise:]")
                            conteudo.extend(imgs)

                        resp = None
                        for tentativa in range(2):
                            try:
                                resp = ia.generate_content(conteudo,
                                    generation_config={"max_output_tokens":1200,"temperature":0.1})
                                if resp and resp.text:
                                    break
                            except Exception as e:
                                if "429" in str(e) and tentativa == 0:
                                    time.sleep(30)
                                else:
                                    raise e

                        if resp and resp.text:
                            bo_gerado = resp.text
                            modo = "gemini"

                    except Exception as e:
                        # Qualquer falha da API → Python assume
                        if "429" in str(e):
                            st.warning("⚠️ Cota Gemini atingida — gerando BO em modo Python local.")
                        else:
                            st.warning(f"⚠️ API indisponível ({str(e)[:60]}) — modo Python local ativado.")

                # Fallback sempre disponível
                if not bo_gerado:
                    bo_gerado = montar_bo_python(
                        relato, mid, modelo,
                        data_fato.strftime('%d/%m/%Y'), hora_fato, local_txt)

                st.session_state.bo_final = bo_gerado
                st.session_state.arq = f"BO_{data_fato.strftime('%Y%m%d')}_{hora_fato.replace(':','')}.txt"
                st.session_state["ultimo_relato"] = relato

                if modo == "python":
                    st.info("📋 Boletim gerado em modo Python local. Revise antes do envio oficial.")
                else:
                    st.success("✅ Boletim gerado pelo Gemini com sucesso!")

# ── EXIBIÇÃO DO RESULTADO ──────────────────────────────────────────────────────
if st.session_state.bo_final:
    st.success("✅ Boletim pronto!")
    st.text_area("", value=st.session_state.bo_final, height=560, key="exib")

    col_a, col_b = st.columns(2)
    with col_a:
        st.download_button("⬇️ Baixar (.txt)",
            data=st.session_state.bo_final.encode("utf-8"),
            file_name=st.session_state.arq or "BO.txt",
            mime="text/plain", use_container_width=True)
    with col_b:
        if st.button("🔄 Novo Boletim", use_container_width=True):
            st.session_state.bo_final = None
            st.session_state["ultimo_relato"] = None
            st.rerun()
