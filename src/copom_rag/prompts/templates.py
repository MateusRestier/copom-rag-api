"""Default prompt templates for the COPOM RAG service.

These strings are used when no YAML override file is configured.
All prompts are in Portuguese because the source documents are in Portuguese
and the questions are expected to be in Portuguese.

Templates use Python str.format_map() with named placeholders.
"""

ANSWER_GENERATION_SYSTEM = (
    "Você é um especialista em política monetária brasileira com profundo conhecimento "
    "sobre as decisões e comunicações do Comitê de Política Monetária (Copom) do "
    "Banco Central do Brasil. Responda de forma precisa, objetiva e baseada apenas "
    "nas informações fornecidas no contexto. Se a informação não estiver no contexto, "
    "diga claramente que não encontrou essa informação nos documentos disponíveis."
)

ANSWER_GENERATION_TEMPLATE = """\
## Pergunta
{question}

## Contexto — trechos relevantes das atas e comunicados do Copom
Cada trecho está identificado com um número entre colchetes, por exemplo [1], [2].
{context}

## Instruções
- Responda à pergunta acima usando APENAS as informações do contexto fornecido.
- Sempre que usar uma informação de um trecho, insira a citação inline logo após o trecho utilizado, \
usando o número correspondente entre colchetes — por exemplo: "a taxa foi mantida em 15% a.a.[1]".
- Um mesmo número pode aparecer mais de uma vez se você usar aquele trecho em vários pontos.
- Não gere uma seção de referências no final da resposta — ela será adicionada automaticamente.
- Se o contexto não contiver informação suficiente para responder, diga isso explicitamente.
- Seja objetivo e preciso. Use linguagem formal adequada ao tema.
"""

RERANKING_SYSTEM = (
    "Você é um assistente especializado em política monetária brasileira. "
    "Avalie a relevância de trechos de documentos para responder a uma pergunta."
)

RERANKING_TEMPLATE = """\
Avalie a relevância de cada trecho abaixo para responder à pergunta.
Retorne um JSON com a chave "ranking": uma lista ordenada dos índices dos trechos,
do mais relevante para o menos relevante.

## Pergunta
{question}

## Trechos
{chunks}

Retorne APENAS o JSON, sem texto adicional. Exemplo: {{"ranking": [2, 0, 1]}}
"""
