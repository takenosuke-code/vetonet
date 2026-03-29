#!/usr/bin/env python3
"""
Train a sentence-based classifier on VetoNet attack data.

Uses sentence-transformers for embeddings and sklearn for classification.
Runs on CPU, no GPU required.

Usage:
    python scripts/train_classifier.py

Requirements:
    pip install sentence-transformers scikit-learn joblib
"""

import os
import sys
import json
import joblib
import numpy as np
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from sentence_transformers import SentenceTransformer
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split, cross_val_score
    from sklearn.metrics import classification_report, confusion_matrix, f1_score
except ImportError as e:
    print("Missing dependencies. Install with:")
    print("  pip install sentence-transformers scikit-learn joblib")
    sys.exit(1)


def load_training_data(path: str) -> tuple[list, list]:
    """Load training data from JSONL file."""
    texts = []
    labels = []

    with open(path, 'r') as f:
        for line in f:
            item = json.loads(line)
            texts.append(item['text'])
            labels.append(item['label'])

    return texts, labels


def create_embeddings(texts: list, model_name: str = 'all-MiniLM-L6-v2') -> np.ndarray:
    """Create sentence embeddings for all texts."""
    print(f"Loading embedding model: {model_name}")
    model = SentenceTransformer(model_name)

    print(f"Creating embeddings for {len(texts)} texts...")
    embeddings = model.encode(texts, show_progress_bar=True)

    return embeddings


def train_classifier(X_train: np.ndarray, y_train: list) -> RandomForestClassifier:
    """Train a RandomForest classifier."""
    print("Training RandomForest classifier...")

    # Use class weights to handle imbalanced data
    clf = RandomForestClassifier(
        n_estimators=100,
        max_depth=20,
        min_samples_split=5,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1,
        verbose=1
    )

    clf.fit(X_train, y_train)
    return clf


def evaluate_model(clf, X_test: np.ndarray, y_test: list):
    """Evaluate the trained model."""
    print("\n--- Model Evaluation ---")

    y_pred = clf.predict(X_test)
    y_proba = clf.predict_proba(X_test)

    # Classification report
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=['Legitimate', 'Attack']))

    # Confusion matrix
    print("\nConfusion Matrix:")
    cm = confusion_matrix(y_test, y_pred)
    print(f"  TN={cm[0][0]}, FP={cm[0][1]}")
    print(f"  FN={cm[1][0]}, TP={cm[1][1]}")

    # F1 Score
    f1 = f1_score(y_test, y_pred)
    print(f"\nF1 Score: {f1:.4f}")

    # Confidence distribution
    confidences = np.max(y_proba, axis=1)
    print(f"\nConfidence distribution:")
    print(f"  Mean: {np.mean(confidences):.3f}")
    print(f"  Min:  {np.min(confidences):.3f}")
    print(f"  Max:  {np.max(confidences):.3f}")

    return f1


def save_model(clf, output_path: str):
    """Save the trained model."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, output_path)
    print(f"\nModel saved to: {output_path}")


def main():
    print("=" * 50)
    print("VetoNet Attack Classifier Training")
    print("=" * 50)
    print()

    # Paths
    data_path = Path(__file__).parent.parent / 'data' / 'training_data.jsonl'
    model_path = Path(__file__).parent.parent / 'models' / 'attack_classifier.pkl'

    # Check if training data exists
    if not data_path.exists():
        print(f"Training data not found: {data_path}")
        print("Run export_training_data.py first!")
        sys.exit(1)

    # Load data
    print(f"Loading training data from: {data_path}")
    texts, labels = load_training_data(str(data_path))
    print(f"Loaded {len(texts)} examples")
    print(f"  Attacks: {sum(labels)}")
    print(f"  Legitimate: {len(labels) - sum(labels)}")

    # Create embeddings
    print()
    embeddings = create_embeddings(texts)
    print(f"Embeddings shape: {embeddings.shape}")

    # Split data
    print("\nSplitting data (80% train, 20% test)...")
    X_train, X_test, y_train, y_test = train_test_split(
        embeddings, labels,
        test_size=0.2,
        random_state=42,
        stratify=labels
    )
    print(f"  Train: {len(y_train)} examples")
    print(f"  Test:  {len(y_test)} examples")

    # Train classifier
    print()
    clf = train_classifier(X_train, y_train)

    # Evaluate
    f1 = evaluate_model(clf, X_test, y_test)

    # Check if model is good enough
    if f1 < 0.7:
        print("\n[WARNING] F1 score is below 0.70 - model may need improvement")
        print("Consider: more data, different model, or feature engineering")

    # Save model
    save_model(clf, str(model_path))

    # Save metadata
    metadata = {
        'trained_at': datetime.utcnow().isoformat(),
        'n_examples': len(texts),
        'n_attacks': sum(labels),
        'n_legitimate': len(labels) - sum(labels),
        'f1_score': float(f1),
        'embedding_model': 'all-MiniLM-L6-v2',
        'classifier': 'RandomForestClassifier',
    }
    metadata_path = model_path.parent / 'attack_classifier_metadata.json'
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"Metadata saved to: {metadata_path}")

    print("\n" + "=" * 50)
    print("Training complete!")
    print(f"Model: {model_path}")
    print(f"F1 Score: {f1:.4f}")
    print("=" * 50)


if __name__ == '__main__':
    main()
