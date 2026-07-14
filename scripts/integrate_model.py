import pickle
import sys
sys.path.insert(0, 'src')

# Load trained model
with open("specialty_router_model.pkl", "rb") as f:
    clf, vectorizer = pickle.load(f)

# Test integration
from core.enums import Specialty

text = "My knee is swollen and painful"
vec = vectorizer.transform([text])
pred = clf.predict(vec)[0]
conf = clf.predict_proba(vec)[0].max()

print(f"Text: {text}")
print(f"Prediction: {pred}")
print(f"Confidence: {conf:.2%}")

# Map to Specialty enum
specialty_map = {
    'cardiology': Specialty.CARDIOLOGY,
    'orthopedics': Specialty.ORTHOPEDICS,
    'dermatology': Specialty.DERMATOLOGY,
    'general_triage': Specialty.GENERAL_TRIAGE,
}

print(f"Specialty enum: {specialty_map[pred]}")
