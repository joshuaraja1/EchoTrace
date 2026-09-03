from echotrace_ai.video_intelligence import AzureVideoIndexer, LocalVideoIntelligence


def test_local_video_intelligence_is_noop(tmp_path):
    assert LocalVideoIntelligence().enrich(tmp_path / "video.mp4") == {}


def test_azure_video_insights_exclude_faces_and_keep_evidence_text():
    result = AzureVideoIndexer._safe_insights(
        {
            "videos": [
                {
                    "insights": {
                        "transcript": [{"text": "brakes applied", "confidence": 0.9}],
                        "ocr": [{"text": "14:32:17", "confidence": 0.8}],
                        "labels": [{"name": "vehicle"}],
                        "faces": [{"name": "should never leave adapter"}],
                    }
                }
            ]
        },
        "video-1",
    )
    assert result["transcript"][0]["text"] == "brakes applied"
    assert result["ocr"][0]["text"] == "14:32:17"
    assert "faces" not in result
    assert "faces" in result["excluded_insights"]
