"""Document handling tools using docling and ChromaDB with chunking and metadata."""
import chromadb
import nltk
from docling.document_converter import DocumentConverter
from sentence_transformers import SentenceTransformer

# Download the sentence tokenizer model if not already downloaded
try:
    nltk.data.find('tokenizers/punkt')
except nltk.downloader.DownloadError:
    nltk.download('punkt')

# Initialize ChromaDB client and create/get the 'rag' collection
client = chromadb.Client()
collection = client.get_or_create_collection("rag")

# Load the sentence transformer model
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

def chunk_text(text: str, sentences_per_chunk: int = 5) -> list[str]:
    """Chunks the text into smaller pieces of a specified number of sentences."""
    sentences = nltk.sent_tokenize(text)
    chunks = []
    for i in range(0, len(sentences), sentences_per_chunk):
        chunk = " ".join(sentences[i:i + sentences_per_chunk])
        chunks.append(chunk)
    return chunks

def process_document_and_store_in_db(file_path: str) -> str:
    """
    Processes a document from a file path, chunks it, creates embeddings, and stores it in the 'rag' ChromaDB collection.

    Args:
        file_path: The path to the document file.

    Returns:
        A confirmation message indicating the document has been processed and stored.
    """
    # Use docling to convert the document
    converter = DocumentConverter()
    result = converter.convert(file_path)
    document_content = result.document.export_to_markdown()

    # Chunk the document content
    chunks = chunk_text(document_content)

    # Create embeddings for each chunk
    embeddings = [embedding_model.encode(chunk).tolist() for chunk in chunks]

    # Create metadata for each chunk
    metadatas = [
        {"source": file_path, "chunk_number": i}
        for i in range(len(chunks))
    ]

    # Create unique IDs for each chunk
    ids = [f"{file_path}_{i}" for i in range(len(chunks))]

    # Store the chunks, embeddings, and metadata in the 'rag' collection
    collection.add(
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas,
        ids=ids
    )

    return f"Document '{file_path}' processed, chunked, and stored in the 'rag' ChromaDB collection."

def find_similar_documents(query: str, top_k: int = 3) -> list:
    """
    Finds similar document chunks in the 'rag' collection based on a query.

    Args:
        query: The query to search for.
        top_k: The number of similar chunks to return.

    Returns:
        A list of dictionaries, where each dictionary contains the chunk content, metadata, and similarity score.
    """
    if collection.count() == 0:
        return []

    query_embedding = embedding_model.encode(query).tolist()

    # Query the 'rag' collection
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )

    # Format the results
    similar_chunks = []
    if results and results['ids']:
        for i, doc_id in enumerate(results['ids'][0]):
            distance = results['distances'][0][i]
            metadata = results['metadatas'][0][i]
            document = results['documents'][0][i]
            similar_chunks.append({
                "id": doc_id,
                "chunk_content": document,
                "metadata": metadata,
                "similarity": 1 - distance # Convert distance to similarity score
            })

    return similar_chunks
