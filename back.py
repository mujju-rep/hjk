from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import pandas as pd
import os
import google.generativeai as genai

app = Flask(__name__)
CORS(app)

genai.configure(api_key="YOUR_GEMINI_API_KEY")  # Replace with your actual API key
model = genai.GenerativeModel("gemini-pro")

df = pd.DataFrame()
results_df = pd.DataFrame()

@app.route('/upload', methods=['POST'])
def upload():
    global df
    file = request.files['file']
    ext = file.filename.split('.')[-1]
    if ext in ['xlsx', 'xls']:
        df = pd.read_excel(file)
    elif ext == 'csv':
        df = pd.read_csv(file)
    else:
        return jsonify({'error': 'Unsupported file type'}), 400
    return jsonify({"columns": list(df.columns)})

@app.route('/filter-values', methods=['POST'])
def get_filter_values():
    global df
    column = request.json['column']
    if column not in df.columns:
        return jsonify({"values": []})
    values = df[column].dropna().unique().tolist()
    return jsonify({"values": values})

@app.route('/analyze', methods=['POST'])
def analyze():
    global df, results_df
    data = request.json
    answer_col = data['answer_col']
    filter_col = data['filter_col']
    filter_val = data['filter_val']
    top_k = int(data['top_k'])

    filtered = df[df[filter_col] == filter_val].dropna(subset=[answer_col])
    if filtered.empty:
        return jsonify([])

    scores = []
    for answer in filtered[answer_col].astype(str).tolist():
        prompt = f"Evaluate this response for a club application: \"{answer}\". Give a score out of 10 based on clarity, motivation, and relevance. Only return the score."
        try:
            response = model.generate_content(prompt)
            score_text = response.text.strip().split("\n")[0]
            score = float(''.join(filter(str.isdigit, score_text))[:2])
            score = min(score, 10) if score else 0
        except Exception:
            score = 0
        scores.append(score)

    filtered = filtered.copy()
    filtered['score'] = scores
    filtered = filtered.sort_values(by='score', ascending=False).head(top_k)
    results_df = filtered

    return jsonify(filtered.drop(columns=['score']).to_dict(orient='records'))

@app.route('/export', methods=['GET'])
def export():
    global results_df
    out_path = 'top_responses.csv'
    results_df.to_csv(out_path, index=False)
    return send_file(out_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
