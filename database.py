"""
SQLite database access: schema setup and small lookup queries used by the
reminder feature. User auth and prediction queries live directly in the
route handlers in app.py since they're each used in exactly one place.
"""
import sqlite3

import config


def get_connection():
    """Open a new connection to the app database.

    timeout=10 means if the database is briefly locked by another
    connection's write, this waits up to 10s instead of immediately
    raising 'database is locked'.
    """
    return sqlite3.connect(config.DATABASE_PATH, timeout=10)


def init_db():
    """Create all tables if they don't exist yet, and seed default lookup data."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA synchronous=NORMAL;")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            timestamp TEXT,
            age INTEGER,
            gender TEXT,
            bmi REAL,
            hypertension INTEGER,
            heart_disease INTEGER,
            smoking_history TEXT,
            blood_glucose_level INTEGER,
            prediction TEXT,
            probability REAL,
            email_sent INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            enable_breakfast INTEGER DEFAULT 0,
            breakfast_time TEXT DEFAULT '08:00:00',
            enable_lunch INTEGER DEFAULT 0,
            lunch_time TEXT DEFAULT '13:00:00',
            enable_dinner INTEGER DEFAULT 0,
            dinner_time TEXT DEFAULT '19:00:00',
            enable_exercise INTEGER DEFAULT 0,
            exercise_time TEXT DEFAULT '18:00:00',
            dietary_preference TEXT DEFAULT 'balanced',
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS meal_suggestions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meal_type TEXT,
            meal_name TEXT,
            description TEXT,
            calories INTEGER,
            prep_time INTEGER,
            dietary_preference TEXT,
            is_active INTEGER DEFAULT 1
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exercise_suggestions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exercise_name TEXT,
            duration_minutes INTEGER,
            difficulty TEXT,
            calories_burn_estimate INTEGER,
            instructions TEXT,
            is_active INTEGER DEFAULT 1
        )
    ''')

    _seed_defaults(cursor)

    conn.commit()
    conn.close()
    print("Database ready with all tables")


def _seed_defaults(cursor):
    cursor.execute("SELECT COUNT(*) FROM meal_suggestions")
    if cursor.fetchone()[0] == 0:
        default_meals = [
            ('breakfast', 'Oatmeal with Berries', 'Rolled oats topped with fresh berries and a drizzle of honey', 350, 10, 'balanced'),
            ('breakfast', 'Greek Yogurt Parfait', 'Greek yogurt with granola and mixed berries', 320, 5, 'balanced'),
            ('lunch', 'Grilled Chicken Salad', 'Grilled chicken breast over mixed greens with vinaigrette', 450, 15, 'balanced'),
            ('lunch', 'Quinoa Bowl', 'Quinoa with roasted vegetables and tahini dressing', 420, 20, 'vegetarian'),
            ('dinner', 'Baked Salmon with Vegetables', 'Salmon fillet baked with asparagus and cherry tomatoes', 500, 25, 'balanced'),
            ('dinner', 'Lentil Soup', 'Hearty lentil soup with vegetables and spices', 380, 30, 'vegetarian'),
        ]
        cursor.executemany('''
            INSERT INTO meal_suggestions (meal_type, meal_name, description, calories, prep_time, dietary_preference)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', default_meals)

    cursor.execute("SELECT COUNT(*) FROM exercise_suggestions")
    if cursor.fetchone()[0] == 0:
        default_exercises = [
            ('Brisk Walking', 30, 'Easy', 150, 'Walk at a fast pace, keeping your heart rate elevated'),
            ('Yoga', 20, 'Easy', 100, 'Basic stretching and breathing exercises'),
            ('Cycling', 30, 'Moderate', 250, 'Stationary or outdoor cycling at steady pace'),
        ]
        cursor.executemany('''
            INSERT INTO exercise_suggestions (exercise_name, duration_minutes, difficulty, calories_burn_estimate, instructions)
            VALUES (?, ?, ?, ?, ?)
        ''', default_exercises)


def get_meal_suggestion(meal_type, dietary_preference):
    """Return a random active meal matching the preference, falling back to 'balanced'."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT meal_name, description, calories, prep_time
            FROM meal_suggestions
            WHERE meal_type = ? AND dietary_preference = ? AND is_active = 1
            ORDER BY RANDOM()
            LIMIT 1
        ''', (meal_type, dietary_preference))
        result = cursor.fetchone()

        if not result:
            cursor.execute('''
                SELECT meal_name, description, calories, prep_time
                FROM meal_suggestions
                WHERE meal_type = ? AND dietary_preference = 'balanced' AND is_active = 1
                ORDER BY RANDOM()
                LIMIT 1
            ''', (meal_type,))
            result = cursor.fetchone()

        if not result:
            return None

        return {
            'meal_name': result[0],
            'description': result[1],
            'calories': result[2],
            'prep_time': result[3],
        }
    except Exception as e:
        print(f"Error getting meal suggestion: {e}")
        return None
    finally:
        conn.close()


def get_exercise_suggestion():
    """Return a random active exercise suggestion."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT exercise_name, duration_minutes, difficulty,
                   calories_burn_estimate, instructions
            FROM exercise_suggestions
            WHERE is_active = 1
            ORDER BY RANDOM()
            LIMIT 1
        ''')
        result = cursor.fetchone()
        if not result:
            return None

        return {
            'exercise_name': result[0],
            'duration_minutes': result[1],
            'difficulty': result[2],
            'calories_burn_estimate': result[3],
            'instructions': result[4],
        }
    except Exception as e:
        print(f"Error getting exercise suggestion: {e}")
        return None
    finally:
        conn.close()
