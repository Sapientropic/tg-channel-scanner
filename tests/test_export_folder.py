import unittest
from types import SimpleNamespace

from telethon.tl.types import DialogFilter, DialogFilterDefault, TextWithEntities
from telethon.tl.types.messages import DialogFilters


class FakeClient:
    def __init__(self, response, entities=None):
        self.response = response
        self.entities = entities or {}

    async def __call__(self, request):
        return self.response

    async def get_entity(self, peer):
        return self.entities[peer]


def folder(folder_id=3, title="Jobs", include_peers=None, pinned_peers=None):
    return DialogFilter(
        id=folder_id,
        title=TextWithEntities(text=title, entities=[]),
        pinned_peers=pinned_peers or [],
        include_peers=include_peers or [],
        exclude_peers=[],
    )


class ExportFolderTests(unittest.IsolatedAsyncioTestCase):
    async def test_list_folders_unwraps_dialog_filters_and_plain_text_titles(self):
        from scripts import export_folder

        client = FakeClient(
            DialogFilters(filters=[DialogFilterDefault(), folder()], tags_enabled=False)
        )

        folders = await export_folder.list_folders(client)

        self.assertEqual(
            folders,
            [
                {
                    "id": 3,
                    "title": "Jobs",
                    "has_pinned": False,
                    "has_included": False,
                }
            ],
        )

    async def test_export_folder_skips_default_filter_while_matching_by_id(self):
        from scripts import export_folder

        peer = object()
        client = FakeClient(
            DialogFilters(
                filters=[DialogFilterDefault(), folder(folder_id=5, include_peers=[peer])],
                tags_enabled=False,
            ),
            entities={peer: SimpleNamespace(username="jobs_channel", id=12345)},
        )

        channels = await export_folder.export_folder(client, 5)

        self.assertEqual(channels, ["jobs_channel"])


if __name__ == "__main__":
    unittest.main()
