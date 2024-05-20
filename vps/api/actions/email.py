import logging

import mailchimp_transactional as MailchimpTransactional
from mailchimp_transactional.api_client import ApiClientError

from core.config import Config


logger = logging.getLogger("mailing")
try:
    mailchimp = MailchimpTransactional.Client(Config.MAILCHIMP_KEY)
    response = mailchimp.users.ping()
    logger.debug('API called successfully: {}'.format(response))
except ApiClientError as error:
    logger.debug('An exception occurred: {}'.format(error.text))


def return_success_bool(func):
    async def wrapper(*args, **kwargs):
        status = await func(*args, **kwargs)
        #todo: check for failed status instead success because they different
        return status["status"] == "sent"
    return wrapper

@return_success_bool
async def send_verify_email_code(user, token: str):
    response = mailchimp.messages.send_template({
        "template_name": "Welcome",
        "template_content": [{}],
        "message": {
            "to": [{"email": user.email}],
            "global_merge_vars": [
                {
                    "name": "EMAIL_CONFIRMATION",
                    "content": f"{Config.FRONTEND_URL}confirm?token={token}"
                }
            ]
        }
    })
    
    return response[0]

@return_success_bool
async def send_reset_password_code(user, token: str):
    response = mailchimp.messages.send_template({
        "template_name": "Reset password",
        "template_content": [{}],
        "message": {
            "to": [{"email": user.email}],
            "global_merge_vars": [
                {
                    "name": "USER_NAME",
                    "content": user.name
                },
                {
                    "name": "RESET_PASSWORD_LINK",
                    "content": f"{Config.FRONTEND_URL}reset_password?token={token}"
                }
            ]
        }
    })

    return response[0]

@return_success_bool
async def send_localization_done(user, language, localization, project):
    response = mailchimp.messages.send_template({
        "template_name": "Video is ready",
        "template_content": [{}],
        "message": {
            "to": [{"email": user.email}],
            "global_merge_vars": [
                {
                    "name": "USER_NAME",
                    "content": user.name
                },
                {
                    "name": "TARGET_LANGUAGE",
                    "content": language.lang_name
                },
                {
                    "name": "VIDEO_NAME",
                    "content": project.name
                },
                {
                    "name": "LOCALISATION_LINK",
                    "content": f"{Config.FRONTEND_URL}workspace?project_id={str(project.id)}&loc_id={str(localization.id)}"
                }
            ]
        }
    })

    return response[0]