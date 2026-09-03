from echotrace_validation import evaluate_trial


def test_phase_six_evaluator_reports_prd_metrics_and_targets():
    report = evaluate_trial(
        {
            "trial_id": "controlled-001",
            "predictions": {
                "synchronization_offsets": {"cam-a": 0, "cam-b": 7.3, "cam-c": 13.2},
                "events": [
                    {"event_type": "potential_impact", "timestamp_seconds": 18.6},
                    {"event_type": "post_impact_stop", "timestamp_seconds": 20.1},
                ],
                "object_classes": ["car", "car", "person"],
                "collision_labels": [True, False, True],
                "matches": [["cam-a:1", "cam-b:4"]],
                "citations": {"impact": ["cam-a", "cam-b"]},
            },
            "ground_truth": {
                "synchronization_offsets": {"cam-a": 0, "cam-b": 7.14, "cam-c": 13.02},
                "events": [
                    {"event_type": "potential_impact", "timestamp_seconds": 18.42},
                    {"event_type": "post_impact_stop", "timestamp_seconds": 20.0},
                ],
                "object_classes": ["car", "car", "truck"],
                "collision_labels": [True, False, False],
                "matches": [["cam-b:4", "cam-a:1"]],
                "citations": {"impact": ["cam-a", "cam-b"]},
            },
        }
    )

    assert report["metrics"]["median_synchronization_error_seconds"] == 0.16
    assert report["metrics"]["object_detection"]["precision"] == 0.6667
    assert report["metrics"]["collision_detection"]["f1"] == 0.6667
    assert report["targets"]["synchronization_under_0_5_seconds"] is True
    assert report["targets"]["citation_accuracy_at_least_95_percent"] is True


def test_phase_six_evaluator_handles_empty_optional_sections():
    report = evaluate_trial({"predictions": {}, "ground_truth": {}})
    assert report["metrics"]["median_synchronization_error_seconds"] is None
    assert report["targets"]["citation_accuracy_at_least_95_percent"] is False
