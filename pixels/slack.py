import os
from typing import Any, List, Optional

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.web import SlackResponse

from pixels.log import logger


class SlackClient(WebClient):
    def __init__(self, **kwargs: Any):
        super().__init__(token=os.environ["SLACK_TOKEN"], **kwargs)

    def send_message(
        self, channel: str, message: str, blocks: Optional[List] = None
    ) -> SlackResponse:
        try:
            return self.chat_postMessage(channel=channel, text=message, blocks=blocks)
        except SlackApiError as e:
            logger.error("Failed to send a message to slack", error=e)

    def send_history_graph(self, path: str):
        try:
            self.files_upload(file=path, channels=os.environ["SLACK_UPDATES_CHANNEL"])
        except SlackApiError as e:
            logger.error("Failed to send a graph to slack", error=e)

    def send_to_updates(self, message: str, blocks: List[dict]) -> SlackResponse:
        return self.send_message(os.environ["SLACK_UPDATES_CHANNEL"], message, blocks)

    def log_keras_progress(self, state: str, metrics: dict, name: str, uri: str):
        message = f"Model <{uri}|{name}>: {state} "
        batch_id = logger.context.get("AWS_BATCH_JOB_ID")
        if batch_id:
            message += "in <https://eu-central-1.console.aws.amazon.com/batch/"
            message += f"home?region=eu-central-1#jobs/detail/{batch_id}|AWS Batch>"
        else:
            message += "(_locally_)"

        blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": message}}]
        if metrics:
            for key, value in metrics.items():
                blocks.append(
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": f"*{key}*: {value}"},
                    }
                )
        self.send_to_updates(message, blocks)
