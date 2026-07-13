import os
import torch
from datasets import load_dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
    EarlyStoppingCallback
)
import evaluate
import numpy as np

# Configuration
MODEL_NAME = "microsoft/deberta-v3-small"
DATASET_NAME = "glue"
DATASET_TASK = "mrpc" # Microsoft Research Paraphrase Corpus (text similarity/plagiarism)
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../app/ai_model"))

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

def compute_metrics(eval_pred):
    """
    Computes accuracy and f1 for the evaluation loop.
    """
    metric = evaluate.load("glue", "mrpc")
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    return metric.compute(predictions=predictions, references=labels)

def main():
    print(f"Loading tokenizer for {MODEL_NAME}...")
    # Use fast tokenizer, DeBERTa v3 requires sentencepiece (included in modern transformers, but might need pip install sentencepiece if errors occur)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, use_fast=True)

    print(f"Loading dataset: {DATASET_NAME} / {DATASET_TASK}...")
    # MRPC has features: sentence1, sentence2, label (0 or 1), idx
    # Label 1 means they are semantically equivalent (paraphrase/plagiarized).
    # Label 0 means they are not.
    dataset = load_dataset(DATASET_NAME, DATASET_TASK)

    def tokenize_function(examples):
        # Tokenize the pairs of sentences
        # Truncation and padding handled by Trainer/DataCollator usually, 
        # but we can explicitly set it here.
        return tokenizer(
            examples["sentence1"], 
            examples["sentence2"], 
            padding="max_length", 
            truncation=True, 
            max_length=512
        )

    print("Tokenizing dataset...")
    tokenized_datasets = dataset.map(tokenize_function, batched=True)

    # We only need the train and validation sets
    train_dataset = tokenized_datasets["train"]
    eval_dataset = tokenized_datasets["validation"]

    print(f"Loading pre-trained model: {MODEL_NAME}...")
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME, 
        num_labels=2 # Binary classification: 0 (Not Plagiarized) and 1 (Plagiarized)
    )

    # Define training arguments
    # We use aggressive early stopping and evaluation to prevent overfitting
    training_args = TrainingArguments(
        output_dir="./results",
        evaluation_strategy="epoch",
        save_strategy="epoch",
        learning_rate=2e-5, # Good starting LR for DeBERTa
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        num_train_epochs=3,
        weight_decay=0.01,
        load_best_model_at_end=True, # For early stopping
        metric_for_best_model="f1",
        logging_dir='./logs',
        logging_steps=50,
        push_to_hub=False,
    )

    # Initialize Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        compute_metrics=compute_metrics,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=1)]
    )

    print("Starting training...")
    trainer.train()

    print("Evaluating the final best model...")
    eval_results = trainer.evaluate()
    print(f"Evaluation results: {eval_results}")

    print(f"Saving model and tokenizer to {OUTPUT_DIR}...")
    # Save the model and tokenizer to the configured directory
    trainer.save_model(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print("Training complete! Model saved.")

if __name__ == "__main__":
    main()
