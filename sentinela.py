import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import datetime

# ─── Configuração de Página ───────────────────────────────────────────────────
st.set_page_config(
    page_title="Sentinela Bravo — Auditor de BO",
    page_icon="🛡️",
    layout="centered"
)

# Estilização CSS para visual profissional e limpo
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; }
    h1 { font-size: 2.2rem !important; font-weight: 800 !important; color: #1a2a3a; }
    .stTextArea textarea { font-family: 'Courier New', monospace; font-size: 0.9rem; }
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
st.caption("Módulo Boletinista Auditor — Gestão de Segurança Patrimonial Stellantis Betim")
st.markdown("---")

# Inicialização de variáveis na sessão para persistência
if "bo_final" not in st.session_state:
    st.session_state.bo_final = None
if "bo_auditoria" not in st.session_state:
    st.session_state.bo_auditoria = None
if "nome_arquivo" not in st.session_state:
    st.session_state.nome_arquivo = ""

# ─── Configuração da Conexão com API ──────────────────────────────────────────
api_key = st.secrets.get("GOOGLE_API_KEY") or st.secrets.get("GEMINI_API_KEY")

if api_key:
    genai.configure(api_key=api_key)
else:
    st.error("⚠️ Chave de API não configurada nos Secrets do Streamlit.")
    st.stop()

# ─── Painel de Entrada de Dados ───────────────────────────────────────────────
st.markdown("### 📝 Entrada de Dados Operacionais")

col1, col2 = st.columns(2)
with col1:
    # Garantia do Padrão de Data Brasil (DD/MM/YYYY)
    data_fato = st.date_input("Data do Fato (Padrão Brasil)", value=datetime.date.today())
with col2:
    hora_fato = st.selectbox(
        "Hora do Fato (Formato 24h)",
        options=[f"{h:02d}:{m:02d}" for h in range(0, 24) for m in range(0, 60, 5)],
        index=144  # Inicializa em uma hora padrão intermediária
    )

local_detalhado = st.text_input(
    "Local Exato do Fato",
    placeholder="Ex: Portaria 03 baia 02, Galpão 89 coluna 32AC, Pátio de Estocagem"
)

relato_whatsapp = st.text_area(
    "Insira o Relato Bruto (Copiado do WhatsApp / Transcrições)",
    placeholder="Cole aqui todas as informações enviadas pelas equipes de campo, mensagens informais ou anotações rápidas...",
    height=200
)

# ─── Módulo Compressor de Imagem Nativo (Substitui iLovePDF) ──────────────────
st.markdown("### 📷 Registro de Evidências Fotográficas")
st.caption("As imagens anexadas passam por compactação digital otimizada em tempo real para alívio de banda.")

fotos_carregadas = st.file_uploader(
    "Arraste ou selecione as fotos da ocorrência",
    type=["jpg", "jpeg", "png", "webp"],
    accept_multiple_files=True,
    label_visibility="collapsed"
)

imagens_processadas_api = []
imagens_exibicao = []

if fotos_carregadas:
    st.markdown("#### ⏳ Otimizando arquivos visuais...")
    for foto in fotos_carregadas:
        # Leitura dos bytes originais
        foto.seek(0)
        img_original = Image.open(io.BytesIO(foto.read()))
        
        # Redimensionamento inteligente mantendo proporção (Máximo 1200px)
        img_original.thumbnail((1200, 1200))
        
        # Conversão e Compressão em lote via Pillow (Sem serviços externos)
        buffer_otimizado = io.BytesIO()
        if img_original.mode in ("RGBA", "P"):
            img_original = img_original.convert("RGB")
            
        img_original.save(buffer_otimizado, format="JPEG", quality=65, optimize=True)
        buffer_otimizado.seek(0)
        
        # Armazena para envio à API e exibição em tela
        dados_finais_img = buffer_otimizado.getvalue()
        imagens_processadas_api.append(Image.open(io.BytesIO(dados_finais_img)))
        imagens_exibicao.append(dados_finais_img)
        
    st.success(f"✅ {len(fotos_carregadas)} imagem(ns) compactada(s) com sucesso!")
    
    # Exibição de miniaturas leves na tela
    cols_preview = st.columns(min(len(imagens_exibicao), 4))
    for idx, img_bytes in enumerate(imagens_exibicao[:4]):
        with cols_preview[idx]:
            st.image(img_bytes, use_container_width=True, caption=f"Evidência {idx+1}")

st.markdown("---")

# ─── Execução do Processamento e Auditoria ────────────────────────────────────
disparar_analise = st.button("🛡️ Auditar e Confeccionar Boletim", use_container_width=True, type="primary")

if disparar_analise:
    if not relato_whatsapp.strip():
        st.warning("⚠️ Forneça o relato bruto recebido para que o Boletinista possa auditar os dados.")
        st.stop()
        
    with st.spinner("🔄 Atuando como Boletinista: Identificando natureza, checando omissões e formatando relato..."):
        try:
            # Uso do modelo analítico e multimodal nativo
            modelo_boletinista = genai.GenerativeModel("gemini-2.0-flash")
            
            instrucoes_auditoria_e_escrita = f"""Você é o Boletinista Auditor Sênior da Gestão de Segurança Patrimonial na Stellantis Betim, MG.
Sua missão é dupla: primeiro, agir como um auditor rígido caçando omissões de dados obrigatórios; segundo, estruturar o Boletim de Ocorrência Interno (BO) perfeito seguindo rigorosamente as diretrizes operacionais fornecidas pela empresa.

DATA DO REGISTRO: {data_fato.strftime('%d/%m/%Y')}
HORA DO FATO: {hora_fato}
LOCAL INFORMADO: {local_detalhado if local_detalhado else 'Não especificado inicialmente'}
TEXTO DE ENTRADA (WHATSAPP):
\"\"\"
{relato_whatsapp}
\"\"\"

═══════════════════════════════════════════
ETAPA 1: AUDITORIA DE DADOS OBRIGATÓRIOS E OMISSÕES
═══════════════════════════════════════════
Verifique minuciosamente o texto de entrada e procure por omissões. Você deve gerar alertas claros sobre o que está faltando:
1. CADASTRO DE FUNCIONÁRIOS: Verifique se constam Nome Completo, Matrícula (RE), Telefone de contato e Liderança Responsável.
   - ATENÇÃO CRÍTICA: Se houver indicação apenas de "Team Leader" (TL), gere um alerta explícito informando que Team Leaders NÃO respondem por boletins (apenas Líderes, Supervisores ou Gerentes têm essa atribuição).
2. CADASTRO DE TERCEIROS / MOTORISTAS / ATOS DOLOSOS: Pessoas sem vínculo direto (sem crachá Stellantis) exigem rigor máximo. Verifique se constam: Número de Documento (RG/CNH), Empresa/Transportadora, Endereço Residencial Completo, Telefone e Filiação Completa (Nome do Pai e Mãe). Se faltar qualquer um destes, cite textualmente como pendência urgente.
3. ALEGAÇÕES E DEPOIMENTOS: Certifique-se de identificar claramente as declarações de cada envolvido. Se houver contradições entre relatos e evidências, aponte.

═══════════════════════════════════════════
ETAPA 2: IDENTIFICAÇÃO AUTOMÁTICA DA NATUREZA (DIRETRIZ DOS 39 MODELOS)
═══════════════════════════════════════════
Classifique o fato em uma das naturezas oficiais extraídas do manual de instruções da planta. Escolha a que melhor se enquadra técnica e logicamente:
- Recolhimento de Notebook em Revista / Recolhimento de Objetos em Revista
- Confecção de Crachá Manual
- Saída de Visitantes Fora do Horário
- Veículo Rebocado
- Excesso de Carga Horária - Overtime (Permanência superior a 5 horas conforme Lei 13.103)
- Estacionamento Irregular (Automóvel / Motociclta com aplicação de trava-rodas)
- Danos de Trânsito Interno (Aplique as regras técnicas exatas: COLISÃO se for amplo; CHOQUE se um veículo bateu em obstáculo ou veículo parado; ABALROAMENTO se foi impacto lateral com ambos em movimento).
  - REGRA DE TERMOS VISUAIS: É terminantemente proibido usar a palavra genérica "DANIFICADO" para descrever partes de veículos. Use exclusivamente termos técnicos precisos: AMASSADO, ARRANHADO, EMPENADO, QUEBRADO, DESCASCADO, RISCADO, FURADO, ESTOURADO, TRINCADO, DEFORMADO ou SOLTO.
- Queda de Peças de Empilhadeira / Carga Tombada ou Peças Danificadas / Peças Molhadas / Container Danificado
- Peças Encontradas em Vazilhames
- DEEM Maior / DEEM Menor
- Carga com destino ao CKD / Protótipo sem Lacres
- Utilização Indevida de Veículo / Fiscalização de Trânsito ou de Radar
- Extravio de MVM (Portaria ou Guichê)
- Estado de Conservação de Veículo / O.S. com Auxílio de Empilhadeira
- Carteira ou Celular Deixado na Portaria
- Mau Procedimento em Revista / Sinais de Embriaguez / Sider Aberto / Recusa de Carregamento
- Ronda (Recolhimento de Notebook, Portas Destrancadas, Vazamento de Líquido, Cercas Danificadas)
- Atendimento Médico / Perda de Transporte Fretado / Trajando Bermuda / Motorista sem EPIs
- Caminhão com Defeito no Interior da Planta / Instabilidade no Sistema Ronda

═══════════════════════════════════════════
ETAPA 3: REGRAS DE FORMATAÇÃO E PADRÃO TEXTUAL
═══════════════════════════════════════════
1. IDIOMA E TOM: Português do Brasil. Linguagem culta, técnica, formal, porém simples e direta (sem termos subjetivos ou adjetivos desnecessários). Relato estritamente factual.
2. PRESERVAÇÃO DE DADOS: Corrija os erros ortográficos e gírias vindas do WhatsApp, mas preserve com exatidão matemática números de RE, placas de veículos, numeração de chassis, ordens de carga, códigos de racks, números de documentos ou Danfes.
3. CRONOLOGIA: Monte o histórico em ordem cronológica de acontecimentos (início, meio e fim).
4. LAYOUT DE SAÍDA: Estruture o documento usando linhas divisórias claras e caixas de texto limpas. O layout deve ser perfeitamente compatível para cópia direta no Bloco de Notas (Notepad) ou Microsoft Word, sem quebrar colunas ou perder formatação de parágrafos.

Gere o resultado exatamente na estrutura dividida abaixo:

========= PAINEL DE AUDITORIA DO BOLETINISTA =========
[Apresente aqui uma análise crítica do texto enviado. Liste em formato de tópicos claros todas as omissões encontradas: se faltam dados de terceiros como endereço/filiação, se faltam REs, se o líder informado é inválido por ser apenas Team Leader, etc. Caso todas as informações estejam completas, escreva: "NENHUMA OMISSÃO DETECTADA"].
[Apresente a JUSTIFICATIVA TÉCNICA da escolha da Natureza da Ocorrência].

========= BOLETIM DE OCORRÊNCIA OFICIAL =========
STELLANTIS — PLANT INDUSTRIAL DE BETIM, MG
SEGURANÇA E GESTÃO DE FACILIDADES PATRIMONIAIS

1. DADOS LOGÍSTICOS E IDENTIFICAÇÃO
- Data do Fato: [Exibir em formato DD/MM/YYYY]
- Hora do Fato: [Exibir HHHH]
- Local Exato: [Local exato]
- Natureza da Ocorrência: [Classificação técnica exata escolhida]

2. QUALIFICAÇÃO DOS ENVOLVIDOS
[Liste todos os envolvidos, separando claramente: Funcionários (Nome, RE, Empresa, Contato, Superior Imediato válido) e Terceiros/Motoristas (Nome, Documento, Empresa/Transportadora, Telefone, Endereço Residencial Completo, Filiação)].

3. HISTÓRICO DETALHADO DOS FATOS (CRONOLOGIA)
[Texto narrativo formal e claro contendo o início, o meio e o fim do fato. Inclua as alegações de cada envolvido de forma distinta].

4. PROVIDÊNCIAS OPERACIONAIS ADOTADAS
[Descrever acionamento de lideranças, encaminhamento ao CSO/Ambulatório, acionamento de guinchos, isolamento de área, colocação de travas, recolhimento de materiais na alfândega ou orientações preventivas aplicadas].

5. ENCERRAMENTO E REGISTRO
- Vigilante Relator: ___________________________ Matricula/RE: ___________
- Inspetor de Plantão Ciente: ___________________________
- Prazo Limite para Inserção Sistêmica: [Calcular 1 hora após o horário do fato]
- Data/Hora da Emissão do Relatório: [Data e hora atual do sistema]
================────────────────────────────────"""

            conteudo_requisicao = [instrucoes_auditoria_e_escrita]
            
            # Adiciona as imagens comprimidas na memória se existirem
            if imagens_processadas_api:
                conteudo_requisicao.append(
                    "\n[EVIDÊNCIAS VISUAIS ANEXAS]: Analise as imagens abaixo para auxiliar no cruzamento de dados operacionais (verificação de avarias veiculares, placas legíveis ou leitura de documentos):"
                )
                conteudo_requisicao.extend(imagens_processadas_api)

            resposta_boletinista = modelo_boletinista.generate_content(conteudo_requisicao)
            
            if resposta_boletinista and hasattr(resposta_boletinista, "text") and resposta_boletinista.text:
                texto_gerado = resposta_boletinista.text
                
                # Divisão visual das duas seções geradas pela inteligência
                if "========= BOLETIM DE OCORRÊNCIA OFICIAL =========" in texto_gerado:
                    partes = texto_gerado.split("========= BOLETIM DE OCORRÊNCIA OFICIAL =========")
                    st.session_state.bo_auditoria = partes[0].replace("========= PAINEL DE AUDITORIA DO BOLETINISTA =========", "").strip()
                    st.session_state.bo_final = "========= BOLETIM DE OCORRÊNCIA OFICIAL =========\n" + partes[1].strip()
                else:
                    st.session_state.bo_auditoria = "Análise concluída."
                    st.session_state.bo_final = texto_gerado
                
                # Nome de arquivo limpo padronizado
                st.session_state.nome_arquivo = f"BO_{data_fato.strftime('%Y%m%d')}_{hora_fato.replace(':', '')}.txt"
            else:
                st.error("❌ Resposta nula recebida da central de processamento de texto.")
                
        except Exception as falha:
            st.error(f"❌ Falha de processamento no Módulo Boletinista: {str(falha)}")

# ─── Área de Exibição dos Resultados (Persistente e Formatada) ────────────────
if st.session_state.bo_auditoria:
    st.markdown("### 📊 Relatório de Auditoria do Plantão")
    
    # Exibe em formato de aviso dinâmico para destacar pendências e falta de dados
    if "NENHUMA OMISSÃO DETECTADA" in st.session_state.bo_auditoria.upper():
        st.success(st.session_state.bo_auditoria)
    else:
        st.warning(st.session_state.bo_auditoria)

if st.session_state.bo_final:
    st.markdown("---")
    st.markdown("### 📋 Documento Final Formatado (Padrão Stellantis)")
    st.caption("O texto abaixo está pronto para cópia ou download. As configurações ortográficas e alinhamentos permanecem intactos ao colar no Word.")
    
    # Área de texto monoespaçada ideal para preservação de layouts
    st.text_area(
        label="Conteúdo do Boletim de Ocorrência Interno",
        value=st.session_state.bo_final,
        height=550,
        label_visibility="collapsed",
        key="visualizador_bo_final"
    )
    
    # Download direto como arquivo de texto compatível com Bloco de Notas e Word
    st.download_button(
        label="⬇️ Baixar Boletim para Bloco de Notas / Word (.txt)",
        data=st.session_state.bo_final.encode("utf-8"),
        file_name=st.session_state.nome_arquivo,
        mime="text/plain",
        use_container_width=True
    )
