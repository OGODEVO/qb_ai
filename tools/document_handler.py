"""Document handling tools using docling."""
from docling.document_converter import DocumentConverter

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
    # In the future, this function will use a model to suggest metadata.
    # For now, it returns a predefined set of suggestions.
    return {
        "title": "Suggested Title",
        "tags": ["tag1", "tag2", "tag3"],
        "summary": "This is a summary of the document."
    }

def get_tools():
    """Returns the tools for the document handler."""
    return [
        {
            "type": "function",
            "function": {
                "name": "process_document",
                "description": "Processes a document from a file path and returns its content.",
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
                "description": "Suggests metadata and tags for a given document content.",
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
        }
    ]