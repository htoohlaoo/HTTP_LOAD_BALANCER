import pandas as pd
import numpy as np
import pickle
import re
from collections import defaultdict
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

# 🔹 Load dataset correctly
df = pd.read_csv("archive/sqli.csv", encoding='utf-16')  # Ensure correct columns
df.rename(columns={"Sentence": "query", "Label": "is_sqli"}, inplace=True)
df['is_sqli'] = df['is_sqli'].astype(int)  # Convert labels to integers

# 🔹 Tokenization
def tokenize_sql(query):
    if not isinstance(query, str):  
        query = str(query)  
    query = query.lower()
    query = re.sub(r'(\s+)', ' ', query)  
    return list(query)  

df['tokens'] = df['query'].apply(tokenize_sql)

# 🔹 Markov Chain Model (Fix: Avoid lambda in defaultdict)
class MarkovChainSQLi:
    def __init__(self):
        self.normal_chain = {}
        self.sqli_chain = {}

    def train(self, tokenized_queries, labels):
        normal_queries = [tokens for tokens, label in zip(tokenized_queries, labels) if label == 0]
        sqli_queries = [tokens for tokens, label in zip(tokenized_queries, labels) if label == 1]

        self.normal_chain = self._build_chain(normal_queries)
        self.sqli_chain = self._build_chain(sqli_queries)

    def _build_chain(self, queries):
        transitions = defaultdict(lambda: defaultdict(int))  # This was causing the pickle error
        for query in queries:
            for i in range(len(query) - 1):
                char, next_char = query[i], query[i + 1]
                transitions[char][next_char] += 1

        # Normalize probabilities
        for char, next_chars in transitions.items():
            total = sum(next_chars.values())
            transitions[char] = {k: v / total for k, v in next_chars.items()}

        return dict(transitions)  # Convert defaultdict to dict before pickling

    def predict(self, query):
        tokens = tokenize_sql(query)
        normal_prob = self._compute_probability(tokens, self.normal_chain)
        sqli_prob = self._compute_probability(tokens, self.sqli_chain)
        return 1 if sqli_prob > normal_prob else 0

    def _compute_probability(self, tokens, chain):
        if len(tokens) < 2:
            return 0  

        prob = 1
        for i in range(len(tokens) - 1):
            char, next_char = tokens[i], tokens[i + 1]
            prob *= chain.get(char, {}).get(next_char, 1e-6)  

        return prob

# 🔹 Train-Test Split
X_train, X_test, y_train, y_test = train_test_split(df['query'], df['is_sqli'], test_size=0.2, random_state=42)

# 🔹 Train the Markov Model
markov_model = MarkovChainSQLi()
markov_model.train(df['tokens'], df['is_sqli'])

# 🔹 Evaluate Model
y_pred = [markov_model.predict(query) for query in X_test]
accuracy = accuracy_score(y_test, y_pred)

print(f"✅ Model Accuracy: {accuracy:.2f}")
print("🔹 Classification Report:")
print(classification_report(y_test, y_pred))

# ✅ Fix: Convert defaultdict to dict before saving to pickle
with open("markov_sqli_model.pkl", "wb") as f:
    pickle.dump(markov_model, f)

print("✅ Model saved successfully as 'markov_sqli_model.pkl'")
