import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import datetime
import time  # Biblioteca importada corretamente para evitar o NameError

# ─── Configuração de Página e Layout ──────────────────────────────────────────
st.set_page_config(
    page_title="Sentinela Bravo — Auditor & Revisor",
    page_icon="🛡️",
    layout="centered"
)

# Estilização CSS para máxima legibilidade no celular
st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    h1 { font-size: 2.1rem !important; font-weight: 800 !important; color: #1e3d59; }
    .stTextArea textarea { font-family: 'Courier New', monospace; font-size: 0.95rem; }
    .stButton > button[kind="primary"] {
        background-color: #1e3d59;
        color: white;
        font-weight: 700;
        font-size: 1.05rem;
        border: none;
        padding: 0.75rem;
        border-radius: 6px;
    }
    .stButton > button[kind="primary"]:hover { background-color: #17b978; color: white; }
    div[data-testid="stAlert"] { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

st.markdown("# 🛡️ Sentinela Bravo")
st.caption("Arquitetura Híbrida: Pré-Auditoria em Python & Revisão por Inteligência Artificial")
st.markdown("---")

# Inicialização das variáveis de estado para persistência estável no mobile
if "documento_revisado" not in st.session_state:
    st.session_state.documento_revisado = None
if "nome_arquivo" not in st.session_state:
    st.session_state.nome_arquivo = ""

# ─── Autenticação da Chave API ────────────────────────────────────────────────
api_key = st.secrets.get("GOOGLE_API_KEY") or st.secrets.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    st.error("⚠️ Chave de API não localizada nas configurações internas do Streamlit.")
    st.stop()

# ─── Entrada de Dados Operacionais ────────────────────────────────............
st.markdown("### 📝 Informações de Campo")

col1, col2 = st.columns(2)
with col1:
    data_fato = st.date_input("Data da Ocorrência", value=datetime.date.today())
with col2:
    hora_fato = st.selectbox(
        "Horário do Fato (Formato 24h)",
        options=[f"{h:02d}:{m:02d}" for h in range(0, 24) for m in range(0, 60, 5)],
        index=144
    )

local_detalhado = st.text_input(
    "Local Exato (Planta Betim)",
    placeholder="Ex: Portaria 03 baia 02, Galpão 89 coluna 32AC..."
)

relato_bruto = st.text_area(
    "Relato Bruto do Plantão (Copiado do WhatsApp / Anotações)",
    placeholder="Insira as mensagens informais trazidas pelas equipes de campo para triagem...",
    height=180
)

# ─── Otimizador e Compressor de Imagens de Campo (Nativo em Python) ───────────
st.markdown("### 📷 Evidências Visuais")
fotos_carregadas = st.file_uploader(
    "Anexe as fotos da ocorrência",
    type=["jpg", "jpeg", "png", "webp"],
    accept_multiple_files=True,
    label_visibility="collapsed"
)

imagens_processadas = []
if fotos_carregadas:
    for foto in fotos_carregadas:
        try:
            foto.seek(0)
            img = Image.open(io.BytesIO(foto.read()))
            img.thumbnail((1024, 1024))
            
            buffer = io.BytesIO()
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
                
            img.save(buffer, format="JPEG", quality=70, optimize=True)
            buffer.seek(0)
            imagens_processadas.append(Image.open(buffer))
        except Exception:
            pass
            
    if imagens_processadas:
        st.success(f"✅ {len(imagens_processadas)} evidência(s) comprimida(s) localmente pelo Python!")

st.markdown("---")

# ─── MOTOR DE PRÉ-AUDITORIA INTERNA (PYTHON PURO — SEM CONSUMO DE COTA) ───────
def executar_auditoria_local(texto):
    """
    Varre o texto procurando inconsistências críticas antes de acionar a IA.
    """
    pendencias = []
    texto_alvo = texto.lower()
    
    # 1. Auditoria de dados de identificação para funcionários internos
    if "re" not in texto_alvo and "matrícula" not in texto_alvo and "matricula" not in texto_alvo:
        if "motorista" not in texto_alvo and "terceiro" not in texto_alvo:
            pendencias.append("Ausência de Registro Funcional (RE / Matrícula) do envolvido.")
            
    # 2. Auditoria de meios de contato diretos
    if "tel" not in texto_alvo and "fone" not in texto_alvo and "celular" not in texto_alvo:
        pendencias.append("Ausência de número de telefone ou canal de contato telefônico.")
        
    # 3. Auditoria de Lideranças de Turno
    if "lider" not in texto_alvo and "líder" not in texto_alvo and "supervisor" not in texto_alvo and "gerente" not in texto_alvo and "inspetor" not in texto_alvo:
        pendencias.append("Ausência de menção à liderança imediata ciente do registro.")
        
    # 4. Alerta Técnico de Termos Banidos (Ex: Termo genérico 'danificado')
    if "danificado" in texto_alvo:
        pendencias.append("Uso do termo genérico 'danificado'. Substitua por termos específicos (amassado, riscado, quebrado, empenado).")
        
    return pendencias

# ─── Acionamento e Processamento Combinado ────────────────────────────────────
if st.button("🛡️ Executar Auditoria e Revisão", use_container_width=True, type="primary"):
    if not relato_bruto.strip():
        st.warning("⚠️ O campo de relato bruto não pode estar vazio para a análise.")
        st.stop()
        
    # Passo 1: O Python faz a validação das regras fixas localmente
    lista_pendencias = executar_auditoria_local(relato_bruto)
    
    if lista_pendencias:
        st.error("⛔ **REGISTRO BLOQUEADO PELA PRÉ-AUDITORIA LOCAL**")
        st.markdown("O texto enviado não cumpre os requisitos mínimos estabelecidos. Corrija os desvios abaixo:")
        for item in lista_pendencias:
            st.markdown(f"- ❌ {item}")
        st.info("💡 *Dica do Sistema: A correção prévia impede o envio de dados incompletos e economiza a cota da IA.*")
    else:
        # Passo 2: Se passou, a versão mais recente do Gemini atua como revisor de texto técnico
        with st.spinner("🔄 Pré-auditoria aprovada! Acionando o Revisor de IA para formatação do documento final..."):
            try:
                modelo_revisor = genai.GenerativeModel("gemini-2.0-flash")
                
                prompt_revisao = f"""Você é o Revisor Ortográfico e Boletinista Técnico da Gestão de Segurança Patrimonial na Stellantis Betim, MG.
Sua única função agora é receber as informações limpas e estruturá-las no padrão culto de Relatório Técnico, eliminando gírias e vícios de linguagem do WhatsApp, gerando uma formatação estável e compatível com Bloco de Notas ou Word.

DADOS LOGÍSTICOS CONSOLIDADOS:
- Data do Fato: {data_fato.strftime('%d/%m/%Y')}
- Hora do Fato: {hora_fato}
- Local Definido: {local_detalhado if local_detalhado else 'Informado no corpo do texto'}

TEXTO DE ENTRADA DO PLANTÃO:
\"\"\"
{relato_bruto}
\"\"\"

INSTRUÇÕES DE ESCRITA FORMAL:
1. Identifique a natureza da ocorrência segundo os padrões operacionais da planta (ex: Excesso de Carga Horária - Overtime, Estacionamento Irregular, Danos de Trânsito Interno diferenciando Colisão/Choque/Abalroamento).
2. Escreva em formato técnico puramente factual, neutro, sem termos subjetivos ou adjetivos desnecessários.
3. Preserve com total exatidão números de documentos, RE, placas veiculares, numerações de chassis, racks ou ordens de carga.

Gere a saída rigorosamente estruturada abaixo para cópia imediata:

BOLETIM DE OCORRÊNCIA INTERNO — STELLANTIS BETIM
----------------------------------------------------------------------
1. DADOS LOGÍSTICOS E CLASSIFICAÇÃO
- Data do Fato: {data_fato.strftime('%d/%m/%Y')}
- Hora do Fato: {hora_fato}
- Local Exato: {local_detalhado if local_detalhado else 'Declarado no histórico'}
- Natureza da Ocorrência: [Classificação Técnica da Natureza]

2. QUALIFICAÇÃO DOS ENVOLVIDOS
[Identificação clara de Funcionários ou Terceiros, contendo nomes, registros, contatos e empresas].

3. HISTÓRICO DOS FATOS (NARRATIVA CRONOLÓGICA)
[Texto formal, culto e direto contendo a cronologia exata: início, meio e fim do evento, incluindo as alegações das partes envolvidas].

4. PROVIDÊNCIAS OPERACIONAIS ADOTADAS
[Acionamento de equipes médicas, isolamentos de áreas, colocação de travas, acionamento de guinchos ou lideranças informadas].

5. ENCERRAMENTO DE REGISTRO
- Vigilante Relator: ___________________________ RE: ___________
- Inspetor de Plantão Ciente: ___________________________
- Horário de Emissão do Relatório: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}
----------------------------------------------------------------------
"""
                conteudo_requisicao = [prompt_revisao]
                if imagens_processadas:
                    conteudo_requisicao.append("\n[Análise Visual de Evidências]: Corrobore os dados e avarias textuais cruzando com as imagens em anexo:")
                    conteudo_requisicao.extend(imagens_processadas)
                
                # Sistema de tentativas contra erro 429 (Resource Exhausted) usando a biblioteca importada
                resposta_final = None
                for tentativa in range(3):
                    try:
                        resposta_final = modelo_revisor.generate_content(conteudo_requisicao)
                        if resposta_final and hasattr(resposta_final, "text") and resposta_final.text:
                            break
                    except Exception as e:
                        if "429" in str(e) and tentativa < 2:
                            time.sleep(10)  # Agora funciona perfeitamente sem dar NameError
                        else:
                            raise e
                
                if respuesta_final and resposta_final.text:
                    st.session_state.documento_revisado = respuesta_final.text
                    st.session_state.nome_arquivo = f"BO_{data_fato.strftime('%Y%m%d')}_{hora_fato.replace(':', '')}.txt"
                else:
                    st.error("❌ Falha de comunicação: O motor de inteligência retornou uma resposta em branco.")
                    
            except Exception as falha_ia:
                st.error(f"❌ Erro no motor de IA: {str(falha_ia)}. Tente novamente em alguns segundos.")

# ─── Área de Exibição do Resultado Estável ────────────────────────────────────
if st.session_state.documento_revisado:
    st.success("✅ Documento revisado e estruturado com sucesso!")
    st.markdown("### 📋 Texto Formatado Pronto para Uso")
    
    st.text_area(
        label="",
        value=st.session_state.documento_revisado,
        height=520,
        key="visualizador_final_limpo"
    )
    
    st.download_button(
        label="⬇ " "Baixar Arquivo para Bloco de Notas / Word (.txt)",
        data=st.session_state.documento_revisado.encode("utf-8"),
        file_name=st.session_state.nome_arquivo,
        mime="text/plain",
        use_container_width=True
    )
