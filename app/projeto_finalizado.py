import streamlit as st
import pandas as pd
import openpyxl
import openai
import os
import re
from PyPDF2 import PdfReader
from utils_openai import retorna_resposta_modelo
from utils_files import *

st.set_page_config(page_title="GPT Ambev", layout='centered')

# INICIALIZAÇÃO ==================================================
def inicializacao():
    if not 'mensagens' in st.session_state:
        st.session_state.mensagens = []
    if not 'conversa_atual' in st.session_state:
        st.session_state.conversa_atual = ''
    if not 'modelo' in st.session_state:
        st.session_state.modelo = 'gpt-4o'
    if not 'api_key' in st.session_state:
        st.session_state.api_key = le_chave()
    if 'df_texto' not in st.session_state:
        st.session_state.df_texto = None
    if 'texto' not in st.session_state:  # Inicializar 'texto' caso não exista
        st.session_state.texto = None

    chave = "sua chave"
    if chave != st.session_state['api_key']:
         st.session_state['api_key'] = chave
         salva_chave(chave)
         st.sidebar.success('Chave salva com sucesso')

def clean_text(text):
    """Remove menções de usuários do texto."""
    text = re.sub(r'@\w+', '', text)  # Remove menções de usuários
    text = text.strip()  # Remove espaços em branco extras
    return text

def handle_uploaded_file(uploaded_file, limit=5000):
    try:
        if uploaded_file:
            df = pd.read_excel(uploaded_file)
            tamanho = len(df)
            df = df[df['Texto'].apply(lambda x: isinstance(x, str))]
            df['Texto'] = df['Texto'].apply(clean_text)
            df = df.dropna(subset=['Texto'])
            df = df[df['Texto'] != '']
            df = df.head(limit)
            df.reset_index(drop=True, inplace=True)
            if 'Texto' in df.columns:
                st.dataframe(df['Texto'])
                tamanho_limpo = len(df)
                st.info(f"{tamanho - tamanho_limpo} comentários foram removidos por não contribuírem com a análise!")
                return df
            else:
                st.error("A coluna 'Texto' não foi encontrada no arquivo.")

    except Exception as e:
        st.error("A coluna 'Texto' não foi encontrada no arquivo.")
    return None

def handle_uploaded_file_pdf(uploaded_file):
    text=""
    pdf_reader= PdfReader(uploaded_file)
    for page in pdf_reader.pages:
        text+= page.extract_text()
    return  text


def display_results(results):
    if results:
        results_str = ''.join(results)
        st.write(results_str)


def pagina_principal():
    st.header('🍺 Ambev Chatbot', divider=True)

    if st.button('Melhores Práticas'):
        st.session_state.show_info = not st.session_state.get('show_info', False)
    if st.session_state.get('show_info', False):
        with st.expander("Como utilizar o chat"):
            st.write("""
               Esse chatbot é um GPT Geral, feito para conversar livremente sobre qualquer assunto, podendo enviar arquivos .xlsx ou PDF para análise.
            """)
        with st.expander("Tipo de arquivo"):
            st.write("""
                O chatbot aceita apenas arquivos Excel (.xlsx) com uma coluna chamada 'Texto' contendo os comentários OU arquivo PDF.
            """)
        with st.expander("Comentários removidos"):
            st.write("""
                O modelo remove os comentários que são linhas vazias e menções a outros usuários, para garantir uma análise precisa sobre o tema.
            """)

    # Carregar o arquivo e processar o conteúdo
    uploaded_file = st.file_uploader("Faça o upload do arquivo Excel ou PDF com os comentários sobre a crise", help="O arquivo deve conter uma coluna chamada 'Texto'.", accept_multiple_files=False)
    if uploaded_file:  
        if uploaded_file.name.endswith('.xlsx'):
            st.session_state.df_texto = handle_uploaded_file(uploaded_file)

        elif uploaded_file.name.endswith('.pdf'):
            st.session_state.texto = handle_uploaded_file_pdf(uploaded_file) # Trocar essa funçao para ler pdf
        
        else:
            st.warning("Por favor, faça o upload de um arquivo Excel (.xlsx) ou PDF.")
    
    # Mostrar histórico da conversa
    for mensagem in st.session_state.mensagens:
        if mensagem['role'] == 'user':
            st.chat_message('user').markdown(mensagem['content'])
        else:
            st.chat_message('assistant').markdown(mensagem['content'])

    prompt = st.chat_input('Fale com o chat')
    if prompt:
        if st.session_state['api_key'] == '':
            st.error('Adicione uma chave de API na aba de configurações')
        else:
            # Adicionar a nova mensagem do usuário
            nova_mensagem_usuario = {'role': 'user', 'content': prompt}
            st.session_state.mensagens.append(nova_mensagem_usuario)
            st.chat_message('user').markdown(prompt)
            
            # Inicializar 'comentarios_texto'
            comentarios_texto = ""

            # Adicionar conteúdo do arquivo ao prompt se existir
            if st.session_state.df_texto is not None and not st.session_state.df_texto['Texto'].empty:
                comentarios_texto = '\n'.join(st.session_state.df_texto['Texto'].tolist())
                prompt_completo = f"{prompt}\n\nComentários do arquivo:\n{comentarios_texto}"
        
           
            elif st.session_state.texto is not None:
                prompt_completo = f"{prompt}\n\nArquivo PDF:\n{st.session_state.texto}"
            
            else:
                prompt_completo = prompt

            # Obter resposta do modelo
            chat = st.chat_message('assistant')
            placeholder = chat.empty()
            placeholder.markdown("▌")
            resposta_completa = ''
            try:
                respostas = retorna_resposta_modelo(st.session_state.mensagens + [{'role': 'user', 'content': prompt_completo}], st.session_state['api_key'], modelo=st.session_state['modelo'], stream=True)
                for resposta in respostas:
                    resposta_completa += resposta.choices[0].delta.get('content', '')
                    placeholder.markdown(resposta_completa + "▌")
                placeholder.markdown(resposta_completa)
                nova_mensagem_assistente = {'role': 'assistant', 'content': resposta_completa}
                st.session_state.mensagens.append(nova_mensagem_assistente)
            except Exception as e:
                st.error(f"Erro ao obter resposta do modelo: {e}")


    if st.session_state.mensagens:
        df_mensagens = pd.DataFrame(st.session_state.mensagens)
        csv = df_mensagens.to_csv(index=False, sep=':', encoding='utf-8', header=False)

        st.download_button(
            label="Baixar Conversa",
            data=csv,
            file_name='conversa.csv',
            mime='text/csv'
        )
# MAIN ==================================================
def main():
    inicializacao()
    pagina_principal()
  
    
if __name__ == '__main__':
    main()
