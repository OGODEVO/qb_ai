import os
import logging
import tiktoken
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

# Configure logging
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_file = os.path.join(log_dir, 'suggestions.log')
logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s - %(message)s')

class AttentionLayer:
    def __init__(self, model_name='all-MiniLM-L6-v2', min_turns=3, max_turns=8, token_budget=700, threshold=0.9, decay=0.85):
        """
        Initializes the AttentionLayer.

        Args:
            model_name (str): The name of the sentence-transformer model to use.
            min_turns (int): The minimum number of recent turns to analyze.
            max_turns (int): The maximum number of recent turns to analyze.
            token_budget (int): The maximum number of tokens to include in the analysis.
            threshold (float): The similarity threshold to determine topic cohesion.
            decay (float): The decay factor for older messages.
        """
        self.model = SentenceTransformer(model_name)
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        self.min_turns = min_turns
        self.max_turns = max_turns
        self.token_budget = token_budget
        self.threshold = threshold
        self.decay = decay
        self.sentiment_analyzer = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")
        self.performance_data = {}

    def _select_recent_messages(self, messages: list[dict]) -> list[str]:
        """
        Selects recent messages based on token budget and turn limits.
        """
        recent_messages = []
        token_count = 0
        for msg in reversed(messages):
            if len(recent_messages) >= self.max_turns:
                break
            
            num_tokens = len(self.tokenizer.encode(msg['content']))
            if token_count + num_tokens > self.token_budget and len(recent_messages) >= self.min_turns:
                break
            
            recent_messages.append(msg['content'])
            token_count += num_tokens
        
        return list(reversed(recent_messages))

    def analyze_conversation(self, messages: list[dict]) -> dict | None:
        """
        Analyzes the last N turns of a conversation to check for topic cohesion.

        Args:
            messages (list[dict]): The list of chat messages.

        Returns:
            dict | None: A dictionary with the suggestion and similarity score, or None if analysis is not possible.
        """
        recent_messages = self._select_recent_messages(messages)

        if len(recent_messages) < self.min_turns:
            return None

        # Generate embeddings
        embeddings = self.model.encode(recent_messages)

        # Calculate pairwise cosine similarity
        similarity_matrix = cosine_similarity(embeddings)

        # Get the upper triangle of the similarity matrix
        upper_triangle_indices = np.triu_indices_from(similarity_matrix, k=1)
        
        if len(upper_triangle_indices[0]) == 0:
            return None

        # Create decay weights
        num_messages = len(recent_messages)
        weights = np.array([self.decay**(num_messages - i - 1) for i in range(num_messages)])
        
        # Create a weight matrix for the pairwise similarities
        weight_matrix = np.ones_like(similarity_matrix)
        for i in range(num_messages):
            for j in range(i + 1, num_messages):
                weight_matrix[i, j] = weights[i] * weights[j]
        
        weighted_similarities = similarity_matrix[upper_triangle_indices] * weight_matrix[upper_triangle_indices]
        
        # Calculate the weighted average similarity
        average_similarity = np.sum(weighted_similarities) / np.sum(weight_matrix[upper_triangle_indices])

        suggestion = None
        if average_similarity > self.threshold:
            suggestion = self._generate_suggestion(recent_messages)
            logging.info(f"Suggestion: {suggestion} (Similarity: {average_similarity:.2f})")

        return {"suggestion": suggestion, "similarity": average_similarity}

    def _generate_suggestion(self, recent_messages: list[str], top_n: int = 3) -> str:
        """
        Generates a suggestion based on the keywords of the recent messages.

        Args:
            recent_messages (list[str]): The content of recent messages.
            top_n (int): The number of top keywords to extract.

        Returns:
            str: The generated suggestion string.
        """
        # Extract keywords using TF-IDF
        tfidf_matrix = self.vectorizer.fit_transform(recent_messages)
        feature_names = self.vectorizer.get_feature_names_out()
        
        # Get the top N keywords from the TF-IDF matrix
        # Sum the tf-idf scores for each term across all documents
        summed_tfidf = tfidf_matrix.sum(axis=0)
        # Get the indices of the top N scores
        top_indices = np.argsort(summed_tfidf).A1[-top_n:]
        
        keywords = [feature_names[i] for i in reversed(top_indices)]

        return f"The conversation is focused on: {', '.join(keywords)}"

    def get_performance_report(self) -> str:
        """
        Analyzes the conversation history and returns a performance report.

        Returns:
            str: A performance report.
        """
        if not self.performance_data:
            return "No performance data to analyze."

        report = "**Performance Report:**\n"
        for topic, data in self.performance_data.items():
            report += f"\n**Topic:** {topic}\n"
            report += f"- Positive messages: {data['positive']}\n"
            report += f"- Negative messages: {data['negative']}\n"
            report += f"- Neutral messages: {data['neutral']}\n"

            if data['negative'] > 0:
                report += "\n**Recommendation:** The user has expressed negative sentiment on this topic. Consider revising the prompt to be more helpful or empathetic."

        return report

    def get_most_relevant_user_message(self, agent_response: str, user_messages: list[str]) -> str:
        """
        Finds the user message that is most relevant to the agent's last response.

        Args:
            agent_response (str): The agent's last response.
            user_messages (list[str]): A list of user messages.

        Returns:
            str: The most relevant user message.
        """
        if not user_messages:
            return ""

        # Generate embeddings for the agent's response and the user messages
        agent_embedding = self.model.encode([agent_response])
        user_embeddings = self.model.encode(user_messages)

        # Calculate the cosine similarity between the agent's response and each user message
        similarities = cosine_similarity(agent_embedding, user_embeddings)[0]

        # Find the index of the most similar user message
        most_similar_index = np.argmax(similarities)

        return user_messages[most_similar_index]

    def get_underperforming_topics(self, threshold: float = 0.5) -> list[str]:
        """
        Identifies topics where the agent's performance is below a certain threshold.

        Args:
            threshold (float): The performance threshold. If the ratio of negative messages to total messages is greater than this threshold, the topic is considered underperforming.

        Returns:
            list[str]: A list of the underperforming topics.
        """
        underperforming_topics = []
        for topic, data in self.performance_data.items():
            total_messages = data["positive"] + data["negative"] + data["neutral"]
            if total_messages == 0:
                continue

            negative_ratio = data["negative"] / total_messages
            if negative_ratio > threshold:
                underperforming_topics.append(topic)

        return underperforming_topics
