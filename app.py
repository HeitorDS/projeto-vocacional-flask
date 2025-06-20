from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, Response
import pandas as pd
import numpy as np
import re
import json
import time
import os
import threading
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import csv
from datetime import datetime
import joblib
import tensorflow as tf
import traceback
import random
import requests
from fpdf import FPDF
import io

app = Flask(__name__)

BASE_DATA_PATH = os.getenv('DATA_DIR_PATH', '.')
app.secret_key = os.getenv('SECRET_KEY', 'Teste321')


CSV_FILE_PATH = os.path.join(BASE_DATA_PATH, 'completo.csv')
METRICS_FILE_PATH = os.path.join(BASE_DATA_PATH, 'ai_metrics.json')
SCALER_PATH = os.path.join(BASE_DATA_PATH, 'scaler.joblib')
LABEL_ENCODER_PATH = os.path.join(BASE_DATA_PATH, 'label_encoder.joblib')
MODEL_SAVE_PATH = os.path.join(BASE_DATA_PATH, "modelo_area_interesse.keras")
TRAINING_IN_PROGRESS_FLAG = os.path.join(BASE_DATA_PATH, "training_lock.tmp")

interest_to_weight = {1: 0.1, 2: 0.3, 3: 0.5, 4: 0.7, 5: 0.9}
answer_value_to_string = {
    "1": "1- Nenhum interesse", "2": "2- Algum interesse",
    "3": "3- Interesse moderado", "4": "4- Bastante interesse",
    "5": "5- Total interesse"
}
NUM_QUESTIONS = 30

ORIGINAL_QUESTION_TEXTS = [
    "Você tem interesse em planejar e organizar projetos, definir metas, ciar cronogramas e distribuir tarefas?",
    "Você tem interesse em liderar ou coordenar equipes para alcançar um objetivo comum, motivando as pessoas e gerenciando conflitos?",
    "Você tem interesse em analisar dados financeiros (orçamentos, relatórios, investimentos) para tomar decisões ou avaliar o desempenho?",
    "Você tem interesse em pensar estrategicamente sobre o futuro, identificando oportunidades, riscos e definindo o rumo de uma ação ou projeto?",
    "Você tem interesse em negociar acordos, apresentar ideias de forma persuasiva ou convencer outras pessoas sobre um ponto de vista?",
    "Você tem interesse em identificar problemas em um processo ou sistema (organizacional, não técnico) e propor soluções eficientes?",
    "Você tem interesse em gerenciar recursos (tempo, dinheiro, pessoas) de forma eficaz para maximizar os resultados?",
    "Você tem interesse em analisar o mercado, entender as necessidades dos clientes ou acompanhar as ações da concorrência?",
    "Você tem interesse em desenvolver planos de negócios, estratégias de marketing ou planos de crescimento para uma organização?",
    "Você tem interesse em falar em público, fazer apresentações claras e concisas para diferentes audiências?",
    "Você tem interesse em estudar o funcionamento do corpo humano, incluindo anatomia, fisiologia e como as doenças se desenvolvem?",
    "Você tem interesse em ajudar diretamente pessoas que estão doentes, machucadas ou passando por dificuldades emocionais?",
    "Você tem interesse em seguir procedimentos e protocolos médicos ou estéticos com precisão e atenção aos detalhes para garantir a segurança e o cuidado correto?",
    "Você tem interesse em pesquisar sobre condições de saúde, tratamentos médicos, cuidados estéticos ou novas descobertas científicas na área da saúde?",
    "Você tem interesse em entender o funcionamento de procedimentos estéticos e cuidados pessoais?",
    "Você tem interesse em desenvolver melhor suas habilidades manuais (utilizar suas mãos para realização de massagens, utilização de produtos cosméticos, etc...)?",
    "Você tem interesse em agir com calma e tomar decisões rápidas e eficazes em situações de emergência ou sob pressão?",
    "Você tem interesse em observar atentamente pequenas mudanças no estado físico, estético ou emocional de uma pessoa?",
    "Você tem interesse em lidar com situações delicadas ou emocionalmente carregadas, mantendo a compostura, sigilo e o profissionalismo?",
    "Você tem interesse em trabalhar em equipe e em ambientes que exigem interação constante com pessoas de diferentes idades, convicções, pensamentos e condições (pacientes, famílias, funcionários)?",
    "Você tem interesse em investigar e resolver problemas lógicos em um sistema, como encontrar um bug em um código ou descobrir por que um programa não funciona?",
    "Você tem interesse em aprender linguagens de programação para criar websites, aplicativos ou automatizar tarefas?",
    "Você tem interesse em analisar grandes volumes de dados para encontrar padrões, tendências ou anomalias (ex: logs de sistema, dados de uso).",
    "Você tem interesse em montar, configurar ou consertar hardware de computadores ou equipamentos eletrônicos?",
    "Você tem interesse em entender profundamente como funcionam redes de computadores, sistemas operacionais ou bancos de dados?",
    "Você tem interesse em pensar como proteger sistemas contra ataques cibernéticos e garantir a segurança de informações digitais?",
    "Você tem interesse em projetar a aparência e a usabilidade (facilidade de uso) de um software ou website para que outras pessoas possam usá-lo bem?",
    "Você tem interesse em passar tempo concentrado(a) em tarefas técnicas complexas que exigem atenção aos detalhes e raciocínio abstrato?",
    "Você tem interesse em manter-se atualizado(a) sobre as últimas novidades em tecnologia, gadgets e softwares?",
    "Você tem interesse em usar ferramentas tecnológicas para otimizar processos e tornar tarefas mais eficientes?"
]
if len(ORIGINAL_QUESTION_TEXTS) != NUM_QUESTIONS:
    raise ValueError(f"NUM_QUESTIONS ({NUM_QUESTIONS}) não corresponde ao número de perguntas em ORIGINAL_QUESTION_TEXTS ({len(ORIGINAL_QUESTION_TEXTS)})")

GESTÃO_QUESTIONS_INDICES_APP = list(range(3, 13))
SAUDE_QUESTIONS_INDICES_APP = list(range(13, 23))
TI_QUESTIONS_INDICES_APP = list(range(23, 33))

ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', "admin")
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', "adm123")

NODE_API_BASE_URL = os.getenv('NODE_API_BASE_URL', "https://apicursos.glitch.me")

def extract_score_from_answer(answer_str):
    if pd.isna(answer_str) or not isinstance(answer_str, str): return None
    match = re.match(r"^\s*(\d+)", answer_str)
    return int(match.group(1)) if match else None

def calculate_area_score(row, question_indices_config, weight_map):
    total_score = 0
    for col_idx in question_indices_config:
        if col_idx < len(row):
            answer_str = row.iloc[col_idx]
            numeric_value = extract_score_from_answer(answer_str)
            if numeric_value is not None and numeric_value in weight_map:
                total_score += weight_map[numeric_value]
    return round(total_score, 2)

def determine_target_area_and_scores_from_row(row):
    score_gestao = calculate_area_score(row, GESTÃO_QUESTIONS_INDICES_APP, interest_to_weight)
    score_saude = calculate_area_score(row, SAUDE_QUESTIONS_INDICES_APP, interest_to_weight)
    score_ti = calculate_area_score(row, TI_QUESTIONS_INDICES_APP, interest_to_weight)
    scores_dict = {"Gestão": score_gestao, "Saúde": score_saude, "TI": score_ti}
    recommended_area = "Indefinido"
    if any(s > 0 for s in scores_dict.values()):
        recommended_area = max(scores_dict, key=scores_dict.get)
    return score_gestao, score_saude, score_ti, recommended_area

def process_survey_data(filter_name=None, filter_area=None):
    processed_results = []
    try:
        if not os.path.exists(CSV_FILE_PATH):
            return [{"Nome": "Erro", "Mensagem": f"Arquivo '{CSV_FILE_PATH}' não encontrado para análise vocacional."}]
        df = pd.read_csv(CSV_FILE_PATH)

        if filter_name:
            df = df[df.iloc[:, 1].astype(str).str.contains(filter_name, case=False, na=False)]
        
        temp_results_for_filtering = []
        max_expected_index = max(max(GESTÃO_QUESTIONS_INDICES_APP), max(SAUDE_QUESTIONS_INDICES_APP), max(TI_QUESTIONS_INDICES_APP))

        for index, row in df.iterrows():
            nome = str(row.iloc[1]) if len(row) > 1 and pd.notna(row.iloc[1]) else "Participante Desconhecido"
            
            if len(row) <= max_expected_index:
                score_g, score_s, score_t, rec_area = 0,0,0, "Dados insuficientes"
            else:
                score_g, score_s, score_t, rec_area = determine_target_area_and_scores_from_row(row)
            
            temp_results_for_filtering.append({
                "original_row": row,
                "Nome": nome, 
                "Score Gestão": score_g, 
                "Score Saúde": score_s, 
                "Score TI": score_t, 
                "Área Recomendada": rec_area
            })
        
        if filter_area:
            if filter_area in ["Dados insuficientes", "Indefinido"]:
                 filtered_by_area = [
                    item for item in temp_results_for_filtering 
                    if item["Área Recomendada"] == filter_area
                ]
            else:
                filtered_by_area = [
                    item for item in temp_results_for_filtering 
                    if item["Área Recomendada"].startswith(filter_area) 
                ]
            processed_results = filtered_by_area
        else:
            processed_results = temp_results_for_filtering
            
    except Exception as e:
        print(f"Erro ao ler ou filtrar {CSV_FILE_PATH} para análise vocacional: {e}")
        traceback.print_exc()
        return [{"Nome": "Erro", "Mensagem": f"Erro ao processar/filtrar CSV para análise: {e}"}]

    return [
        {k: v for k, v in item.items() if k != 'original_row'} 
        for item in processed_results
    ]

def load_ai_metrics():
    try:
        if not os.path.exists(METRICS_FILE_PATH):
            return 0.0, 0.0, "Ainda não treinado"
        with open(METRICS_FILE_PATH, 'r') as f:
            metrics = json.load(f)
            accuracy = metrics.get("accuracy_test", 0.0)
            loss = metrics.get("loss_test", 0.0)
            timestamp_iso = metrics.get("last_trained_timestamp", None)

            formatted_timestamp = "N/A"
            if timestamp_iso:
                try:
                    dt_object = datetime.fromisoformat(timestamp_iso)
                    formatted_timestamp = dt_object.strftime("No dia %d/%m/%Y às %H:%M:%S")
                except ValueError:
                    formatted_timestamp = "Timestamp inválido"
                    print(f"AVISO: Timestamp '{timestamp_iso}' em {METRICS_FILE_PATH} não é um formato ISO válido.")
                except Exception as e:
                    formatted_timestamp = "Erro ao formatar timestamp"
                    print(f"ERRO ao formatar timestamp '{timestamp_iso}': {e}")
            
            return accuracy, loss, formatted_timestamp
    except json.JSONDecodeError:
        print(f"Erro ao decodificar JSON de {METRICS_FILE_PATH}. Retornando defaults.")
        return 0.0, 0.0, "Erro no arquivo de métricas"
    except FileNotFoundError:
        print(f"Arquivo de métricas {METRICS_FILE_PATH} não encontrado. Retornando defaults.")
        return 0.0, 0.0, "Ainda não treinado"
    except Exception as e:
        print(f"Erro desconhecido ao carregar métricas: {e}. Retornando defaults.")
        return 0.0, 0.0, "Erro ao carregar métricas"

def fetch_courses_from_api(area_endpoint_segment):
    """Busca cursos de uma área específica da API Node.js."""
    if not area_endpoint_segment:
        print("Segmento do endpoint da área está vazio, não buscando cursos.")
        return []
    try:
        api_url = f"{NODE_API_BASE_URL}/{area_endpoint_segment.lower()}"
        print(f"Buscando cursos de: {api_url}")
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        courses_data = response.json()
        print(f"Cursos recebidos para '{area_endpoint_segment}': {len(courses_data)} cursos.")
        return courses_data
    except requests.exceptions.Timeout:
        print(f"Timeout ao buscar cursos da API para '{area_endpoint_segment}' em {api_url}")
        return []
    except requests.exceptions.HTTPError as http_err:
        print(f"Erro HTTP ao buscar cursos da API para '{area_endpoint_segment}' em {api_url}: {http_err}")
        return []
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Erro de conexão ao buscar cursos da API para '{area_endpoint_segment}' em {api_url}: {conn_err}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"Erro genérico ao buscar cursos da API para '{area_endpoint_segment}' em {api_url}: {e}")
        return []
    except json.JSONDecodeError as json_err:
        print(f"Erro ao decodificar JSON da API para '{area_endpoint_segment}' em {api_url}: {json_err}")
        print(f"Conteúdo da resposta que causou o erro: {response.text[:500]}...")
        return []

TRAINING_IN_PROGRESS_FLAG = "training_lock.tmp"
csv_write_lock = threading.Lock()

class CSVChangeHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        self.last_triggered_time = 0
        self.debounce_period = 10

    def on_modified(self, event):
        if event.is_directory: return
        if os.path.abspath(event.src_path) == os.path.abspath(CSV_FILE_PATH):
            current_time = time.time()
            if current_time - self.last_triggered_time > self.debounce_period:
                self.last_triggered_time = current_time
                if os.path.exists(TRAINING_IN_PROGRESS_FLAG):
                    print(f"[{pd.Timestamp.now()}] Treinamento já em progresso...")
                    return
                print(f"[{pd.Timestamp.now()}] {CSV_FILE_PATH} modificado. Iniciando treinamento...")
                try:
                    with open(TRAINING_IN_PROGRESS_FLAG, 'w') as f: f.write("training")
                    process = subprocess.Popen(['python', '-u', 'train_ai_model.py'],
                                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    stdout, stderr = process.communicate()
                    if process.returncode == 0:
                        print(f"[{pd.Timestamp.now()}] Script de treinamento concluído.")
                        if stdout: print(f"Saída Treinamento:\n{stdout}")
                    else:
                        print(f"[{pd.Timestamp.now()}] Treinamento falhou. Código: {process.returncode}")
                        if stdout: print(f"Saída (stdout) Treinamento:\n{stdout}")
                        if stderr: print(f"Erro (stderr) Treinamento:\n{stderr}")
                except Exception as e: print(f"[{pd.Timestamp.now()}] Exceção ao treinar: {e}")
                finally:
                    if os.path.exists(TRAINING_IN_PROGRESS_FLAG): os.remove(TRAINING_IN_PROGRESS_FLAG)
            else: print(f"[{pd.Timestamp.now()}] Debouncing modificação no CSV.")

def start_file_monitor():
    print("Iniciando monitor de arquivo para o CSV...")
    event_handler = CSVChangeHandler()
    observer = Observer()
    path_to_watch = os.path.dirname(os.path.abspath(CSV_FILE_PATH)) or "."
    observer.schedule(event_handler, path_to_watch, recursive=False)
    observer.start()
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt: observer.stop()
    observer.join()
    print("Monitor de arquivo interrompido.")

@app.context_processor
def inject_user_status():
    return dict(admin_logged_in=session.get('logged_in_admin', False))

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    if not session.get('logged_in_admin'):
        flash('Por favor, faça login para acessar o painel de administrador.', 'warning')
        return redirect(url_for('show_login_form'))
    
    filter_name = request.args.get('filter_name', None)
    filter_area = request.args.get('filter_area', None)

    if filter_area == "":
        filter_area = None
        
    print(f"DEBUG: Filtros recebidos - Nome: '{filter_name}', Área: '{filter_area}'")

    survey_results = process_survey_data(filter_name=filter_name, filter_area=filter_area)
    ai_accuracy, ai_loss, last_trained = load_ai_metrics()
    nome_arquivo_grafico = 'grafico_acuracia_perda_modelo.png'
    grafico_modelo_url = None
    if os.path.exists(os.path.join(app.static_folder, nome_arquivo_grafico)):
        grafico_modelo_url = url_for('static', filename=nome_arquivo_grafico)
    
    return render_template('index.html',
                           results=survey_results,
                           ai_accuracy=ai_accuracy,
                           ai_loss=ai_loss,
                           last_trained_timestamp=last_trained,
                           grafico_modelo_url=grafico_modelo_url,
                           current_filter_name=filter_name,
                           current_filter_area=filter_area)

def get_report_data(filter_name=None, filter_area=None):
    """Função auxiliar para buscar os dados do CSV para os relatórios, aplicando filtros."""
    if not os.path.exists(CSV_FILE_PATH):
        return None, ["Erro: Arquivo de dados não encontrado."]
    try:
        data_for_report = process_survey_data(filter_name=filter_name, filter_area=filter_area)

        if not data_for_report or (isinstance(data_for_report[0], dict) and "Mensagem" in data_for_report[0]):
            error_msg = data_for_report[0]["Mensagem"] if data_for_report else "Nenhum dado encontrado com os filtros."
            return None, [error_msg]

        header = ["Nome", "Score Gestão", "Score Saúde", "Score TI", "Área Recomendada"]
        rows = []
        for item in data_for_report:
            rows.append([
                item.get("Nome", ""),
                item.get("Score Gestão", 0),
                item.get("Score Saúde", 0),
                item.get("Score TI", 0),
                item.get("Área Recomendada", "")
            ])
        return header, rows
    except Exception as e:
        print(f"Erro ao preparar dados para relatório com filtros: {e}")
        traceback.print_exc()
        return None, [f"Erro ao gerar dados para relatório: {e}"]


@app.route('/download_report/csv')
def download_csv_report():
    if not session.get('logged_in_admin'):
        return redirect(url_for('show_login_form'))

    filter_name = request.args.get('filter_name', None)
    filter_area = request.args.get('filter_area', None)
    if filter_area == "": filter_area = None

    header, data_rows = get_report_data(filter_name=filter_name, filter_area=filter_area)

    if not header or (data_rows is None and header and "Erro" in header[0]):
        flash(header[0] if header else "Não foi possível gerar o relatório CSV.", "danger")
        return redirect(url_for('admin_dashboard'))
    if not data_rows and header:
        flash("Nenhum dado encontrado para os filtros aplicados no relatório CSV.", "info")

    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(header)
    if data_rows:
        cw.writerows(data_rows)
    output = si.getvalue()
    
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition":
                 "attachment; filename=relatorio_aptidao_filtrado.csv"})

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Relatório de Aptidão Vocacional', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, title, 0, 1, 'L')
        self.ln(5)

    def chapter_body(self, header, data):
        self.set_fill_color(200, 220, 255) 
        self.set_font('Arial', 'B', 8)
        
        col_widths = [50, 25, 25, 25, 65] 
        
        for i, col_name in enumerate(header):
            self.cell(col_widths[i], 7, str(col_name), 1, 0, 'C', 1)
        self.ln()

        self.set_font('Arial', '', 8)
        for row in data:
            for i, item in enumerate(row):
                try:
                    cell_text = str(item).encode('latin-1', 'replace').decode('latin-1')
                except UnicodeEncodeError:
                    cell_text = str(item).encode('ascii', 'replace').decode('ascii')
                self.cell(col_widths[i], 6, cell_text, 1)
            self.ln()

@app.route('/download_report/pdf')
def download_pdf_report():
    if not session.get('logged_in_admin'):
        return redirect(url_for('show_login_form'))

    filter_name = request.args.get('filter_name', None)
    filter_area = request.args.get('filter_area', None)
    if filter_area == "": filter_area = None

    header, data_rows = get_report_data(filter_name=filter_name, filter_area=filter_area)

    if not header or (data_rows is None and header and "Erro" in header[0]):
        flash(header[0] if header else "Não foi possível gerar o relatório PDF.", "danger")
        return redirect(url_for('admin_dashboard'))
    if not data_rows and header:
        flash("Nenhum dado encontrado para os filtros aplicados no relatório PDF.", "info")
        return redirect(url_for('admin_dashboard'))


    pdf = PDF(orientation='P', unit='mm', format='A4') 
    pdf.add_page()
    if data_rows:
        pdf.chapter_body(header, data_rows)
    else:
        pdf.chapter_title("Relatório de Aptidão Vocacional")
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 10, "Nenhum dado encontrado para os filtros aplicados.", 0, 1, 'C')

    pdf_output_bytes = pdf.output(dest='S')
    if isinstance(pdf_output_bytes, bytearray):
        pdf_output_bytes = bytes(pdf_output_bytes)

    return Response(pdf_output_bytes,
                    mimetype='application/pdf',
                    headers={'Content-Disposition': 'attachment;filename=relatorio_aptidao_filtrado.pdf'})

@app.route('/login', methods=['GET', 'POST'])
def show_login_form():
    if session.get('logged_in_admin'):
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in_admin'] = True
            flash('Login bem-sucedido como administrador!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Nome de usuário ou senha inválidos.', 'danger')
            return redirect(url_for('show_login_form')) 
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in_admin', None)
    flash('Você foi desconectado.', 'info')
    return redirect(url_for('landing'))

@app.route('/questionnaire', methods=['GET'])
def show_questionnaire_form():
    if session.get('logged_in_admin'):
        return redirect(url_for('admin_dashboard'))

    questions_with_indices = []
    for i, text in enumerate(ORIGINAL_QUESTION_TEXTS):
        questions_with_indices.append({"id": f"q_orig_{i}", "text": text, "original_index": i})
    random.shuffle(questions_with_indices)
    return render_template('questionnaire.html', questions_shuffled=questions_with_indices)

@app.route('/submit_questionnaire', methods=['POST'])
def submit_questionnaire():
    if session.get('logged_in_admin'):
        flash('Administradores não podem submeter o questionário.', 'danger')
        return redirect(url_for('admin_dashboard'))

    user_name_for_template = request.form.get('nome', 'Anônimo')
    try:
        idade = request.form.get('idade', '0')
        answers_numeric = []
        answers_for_csv_formatted = []
        all_questions_answered = True
        for i in range(NUM_QUESTIONS):
            form_field_name = f'q_orig_{i}'
            answer_val_str = request.form.get(form_field_name)
            if not answer_val_str:
                all_questions_answered = False; break
            answers_numeric.append(int(answer_val_str))
            answers_for_csv_formatted.append(answer_value_to_string.get(answer_val_str, answer_val_str))

        if not all_questions_answered:
            return render_template('prediction_result.html', name=user_name_for_template, error="Por favor, responda todas as perguntas.")

        timestamp = datetime.now().strftime("%Y/%m/%d %I:%M:%S %p GMT%z")
        if timestamp.endswith("00"): timestamp = timestamp[:-2]
        new_row_data = [timestamp, user_name_for_template, idade] + answers_for_csv_formatted + [""]

        with csv_write_lock:
            file_exists = os.path.isfile(CSV_FILE_PATH)
            write_header = not file_exists or os.path.getsize(CSV_FILE_PATH) == 0
            with open(CSV_FILE_PATH, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if write_header:
                    header = ["Carimbo de data/hora", "Nome", "Idade"] + ORIGINAL_QUESTION_TEXTS + ["Declaro que..."]
                    writer.writerow(header)
                writer.writerow(new_row_data)
            print(f"Nova resposta (ordenada) de {user_name_for_template} adicionada ao {CSV_FILE_PATH}")
        
        user_features_weighted = np.array([interest_to_weight.get(ans, 0.0) for ans in answers_numeric]).reshape(1, -1)
        predicted_area_label_for_display = "Não foi possível determinar a área."
        area_for_api_call = None
        recommended_courses = []
        api_area_map = {"TI": "ti", "Saúde": "saude", "Gestão": "gestao"}

        try:
            print(f"\n--- Iniciando Predição IA para: {user_name_for_template} ---")
            print(f"DEBUG: SCALER_PATH existe: {os.path.exists(SCALER_PATH)}")
            print(f"DEBUG: LABEL_ENCODER_PATH existe: {os.path.exists(LABEL_ENCODER_PATH)}")
            print(f"DEBUG: MODEL_SAVE_PATH existe: {os.path.exists(MODEL_SAVE_PATH)}")

            if os.path.exists(SCALER_PATH) and os.path.exists(LABEL_ENCODER_PATH) and os.path.exists(MODEL_SAVE_PATH):
                scaler = joblib.load(SCALER_PATH)
                label_encoder = joblib.load(LABEL_ENCODER_PATH)
                model = tf.keras.models.load_model(MODEL_SAVE_PATH)
                print(f"DEBUG: LabelEncoder classes: {label_encoder.classes_ if hasattr(label_encoder, 'classes_') else 'N/A'}")
                user_features_scaled = scaler.transform(user_features_weighted)
                prediction_probs = model.predict(user_features_scaled)
                predicted_class_index = np.argmax(prediction_probs, axis=1)[0]
                temp_predicted_area_ia = "Erro IA"
                if hasattr(label_encoder, 'classes_') and predicted_class_index < len(label_encoder.classes_):
                    temp_predicted_area_ia = label_encoder.inverse_transform([predicted_class_index])[0]
                predicted_area_label_for_display = temp_predicted_area_ia
                if temp_predicted_area_ia in api_area_map:
                    area_for_api_call = temp_predicted_area_ia
                print(f"DEBUG: Predição IA: {predicted_area_label_for_display}, Área para API (após IA): {area_for_api_call}")
            else:
                print(f"DEBUG: Artefatos da IA não encontrados. Marcando para fallback para {user_name_for_template}.")
                predicted_area_label_for_display = "Análise Direta (artefatos IA ausentes)"
        except Exception as e:
            print(f"ERRO DETALHADO durante a predição IA para {user_name_for_template}:")
            traceback.print_exc()
            predicted_area_label_for_display = "Erro na Predição IA"

        if not area_for_api_call:
            print(f"DEBUG: IA não forneceu área mapeável ('{predicted_area_label_for_display}'), usando análise direta para {user_name_for_template}.")
            from pandas import Series
            pseudo_pd_series = Series([None, None, None] + answers_for_csv_formatted)
            GESTÃO_DIRECT_INDICES = list(range(3, 3 + 10)); SAUDE_DIRECT_INDICES = list(range(3 + 10, 3 + 20)); TI_DIRECT_INDICES = list(range(3 + 20, 3 + 30))
            score_g_direct = calculate_area_score(pseudo_pd_series, GESTÃO_DIRECT_INDICES, interest_to_weight)
            score_s_direct = calculate_area_score(pseudo_pd_series, SAUDE_DIRECT_INDICES, interest_to_weight)
            score_t_direct = calculate_area_score(pseudo_pd_series, TI_DIRECT_INDICES, interest_to_weight)
            scores_direct_dict = {"Gestão": score_g_direct, "Saúde": score_s_direct, "TI": score_t_direct}
            if any(s > 0 for s in scores_direct_dict.values()):
                direct_area_label = max(scores_direct_dict, key=scores_direct_dict.get)
                predicted_area_label_for_display = f"{direct_area_label} (Análise Direta)"
                if direct_area_label in api_area_map: area_for_api_call = direct_area_label
            else: predicted_area_label_for_display = "Área Indefinida (Análise Direta)"
            print(f"DEBUG: Resultado da Análise Direta: {predicted_area_label_for_display}, Área para API (após fallback): {area_for_api_call}")

        if area_for_api_call and area_for_api_call in api_area_map:
            endpoint_segment = api_area_map[area_for_api_call]
            print(f"DEBUG: Chamando fetch_courses_from_api com endpoint_segment: '{endpoint_segment}'")
            recommended_courses = fetch_courses_from_api(endpoint_segment)
            if not recommended_courses: print(f"AVISO: Nenhum curso retornado da API para {area_for_api_call} (endpoint: {endpoint_segment}).")
        else:
            print(f"AVISO: Nenhuma área válida ('{area_for_api_call}') para buscar cursos na API. `recommended_courses` permanecerá vazio.")
            recommended_courses = []
        return render_template('prediction_result.html', name=user_name_for_template, recommended_area=predicted_area_label_for_display, courses=recommended_courses)
    except Exception as e:
        print(f"ERRO GERAL em submit_questionnaire:"); traceback.print_exc()
        return render_template('prediction_result.html', name=user_name_for_template, error=f"Ocorreu um erro crítico ao processar suas respostas.")


@app.route('/api/courses/<string:area_name>')
def api_get_courses_by_area(area_name):
    print(f"DEBUG: Rota /api/courses chamada com area_name: '{area_name}'")
    api_area_map = {"TI": "ti", "Saúde": "saude", "Gestão": "gestao"}
    endpoint_segment = api_area_map.get(area_name)
    if not endpoint_segment:
        clean_area_name = area_name.split(" (")[0]
        endpoint_segment = api_area_map.get(clean_area_name)
        print(f"DEBUG: Tentativa de limpar area_name. Novo endpoint_segment: '{endpoint_segment}' para clean_area_name: '{clean_area_name}'")
    if endpoint_segment:
        courses = fetch_courses_from_api(endpoint_segment)
        if courses: return jsonify(courses)
        else: return jsonify({"error": f"Nenhum curso encontrado ou erro ao buscar para {area_name}"}), 404
    else: return jsonify({"error": "Área inválida ou não mapeada para API"}), 404


if __name__ == '__main__':
    if not os.path.exists(METRICS_FILE_PATH):
        with open(METRICS_FILE_PATH, 'w') as f:
            json.dump({"accuracy_test": 0.0, "loss_test": 0.0, "last_trained_timestamp": None}, f)
    if not os.path.exists(CSV_FILE_PATH):
        with open(CSV_FILE_PATH, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            header = ["Carimbo de data/hora","Nome","Idade"] + ORIGINAL_QUESTION_TEXTS + ["Declaro que somente para o uso deste projeto, aceito a coleta dos dados inseridos!"]
            writer.writerow(header)
        print(f"Arquivo {CSV_FILE_PATH} criado com cabeçalho.")
    monitor_thread = threading.Thread(target=start_file_monitor, daemon=True)
    monitor_thread.start()
    app.run(debug=True, use_reloader=False)