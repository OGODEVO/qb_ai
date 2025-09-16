# Reki - Your AI Assistant

Reki is an AI assistant that can answer questions about QuickBooks, Meta Ads, and Google Calendar. It provides an OpenAI-compatible API for chat completions and can be extended with new tools.

## Features

*   **OpenAI-Compatible API**: Reki provides a `/v1/chat/completions` endpoint that is compatible with the OpenAI API. This allows you to use Reki with any client that supports the OpenAI API.
*   **Tool Server Management**: Reki can be extended with new tools by adding tool servers. Tool servers are separate applications that provide a set of tools that Reki can use to answer questions.
*   **Extensible**: Reki is designed to be extensible. You can add new agents, tools, and data sources to Reki to meet your needs.
*   **FastAPI Backend**: Reki is built with FastAPI, a modern, fast (high-performance), web framework for building APIs with Python 3.10+ based on standard Python type hints.
*   **Sentry Integration**: Reki is integrated with Sentry for error tracking and monitoring.

## Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/your-username/reki.git
    ```
2.  Install the dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Set up your environment variables by copying `.env.example` to `.env` and filling in the required values.

## Usage

1.  Start the Reki server:
    ```bash
    sh start.sh
    ```
2.  The Reki server will be running at `http://localhost:8000`. You can interact with the Reki API using any client that supports the OpenAI API.

## Dependencies

Reki uses the following dependencies:

*   [streamlit](https://streamlit.io/): To create the user interface.
*   [python-dotenv](https://pypi.org/project/python-dotenv/): To manage environment variables.
*   [httpx](https://www.python-httpx.org/): To make HTTP requests.
*   [pydantic](https://pydantic-docs.helpmanual.io/): To define data models.
*   [tenacity](https://tenacity.readthedocs.io/en/latest/): To retry failed operations.
*   [python-dateutil](https://dateutil.readthedocs.io/en/stable/): To parse dates and times.
*   [openai](https://github.com/openai/openai-python): To interact with the OpenAI API.
*   [requests](https://requests.readthedocs.io/en/master/): To make HTTP requests.
*   [transformers](https://huggingface.co/docs/transformers/index): To use state-of-the-art machine learning models.
*   [sentence-transformers](https://www.sbert.net/): To compute sentence embeddings.
*   [torch](https://pytorch.org/): To build and train machine learning models.
*   [scikit-learn](https://scikit-learn.org/stable/): To use machine learning algorithms.
*   [tiktoken](https://github.com/openai/tiktoken): To count tokens in a text string.
*   [chromadb](https://www.trychroma.com/): To store and retrieve embeddings.
*   [onnxruntime](https://onnxruntime.ai/): To run ONNX models.
*   [google-api-python-client](https://github.com/googleapis/google-api-python-client): To interact with Google APIs.
*   [google-auth-httplib2](https://github.com/googleapis/google-auth-library-python-httplib2): To authenticate with Google APIs.
*   [google-auth-oauthlib](https://github.com/googleapis/google-auth-library-python-oauthlib): To authenticate with Google APIs.
*   [fastapi](https://fastapi.tiangolo.com/): To build the API.
*   [uvicorn](https://www.uvicorn.org/): To run the FastAPI server.
*   [fastapi-mcp](https://pypi.org/project/fastapi-mcp/): To mount multiple FastAPI applications.
*   [sentry-sdk[fastapi]](https://docs.sentry.io/platforms/python/guides/fastapi/): To integrate with Sentry.
*   [docling](httpspypi.org/project/docling/): To handle documents.
*   [nltk](https://www.nltk.org/): To process natural language.