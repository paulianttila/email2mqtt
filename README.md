# email2mqtt

Simple email client to monitor new emails and forward them to MQTT broker.

## Environament variables

See commonn environment variables from [MQTT-Framework](https://github.com/paulianttila/MQTT-Framework).

| **Variable**               | **Default** | **Descrition**                                                                                                 |
|----------------------------|-------------|----------------------------------------------------------------------------------------------------------------|
| CFG_APP_NAME               | email2mqtt  | Name of the app.                                                                                               |
| CFG_EMAIL_SERVER           | None        | Email server URL to connect.                                                                                   |
| CFG_EMAIL_USERNAME         | None        | Email server username used for authentication.                                                                 |
| CFG_EMAIL_PASSWORD         | None        | Email server password used for authentication.                                                                 |
| CFG_EMAIL_FOLDER           | INBOX       | Email server folder name to monitor.                                                                           |
| CFG_EMAIL_IDLE_TIMEOUT     | 300         | Idle timeout for email server connection.                                                                      |
| CFG_EMAIL_SKIP_UNREAD      | True        | Skip unreaded emails during connection.                                                                        |

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