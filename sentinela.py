import streamlit as st
import google.generativeai as genai

# Configuração da página para ficar bonita no celular
st.set_page_config(page_title="Sentinela - BO", page_icon="🛡️", layout="centered")

# Estilo customizado para o Modo Escuro (Dark Mode)
st.markdown("""
    <style>
    .main { background-color: #06090d; }
    h1 { color: #f97316; text-align: center; font-size: 28px; }
    .stTextArea textarea { background-color: #161b22; color: white; border: 1px solid #30363d; border-radius: 8px; font-size: 16px; }
    .stButton button { width: 100%; background-color: #f97316; color: white; font-weight: bold; padding: 12px; border-radius: 8px; border: none; }
    .stButton button:hover { background-color: #ea580c; }
    .bo-box { background-color: #161b22; padding: 15px; border-left: 4px solid #f97316; border-radius: 4px; color: white; white-space: pre-wrap; }
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ Sentinela")
st.subheader("Formatador Inteligente de Boletins")

# Verifica se a chave da API está configurada nos Secrets do Streamlit
if "GEMINI_API_KEY" not in st.secrets:
    st.error("Erro: A chave GEMINI_API_KEY não foi encontrada nas configurações avançadas do Streamlit.")
else:
    # Configura a IA com a chave salva
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    
    # Campo para o vigilante digitar ou ditar
    relato_bruto = st.text_area("Digite ou dite o relato bruto da ocorrência:", height=150, placeholder="Ex: Por volta das 6h18 o funcionário parou em vaga irregular na portaria 5...")
    
    if st.button("Gerar Boletim de Ocorrência"):
        if relato_bruto.strip() == "":
            st.warning("Por favor, digite o relato antes de gerar.")
        else:
            with st.spinner("O Gemini está organizando e formatando o relatório... Aguarde."):
                try:
                    # Inicializa o modelo do Gemini
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    # Prompt focado em segurança patrimonial industrial
                    prompt = (
                        "Você é um especialista em segurança patrimonial industrial. "
                        "Pegue o seguinte relato bruto de um vigilante e transforme-o em um "
                        "Boletim de Ocorrência formal, profissional, corrigindo a gramática, "
                        "ajustando a concordância e organizando os fatos em ordem cronológica clara. "
                        "Mantenha um tom técnico, impessoal e limpo:\n\n"
                        f"{relato_bruto}"
                    )
                    
                    response = model.generate_content(prompt)
                    
                    # Mostra o resultado na tela
                    st.success("Boletim Gerado com Sucesso!")
                    st.markdown("### 📋 Boletim de Ocorrência Formatado:")
                    st.markdown(f'<div class="bo-box">{response.text}</div>', unsafe_allow_html=True)
                    
                except Exception as e:
                    st.error(f"Erro ao processar com a IA: {e}")
