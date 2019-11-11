import json
import datetime
import pytz

__all__ = ["Reaction", "Attachment", "Message", "Conversation"]


def _get_datetimes(timestamp, timezone):
    naive_datetime = datetime.datetime.utcfromtimestamp(timestamp)
    utc_datetime = pytz.UTC.localize(naive_datetime)
    if timezone is None:
        return utc_datetime, utc_datetime
    else:
        return utc_datetime, utc_datetime.astimezone(timezone)


def _text_encoding(text):
    return bytearray(map(ord, text)).decode("utf-8")


class Reaction:
    TYPES = ['👍', '😍', '😆', '😢', '😮', '😠', '👎', '❤']

    def __init__(self, message, data):
        self.message = message
        self.type = _text_encoding(data["reaction"])
        self.actor = data["actor"]


class Attachment:
    ATTACHMENT_TYPES = [("photos", "photos"),
                        ("videos", "videos"),
                        ("gifs", "gifs"),
                        ("files", "files"),
                        ("audio", "audio_files")]

    def __init__(self, message, folder_type, data):
        self.message = message
        self.type = folder_type
        self.uri = data["uri"]

        if "creation_timestamp" in data:
            self.timestamp = data["creation_timestamp"]
        else:
            self.timestamp = message.timestamp
        timezone = self.message.conversation.data_dump.local_timezone
        self.utc_datetime, self.datetime = _get_datetimes(self.timestamp, timezone)

    def open(self):
        return self.message.conversation.data_dump._zipfile.open(self.uri)

    def zip_info(self):
        return self.message.conversation.data_dump._zipfile.getinfo(self.uri)

    def __str__(self):
        return "Attachment({})".format(self.uri)


# TODO msg["type"], {'Share', 'Generic', 'Unsubscribe', 'Subscribe', 'Call'}
class Message:

    def __init__(self, conversation, msg):
        self.conversation = conversation
        self.sender_name = msg["sender_name"]

        self.timestamp = msg["timestamp_ms"] / 1000
        timezone = self.conversation.data_dump.local_timezone
        self.utc_datetime, self.datetime = _get_datetimes(self.timestamp, timezone)

        if "content" in msg:
            self.content = _text_encoding(msg["content"])
        else:
            self.content = None

        if "reactions" in msg:
            self.reactions = [Reaction(self, d) for d in msg["reactions"]]
        else:
            self.reactions = []

        self.all_attachments = []
        for folder_name, json_name in Attachment.ATTACHMENT_TYPES:
            attach_list = []
            setattr(self, folder_name, attach_list)
            if json_name in msg:
                for item in msg[json_name]:
                    attachment = Attachment(self, folder_name, item)

                    attach_list.append(attachment)
                    self.all_attachments.append(attachment)

                    getattr(self.conversation, folder_name).append(attachment)
                    self.conversation.all_attachments.append(attachment)

    def __str__(self):
        return "Message({}, '{}')".format(self.datetime, self.conversation.path)


class Conversation:

    def __init__(self, data_dump, name, type, path):
        self.data_dump = data_dump
        self.name = name
        self.type = type
        self.path = path

        self._data_files = list(filter(lambda x: x.startswith(path.lower() + "message_"), data_dump._zipfile.namelist()))
        with data_dump._zipfile.open(self._data_files[0]) as file:
            self._data = json.load(file)
        for df in self._data_files[1:]:
            with data_dump._zipfile.open(df) as file:
                self._data["messages"] += json.load(file)["messages"]

        self.all_attachments = []
        for folder_name, json_name in Attachment.ATTACHMENT_TYPES:
            setattr(self, folder_name, [])

        self.participants = [p["name"] for p in self._data["participants"]]
        self.messages = [Message(self, msg) for msg in self._data["messages"]]
        self.messages.sort(key=lambda x: x.utc_datetime)

    def __str__(self):
        return "Conversation('{}', '{}')".format(self.data_dump.path, self.path)
