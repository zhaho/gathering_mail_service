import os, logging, smtplib, requests
from dotenv import load_dotenv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta

version = "2.2"
day_limit = 2  # Limit for when to start send email
load_dotenv()

# Logging configuration
logging.basicConfig(filename=os.getenv('LOG_DESTINATION'), encoding='utf-8', level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
logging.info('script running')
logging.info('using version: '+version)

def send_mail(to, subject, body):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = os.getenv('MAIL_FROM')
    msg['To'] = to
    msg.attach(MIMEText(body, 'html'))

    with smtplib.SMTP(os.getenv('SMTP_SERVER'), 587) as mail:
        mail.ehlo()
        mail.starttls()
        mail.login(os.getenv('SMTP_LOGIN'), os.getenv('SMTP_PASS'))
        mail.sendmail(os.getenv('MAIL_FROM'), to, msg.as_string())

def get_api_data(endpoint):
    api_url = os.getenv('API_URL') + endpoint
    req = requests.get(api_url)
    return req.json()

def process_event(event, day_limit):
    logging.info("processing event: "+ event['id'])
    mail_games, mail_users = {}, {}

    event_start = event['date_start'].split(" ")[0]
    variable_date = datetime.strptime(event_start, '%Y-%m-%d')
    current_date = datetime.now()
    difference = variable_date - current_date

    if difference < timedelta(days=day_limit):
        logging.info(f"- < {day_limit} days")
        signups = get_api_data(os.getenv('API_ENDPOINT_LIST_GET_EVENT_SIGNUPS') + f"/{event['id']}")
        users = get_api_data(os.getenv('API_ENDPOINT_LIST_USERS'))

        for signed in signups:
            games = get_api_data(os.getenv('API_ENDPOINT_LIST_GET_TITLES_TO_BRING') + f"/{event['id']}/{signed['user_id']}")

            for user in users:
                if user['id'] == signed['user_id']:
                    mail_games[user['firstname']] = games
                    mail_users[user['email']] = user['firstname']

        if mail_users:
            logging.info(f"- title: '{event['title']}'")
            logging.info(f"- users: {len(mail_users)}")
            logging.info(f"- games: {str(mail_games)}")
        else:
            logging.info("- no users signed - skip")

    else:
        logging.info('- > '+str(day_limit) +' days')

    for mail, usr in mail_users.items():
        subject = "Gathering: Upcoming Event!"
        mail_games_body = ""

        for attender, games in mail_games.items():
            mail_games_body += f"{attender}'s games:<br>"

            for game in games:
                mail_games_body += f"- {game}<br>"
            if not games:
                mail_games_body += f"- No games at the moment<br>"

        body = f"""\
            <html>
            <head></head>
            <body>
                <p>Dear {usr},<br>
                You have an upcoming event within a week that you have signed up for.</p>
                <h3>{event['title']}</h3>
                <b>Event Details:</b><br>
                <p>- Start Date: {event['date_start']}<br>
                - Location: {event['location']}<br>
                - Player Limit: {event['player_limit']}</p>
                
                <h4>Games that are currently planned to be brought:</h4>
                    {mail_games_body}
                <br>
                If you wish to bring some games of your own or vote on some additional games to be brought, the time is now!
                <br><br>
                For more information, go to <a href="{os.getenv('GATHERING_URL')}">Gathering</a>.<br>
                <p>
                    <a href="{os.getenv('GATHERING_URL')}"><img src="{os.getenv('GATHERING_LOGO')}" width="100" height="100" /></a>
                </p>
                </p>
            </body>
            </html>
            """

        send_mail(to=mail, subject=subject, body=body)
        logging.info(f"- sent mail to: {mail}")

if __name__ == "__main__":
    events = get_api_data(os.getenv('API_ENDPOINT_LIST_UPCOMING_EVENTS')) # Get upcoming events

    for event in events:
        process_event(event, day_limit)
    if not events:
        logging.info("no upcoming events")
        logging.info("script ended")