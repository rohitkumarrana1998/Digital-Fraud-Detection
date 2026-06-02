import pandas as pd
import pickle
import os
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

# 🔹 1. Dataset load
data = pd.read_csv('dataset/AIML Dataset.csv')

print("✅ Dataset Loaded")
print(data.head())

# 🔹 2. Correct columns use karo
required_cols = ['amount', 'step', 'isFraud']

# check columns
for col in required_cols:
    if col not in data.columns:
        raise Exception(f"❌ Column '{col}' not found in dataset")

data = data[required_cols]

# 🔹 3. Features & Target
X = data[['amount', 'step']]
y = data['isFraud']

# 🔹 4. Train-Test Split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# 🔹 5. Model training
model = RandomForestClassifier(n_estimators=100)
model.fit(X_train, y_train)

# 🔹 6. Evaluation
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)

print(f"✅ Model Accuracy: {accuracy:.2f}")

# 🔹 7. Save model inside backend folder
model_path = os.path.join('backend', 'model.pkl')
pickle.dump(model, open(model_path, 'wb'))

print(f"✅ Model saved at {model_path}")