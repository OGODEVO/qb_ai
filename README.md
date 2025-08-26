# Reki - Your Self-Improving AI Assistant

**Version:** 1.0.0

## About Reki

Reki is not just another AI assistant. It is a self-learning and self-improving agent designed to make your life simpler. Reki is built with a sophisticated cognitive architecture that allows it to learn from its mistakes, adapt to your needs, and improve its performance over time.

## Key Features

*   **Self-Correction:** Reki can identify its own mistakes and correct them. If you provide feedback that Reki has made a mistake, it will analyze the conversation, identify the correction, and generate a new instruction for itself to avoid making the same mistake in the future.
*   **Proactive Improvement:** Reki can proactively identify areas where it is underperforming and generate a learning plan to address its weaknesses. This allows Reki to continuously improve its knowledge and skills over time.
*   **Long-Term Memory:** Reki has a long-term memory that allows it to remember information from past conversations. This allows Reki to learn your preferences and provide a more personalized experience.
*   **Extensible Toolset:** Reki comes with a set of powerful tools to access your financial data, including QuickBooks and Meta Ads. Reki can also be extended with new tools to meet your specific needs.

## Our Philosophy

We believe that AI should be a tool that empowers users, not a black box that they cannot understand or control. That's why we have designed Reki to be transparent and controllable. You can inspect Reki's reasoning, view its performance reports, and even approve or deny the changes that it makes to its own prompt.

We are committed to building an AI assistant that is not only intelligent and capable, but also safe and trustworthy. We believe that Reki is a major step forward in achieving this goal.

## Getting Started

To get started with Reki, please refer to the technical documentation in the `docs` directory. (Note: I will create this directory and documentation in a future step if you would like me to).

## Language Model Usage

The agent uses the `grok-4` language model for a variety of tasks. Here is a breakdown of where the model is queried:

1.  **Primary Response:** The main call to get the agent's response to a user's prompt.
2.  **Tool Call Response:** If the agent uses a tool, a second call is made to summarize the tool's output.
3.  **Self-Correction (Correction Identification):** If a user provides negative feedback, the model is used to identify the mistake.
4.  **Self-Correction (Instruction Generation):** A second call is made to generate a new instruction for the agent to learn from the mistake.
5.  **Proactive Improvement (Learning Plan):** If the agent identifies a topic it's underperforming on, it uses the model to generate a learning plan.
6.  **Proactive Improvement (Tool Selection):** For each step in the learning plan, the model is used to select the appropriate tool.
7.  **Proactive Memory (Topic Summary):** At the end of a conversation, the model is used to summarize the recurring topics for long-term memory.
8.  **Memory Evaluation:** The model is used to evaluate whether a conversation is "memorable" and to generate a summary for long-term storage.
