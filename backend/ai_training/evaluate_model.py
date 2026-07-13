import os
import torch
import numpy as np
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix
import json

MODEL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../app/ai_model"))
DATASET_NAME = "glue"
DATASET_TASK = "mrpc"

def evaluate_model():
    if not os.path.exists(MODEL_DIR):
        print(f"Error: Model directory not found at {MODEL_DIR}. Please run train.py first.")
        return

    print("Loading saved model and tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()

    print("Loading test dataset...")
    # MRPC only has train, validation, and test. We evaluate on the test split if labels are available,
    # otherwise validation split is used for this example because GLUE test sets often have hidden labels.
    dataset = load_dataset(DATASET_NAME, DATASET_TASK)
    eval_dataset = dataset["validation"] # Using validation as ground truth for metrics since GLUE test labels are hidden.

    def tokenize_function(examples):
        return tokenizer(
            examples["sentence1"], 
            examples["sentence2"], 
            padding="max_length", 
            truncation=True, 
            max_length=512,
            return_tensors="pt"
        )

    print("Tokenizing data...")
    # Map and set format to pytorch tensors
    tokenized_dataset = eval_dataset.map(tokenize_function, batched=True)
    tokenized_dataset.set_format(type='torch', columns=['input_ids', 'attention_mask', 'label'])

    all_preds = []
    all_probs = []
    all_labels = []

    print("Running inference on validation set...")
    batch_size = 16
    
    with torch.no_grad():
        for i in range(0, len(tokenized_dataset), batch_size):
            batch = tokenized_dataset[i:i+batch_size]
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            labels = batch['label'].numpy()

            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            logits = outputs.logits
            probs = torch.softmax(logits, dim=-1)[:, 1].cpu().numpy() # Probability of class 1 (Plagiarized)
            preds = torch.argmax(logits, dim=-1).cpu().numpy()
            
            all_preds.extend(preds)
            all_probs.extend(probs)
            all_labels.extend(labels)

    # Calculate metrics
    accuracy = accuracy_score(all_labels, all_preds)
    precision = precision_score(all_labels, all_preds)
    recall = recall_score(all_labels, all_preds)
    f1 = f1_score(all_labels, all_preds)
    roc_auc = roc_auc_score(all_labels, all_probs)
    conf_matrix = confusion_matrix(all_labels, all_preds)

    results = {
        "Accuracy": accuracy,
        "Precision": precision,
        "Recall": recall,
        "F1-score": f1,
        "ROC-AUC": roc_auc,
        "Confusion Matrix": conf_matrix.tolist()
    }

    print("\n--- Evaluation Results ---")
    for key, value in results.items():
        if key != "Confusion Matrix":
            print(f"{key}: {value:.4f}")
        else:
            print(f"{key}:\n{np.array(value)}")
            
    # Save results to a file
    results_path = os.path.join(os.path.dirname(__file__), "evaluation_metrics.json")
    with open(results_path, "w") as f:
        json.dump(results, f, indent=4)
    print(f"\nResults saved to {results_path}")

if __name__ == "__main__":
    evaluate_model()
