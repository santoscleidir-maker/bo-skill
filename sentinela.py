import streamlit as st
import google.generativeai as genai
import anthropic
from PIL import Image
import io

# Configuração da página para telemóvel
st.set_page_config(page_title="Sentinela - BO Skill", page_icon="🛡️", layout="centered")

# Estilização Dark Mode amigável e intuitiva para o usuário
st.markdown("""
    <style>
    .main { background-color: #0d1117; }
    h1 { color: #f97316; text-align: center; font-size: 32px; font-weight: bold; margin-bottom: 5px; }
    .subtitle { color: #8b949e; text-align: center; font-size: 16px; margin-bottom: 25px; }
    .section-card { background-color: #161b22; padding: 18px; border-radius: 12px; border: 1px solid #30363d; margin-bottom: 20px; }
    .section-title { color: #f97316; font-size: 18px; font-weight: bold; margin-bottom: 12px; }
    .stTextArea textarea { background-color: #0d1117; color: white; border: 1px solid #30363d; border-radius: 8px; font-size: 16px; }
    .stButton button { width: 100%; background-color: #f97316; color: white; font-weight: bold; padding: 14px; border-radius: 8px; border: none; font-size: 18px; }
    .stButton button:hover { background-color: #ea580c; }
    .bo-box { background-color: #161b22; padding: 20px; border-left: 5px solid #238636; border-radius: 8px; color: #e6edf3; font-family: 'Courier New', Courier, monospace; font-size: 15px; white-space: pre-wrap; line-height: 1.6; }
    .warning-box { background-color: #2c1a04; padding: 15px; border-left: 5px solid #d97706; border-radius: 8px; color: #fcd34d; margin-bottom: 15px; }
    .hint-text { color: #8b949e; font-size: 13px; margin-top: 5px; }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1>🛡️ Sentinela</h1>", unsafe_allow_html=True)
st.markdown("<p class=\"subtitle\">Ecossistema Inteligente de Segurança Patrimonial</p>", unsafe_allow_html=True)

# Verificação das Chaves nos Secrets do Streamlit
if "GEMINI_API_KEY" not in st.secrets or "CLAUDE_API_KEY" not in st.secrets:
    st.error("Erro: Certifique-se de configurar GEMINI_API_KEY e CLAUDE_API_KEY nas Configurações Avançadas do Streamlit.")
else:
    # Inicialização das APIs
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    claude_client = anthropic.Anthropic(api_key=st.secrets["CLAUDE_API_KEY"])

    # Bloco 1: Entrada do Usuário
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">✍️ Relato da Ocorrência</div>', unsafe_allow_html=True)
    st.markdown('<p class="hint-text"><b>Linguagem Simpática:</b> Pode ditar ou escrever do seu jeito! O sistema vai conferir se está tudo certinho antes de fechar o relatório.</p>', unsafe_allow_html=True)
    
    relato_bruto = st.text_area(
        "O que aconteceu no turno?",
        height=140,
        placeholder="Ex: Teve uma batida de uma carreta na viga da portaria 4 agora cedo. Amassou a viga e quebrou o parachoque do caminhão..."
    )
    st.markdown('</div>', unsafe_allow_html=True)

    # Bloco 2: Anexos
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📸 Adicionar Fotos ou Documentos</div>', unsafe_allow_html=True)
    arquivo_anexado = st.file_uploader("Toque para abrir a câmera ou anexar evidência:", type=["png", "jpg", "jpeg"])
    
    imagem_carregada = None
    if arquivo_anexado is not None:
        imagem_carregada = Image.open(arquivo_anexado)
        st.image(imagem_carregada, caption="⚡ Evidência anexada com sucesso!", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Execução do Fluxo Integrado (Claude Valida -> Gemini Escreve)
    if st.button("🚀 ENVIAR PARA PROCESSAMENTO"):
        if relato_bruto.strip() == "" and imagem_carregada is None:
            st.warning("Por favor, digite um relato ou insira uma imagem antes de continuar.")
        else:
            # --- FASE 1: O CLAUDE VALIDA O MODELO E COLETAS DE DADOS (Gasto mínimo de tokens) ---
            with st.spinner("O Claude está auditando a ocorrência e checando os dados mínimos..."):
                try:
                    prompt_validacao_claude = (
                        "Você é um auditor rigoroso de conformidade industrial da Stellantis. "
                        "Analise o relato do vigilante e diga se ele contém os dados mínimos necessários para um BO válido.\n"
                        "CHECKLIST EXIGIDO:\n"
                        "1. O que aconteceu (Fato/Danos)?\n"
                        "2. Houve vítimas? (Mesmo que não tenha, deve ser mencionado se foram socorridas ou se não há vítimas)\n"
                        "3. Teve Acidente de Trabalho ou situação de Risco (Classificar se é Near Miss)?\n"
                        "4. Qual o desfecho inicial / o que foi resolvido no local?\n\n"
                        f"Relato do Vigilante: {relato_bruto}\n\n"
                        "RESPOSTA OBRIGATÓRIA:\n"
                        "Se o relato contiver informações ou der a entender as respostas para esses pontos, responda APENAS com a palavra: 'APROVADO'.\n"
                        "Se faltar alguma dessas informações cruciais (como a questão de vítimas, desfecho para o gerente ou se foi um Near Miss), responda de forma muito SIMPÁTICA, acolhedora e direta para o vigilante, dizendo o que falta ele complementar. Seja breve."
                    )

                    message = claude_client.messages.create(
                        model="claude-3-5-sonnet-20241022",
                        max_tokens=150,
                        temperature=0,
                        messages=[{"role": "user", "content": prompt_validacao_claude}]
                    )
                    
                    resultado_auditoria = message.content[0].text.strip()
                    
                except Exception as e:
                    st.error(f"Erro na validação do Claude: {e}")
                    resultado_auditoria = "APROVADO"  # Contingência se a API falhar

            # --- FASE 2: DIRECIONAMENTO DO FLUXO ---
            if "APROVADO" not in resultado_auditoria:
                # Se o Claude achar inconformidade, ele para o fluxo e pede dados adicionais com educação
                st.markdown(f'<div class="warning-box">⚠️ <b>Aviso do Supervisor de Qualidade:</b><br>{resultado_auditoria}</div>', unsafe_allow_html=True)
            else:
                # Se aprovado, o Gemini entra em ação sem limites para construir o documento perfeito
                with st.spinner("Tudo validado! O Gemini está gerando o relatório formal no padrão Stellantis..."):
                    try:
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        
                        prompt_execucao_gemini = (
                            "Você é a inteligência especializada em segurança patrimonial da Stellantis. "
                            "Sua tarefa é redigir o Boletim de Ocorrência definitivo baseado no relato bruto e imagens. "
                            "Use obrigatoriamente a linguagem técnica padrão exigida no ambiente industrial.\n\n"
                            
                            "EXEMPLOS DE APRENDIZADO DO MODELO OFICIAL (Treinamento In-Context):\n"
                            "Exemplo 1: 'Registramos a informação do Motorista Especializado Sr. [Nome], reg. [X], que por volta das [X]h[X]min, ocorreu a colisão do caminhão... causando os seguintes danos... Compareceram ao local a Técnico Segurança Trabalho Sra. [Nome], reg. [X], os quais se cientificaram do fato. Anexo: Fotos.'\n"
                            "Exemplo 2: 'Registramos o comparecimento dos colaboradores listados abaixo, nos balcões das portarias... para confecção de crachás provisórios... devido sistema estar inoperante...'\n\n"
                            
                            "REGRAS DE FORMATAÇÃO E DESFECHO OPERACIONAL:\n"
                            "- Monte a narrativa em ordem cronológica impecável, formal e limpa.\n"
                            "- Extraia dados de placas, avarias ou crachás caso haja imagens anexadas e documente de forma técnica.\n"
                            "- DESFECHO OBRIGATÓRIO: Crie subseções claras ao final detalhando:\n"
                            "  1. PROVINDÊNCIAS IMEDIATAS: O que foi resolvido no local.\n"
                            "  2. REGISTRO DE VÍTIMAS: Declaração explícita sobre a integridade física das partes e socorro se houver.\n"
                            "  3. ANÁLISE DE SEGURANÇA (NEAR MISS): Classifique explicitamente sob o conceito de 'Near Miss' (Quase Acidente) se o evento envolveu riscos operacionais, acidentes de trajeto internos ou batidas com potencial de lesão, para fins de melhoria contínua de segurança do trabalho.\n"
                            "  4. DIRECIONAMENTO: Nota expressa encaminhando o documento ao Gerente de Área responsável para ciência e ações corretivas.\n\n"
                            
                            f"Relato para formatação:\n{relato_bruto}"
                        )

                        conteudo_para_enviar = [prompt_execucao_gemini]
                        if imagem_carregada is not None:
                            conteudo_para_enviar.append(imagem_carregada)

                        response = model.generate_content(conteudo_para_enviar)

                        st.success("✨ Boletim Auditado e Emitido com Sucesso!")
                        st.markdown("### 📋 Documento Oficial Gerado:")
                        st.markdown(f'<div class="bo-box">{response.text}</div>', unsafe_allow_html=True)

                    except Exception as e:
                        st.error(f"Erro na produção do Gemini: {e}")
