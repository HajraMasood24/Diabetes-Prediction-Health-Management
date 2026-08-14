import datetime
import os
import sqlite3
import csv
import io
from functools import wraps

import bcrypt
import jwt
import pandas as pd
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS

import config
import database
import prediction
import ai_advice
import email_service
import reports
import reminders
from validation import validate_input

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = config.SECRET_KEY

database.init_db()
prediction.load_model_and_preprocessor()

#AUTH DECORATOR
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'success': False, 'error': 'Token missing'}), 401
        try:
            token = token.split(' ')[1]
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user_id = data['user_id']
        except Exception:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401
        return f(current_user_id, *args, **kwargs)
    return decorated

#UI ROUTES
@app.route('/')
def serve_landing():
    return send_from_directory('ui', 'landing.html')

@app.route('/landing')
def landing():
    return send_from_directory('ui', 'landing.html')

@app.route('/login')
def login_page():
    return send_from_directory('ui', 'login.html')

@app.route('/signup')
def signup_page():
    return send_from_directory('ui', 'signup.html')

@app.route('/profile')
def profile_page():
    return send_from_directory('ui', 'profile.html')

@app.route('/dashboard')
def dashboard_page():
    return send_from_directory('ui', 'dashboard.html')

@app.route('/doctors')
def doctors_page():
    return send_from_directory('ui', 'doctors.html')

@app.route('/chatbot')
def chatbot_page():
    return send_from_directory('ui', 'chatbot.html')

@app.route('/wellness')
def wellness_page():
    return send_from_directory('ui', 'wellness.html')

@app.route('/app')
def app_page():
    """Main prediction form, shown after login."""
    return send_from_directory('ui', 'index.html')

@app.route('/ui/<path:filename>')
def serve_ui_files(filename):
    return send_from_directory('ui', filename)

#AUTH ENDPOINTS
@app.route('/api/signup', methods=['POST'])
def signup():
    try:
        data = request.json
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

        if not all([username, email, password]):
            return jsonify({'success': False, 'error': 'Missing fields'}), 400

        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, email, password, created_at) VALUES (?, ?, ?, ?)",
            (username, email, hashed, str(datetime.datetime.now()))
        )
        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': 'User created successfully'})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'error': 'Username or email already exists'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')

        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, password FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and bcrypt.checkpw(password.encode(), user[1]):
            token = jwt.encode(
                {'user_id': user[0], 'username': username},
                app.config['SECRET_KEY'], algorithm='HS256'
            )
            return jsonify({'success': True, 'token': token, 'user_id': user[0]})

        return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/user-info', methods=['GET'])
@token_required
def get_user_info(current_user_id):
    try:
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT username, email, created_at FROM users WHERE id = ?", (current_user_id,))
        user = cursor.fetchone()
        conn.close()

        if user:
            return jsonify({
                'success': True,
                'username': user[0],
                'email': user[1],
                'member_since': user[2][:10] if user[2] else 'Recently'
            })
        return jsonify({'success': False, 'error': 'User not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/account', methods=['DELETE'])
@token_required
def delete_account(current_user_id):
    """Permanently delete the current user's account and all their data.
    Requires the account password in the request body to confirm intent.
    """
    try:
        data = request.get_json() or {}
        password = data.get('password')
        if not password:
            return jsonify({'success': False, 'error': 'Password is required to delete your account'}), 400

        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM users WHERE id = ?", (current_user_id,))
        user = cursor.fetchone()

        if not user or not bcrypt.checkpw(password.encode(), user[0]):
            conn.close()
            return jsonify({'success': False, 'error': 'Incorrect password'}), 401

        cursor.execute("DELETE FROM predictions WHERE user_id = ?", (current_user_id,))
        cursor.execute("DELETE FROM user_reminders WHERE user_id = ?", (current_user_id,))
        cursor.execute("DELETE FROM users WHERE id = ?", (current_user_id,))
        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': 'Account deleted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

#PREDICTION ENDPOINTS
@app.route('/api/predict', methods=['POST'])
@token_required
def predict(current_user_id):
    try:
        data = request.json
        errors = validate_input(data)
        if errors:
            return jsonify({'success': False, 'errors': errors}), 400

        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT username, email FROM users WHERE id = ?", (current_user_id,))
        user = cursor.fetchone()
        username, email = user if user else ("User", None)

        probability, pred_label = prediction.make_real_prediction(data)
        print(f"Prediction for user {username}: {pred_label} ({probability:.2%})")

        advice = ai_advice.get_ai_advice(pred_label, probability, data)

        email_sent = 0
        if pred_label == "Diabetic" and probability > 0.7 and email:
            if email_service.send_high_risk_alert(email, username, probability, advice):
                email_sent = 1

        cursor.execute('''
            INSERT INTO predictions
            (user_id, timestamp, age, gender, bmi, hypertension, heart_disease,
             smoking_history, blood_glucose_level, prediction, probability, email_sent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            current_user_id, str(datetime.datetime.now()),
            data['age'], data['gender'], data['bmi'],
            data['hypertension'], data['heart_disease'],
            data['smoking_history'], data['blood_glucose_level'],
            pred_label, probability, email_sent
        ))
        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'prediction': pred_label,
            'probability': probability,
            'risk_level': 'High' if probability > 0.7 else 'Moderate' if probability > 0.3 else 'Low',
            'dietary_advice': advice,
            'email_alert_sent': bool(email_sent),
            'timestamp': str(datetime.datetime.now())
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/dietary', methods=['POST'])
@token_required
def dietary_advice(current_user_id):
    try:
        data = request.json
        user_query = data.get('query', '')
        if not user_query:
            return jsonify({'success': False, 'error': 'Query required'}), 400

        advice = ai_advice.get_custom_advice(user_query)
        return jsonify({
            'success': True,
            'query': user_query,
            'advice': advice,
            'timestamp': str(datetime.datetime.now())
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

#STATS / HISTORY / EXPORT
@app.route('/api/public-statistics')
def public_statistics():
    """Public statistics for the landing page — loaded from the CSV dataset."""
    try:
        df = pd.read_csv(config.DATASET_CSV_PATH)
        total = len(df)
        diabetic_count = df['diabetes'].sum() if 'diabetes' in df.columns else 0
        high_risk_percentage = round((diabetic_count / total * 100) if total > 0 else 0)

        smoking_stats = {}
        if 'smoking_history' in df.columns:
            smoking_stats = {k: int(v) for k, v in df['smoking_history'].value_counts().to_dict().items()}

        return jsonify({
            'success': True,
            'total_assessments': total,
            'diabetic_count': int(diabetic_count),
            'high_risk_percentage': high_risk_percentage,
            'avg_age': round(df['age'].mean(), 1) if 'age' in df.columns else 0,
            'avg_bmi': round(df['bmi'].mean(), 1) if 'bmi' in df.columns else 0,
            'avg_glucose': round(df['blood_glucose_level'].mean(), 1) if 'blood_glucose_level' in df.columns else 0,
            'female_count': int(len(df[df['gender'] == 'Female'])) if 'gender' in df.columns else 0,
            'male_count': int(len(df[df['gender'] == 'Male'])) if 'gender' in df.columns else 0,
            'smoking_stats': smoking_stats,
            'insight': (
                f'Based on global diabetes dataset analysis: out of {total:,} individuals, '
                f'{diabetic_count:,} ({high_risk_percentage}%) have diabetes. Regular screening '
                'and healthy lifestyle choices can help prevent type 2 diabetes.'
            )
        })
    except Exception as e:
        print(f"Error loading dataset: {e}")
        try:
            conn = database.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM predictions")
            total = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM predictions WHERE probability > 0.7")
            high_risk = cursor.fetchone()[0]
            cursor.execute("SELECT AVG(age) FROM predictions")
            avg_age = cursor.fetchone()[0] or 0
            cursor.execute("SELECT AVG(bmi) FROM predictions")
            avg_bmi = cursor.fetchone()[0] or 0
            conn.close()

            high_risk_percentage = round((high_risk / total * 100) if total > 0 else 0)
            return jsonify({
                'success': True,
                'total_assessments': total,
                'high_risk_percentage': high_risk_percentage,
                'avg_age': round(avg_age),
                'avg_bmi': round(avg_bmi, 1),
                'insight': 'Regular screening and healthy lifestyle choices can prevent up to 70% of type 2 diabetes cases.'
            })
        except Exception as fallback_error:
            return jsonify({'success': False, 'error': str(fallback_error)}), 500


@app.route('/api/statistics', methods=['GET'])
@token_required
def get_statistics(current_user_id):
    try:
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT prediction, probability, age, bmi FROM predictions WHERE user_id = ?",
            (current_user_id,)
        )
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return jsonify({'success': True, 'message': 'No data yet', 'statistics': {}})

        df = pd.DataFrame(rows, columns=['prediction', 'probability', 'age', 'bmi'])
        stats = {
            'total_predictions': len(df),
            'diabetic_count': int(len(df[df['prediction'] == 'Diabetic'])),
            'non_diabetic_count': int(len(df[df['prediction'] == 'Non-diabetic'])),
            'current_age': int(df['age'].iloc[-1]),
            'avg_bmi': float(df['bmi'].mean()),
            'avg_risk_probability': float(df['probability'].mean()),
            'risk_distribution': {
                'High': int(len(df[df['probability'] > 0.7])),
                'Moderate': int(len(df[(df['probability'] > 0.3) & (df['probability'] <= 0.7)])),
                'Low': int(len(df[df['probability'] <= 0.3])),
            }
        }
        return jsonify({'success': True, 'statistics': stats})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/history', methods=['GET'])
@token_required
def get_history(current_user_id):
    try:
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, timestamp, age, gender, bmi, prediction, probability
            FROM predictions WHERE user_id = ?
            ORDER BY timestamp DESC LIMIT 50
        ''', (current_user_id,))
        rows = cursor.fetchall()
        conn.close()

        history = [
            {
                'id': r[0], 'timestamp': r[1], 'age': r[2], 'gender': r[3],
                'bmi': r[4], 'prediction': r[5], 'probability': r[6],
            }
            for r in rows
        ]
        return jsonify({'success': True, 'history': history, 'count': len(history)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/export/csv', methods=['GET'])
@token_required
def export_csv(current_user_id):
    try:
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT timestamp, age, gender, bmi, hypertension, heart_disease,
                   smoking_history, blood_glucose_level, prediction, probability
            FROM predictions WHERE user_id = ?
            ORDER BY timestamp DESC
        ''', (current_user_id,))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return jsonify({'success': False, 'error': 'No data to export'}), 404

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Timestamp', 'Age', 'Gender', 'BMI', 'Hypertension', 'Heart Disease',
                          'Smoking History', 'Blood Glucose', 'Prediction', 'Probability'])
        writer.writerows(rows)
        output.seek(0)

        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv', as_attachment=True,
            download_name=f'diabetes_predictions_{current_user_id}.csv'
        )
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/export/pdf', methods=['GET'])
@token_required
def export_pdf(current_user_id):
    try:
        conn = database.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT username, email FROM users WHERE id = ?", (current_user_id,))
        user = cursor.fetchone()
        username, email = user[0], user[1]

        cursor.execute('''
            SELECT timestamp, age, gender, bmi, blood_glucose_level, prediction, probability
            FROM predictions WHERE user_id = ?
            ORDER BY timestamp DESC LIMIT 10
        ''', (current_user_id,))
        predictions_rows = cursor.fetchall()

        cursor.execute('''
            SELECT prediction, probability, timestamp FROM predictions
            WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1
        ''', (current_user_id,))
        latest = cursor.fetchone()
        conn.close()

        if not predictions_rows:
            return jsonify({'success': False, 'error': 'No data to generate report'}), 404

        buffer = reports.build_prediction_report_pdf(username, email, predictions_rows, latest)

        return send_file(
            buffer, mimetype='application/pdf', as_attachment=True,
            download_name=f'Diabetes_Report_{username}_{datetime.datetime.now().strftime("%Y%m%d")}.pdf'
        )
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': str(datetime.datetime.now()),
        'model_loaded': prediction.model is not None,
        'preprocessor_loaded': prediction.preprocessor is not None,
    })

#REMINDER SETTINGS ENDPOINTS
@app.route('/api/reminder/settings', methods=['GET'])
@token_required
def get_reminder_settings(current_user_id):
    try:
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT enable_breakfast, breakfast_time, enable_lunch, lunch_time,
                   enable_dinner, dinner_time, enable_exercise, exercise_time,
                   dietary_preference
            FROM user_reminders WHERE user_id = ?
        ''', (current_user_id,))
        row = cursor.fetchone()
        conn.close()

        defaults = {
            'enable_breakfast': False, 'breakfast_time': '08:00:00',
            'enable_lunch': False, 'lunch_time': '13:00:00',
            'enable_dinner': False, 'dinner_time': '19:00:00',
            'enable_exercise': False, 'exercise_time': '18:00:00',
            'dietary_preference': 'balanced',
        }
        if not row:
            return jsonify(defaults), 200

        settings = {
            'enable_breakfast': bool(row[0]), 'breakfast_time': row[1] or defaults['breakfast_time'],
            'enable_lunch': bool(row[2]), 'lunch_time': row[3] or defaults['lunch_time'],
            'enable_dinner': bool(row[4]), 'dinner_time': row[5] or defaults['dinner_time'],
            'enable_exercise': bool(row[6]), 'exercise_time': row[7] or defaults['exercise_time'],
            'dietary_preference': row[8] or defaults['dietary_preference'],
        }
        return jsonify(settings), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/reminder/settings', methods=['POST'])
@token_required
def update_reminder_settings(current_user_id):
    try:
        data = request.get_json()
        now = str(datetime.datetime.now())

        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM user_reminders WHERE user_id = ?", (current_user_id,))
        exists = cursor.fetchone()

        values = (
            1 if data.get('enable_breakfast', False) else 0, data.get('breakfast_time', '08:00:00'),
            1 if data.get('enable_lunch', False) else 0, data.get('lunch_time', '13:00:00'),
            1 if data.get('enable_dinner', False) else 0, data.get('dinner_time', '19:00:00'),
            1 if data.get('enable_exercise', False) else 0, data.get('exercise_time', '18:00:00'),
            data.get('dietary_preference', 'balanced'),
        )

        if exists:
            cursor.execute('''
                UPDATE user_reminders
                SET enable_breakfast = ?, breakfast_time = ?,
                    enable_lunch = ?, lunch_time = ?,
                    enable_dinner = ?, dinner_time = ?,
                    enable_exercise = ?, exercise_time = ?,
                    dietary_preference = ?, updated_at = ?
                WHERE user_id = ?
            ''', values + (now, current_user_id))
        else:
            cursor.execute('''
                INSERT INTO user_reminders
                (user_id, enable_breakfast, breakfast_time, enable_lunch, lunch_time,
                 enable_dinner, dinner_time, enable_exercise, exercise_time,
                 dietary_preference, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (current_user_id,) + values + (now, now))

        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Reminder settings updated successfully'}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/reminder/test', methods=['POST'])
@token_required
def test_reminder(current_user_id):
    try:
        data = request.get_json()
        reminder_type = data.get('type', 'breakfast')

        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT username, email FROM users WHERE id = ?", (current_user_id,))
        user = cursor.fetchone()
        cursor.execute("SELECT dietary_preference FROM user_reminders WHERE user_id = ?", (current_user_id,))
        pref_row = cursor.fetchone()
        conn.close()

        if not user:
            return jsonify({'error': 'User not found'}), 404

        username, email = user[0], user[1]
        dietary_preference = pref_row[0] if pref_row else 'balanced'

        if reminder_type == 'exercise':
            exercise = database.get_exercise_suggestion()
            if exercise:
                email_service.send_exercise_reminder_email(email, username, exercise)
                return jsonify({'success': True, 'message': f'Test {reminder_type} reminder sent!'}), 200
        else:
            meal = database.get_meal_suggestion(reminder_type, dietary_preference)
            if meal:
                email_service.send_meal_reminder_email(email, username, reminder_type, meal)
                return jsonify({'success': True, 'message': f'Test {reminder_type} reminder sent!'}), 200

        return jsonify({'error': 'Failed to get suggestion'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

#ENTRY POINT
if __name__ == '__main__':
  
    if not config.DEBUG or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        reminders.start_reminder_service()

    print("\n" + "=" * 50)
    print("DIABETES PREDICTION API SERVER")
    print("=" * 50)
    print(f"UI:           http://127.0.0.1:{config.PORT}")
    print(f"Dashboard:    http://127.0.0.1:{config.PORT}/dashboard")
    print(f"Health check: http://127.0.0.1:{config.PORT}/api/health")
    print("=" * 50)
    print("Press CTRL+C to stop\n")

    app.run(debug=config.DEBUG, host=config.HOST, port=config.PORT)
