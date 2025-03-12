import pickle

from sql_markov import MarkovChainSQLi
# ✅ Load the trained Markov Chain SQLi model
with open("markov_sqli_model.pkl", "rb") as f:
    loaded_model = pickle.load(f)

# ✅ Test on a new SQLi input
query = "What is your name"
prediction = loaded_model.predict(query)
print(f"Prediction for '{query}': {'SQLi' if prediction == 1 else 'Normal'}")
