import openai

def retorna_resposta_modelo(mensagens, api_key, modelo='gpt-4o', stream=False):
    openai.api_key = api_key
    try:
        response = openai.ChatCompletion.create(
            model=modelo,
            messages=mensagens,
            stream=stream
        )
        return response
    except Exception as e:
        print(f"Erro ao chamar a API do OpenAI: {e}")
        raise e
