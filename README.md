# QuickBooks Financial Advisor Agent

A specialized accounting/finance advisor that answers questions using QuickBooks Sandbox data, running locally with a Streamlit UI.

## Setup

1.  **Create a virtual environment:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure environment variables:**
    Copy the example `.env` file and fill in your API keys and settings.
    ```bash
    cp .env.example .env
    ```
    You will need to add your credentials for the xAI API and QuickBooks Online.

## How to Run

Launch the Streamlit web interface:
```bash
streamlit run app.py
```

## Toggling QuickBooks Data Source

You can switch between using live QuickBooks data and deterministic, stubbed sample data for local development.

-   **To use stubbed data:**
    Set `QB_USE_STUB=true` in your `.env` file. This is the default and allows the app to run without any QuickBooks credentials.

-   **To use live QuickBooks data:**
    Set `QB_USE_STUB=false` in your `.env` file and ensure your `QB_*` credentials are correct.

## Example Prompts

- How much did we spend on advertising last month?
- What were our top 5 expense categories YTD?
- Show me the vendor breakdown for Stripe in Q2 2025.
- What was our total revenue for July 2025?