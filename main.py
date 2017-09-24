import json
import logging
import time

from ttn import MQTTManager
from app_keys import ttn_app_info, sms_info
import boto3


initialised = False
send_now = False
sns = None
last_device = ""
logger = None
client = None


def send():
    logger.info("Alarm from {0!s}".format(last_device))
    msg = "Your keyfob alarm was activated by device {0!s}".format(last_device)
    number = sms_info['phone']
    sns.publish(PhoneNumber=number, Message=msg)


def ttn_cb(msg):
    global send_now, last_device
    payload = json.loads(msg.payload.decode('utf-8'))
    last_device = payload['dev_id']
    if not initialised:
        send_now = True
        return
    send()


def run():
    global send_now, initialised, sns, logger
    logging.basicConfig()
    logger = logging.getLogger('lka')
    logging.getLogger('').setLevel(logging.DEBUG)

    logger.debug("Initialising connection to The Things Network")
    try:
        m = MQTTManager(ttn_app_info, callback=ttn_cb)
    except Exception as error:
        print(error)
        raise error

    logger.debug("Initialising connection to Amazon SMS")
    sns = boto3.client('sns')

    initialised = True
    if send_now:
        send()
    logger.info("Initialised, waiting for messages")
    while True:
        time.sleep(1)


if __name__ == '__main__':
    run()
