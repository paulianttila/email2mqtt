# email2mqtt

Simple email client to monitor new emails and forward them to MQTT broker.

## Environament variables

| **Variable**           | **Default** | **Descrition**                                                                                                 |
|------------------------|-------------|----------------------------------------------------------------------------------------------------------------|
| APP_NAME               | email2mqtt  | Name of the app.                                                                                               |
| LOG_LEVEL              | INFO        | Logging level: CRITICAL, ERROR, WARNING, INFO or DEBUG                                                         |
| UPDATE_INTERVAL        | 60          | Update interval in seconds.                                                                                    |
| DELAY_BEFORE_FIRST_TRY | 5           | Delay before first try in seconds.                                                                             |
| MQTT_CLIENT_ID         | <APP_NAME>  | the unique client id string used when connecting to the broker.                                                |
| MQTT_BROKER_URL        | 127.0.0.1   | MQTT broker URL that should be used for the connection.                                                        |
| MQTT_BROKER_PORT       | 1883        | MQTT broker port that should be used for the connection.                                                       |
| MQTT_USERNAME          | None        | MQTT broker username used for authentication. If none is provided authentication is disabled.                  |
| MQTT_PASSWORD          | None        | MQTT broker password used for authentication.                                                                  |
| MQTT_TLS_CA_CERTS      | None        | A string path to the Certificate Authority certificate files that are to be treated as trusted by this client. |
| MQTT_TLS_CERTFILE      | None        | String pointing to the PEM encoded client certificate.                                                         |
| MQTT_TLS_KEYFILE       | None        | String pointing to the PEM encoded client private key.                                                         |
| MQTT_TLS_INSECURE      | False       | Configure verification of the server hostname in the server certificate.                                       |
| MQTT_TOPIC_PREFIX      | <APP_NAME>/ | MQTT topic prefix.                                                                                             |
| EMAIL_SERVER           | None        | Email server URL to connect.                                                                                   |
| EMAIL_USERNAME         | None        | Email server username used for authentication.                                                                 |
| EMAIL_PASSWORD         | None        | Email server password used for authentication.                                                                 |
| EMAIL_FOLDER           | INBOX       | Email server folder name to monitor.                                                                           |
| EMAIL_IDLE_TIMEOUT     | 300         | Idle timeout for email server connection.                                                                      |
| EMAIL_SKIP_UNREAD      | True        | Skip unreaded emails during connection.                                                                        |

## Example docker-compose.yaml

```yaml
version: "3.5"

services:
  email2mqtt:
    container_name: email2mqtt
    image: paulianttila/email2mqtt:2.0.0
    restart: unless-stopped
    security_opt:
      - no-new-privileges:true
    environment:
      - CFG_LOG_LEVEL=DEBUG
      - CFG_MQTT_BROKER_URL=127.0.0.1
      - CFG_MQTT_BROKER_PORT=1883
      - CFG_EMAIL_SERVER=imap-mail.outlook.com
      - CFG_EMAIL_USERNAME=<username>
      - CFG_EMAIL_PASSWORD=<password>
      - CFG_EMAIL_SKIP_UNREAD=True
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/healthy"]
      interval: 60s
      timeout: 3s
      start_period: 5s
      retries: 3
 ```