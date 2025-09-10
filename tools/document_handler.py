"""Document handling tools using docling."""
import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from docling.document_converter import DocumentConverter
import chromadb
from sentence_transformers import SentenceTransformer
import uuid

load_dotenv(override=True)

def process_document(file_path: str) -> str:
    """
    Processes a document from a file path and returns its content.

    Args:
        file_path: The path to the document file.

    Returns:
        The content of the document as a string.
    """
    # Use docling to convert the document
    converter = DocumentConverter()
    result = converter.convert(file_path)
    document_content = result.document.export_to_markdown()
    return document_content

def suggest_metadata(document_content: str) -> dict:
    """
    Suggests metadata and tags for a given document content.

    Args:
        document_content: The content of the document.

    Returns:
        A dictionary containing suggested metadata and tags.
    """
    try:
        client = OpenAI(
            api_key=os.environ["XAI_API_KEY"],
            base_url=os.environ["XAI_BASE_URL"],
        )
    except KeyError:
        raise RuntimeError("Missing xAI credentials. Please set XAI_API_KEY and XAI_BASE_URL in your .env file.")

    prompt = f'''You are a metadata suggestion expert.
You will be given a document and you need to suggest a title, a short summary, and a list of tags.
The output should be a JSON object with the keys "title", "summary", and "tags".
The summary should be a single sentence.
The tags should be a list of strings.

Here is the document:

{document_content}
'''

    if len(prompt) > 16000:
        prompt = prompt[:16000] + "... (truncated)"


    response = client.chat.completions.create(
        model="grok-3-fast",
        messages=[
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )

    try:
        metadata = json.loads(response.choices[0].message.content)
        return metadata
    except (json.JSONDecodeError, KeyError):
        return {
            "title": "Could not generate title",
            "summary": "Could not generate summary",
            "tags": [],
        }


def vectorize_and_store_document(document_content: str, metadata: dict) -> str:
    """
    Vectorizes the document content and stores it with metadata in ChromaDB.

    Args:
        document_content: The content of the document.
        metadata: The metadata for the document.

    Returns:
        A string indicating the result of the operation.
    """
    try:
        # Initialize the sentence transformer model
        model = SentenceTransformer('all-MiniLM-L6-v2')

        # Initialize the ChromaDB client
        try:
            api_key = os.environ["CHROMA_API_KEY"]
            tenant = os.environ["CHROMA_TENANT"]
            database = os.environ["CHROMA_DATABASE"]
        except KeyError:
            raise ConnectionError(
                "ChromaDB Cloud credentials not found. Please set CHROMA_API_KEY, "
                "CHROMA_TENANT, and CHROMA_DATABASE in your environment variables."
            )

        client = chromadb.CloudClient(
            api_key=api_key,
            tenant=tenant,
            database=database
        )
        # Get or create a collection
        collection = client.get_or_create_collection("documents")

        # Generate a unique ID for the document
        doc_id = str(uuid.uuid4())

        # Generate embeddings for the document content
        embeddings = model.encode(document_content)

        # Store the document in the collection
        collection.add(
            embeddings=[embeddings.tolist()],
            documents=[document_content],
            metadatas=[metadata],
            ids=[doc_id]
        )

        return f"Document stored successfully with ID: {doc_id}"
    except Exception as e:
        return f"Error storing document: {e}"


def get_tools():
    """Returns the tools for the document handler."""
    return [
        {
            "type": "function",
            "function": {
                "name": "process_document",
                "description": "Processes a document from a given file path by converting it into a clean Markdown format. This tool is useful for extracting text and structure from various document types (like PDF, DOCX, etc.) for further analysis or processing.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "The path to the document file."
                        }
                    },
                    "required": ["file_path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "suggest_metadata",
                "description": "Analyzes the provided document content and suggests relevant metadata, including a concise title, a set of descriptive tags (keywords), and a brief summary. This is useful for cataloging, organizing, and enabling efficient retrieval of documents.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "document_content": {
                            "type": "string",
                            "description": "The content of the document."
                        }
                    },
                    "required": ["document_content"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "vectorize_and_store_document",
                "description": "Takes the text content of a document and its corresponding metadata, generates vector embeddings from the content, and then stores the text, metadata, and embeddings in a specialized vector database. This is the final step in processing a document and making it available for semantic search and retrieval.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "document_content": {
                            "type": "string",
                            "description": "The content of the document."
                        },
                        "metadata": {
                            "type": "object",
                            "description": "The metadata for the document."
                        }
                    },
                    "required": ["document_content", "metadata"]
                }
            }
        }
    ]