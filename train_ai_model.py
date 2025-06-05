import pandas as pd
import numpy as np
import re
import json
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
import tensorflow as tf
import os
import joblib

CSV_FILE_PATH = 'completo.csv'
METRICS_FILE_PATH = 'ai_metrics.json'
SCALER_PATH = 'scaler.joblib'
LABEL_ENCODER_PATH = 'label_encoder.joblib'
MODEL_SAVE_PATH = "modelo_area_interesse.keras"

RANDOM_STATE = 42

interest_to_weight = {1: 0.1, 2: 0.3, 3: 0.5, 4: 0.7, 5: 0.9}
GESTÃO_QUESTIONS_INDICES = list(range(3, 13))
SAUDE_QUESTIONS_INDICES = list(range(13, 23))
TI_QUESTIONS_INDICES = list(range(23, 33))
ALL_QUESTION_INDICES = GESTÃO_QUESTIONS_INDICES + SAUDE_QUESTIONS_INDICES + TI_QUESTIONS_INDICES

def extract_score_from_answer(answer_str):
    if pd.isna(answer_str) or not isinstance(answer_str, str): return None
    match = re.match(r"^\s*(\d+)", answer_str)
    return int(match.group(1)) if match else None

def get_weighted_score(answer_str):
    numeric_value = extract_score_from_answer(answer_str)
    return interest_to_weight.get(numeric_value, 0.0)

def determine_target_area(row):
    score_gestao = sum(get_weighted_score(row.iloc[idx]) for idx in GESTÃO_QUESTIONS_INDICES)
    score_saude = sum(get_weighted_score(row.iloc[idx]) for idx in SAUDE_QUESTIONS_INDICES)
    score_ti = sum(get_weighted_score(row.iloc[idx]) for idx in TI_QUESTIONS_INDICES)
    scores = {"Gestão": score_gestao, "Saúde": score_saude, "TI": score_ti}
    if all(s == 0 for s in scores.values()): return "Indefinido"
    return max(scores, key=scores.get)

def train_and_evaluate():
    print(f"[{pd.Timestamp.now()}] Iniciando treinamento da IA com dados de: {CSV_FILE_PATH}")
    try:
        df = pd.read_csv(CSV_FILE_PATH)
    except Exception as e:
        print(f"Erro ao ler {CSV_FILE_PATH} no script de treinamento: {e}")
        return None, None, None, None

    features_cols = []
    for i, idx in enumerate(ALL_QUESTION_INDICES):
        col_name = f"q_{i+1}_weight"
        df[col_name] = df.iloc[:, idx].apply(get_weighted_score)
        features_cols.append(col_name)

    X_data = df[features_cols].values
    df['target_area'] = df.apply(determine_target_area, axis=1)
    df_filtered = df[df['target_area'] != "Indefinido"].copy()

    if df_filtered.empty or len(df_filtered) < 10:
        print("Não há dados suficientes após filtrar para treinar o modelo.")
        return None, None, None, None

    y_categorical = df_filtered['target_area']
    label_encoder = LabelEncoder()
    y_data = label_encoder.fit_transform(y_categorical)
    num_classes = len(label_encoder.classes_)
    X_data_filtered = df_filtered[features_cols].values

    if X_data_filtered.shape[0] == 0:
        print("X_data_filtered está vazio após a filtragem.")
        return None, None, None, None

    X_train, X_test, y_train, y_test = train_test_split(
        X_data_filtered, y_data, test_size=0.2, random_state=RANDOM_STATE,
        stratify=y_data if num_classes > 1 and len(np.unique(y_data)) > 1 and len(y_data) >= num_classes * 2 else None # Adicionada verificação para stratify
    )

    if len(X_train) == 0 or len(X_test) == 0:
        print("Divisão resultou em conjunto de treino ou teste vazio.")
        return None, None, None, None

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    model = tf.keras.models.Sequential([
        tf.keras.layers.Dense(64, activation='relu', input_shape=(X_train_scaled.shape[1],)),
        tf.keras.layers.Dropout(0.3),
        tf.keras.layers.Dense(32, activation='relu'),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.Dense(num_classes, activation='softmax')
    ])
    model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
    
    print("Treinando o modelo...")
    val_split = 0.1 if len(X_train) > 10 else 0
    model.fit(X_train_scaled, y_train, epochs=50, batch_size=8, verbose=0, validation_split=val_split)

    print("Avaliando o modelo...")
    loss, accuracy = model.evaluate(X_test_scaled, y_test, verbose=0)

    print(f"Treinamento concluído. Acurácia Teste: {accuracy*100:.2f}%, Perda Teste: {loss:.4f}")

    try:
        model.save(MODEL_SAVE_PATH)
        print(f"Modelo salvo em {MODEL_SAVE_PATH}")
        joblib.dump(scaler, SCALER_PATH)
        print(f"Scaler salvo em {SCALER_PATH}")
        joblib.dump(label_encoder, LABEL_ENCODER_PATH)
        print(f"LabelEncoder salvo em {LABEL_ENCODER_PATH}")
    except Exception as e:
        print(f"Erro ao salvar modelo/scaler/label_encoder: {e}")

    return accuracy, loss, scaler, label_encoder

def save_metrics(accuracy, loss):
    if accuracy is not None and loss is not None:
        metrics_data = {
            "accuracy_test": accuracy * 100,
            "loss_test": loss,
            "last_trained_timestamp": pd.Timestamp.now().isoformat()
        }
        try:
            with open(METRICS_FILE_PATH, 'w') as f:
                json.dump(metrics_data, f, indent=4)
            print(f"Métricas salvas em {METRICS_FILE_PATH}")
        except Exception as e:
            print(f"Erro ao salvar métricas: {e}")
    else:
        print("Treinamento falhou ou não produziu métricas, não salvando.")

if __name__ == "__main__":
    acc, lss, saved_scaler, saved_label_encoder = train_and_evaluate()
    if acc is not None and lss is not None:
        save_metrics(acc, lss)
    else:
        print("Não foi possível treinar o modelo ou obter métricas.")
