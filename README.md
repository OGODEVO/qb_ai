# Reki: Your AI-Powered Financial Advisor

Reki is a sophisticated, AI-powered agent designed to act as a financial advisor. It provides a conversational interface to help you analyze your financial data from various sources, including QuickBooks and Meta Ads. Reki is built with a modular architecture, allowing for easy extension and customization.

## Features

- **Conversational Interface:** Interact with Reki using natural language through a user-friendly Streamlit-based chat interface.
- **Extensible Toolset:** Reki comes with a set of powerful tools to access your financial data:
  - **QuickBooks:** Query your QuickBooks account for financial data like expenses, revenue, and reports.
  - **Meta Ads:** Get insights into your advertising spend and performance on Meta platforms.
  - **Web Browser:** Access real-time information from the web to supplement its knowledge.
- **Cognitive Architecture:** Reki is equipped with a cognitive architecture that enables it to:
  - **Focus its Attention:** An attention layer helps Reki understand the context of the conversation and focus on the most relevant information.
  - **Long-Term Memory:** Reki can store and recall information from past conversations, allowing it to learn and adapt over time.
- **Verbose Mode:** A verbose mode allows you to inspect the agent's reasoning and tool calls, providing transparency into its decision-making process.
- **Stub Data for Development:** The QuickBooks tool includes a stub data feature, allowing for local development and testing without requiring live API credentials.

## Getting Started

### Prerequisites

- Python 3.10+
- An account with [xAI](https://x.ai/) to access their language models.
- (Optional) API credentials for the following services:
  - QuickBooks
  - Meta Ads
  - Brave Search

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/reki.git
   cd reki
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. **Install the dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Configuration

1. **Create a `.env` file:**
   ```bash
   cp .env.example .env
   ```

2. **Add your API keys to the `.env` file:**
   ```
   # xAI Grok API Credentials
   XAI_API_KEY=your-xai-api-key
   XAI_BASE_URL=https://api.x.ai/v1
   XAI_MODEL=grok-4

   # ChromaDB Cloud Credentials
   CHROMA_API_KEY=your-chromadb-api-key
   CHROMA_TENANT=your-chromadb-tenant
   CHROMA_DATABASE=your-chromadb-database

   # --- Optional ---

   # --- Brave Search ---
   BRAVE_API_KEY=your-brave-api-key

   # --- QuickBooks ---
   QB_CLIENT_ID=your-qb-client-id
   QB_CLIENT_SECRET=your-qb-client-secret
   QB_REALM_ID=your-qb-realm-id
   QB_REDIRECT_URI=http://localhost:8501/
   QB_ENVIRONMENT=sandbox # or "production"
   QB_USE_STUB=true # Set to false to use the live QuickBooks API

   # --- Meta Ads ---
   META_APP_ID=your-meta-app-id
   META_APP_SECRET=your-meta-app-secret
   META_ACCESS_TOKEN=your-meta-access-token
   META_AD_ACCOUNT_ID=act_...
   ```

## Usage

To start the application, run the following command:

```bash
streamlit run app.py
```

This will open the Reki chat interface in your web browser. You can then start a conversation with Reki and ask it questions about your financial data.

## Project Structure

```
/workspaces/qb_ai/
├───.gitignore
├───.python-version
├───app.py
├───pyproject.toml
├───README.md
├───requirements.txt
├───.git/...
├───core/
│   ├───attention.py
│   ├───history.py
│   ├───memory.py
│   └───__pycache__/
├───logs/
├───prompts/
│   └───system.txt
├───tools/
│   ├───__init__.py
│   ├───browser.py
│   ├───meta_ads.py
│   ├───quickbooks.py
│   └───__pycache__/
└───venv/
    ├───bin/...
    └───lib/...
```

## Core Components

### Attention Layer (`core/attention.py`)

The attention layer analyzes the conversation to determine if the conversation is focused on a specific topic. It uses a sentence transformer model to calculate the similarity between recent messages and, if the similarity is above a certain threshold, it generates a "suggestion" (a summary of the topic).

### Long-Term Memory (`core/memory.py`)

The long-term memory component uses ChromaDB to provide long-term memory for the agent. It has methods for saving memories, remembering specific facts, and querying the memory. It also has a method for evaluating a conversation and summarizing it if it's deemed "memorable."

## Tools

### QuickBooks (`tools/quickbooks.py`)

The QuickBooks tool allows Reki to query your QuickBooks account for financial data. It can retrieve reports like Profit & Loss, expenses by category, and expenses by vendor.

### Meta Ads (`tools/meta_ads.py`)

The Meta Ads tool enables Reki to query the Meta Ads API to get insights into your advertising campaigns, ad sets, and ads.

### Browser (`tools/browser.py`)

The browser tool allows Reki to search the web using the Brave Search API, giving it access to real-time information.