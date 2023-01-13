# email2mqtt

## Additional environment variables

Create .env file 

    # nano .env

add following environment variables

    LOG_LEVEL=
    MQTT_BROKER_URL=
    MQTT_BROKER_PORT=
    MQTT_USERNAME=
    MQTT_PASSWORD=
    EMAIL_SERVER=
    EMAIL_USERNAME=
    EMAIL_PASSWORD=

### Example

    LOG_LEVEL=DEBUG
    MQTT_BROKER_URL=192.168.10.20
    MQTT_BROKER_PORT=1883
    MQTT_USERNAME=email2mqtt
    MQTT_PASSWORD=12345678
    EMAIL_SERVER=imap-mail.outlook.com
    EMAIL_USERNAME=pauli.anttilaa@example.com
    EMAIL_PASSWORD=12345678
