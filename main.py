import json
import logging
import time

from telegram.ext import Updater, CommandHandler, Job
from ttn import MQTTClient
from app_keys import apps, telegram_token
import boto3


class Alarmer(object):
    mqtt_clients = {}

    def __init__(self, settings, sns, bot):
        self._bot = bot
        self._sns = sns
        self._initialised = False
        self._logger = logging.getLogger("lka.alarmer")
        for name, app in settings.items():
            username = name
            password = app['ttn']['app_key']
            host = app['ttn']['host']
            secure = 'secure' in app['ttn'] and app['ttn']['secure']
            self._logger.debug("Initiating connection to {0} as {1}".format(host, username))
            self.mqtt_clients[username] = MQTTClient(host=host, client_id=username,
                                                     username=username, password=password,
                                                     userdata=app,
                                                     cert='ttn_cert.pem' if secure else None)
            self.mqtt_clients[username].on_event = self.on_ttn
            self._logger.info("Activated {0}".format(username))
        self._initialised = True

    def on_ttn(self, msg, userdata):
        payload = json.loads(msg.payload.decode('utf-8'))
        if not self._initialised:
            self._logger.error("Not initialised, skipping {0!s}".format(payload))
            return

        if 'sms' in userdata:
            for name, number in userdata['sms'].items():
                self._logger.info("SMS Alarm from {0!s} sent to {1!s} ({2!s})".format(payload['dev_id'], name, number))
                msg = "Your keyfob alarm was activated by device {0!s}".format(payload['dev_id'])
                self._sns.publish(PhoneNumber=number, Message=msg)
                self._logger.info("SMS Sent to {0!s} ({1!s})".format(name, number))

        if 'telegram' in userdata:
            for name, number in userdata['telegram'].items():
                self._logger.info("Telegram Alarm from {0!s} sent to {1!s} ({2!s})".format(payload['dev_id'], name, number))
                msg = "Your keyfob alarm was activated by device {0!s}".format(payload['dev_id'])
                self._bot.send_message(number, text=msg)
                self._logger.info("Telegram Sent to {0!s} ({1!s})".format(name, number))


def run():
    logging.basicConfig()
    logger = logging.getLogger('lka')
    logging.getLogger('').setLevel(logging.DEBUG)

    def error(bot, update, error):
        logger.warning('Update "%s" caused error "%s"' % (update, error))

    logger.debug("Initialising connection to Amazon SMS")
    sns = boto3.client('sns')

    logger.info("Initialising Telegram bot")
    updater = Updater(telegram_token)
    dp = updater.dispatcher
    dp.add_error_handler(error)
    dp.add_handler(CommandHandler("id",
                                  lambda bot, update: update.message.reply_text(text="{0!s}".format(update.message.chat_id))))
    updater.start_polling()

    logger.debug("Initialising app connections")
    try:
        a = Alarmer(apps, sns, updater.bot)
    except Exception as error:
        print(error)
        raise error

    logger.debug("Running")
    updater.idle()


if __name__ == '__main__':
    run()
