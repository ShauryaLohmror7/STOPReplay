from __future__ import annotations

from unittest.mock import Mock

from youtube_transcript_api import FetchedTranscript, FetchedTranscriptSnippet, TranscriptsDisabled

from stopreplay_collect.adapters import YouTubeAdapter
from stopreplay_collect.models import ResearchRequest
from stopreplay_collect.pipeline import CollectionPipeline

_VIDEO_ID = "e7h-h-d3FG4"
_VIDEO_URL = f"https://www.youtube.com/watch?v={_VIDEO_ID}"


def test_youtube_preserves_original_caption_times_across_runs(storage):
    client = Mock()
    client.fetch.return_value = FetchedTranscript(
        [FetchedTranscriptSnippet("Project announcement.", 48.015, 2.11),
         FetchedTranscriptSnippet("Second caption.", 50.125, 1.2)],
        _VIDEO_ID, "English (United States)", "en-US", False,
    )
    pipeline = CollectionPipeline(storage)
    adapter = YouTubeAdapter(client=client)
    params = {"urls": [_VIDEO_URL, f"https://youtu.be/{_VIDEO_ID}?t=48"], "languages": ["en-US"]}
    request = ResearchRequest("recon", "fixture", params=params)
    assert pipeline.run(adapter, request).sources_registered == 2
    client.fetch.assert_called_once_with(_VIDEO_ID, languages=["en-US"])
    assert pipeline.run(adapter, request).sources_registered == 0
    assert pipeline.run(adapter, ResearchRequest("other", "fixture", params=params)).sources_registered == 2

    source_ref = f"youtube:{_VIDEO_ID}:en-US:48015:50125:1"
    source = storage.get_source("recon", source_ref)
    assert source["url"] == f"{_VIDEO_URL}&t=48s"
    assert source["locator"] == "48.015s–50.125s (en-US, captions)"
    assert source["excerpt"] == "Project announcement."
    assert storage.get_facts("recon") == []


def test_youtube_reports_inaccessible_captions_and_ignores_unsupported_hosts():
    client = Mock()
    client.fetch.side_effect = TranscriptsDisabled(_VIDEO_ID)
    urls = ["https://youtube.com.example.com/watch?v=abcdefghijk", _VIDEO_URL]
    output = YouTubeAdapter(client=client).collect(ResearchRequest("recon", "fixture", params={"urls": urls}))

    assert output.sources == []
    assert len(output.retrieval_failures) == 2
    assert output.retrieval_failures[1] == {"url": _VIDEO_URL, "error": "TranscriptsDisabled"}
    client.fetch.assert_called_once_with(_VIDEO_ID, languages=("en", "en-US", "en-GB"))
