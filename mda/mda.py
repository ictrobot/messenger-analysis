import zipfile
from mda.conversation import Conversation
from collections import namedtuple

__all__ = ["DataDump", "ConversationInfo"]

ConversationInfo = namedtuple("ConversationInfo", ["name", "id", "type", "path"])


class DataDump:
    CONVERSATION_TYPES = ["inbox", "message_requests", "archived_threads"]

    def __init__(self, data_zip_path, local_timezone=None):
        self.path = data_zip_path
        self.local_timezone = local_timezone
        self._zipfile = zipfile.ZipFile(self.path, mode="r")
        self._conversations = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._zipfile.close()

    def __str__(self):
        return "DataDump('{}')".format(self.path)

    def close(self):
        self._zipfile.close()

    def get_conversation_by_name(self, name, conversation_type="inbox"):
        path = "messages/{}/{}/".format(conversation_type, name)
        if not self._zipfile.getinfo(path).is_dir():
            raise KeyError("Invalid conversation")
        return Conversation(self, name, conversation_type, path)

    def get_conversation_by_info(self, info):
        return self.get_conversation_by_name(info.name, info.type)

    def get_conversation_by_id(self, conv_id):
        conv_list = self.get_conversations()
        filtered_list = list(filter(lambda c: c.id == conv_id, conv_list))
        if not filtered_list:
            raise KeyError("No conversation for key '{}'".format(conv_id))
        return self.get_conversation_by_info(filtered_list[0])

    def get_conversations(self):
        if self._conversations:
            return self._conversations

        for name in self._zipfile.namelist():
            sections = name.split("/")
            if len(sections) != 4 or sections[3]:
                continue

            base_dir, conv_type, conv_name, _ = sections
            if base_dir == "messages" and conv_type in DataDump.CONVERSATION_TYPES:
                # id is last 10 characters
                conv_id = conv_name[-10:]
                info = ConversationInfo(conv_name, conv_id, conv_type, name)
                self._conversations.append(info)

        return self._conversations
