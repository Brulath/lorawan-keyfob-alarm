import json
import logging
import time

from ttn import MQTTClient
from app_keys import apps
import boto3


class Alarmer(object):
    mqtt_clients = {}

    def __init__(self, settings, sns):
        self._sns = sns
        self._initialised = False
        self._logger = logging.getLogger("lka.alarmer")
        for name, app in settings.items():
            username = name
            password = app['ttn']['app_key']
            host = app['ttn']['host']
            self._logger.debug("Initiating connection to {0} as {1}".format(host, username))
            self.mqtt_clients[username] = MQTTClient(host=host, client_id=username,
                                                     username=username, password=password,
                                                     userdata=app)
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
                self._logger.info("Alarm from {0!s} sent to {1!s} ({2!s})".format(payload['dev_id'], name, number))
                msg = "Your keyfob alarm was activated by device {0!s}".format(payload['dev_id'])
                self._sns.publish(PhoneNumber=number, Message=msg)
                self._logger.info("Sent to {0!s} ({1!s})".format(name, number))

        if 'telegram' in userdata:
            self._logger.warning("Telegram support not yet integrated")


def run():
    logging.basicConfig()
    logger = logging.getLogger('lka')
    logging.getLogger('').setLevel(logging.DEBUG)

    logger.debug("Initialising connection to Amazon SMS")
    sns = boto3.client('sns')

    logger.debug("Initialising app connections")
    try:
        a = Alarmer(apps, sns)
    except Exception as error:
        print(error)
        raise error

    logger.info("Initialised, waiting for messages")
    while True:
        time.sleep(1)


if __name__ == '__main__':
    run()
