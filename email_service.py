"""Email sending: high-risk alerts and meal/exercise reminders.
All three email types share the same layout (header, colored info box,
details table, footer) so the shared CSS/skeleton lives in
_EMAIL_CSS / _wrap_email() and each function only builds its own body content."""

import smtplib
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import config

_EMAIL_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; line-height: 1.5; background-color: #f0f0f0; padding: 0; margin: 0; }
.email-container { max-width: 100%; background: #ffffff; }
.header { background-color: #5C2525; padding: 28px 24px; text-align: center; }
.company-name { color: #ffffff; font-size: 22px; font-weight: 700; letter-spacing: 0.3px; margin: 0; }
.header-subtitle { color: #e0c8c8; font-size: 13px; margin: 8px 0 0 0; letter-spacing: 0.6px; }
.content { padding: 28px 24px; }
.salutation { font-size: 16px; color: #1a1a1a; margin-bottom: 16px; font-weight: 600; }
.intro { font-size: 14px; color: #4a4a4a; margin-bottom: 24px; line-height: 1.6; }
.highlight-box { background-color: #5C2525; padding: 22px 20px; margin: 24px 0; border-radius: 12px; text-align: center; }
.highlight-label { font-size: 11px; letter-spacing: 1.5px; text-transform: uppercase; opacity: 0.8; margin-bottom: 8px; color: #e0c8c8; }
.highlight-value { font-size: 40px; font-weight: 700; line-height: 1; margin: 8px 0; color: #ffffff; }
.highlight-sub { font-size: 13px; margin-top: 6px; opacity: 0.9; color: #e0c8c8; }
.details-table { width: 100%; margin: 20px 0; border-collapse: collapse; background-color: #f8f8f8; border-radius: 10px; overflow: hidden; }
.details-table td { padding: 12px 16px; font-size: 13px; border-bottom: 1px solid #e8e8e8; }
.details-table td:first-child { font-weight: 700; width: 42%; }
.details-table tr:last-child td { border-bottom: none; }
.section-heading { font-size: 16px; font-weight: 700; color: #1a1a1a; margin: 28px 0 14px 0; padding-bottom: 8px; border-bottom: 2px solid #5C2525; display: inline-block; }
.note-box { background-color: #fff8f0; border-left: 3px solid #5C2525; padding: 18px 20px; margin: 16px 0; font-size: 14px; color: #2c2c2c; line-height: 1.7; border-radius: 0 10px 10px 0; }
.note-box strong { color: #5C2525; font-weight: 700; display: block; margin-top: 12px; }
.note-box strong:first-child { margin-top: 0; }
.action-list { list-style: none; margin: 16px 0; counter-reset: action-counter; padding: 0; }
.action-item { padding: 10px 0 10px 30px; font-size: 14px; color: #2c2c2c; border-bottom: 1px solid #eeeeee; position: relative; counter-increment: action-counter; }
.action-item:before { content: counter(action-counter) "."; position: absolute; left: 5px; font-weight: 700; color: #5C2525; }
.disclaimer-box { background-color: #fdf8f0; border: 1px solid #e8ddd0; padding: 16px 18px; margin-top: 28px; border-radius: 10px; font-size: 12px; color: #6b5b4f; line-height: 1.6; }
.disclaimer-heading { font-weight: 700; color: #5C2525; margin-bottom: 8px; font-size: 13px; }
.footer { background-color: #f0f0f0; padding: 18px 24px; text-align: center; font-size: 11px; color: #8a8a8a; }
.footer-company { color: #5C2525; font-weight: 600; margin-bottom: 4px; }
@media (prefers-color-scheme: dark) {
  body { background-color: #121212; }
  .email-container { background: #1e1e1e; }
  .salutation, .section-heading { color: #ffffff; }
  .intro, .action-item { color: #bbbbbb; border-bottom-color: #2c2c2c; }
  .details-table { background-color: #252525; }
  .details-table td { color: #dddddd; border-bottom-color: #333333; }
  .note-box { background-color: #2a2415; color: #dddddd; }
  .note-box strong { color: #c97a5e; }
  .disclaimer-box { background-color: #2a2415; border-color: #4a3a2a; color: #bbaa99; }
  .disclaimer-heading { color: #c97a5e; }
  .footer { background-color: #181818; color: #6a6a6a; }
  .footer-company { color: #c97a5e; }
}
@media only screen and (max-width: 600px) {
  .header, .content { padding: 24px 20px; }
  .highlight-value { font-size: 34px; }
  .company-name { font-size: 20px; }
  .section-heading { font-size: 15px; }
}
"""
def _wrap_email(subtitle, body_html, footer_line):
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<meta name="color-scheme" content="light dark">
<style>{_EMAIL_CSS}</style>
</head>
<body>
<div class="email-container">
  <div class="header">
    <h1 class="company-name">{config.EMAIL_DISPLAY_NAME}</h1>
    <p class="header-subtitle">{subtitle}</p>
  </div>
  <div class="content">
    {body_html}
  </div>
  <div class="footer">
    <div class="footer-company">{config.EMAIL_DISPLAY_NAME}</div>
    <div>{footer_line}</div>
    <div style="margin-top: 6px;">This is an automated message. Please do not reply to this email.</div>
  </div>
</div>
</body>
</html>"""

def _send(to_email, subject, text_body, html_body):
    msg = MIMEMultipart('alternative')
    msg['From'] = f'{config.EMAIL_DISPLAY_NAME} <{config.EMAIL_SENDER}>'
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(text_body, 'plain'))
    msg.attach(MIMEText(html_body, 'html'))

    server = smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT)
    try:
        server.starttls()
        server.login(config.EMAIL_SENDER, config.EMAIL_PASSWORD)
        server.send_message(msg)
    finally:
        server.quit()

def send_high_risk_alert(email, username, probability, advice):
#Email a user their high-risk diabetes assessment and clinical recommendations.
    try:
        clean_advice = (
            advice.replace('**', '')
            .replace('Foods to Avoid:', '<strong>Foods to Avoid:</strong>')
            .replace('Foods to Eat:', '<strong>Foods to Eat:</strong>')
            .replace('Lifestyle Changes:', '<strong>Lifestyle Changes:</strong>')
        )
        now = datetime.datetime.now()

        text_body = f"""DIABETES RISK ASSESSMENT RESULTS

Dear {username},
We have completed your diabetes risk assessment based on the health information you provided.

ASSESSMENT SUMMARY
Risk Level: HIGH RISK
Risk Probability: {probability:.1%}
Assessment Date: {now.strftime('%B %d, %Y')}

CLINICAL RECOMMENDATIONS
{advice.replace('**', '')}

IMMEDIATE ACTION REQUIRED
1. Schedule an appointment with your healthcare provider within 2 weeks
2. Begin daily monitoring of fasting blood glucose levels
3. Implement the dietary and lifestyle modifications outlined above
4. Present this assessment to your physician during consultation

MEDICAL DISCLAIMER
This assessment is generated using AI-based predictive analytics and is intended for informational purposes only. It does not constitute medical diagnosis or treatment advice. Consult a qualified healthcare professional for comprehensive evaluation and personalized care.

Regards,
{config.EMAIL_DISPLAY_NAME}
Clinical Assessment Team

---
This is an automated message. Please do not reply to this email."""

        body_html = f"""
<div class="salutation">Dear {username},</div>
<div class="intro">Following the analysis of your health data, we have prepared this comprehensive risk assessment report. Please review the findings and recommendations carefully.</div>
<div class="highlight-box">
  <div class="highlight-label">Risk Assessment Result</div>
  <div class="highlight-value">{probability:.1%}</div>
  <div class="highlight-sub">High Risk Category · Clinical Attention Advised</div>
</div>
<table class="details-table">
  <tr><td>Assessment Date</td><td>{now.strftime('%B %d, %Y at %I:%M %p')}</td></tr>
  <tr><td>Patient Reference</td><td>DP-{username.upper()[:6]}-{now.strftime('%Y%m')}</td></tr>
  <tr><td>Risk Classification</td><td style="color: #5C2525; font-weight: 600;">High Risk</td></tr>
</table>
<div class="section-heading">Clinical Recommendations</div>
<div class="note-box">{clean_advice.replace(chr(10), '<br>')}</div>
<div class="section-heading">Required Actions</div>
<ul class="action-list">
  <li class="action-item">Schedule an appointment with your healthcare provider within 2 weeks</li>
  <li class="action-item">Begin daily monitoring of fasting blood glucose levels</li>
  <li class="action-item">Implement the dietary and lifestyle modifications outlined above</li>
  <li class="action-item">Present this assessment to your physician during consultation</li>
</ul>
<div class="disclaimer-box">
  <div class="disclaimer-heading">Medical Disclaimer</div>
  This assessment is generated using AI-based predictive analytics and is intended for informational purposes only. It does not constitute medical diagnosis or treatment advice. Please consult a qualified healthcare professional for comprehensive evaluation and personalized care.
</div>"""

        html_body = _wrap_email("Clinical Risk Assessment", body_html, "Clinical AI Risk Assessment · Secure & Confidential")
        _send(email, 'Diabetes Risk Assessment - High Risk Alert', text_body, html_body)
        print(f"Email sent successfully to {email}")
        return True
    except Exception as e:
        print(f"Email delivery failed: {e}")
        return False


def send_meal_reminder_email(user_email, username, meal_type, meal_suggestion):
#Email a user a suggested meal for the given meal type.
    try:
        text_body = f"""DIABETES PREDICTION CO - HEALTHY MEAL REMINDER

Dear {username},

It's time for your {meal_type}. Here is a healthy meal suggestion based on your preferences.

MEAL SUGGESTION
Meal: {meal_suggestion['meal_name']}
Description: {meal_suggestion['description']}
Calories: {meal_suggestion['calories']}
Preparation Time: {meal_suggestion['prep_time']} minutes

HEALTHY TIP
Remember to monitor your blood sugar before and after meals. Eating slowly and mindfully can help with better blood sugar control.

Regards,
{config.EMAIL_DISPLAY_NAME}
Wellness Team

---
This is an automated message. Please do not reply to this email."""

        body_html = f"""
<div class="salutation">Dear {username},</div>
<div class="intro">It's time for your {meal_type}. Here is a healthy meal suggestion based on your preferences.</div>
<div class="highlight-box">
  <div class="highlight-label">Recommended Meal</div>
  <div class="highlight-value" style="font-size: 26px;">{meal_suggestion['meal_name']}</div>
  <div class="highlight-sub">{meal_suggestion['description']}</div>
</div>
<table class="details-table">
  <tr><td>Calories</td><td>{meal_suggestion['calories']} kcal</td></tr>
  <tr><td>Preparation Time</td><td>{meal_suggestion['prep_time']} minutes</td></tr>
  <tr><td>Meal Type</td><td>{meal_type.title()}</td></tr>
</table>
<div class="section-heading">Healthy Tip</div>
<div class="note-box">Remember to monitor your blood sugar before and after meals. Eating slowly and mindfully can help with better blood sugar control.</div>"""

        html_body = _wrap_email("Healthy Meal Reminder", body_html, "Wellness Reminder · Healthy Eating Support")
        _send(user_email, f'{config.EMAIL_DISPLAY_NAME} - {meal_type.title()} Time! Healthy Meal Suggestion', text_body, html_body)
        print(f"Meal reminder sent to {user_email}")
        return True
    except Exception as e:
        print(f"Failed to send meal reminder: {e}")
        return False


def send_exercise_reminder_email(user_email, username, exercise_suggestion):
#Email a user a suggested exercise for today.
    try:
        text_body = f"""DIABETES PREDICTION CO - EXERCISE REMINDER

Dear {username},

Time to get moving! Here is your exercise suggestion for today.

EXERCISE SUGGESTION
Exercise: {exercise_suggestion['exercise_name']}
Duration: {exercise_suggestion['duration_minutes']} minutes
Calories Burn Estimate: ~{exercise_suggestion['calories_burn_estimate']} calories

Instructions:
{exercise_suggestion['instructions']}

BENEFITS OF REGULAR EXERCISE
Regular physical activity helps improve insulin sensitivity, lowers blood sugar levels, and supports overall metabolic health.

Regards,
{config.EMAIL_DISPLAY_NAME}
Wellness Team

---
This is an automated message. Please do not reply to this email."""

        body_html = f"""
<div class="salutation">Dear {username},</div>
<div class="intro">Time to get moving! Here is your exercise suggestion for today.</div>
<div class="highlight-box">
  <div class="highlight-label">Recommended Exercise</div>
  <div class="highlight-value" style="font-size: 26px;">{exercise_suggestion['exercise_name']}</div>
  <div class="highlight-sub">Duration: {exercise_suggestion['duration_minutes']} minutes</div>
</div>
<table class="details-table">
  <tr><td>Calories Burn Estimate</td><td>~{exercise_suggestion['calories_burn_estimate']} calories</td></tr>
  <tr><td>Difficulty Level</td><td>{exercise_suggestion['difficulty']}</td></tr>
</table>
<div class="section-heading">Instructions</div>
<div class="note-box">{exercise_suggestion['instructions']}</div>
<div class="section-heading">Benefits of Regular Exercise</div>
<div class="note-box">Regular physical activity helps improve insulin sensitivity, lowers blood sugar levels, and supports overall metabolic health.</div>"""

        html_body = _wrap_email("Exercise Reminder", body_html, "Wellness Reminder · Physical Activity Support")
        _send(user_email, f'{config.EMAIL_DISPLAY_NAME} - Time to Exercise! Your Daily Activity Suggestion', text_body, html_body)
        print(f"Exercise reminder sent to {user_email}")
        return True
    except Exception as e:
        print(f"Failed to send exercise reminder: {e}")
        return False
