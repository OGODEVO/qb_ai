import os
import logging
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
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        """
        Initializes the AttentionLayer.

        Args:
            model_name (str): The name of the sentence-transformer model to use.
        """
        self.model = SentenceTransformer(model_name)
        self.vectorizer = TfidfVectorizer(stop_words='english')

    def analyze_conversation(self, messages: list[dict], turns: int = 4, threshold: float = 0.75) -> str | None:
        """
        Analyzes the last N turns of a conversation to check for topic cohesion.

        Args:
            messages (list[dict]): The list of chat messages.
            turns (int): The number of recent turns to analyze.
            threshold (float): The similarity threshold to determine topic cohesion.

        Returns:
            str | None: A suggestion string if the topic is cohesive, otherwise None.
        """
        if len(messages) < turns:
            return None

        # Get the content of the last N turns
        recent_messages = [msg['content'] for msg in messages[-turns:]]

        # Generate embeddings
        embeddings = self.model.encode(recent_messages)

        # Calculate pairwise cosine similarity
        similarity_matrix = cosine_similarity(embeddings)

        # Get the average similarity of the upper triangle of the matrix
        upper_triangle_indices = np.triu_indices_from(similarity_matrix, k=1)
        average_similarity = np.mean(similarity_matrix[upper_triangle_indices])

        if average_similarity > threshold:
            suggestion = self._generate_suggestion(recent_messages)
            logging.info(f"Suggestion: {suggestion}")
            return suggestion
        
        return None

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