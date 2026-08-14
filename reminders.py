"""
Background service that checks every minute whether any user has a meal or
exercise reminder due, and emails them if so.
"""
import threading
import time
import datetime

import database
import email_service


def check_and_send_reminders():
    """Check all users' reminder settings against the current time and send any that are due."""
    try:
        current_time = datetime.datetime.now().strftime("%H:%M")

        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.id, u.username, u.email,
                   r.enable_breakfast, r.breakfast_time,
                   r.enable_lunch, r.lunch_time,
                   r.enable_dinner, r.dinner_time,
                   r.enable_exercise, r.exercise_time,
                   r.dietary_preference
            FROM users u
            LEFT JOIN user_reminders r ON u.id = r.user_id
        ''')
        users = cursor.fetchall()
        conn.close()

        for user in users:
            _, username, email, enable_breakfast, breakfast_time, \
                enable_lunch, lunch_time, enable_dinner, dinner_time, \
                enable_exercise, exercise_time, dietary_preference = (
                    list(user) + [None] * (12 - len(user))
                )
            dietary_preference = dietary_preference or 'balanced'

            if enable_breakfast == 1 and breakfast_time and breakfast_time[:5] == current_time:
                meal = database.get_meal_suggestion('breakfast', dietary_preference)
                if meal:
                    email_service.send_meal_reminder_email(email, username, 'breakfast', meal)

            if enable_lunch == 1 and lunch_time and lunch_time[:5] == current_time:
                meal = database.get_meal_suggestion('lunch', dietary_preference)
                if meal:
                    email_service.send_meal_reminder_email(email, username, 'lunch', meal)

            if enable_dinner == 1 and dinner_time and dinner_time[:5] == current_time:
                meal = database.get_meal_suggestion('dinner', dietary_preference)
                if meal:
                    email_service.send_meal_reminder_email(email, username, 'dinner', meal)

            if enable_exercise == 1 and exercise_time and exercise_time[:5] == current_time:
                exercise = database.get_exercise_suggestion()
                if exercise:
                    email_service.send_exercise_reminder_email(email, username, exercise)

    except Exception as e:
        print(f"Error in reminder checker: {e}")


def _run_scheduler():
    print("Reminder service started")
    while True:
        try:
            check_and_send_reminders()
        except Exception as e:
            print(f"Scheduler error: {e}")
        time.sleep(60)


def start_reminder_service():
    """Start the reminder-checking loop in a background daemon thread."""
    thread = threading.Thread(target=_run_scheduler, daemon=True)
    thread.start()
    print("Reminder service running in background")
