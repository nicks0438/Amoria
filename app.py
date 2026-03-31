import streamlit as st
import requests
import json
import uuid
import base64
import time

# --- 1. CONFIGURAÇÕES DE IDENTIDADE E INTERFACE ---
st.set_page_config(page_title="Amoria", page_icon="🤖", layout="wide")

# --- 2. AS DUAS CHAVES DE API E URLs ---
TEXT_API_KEY = st.secrets["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"]
IMAGE_API_KEY = st.secrets["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"]

TEXT_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
IMAGE_URL = "https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.2-klein-4b"

headers_text = {
    "Authorization": f"Bearer {TEXT_API_KEY}",
    "Accept": "text/event-stream",
    "Content-Type": "application/json"
}

headers_image = {
    "Authorization": f"Bearer {IMAGE_API_KEY}",
    "Accept": "application/json",
    "Content-Type": "application/json"
}

def gerar_questoes_formulario(assunto):
    prompt_sistema = """
    Você é um gerador de formulários educativos. 
    Crie EXATAMENTE 10 questões inéditas, criativas e variadas sobre o assunto solicitado.
    As questões devem ser desafiadoras e educativas.
    
    Retorne APENAS um JSON no seguinte formato:
    [
      {
        "tipo": "multipla", 
        "pergunta": "Texto da pergunta", 
        "opcoes": ["A", "B", "C", "D"], 
        "correta": "A"
      },
      {
        "tipo": "escrita", 
        "pergunta": "Texto da pergunta dissertativa"
      }
    ]
    """
    payload = {
        "model": "mistralai/mistral-small-4-119b-2603",
        "messages": [
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": f"Assunto: {assunto}"}
        ],
        "temperature": 0.8 
    }
    try:
        res = requests.post(TEXT_URL, headers=headers_text, json=payload)
        conteudo = res.json()['choices'][0]['message']['content'].replace('```json', '').replace('```', '').strip()
        return json.loads(conteudo)
    except Exception as e:
        st.error(f"Erro ao gerar perguntas: {e}")
        return None

# --- 3. INICIALIZAÇÃO DE VARIÁVEIS DE SESSÃO ---
if "chats" not in st.session_state:
    st.session_state.chats = {} 
if "current_chat" not in st.session_state:
    primeiro_id = str(uuid.uuid4())
    st.session_state.chats[primeiro_id] = [
        {"role": "system", "content": "Você é uma IA educacional didática que fala Português. Seu nome é Amoria, e seu objetivo é explicar conteúdos de forma clara e objetiva."}
    ]
    st.session_state.current_chat = primeiro_id
if "historico_forms" not in st.session_state:
    st.session_state.historico_forms = []
if "modo_form" not in st.session_state:
    st.session_state.modo_form = False
if "questoes" not in st.session_state:
    st.session_state.questoes = None

# --- 4. BARRA LATERAL ORGANIZADA ---
with st.sidebar:
    st.title("⚙️ Painel Amoria")
    
    st.subheader("Configurações")
    gerar_imagem = st.toggle("🎨 Modo Gerar Imagem", help="Ative para ilustrar as respostas do chat.")
    st.divider()

    st.subheader("💬 Conversas")
    if st.button("➕ Nova Conversa", use_container_width=True):
        novo_id = str(uuid.uuid4())
        st.session_state.chats[novo_id] = [
            {"role": "system", "content": "Você é uma IA educacional didática que fala Português. Seu nome é Amoria..."}
        ]
        st.session_state.current_chat = novo_id
        st.rerun()
    
    if len(st.session_state.chats) > 1:
        chat_escolhido = st.selectbox(
            "Alternar entre conversas:",
            options=list(st.session_state.chats.keys()),
            format_func=lambda x: f"Conversa {x[:8]}..."
        )
        st.session_state.current_chat = chat_escolhido

    st.divider()

    st.subheader("📝 Ferramentas de Estudo")
    if st.button("📝 Criar Novo Formulário", use_container_width=True):
        st.session_state.modo_form = True
        st.session_state.questoes = None
        st.rerun()

    if st.session_state.historico_forms:
        with st.expander("📈 Ver Meus Resultados", expanded=False):
            for form in reversed(st.session_state.historico_forms):
                st.write(f"**{form['tema']}**")
                st.caption(f"Nota: {form['nota']:.1f}/10")
                st.divider()
    
    if st.button("🗑️ Limpar Tudo", use_container_width=True, help="Apaga conversas e notas"):
        st.session_state.chats = {}
        st.session_state.historico_forms = []
        st.rerun()
    
    st.divider()
    
    # Lista de chats deletáveis
    for chat_id in list(st.session_state.chats.keys()):
        mensagens = st.session_state.chats[chat_id]
        titulo_chat = "Nova Conversa"
        for msg in mensagens:
            if msg["role"] == "user":
                titulo_chat = msg["content"][:20] + "..."
                break
        
        marcador = "📍 " if chat_id == st.session_state.current_chat else ""
        col1, col2 = st.columns([4, 1])
        with col1:
            if st.button(f"{marcador}{titulo_chat}", key=f"btn_{chat_id}", use_container_width=True):
                st.session_state.current_chat = chat_id
                st.rerun()
        with col2:
            if st.button("🗑️", key=f"del_{chat_id}"):
                del st.session_state.chats[chat_id]
                if not st.session_state.chats:
                    st.session_state.current_chat = None
                st.rerun()

# --- 5. ÁREA PRINCIPAL: FORMULÁRIOS ---
st.title("🎓 Amoria: IA Educacional")
st.caption("Desenvolvido por Nicolas Lengler Warken")

if st.session_state.modo_form:
    st.info("📝 **Modo Formulário**")
    
    # TELA A: ESCOLHA DE TEMA (Onde você quer o botão de voltar)
    if st.session_state.questoes is None:
        tema = st.text_input("Sobre qual assunto vamos praticar hoje?")
        
        col1, col2 = st.columns(2)
        with col1:
            btn_gerar = st.button("Gerar Formulário Completo", use_container_width=True)
            if btn_gerar and tema:
                with st.spinner("Amoria está elaborando suas questões..."):
                    st.session_state.questoes = gerar_questoes_formulario(tema)
                    st.session_state.tema_atual = tema
                    st.rerun()
        with col2:
            # BOTÃO DE SAÍDA ANTES DE GERAR
            if st.button("⬅️ Voltar para o Chat", use_container_width=True):
                st.session_state.modo_form = False
                st.rerun() # Isso força o Streamlit a ler o código do chat abaixo

        st.stop() # Interrompe aqui APENAS se o modo_form for True
        
    # TELA B: RESOLUÇÃO DO FORMULÁRIO (Questões já geradas)
    else:
        if st.button("⬅️ Cancelar e Voltar ao Chat", use_container_width=True):
            st.session_state.modo_form = False
            st.session_state.questoes = None
            st.rerun()
            
        st.divider()
        respostas_usuario = {}

        for i, q in enumerate(st.session_state.questoes):
            st.write(f"**{i+1}. {q['pergunta']}**")
            if q['tipo'] == "multipla":
                respostas_usuario[i] = st.radio(f"Escolha uma opção (Q{i+1}):", q['opcoes'], key=f"q{i}")
            else:
                respostas_usuario[i] = st.text_area(f"Sua resposta (Q{i+1}):", key=f"q{i}")
            st.divider()
            
        if st.button("Finalizar, Corrigir e Salvar"):
            st.subheader("📊 Seu Desempenho")
            acertos = 0
            total_multipla = sum(1 for q in st.session_state.questoes if q['tipo'] == "multipla")
            
            for i, q in enumerate(st.session_state.questoes):
                if q['tipo'] == "multipla":
                    resp_usuario = respostas_usuario[i]
                    correta = q['correta']
                    
                    if resp_usuario == correta:
                        st.success(f"✅ Questão {i+1}: Você acertou! Resposta: {resp_usuario}")
                        acertos += 1
                    else:
                        st.error(f"❌ Questão {i+1}: Você marcou {resp_usuario}, o correto era **{correta}**.")
                else:
                    st.info(f"📝 Questão {i+1} (Escrita): Sua resposta foi enviada para análise.")
            
            if total_multipla > 0:
                nota = (acertos / total_multipla) * 10
                st.metric("Sua Nota Final", f"{nota:.1f}/10")
                
                st.session_state.historico_forms.append({
                    "tema": st.session_state.tema_atual,
                    "nota": nota,
                    "acertos": acertos,
                    "total": total_multipla
                })
                
                if nota >= 7:
                    st.balloons()
                    st.success("Parabéns! Você domina bem esse assunto. 🚀")
                else:
                    st.warning("Continue estudando! Que tal pedir para a Amoria te explicar os pontos que você errou?")
            
            if st.button("Concluir e Voltar ao Chat"):
                st.session_state.modo_form = False
                st.session_state.questoes = None
                st.rerun()
                
        st.stop() # Mantém o chat invisível enquanto o form está ativo

# --- 6. ÁREA PRINCIPAL: CHAT ---
# Proteção caso não exista chat ativo
if st.session_state.current_chat and st.session_state.current_chat in st.session_state.chats:
    mensagens_atuais = st.session_state.chats[st.session_state.current_chat]
    
    for message in mensagens_atuais:
        if message["role"] != "system":
            with st.chat_message(message["role"]):
                if message.get("type") == "image":
                    st.image(message["content"], caption="Gerado pela Amoria")
                else:
                    st.markdown(message["content"])

    if prompt := st.chat_input("Como posso ajudar nos seus estudos?"):
        st.session_state.chats[st.session_state.current_chat].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            if gerar_imagem:
                with st.spinner("Amoria está preparando o seu material visual..."):
                    payload = {"prompt": prompt}
                    try:
                        response = requests.post(IMAGE_URL, headers=headers_image, json=payload)
                        if response.status_code == 200:
                            res_json = response.json()
                            artifacts = res_json.get("artifacts", [])
                            img_b64 = None
                            
                            if artifacts and len(artifacts) > 0:
                                img_b64 = artifacts[0].get("base64")
                            elif "image" in res_json:
                                img_b64 = res_json["image"]
                            
                            if img_b64:
                                image_bytes = base64.b64decode(img_b64)
                                st.image(image_bytes, caption="Gerado pela Amoria")
                                
                                st.download_button(
                                    label="⬇️ Baixar Imagem",
                                    data=image_bytes,
                                    file_name=f"amoria_{int(time.time())}.png",
                                    mime="image/png",
                                    use_container_width=True
                                )
                                
                                st.session_state.chats[st.session_state.current_chat].append({
                                    "role": "assistant", "content": image_bytes, "type": "image"
                                })
                            else:
                                st.error("A API respondeu com sucesso, mas a imagem não foi encontrada.")
                        else:
                            st.error(f"Erro na API de Imagem: {response.status_code} - {response.text}")
                    except Exception as e:
                        st.error(f"Erro de conexão: {e}")
            else:
                placeholder = st.empty()
                full_response = ""
                
                # FILTRO DE SEGURANÇA: Remove imagens do histórico enviado à API de texto
                historico_texto_apenas = [
                    {"role": m["role"], "content": m["content"]} 
                    for m in st.session_state.chats[st.session_state.current_chat] 
                    if m.get("type") != "image"
                ]

                payload = {
                    "model": "mistralai/mistral-small-4-119b-2603",
                    "messages": historico_texto_apenas,
                    "stream": True
                }
                
                try:
                    r = requests.post(TEXT_URL, headers=headers_text, json=payload, stream=True)
                    for line in r.iter_lines():
                        if line:
                            line_text = line.decode("utf-8")
                            if line_text.startswith("data: "):
                                json_str = line_text[6:].strip()
                                if json_str == "[DONE]":
                                    break
                                try:
                                    data = json.loads(json_str)
                                    if 'choices' in data and len(data['choices']) > 0:
                                        delta = data['choices'][0].get('delta', {})
                                        content = delta.get('content', '')
                                        full_response += content
                                        placeholder.markdown(full_response + "▌")
                                except Exception:
                                    continue
                    
                    placeholder.markdown(full_response)
                    st.session_state.chats[st.session_state.current_chat].append({"role": "assistant", "content": full_response})
                except Exception as e:
                    st.error(f"Erro na conexão de texto: {e}")

# --- 7. RODAPÉ ---
st.markdown(
    """
    <style>
    .disclaimer-container {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        background-color: transparent;
        padding: 10px 0;
        text-align: center;
        z-index: 100;
    }
    .disclaimer-text {
        color: #808080;
        font-size: 0.8rem;
        margin: 0;
    }
    </style>
    <div class="disclaimer-container">
        <p class="disclaimer-text">Amoria pode cometer erros. Considere verificar informações importantes.</p>
    </div>
    """,
    unsafe_allow_html=True
)