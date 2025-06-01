import os
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.chat_models import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from langchain.prompts import PromptTemplate
from langchain_community.document_loaders import DirectoryLoader, TextLoader
import pickle
from pathlib import Path
from typing import AsyncGenerator, Generator

from dotenv import load_dotenv
load_dotenv()

# Get the base directory for the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Initialize OpenAI API key
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

EMBEDDING_MODEL = "text-embedding-3-large"
CHAT_MODEL = "gpt-3.5-turbo"
FAISS_INDEX_PATH = BASE_DIR / "core" / "faiss_index"
DOCUMENTS_PATH = BASE_DIR / "documents"  # Directory where documents will be stored

def load_documents():
    """Load documents from the documents directory"""
    if not DOCUMENTS_PATH.exists():
        DOCUMENTS_PATH.mkdir(parents=True, exist_ok=True)
        # Create a sample document if no documents exist
        sample_doc_path = DOCUMENTS_PATH / "sample.txt"
        if not sample_doc_path.exists():
            with open(sample_doc_path, "w", encoding="utf-8") as f:
                f.write("This is a sample document. Replace this with your actual AMU documents.")
    
    try:
        # Load all text files from the documents directory
        loader = DirectoryLoader(
            str(DOCUMENTS_PATH),
            glob="**/*.*",
            loader_cls=TextLoader,
            loader_kwargs={'encoding': 'utf-8'}
        )
        documents = loader.load()
        print(f"Loaded {len(documents)} documents")
        return documents
    except Exception as e:
        print(f"Error loading documents: {str(e)}")
        return []

def initialize_embeddings():
    """Initialize and return OpenAI embeddings"""
    return OpenAIEmbeddings(
        model=EMBEDDING_MODEL,
        openai_api_key=OPENAI_API_KEY
    )

def initialize_llm():
    """Initialize and return the language model"""
    return ChatOpenAI(
        api_key=OPENAI_API_KEY,
        model_name=CHAT_MODEL,
        temperature=0,
        streaming=True  # Enable streaming
    )

def load_or_create_vector_store():
    """Load existing vector store or create a new one"""
    embeddings = initialize_embeddings()
    
    try:
        if FAISS_INDEX_PATH.exists():
            print("Loading existing FAISS index...")
            return FAISS.load_local(
                str(FAISS_INDEX_PATH),
                embeddings,
                allow_dangerous_deserialization=True  # Only allow this because we created the index ourselves
            )
        else:
            print("Creating new FAISS index...")
            documents = load_documents()
            if not documents:
                raise ValueError("No documents found to create the vector store")
            
            # Create and save the vector store
            vector_store = FAISS.from_documents(documents, embeddings)
            FAISS_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
            vector_store.save_local(str(FAISS_INDEX_PATH))
            return vector_store
    except Exception as e:
        print(f"Error loading/creating vector store: {str(e)}")
        raise

def setup_retrievers(vector_store):
    """Set up the hybrid retrieval system"""
    # Vector store retriever
    vector_retriever = vector_store.as_retriever(search_kwargs={"k": 3})
    
    # BM25 retriever
    documents = [doc for doc in vector_store.docstore._dict.values()]
    keyword_retriever = BM25Retriever.from_documents(documents)
    keyword_retriever.k = 3
    
    # Combine retrievers
    return EnsembleRetriever(
        retrievers=[vector_retriever, keyword_retriever],
        weights=[0.7, 0.3]
    )

# Define custom prompt template with formatting instructions
PROMPT_TEMPLATE = """
You are an assistant providing information from AMU's official documents.
Use the following extracted content to answer the query as accurately as possible.

Context:
{context}

Query: {question}

Instructions:
- Respond only using the provided context to answer the query as accurately as possible.
- If the context contains relevant information, provide the answer using the exact wording from the context without paraphrasing or summarizing unless explicitly asked.
- If the context does not contain any relevant information to answer the query, say "I couldn't find this in AMU's documents" and do not include a source link.
- Do not include any source citation in the response, as the source link will be handled separately.
- If extracting information from a table, provide the relevant table content in the response.
- Ensure the response clearly connects the user's query to the information provided in the context.
"""

def create_qa_chain():
    """Create and return the QA chain"""
    try:
        # Initialize components
        vector_store = load_or_create_vector_store()
        retriever = setup_retrievers(vector_store)
        llm = initialize_llm()
        
        # Create prompt
        prompt = PromptTemplate(
            template=PROMPT_TEMPLATE,
            input_variables=["context", "question"]
        )
        
        # Create chain
        chain = (
            {"context": retriever, "question": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
        )
        
        return chain, retriever  # Return retriever for source access
    except Exception as e:
        print(f"Error creating QA chain: {str(e)}")
        raise

# Global chain and retriever instances
qa_chain = None
qa_retriever = None

def get_qa_chain():
    """Get or create the QA chain and retriever"""
    global qa_chain, qa_retriever
    if qa_chain is None or qa_retriever is None:
        qa_chain, qa_retriever = create_qa_chain()
    return qa_chain, qa_retriever

# Initialize the chain and retriever at module level
chain, retriever = get_qa_chain()

async def get_response(query: str) -> AsyncGenerator[str, None]:
    """Process query and stream response with formatted output and source link"""
    try:
        # Ensure query is a string
        if not isinstance(query, str):
            query = str(query)
        
        # Get the chain and retriever
        chain, retriever = get_qa_chain()
        
        # Retrieve documents to extract source
        retrieved_docs = retriever.invoke(query)
        source = retrieved_docs[0].metadata.get('source', 'Unknown source') if retrieved_docs else 'Unknown source'
        
        # Stream the response
        response_text = ""
        async for chunk in chain.astream(query):
            response_text += chunk
            yield chunk
        
        # After streaming is complete, yield the source if response was found
        if response_text.strip() != "I couldn't find this in AMU's documents.":
            yield f"\n\n Source- {source}"
            
    except Exception as e:
        print(f"Error in get_response: {str(e)}")
        yield "I apologize, but I encountered an error processing your request. Please try again."