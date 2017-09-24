from logging import getLogger

import paho.mqtt.client as mqtt


class MQTTClient(object):
    def __init__(self, host='localhost', client_id="", username=None, password=None):
        self._logger = getLogger('ttn.mqtt.{0!s}.{1!s}'.format(host, client_id))
        self._host = host
        self._client_id = client_id
        self._connected = False
        self.on_event = lambda x: x

        self._mqtt = mqtt.Client(client_id=client_id, clean_session=True,
                                 userdata=self, protocol=mqtt.MQTTv311, transport="tcp")
        self._username = username
        self._password = password
        if self._username is not None and self._password is not None:
            self._mqtt.username_pw_set(self._username, self._password)
        self._mqtt.on_connect = self._on_connect
        self._mqtt.on_disconnect = self._on_disconnect
        self._mqtt.on_log = self._on_log
        self._mqtt.on_message = self._on_message
        self._mqtt.on_publish = self._on_publish
        self._mqtt.on_subscribe = self._on_subscribe
        self._mqtt.loop_start()
        self.connect()

    @property
    def connected(self):
        return self._connected

    def connect(self):
        self._logger.debug("Connecting")
        self._connected = self._mqtt.connect(host=self._host) == 0
        return self._connected

    def disconnect(self):
        self._logger.debug("Disconnecting")
        return self._mqtt.disconnect() == 0

    def publish(self, app, device, data):
        topic = "{0!s}/devices/{1!s}/down".format(app, device)
        info = self._mqtt.publish(topic, data, qos=0, retain=False)
        return info.is_published() or info.rc == 0

    def _on_connect(self, client, userdata, flags, rc):
        self._connected = True
        self._logger.debug("Connected and subscribing (flags: %s, err: %s)", flags, mqtt.error_string(rc))
        return self._mqtt.subscribe('+/devices/+/up') == 0

    def _on_disconnect(self, client, userdata, rc):
        self._connected = False
        if rc == 0:
            self._logger.debug("Disconnected {0!r}.".format(self))
        else:
            self._logger.debug("Disconnection unexpected (%s), retrying...", mqtt.error_string(rc))
            self.connect()

    def _on_log(self, client, userdata, level, buf):
        self._logger.debug("Log: %s: %s", level, buf)

    def _on_message(self, client, userdata, msg):
        self._logger.debug("MSG(%s): %s", msg.topic, msg.payload)
        self.on_event(msg)

    def _on_publish(self, client, userdata, mid):
        # self._logger.debug("Publish finished")
        pass

    def _on_subscribe(self, client, userdata, mid, granted_qos):
        self._logger.debug("Subbed: %s %s", mid, granted_qos)

    def __repr__(self):
        return "{0!s}.{1!s}".format(self._host, self._client_id)


class MQTTManager(object):
    clients = {}

    def __init__(self, ttn_app_info, callback):
        self._logger = getLogger("ttn.mqtt.manager")
        for app in ttn_app_info:
            username = app['username']
            password = app['password']
            host = app['host']
            self._logger.debug("Initiating connection to {0} as {1}".format(host, username))
            self.clients[username] = MQTTClient(host=host, client_id=username, username=username, password=password)
            self.clients[username].on_event = callback
            self._logger.info("Activated {0}".format(username))
