import os
import streamlit as st
from dotenv import load_dotenv
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.chat_models import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.callbacks.base import BaseCallbackHandler
from langchain.retrievers import BM25Retriever, EnsembleRetriever
from langchain.prompts import PromptTemplate

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-3.5-turbo")

class StreamlitCallbackHandler(BaseCallbackHandler):
    def __init__(self, container):
        self.container = container
        self.text = ""

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        self.text += token
        self.container.markdown(self.text)

    def get_final_text(self):
        return self.text

# Create OpenAI embeddings
embeddings = OpenAIEmbeddings(
    model=EMBEDDING_MODEL,
    openai_api_key=OPENAI_API_KEY
)

# Load the FAISS index
try:
    vectorstore = FAISS.load_local(
        "faiss_index", embeddings, allow_dangerous_deserialization=True
    )
except Exception as e:
    st.error(f"Failed to load FAISS index: {str(e)}")
    st.stop()

# Create semantic retriever (FAISS)
vector_retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# Create keyword-based retriever (BM25)
documents = [doc for doc in vectorstore.docstore._dict.values()]
keyword_retriever = BM25Retriever.from_documents(documents)
keyword_retriever.k = 3

# Create hybrid retriever
hybrid_retriever = EnsembleRetriever(
    retrievers=[vector_retriever, keyword_retriever], 
    weights=[0.7, 0.3]
)

# Define custom prompt template
custom_prompt_template = """
You are an assistant providing information from AMU's official documents.
Use the following extracted content to answer the query as accurately as possible.

Context:
{context}

Query: {question}

Instructions:
- Respond only using the provided context to answer the query as accurately as possible.
- If the context contains relevant information, provide the answer using the exact wording from the context without paraphrasing or summarizing unless explicitly asked. Consolidate any repeated information (e.g., eligibility criteria or lists) into a single coherent response based on the preprocessed context, ensuring no duplication of criteria or lists.
- If the context does not contain any relevant information to answer the query, say "I couldn't find this in AMU's documents" and do not include a source link.
- Do not include any source citation (e.g., "Source: [link]") in the response, as the source link will be handled separately.
- If extracting information from a table, provide the relevant table content in the response.
- Ensure the response clearly connects the user's query to the information provided in the context.
"""
PROMPT = PromptTemplate(
    template=custom_prompt_template, input_variables=["context", "question"]
)

# STREAMLIT UI
st.set_page_config(page_title="AMU QueryBot")
st.title("AMU QueryBot")

# Session state for chat history
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = [
        {'role': 'assistant', 'content': "Hello, I am a bot. How can I help you?"}
    ]

# Display chat history
for message in st.session_state.chat_history:
    st.chat_message(message['role']).markdown(message['content'])

# Input prompt
prompt = st.chat_input("Enter your query...")

if prompt:
    st.chat_message('user').markdown(prompt)
    st.session_state.chat_history.append({'role': 'user', 'content': prompt})

    # Create the assistant response
    with st.chat_message("assistant"):
        response_container = st.empty()
        stream_handler = StreamlitCallbackHandler(response_container)

        # Initialize OpenAI model
        llm = ChatOpenAI(
            api_key=OPENAI_API_KEY,
            model_name=CHAT_MODEL,
            temperature=0,
            streaming=True,
            callbacks=[stream_handler],
        )

        # Create RetrievalQA chain with custom prompt
        chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=hybrid_retriever,
            input_key="question",
            return_source_documents=True,
            chain_type_kwargs={"prompt": PROMPT}
        )

        # Invoke chain with raw prompt
        result = chain.invoke({"question": prompt})

        # Extract answer safely
        answer = result.get("result", "No answer found in the response.").strip()

        # Extract unique source links from metadata of retrieved documents
        source_links = list(set(
            doc.metadata.get("source", "") for doc in result["source_documents"] if doc.metadata.get("source")
        ))

        # Determine response based on whether answer is from context
        if "I couldn't find this in AMU's documents" not in answer and source_links:
            sources_text = "\n\nSources:\n" + "\n".join([f"- {link}" for link in source_links])
            response = f"{answer}{sources_text}"
        else:
            response = answer  # No source links when answer is not from context or no valid sources

        # Update response container with final response
        response_container.markdown(response)

        # Store final response in chat history
        st.session_state.chat_history.append({'role': 'assistant', 'content': response})