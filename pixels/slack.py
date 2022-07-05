import os
from typing import Any

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.web import SlackResponse

from pixels.log import logger


class SlackClient(WebClient):
    def __init__(self, **kwargs: Any):
        super().__init__(token=os.environ["SLACK_TOKEN"], **kwargs)

    def send_message(self, channel: str, message: str) -> SlackResponse:
        try:
            return self.chat_postMessage(channel=channel, text=message)
        except SlackApiError as e:
            logger.error("Failed to send a message to slack", error=e)

    def send_to_updates(self, message: str) -> SlackResponse:
        return self.send_message(os.environ["SLACK_UPDATES_CHANNEL"], message)

    def log_keras_progress(self, state: str, metrics: dict):
        message = f"Model doing {state} in BatchID {logger.context['AWS_BATCH_JOB_ID']}"
        if metrics:
            message += ":\n"
            for key, value in metrics.items():
                message += f"{key}:\t{value}\n"
        self.send_to_updates(message)
