"""Beginner UI behavior without assigning pronunciation grades."""
import unittest
import re
from unittest.mock import patch, ANY, Mock

import app_2


def result(state="partial"):
    return {"overall_status": state, "prompt_id": "think", "prompt": {"id": "think"},
            "stage_statuses": {}, "audio_paths": {"original": None, "reference": None},
            "messages": [], "feedback": [], "results_path": None,
            "learner_audio": {}, "phoneme_results": {"segments": []}}


class BeginnerAppTests(unittest.TestCase):
    def test_complete_and_partial_are_not_grades(self):
        for state in ("complete", "partial"):
            message = app_2.learner_notice(result(state))
            self.assertIn("grading is not available", message)
            self.assertIn("not a detected mistake", message)
            self.assertNotIn("CTC", message)
            self.assertNotIn("semitone", message)

    def test_actionable_failures(self):
        for reason, expected in (("audio_too_long", "5 seconds"), ("silent_audio", "closer to the microphone"),
                                 ("cannot_read_audio", "clear recording")):
            r = result("failed")
            r["learner_audio"] = {"reason": reason}
            self.assertIn(expected, app_2.learner_notice(r))
        for stage, expected in (("save", "could not save"),):
            r = result("failed")
            r["stage_statuses"][stage] = {"status": "unavailable"}
            self.assertIn(expected, app_2.learner_notice(r))

    def test_clipping_suggests_recording_change_not_pronunciation_failure(self):
        r = result()
        r["learner_audio"] = {"warnings": ["possible_clipping"]}
        self.assertIn("farther from the microphone", app_2.learner_notice(r))

    def test_no_input_never_calls_pipeline(self):
        with patch.object(app_2, "run_attempt") as run:
            frames = list(app_2.analyze_recording(None, "think"))
        run.assert_not_called()
        self.assertEqual(len(frames), 1)
        self.assertFalse(frames[0][10]["interactive"])

    def test_busy_clears_previous_results_and_disables_changes(self):
        with patch.object(app_2, "run_attempt", return_value=result()) as run:
            gen = app_2.analyze_recording("voice.wav", "think")
            busy = next(gen)
            run.assert_not_called()
            self.assertEqual(busy[1:9], ("", "", "", "", "", "", "", None))
            self.assertFalse(busy[9]["visible"])
            self.assertIsNone(busy[9]["value"])
            self.assertTrue(all(not update["interactive"] for update in busy[10:]))
            final = next(gen)
            run.assert_called_once_with("voice.wav", "think", compare_reference=False, progress_callback=ANY)
            self.assertIn("Focus area for this prompt", final[0])
            self.assertTrue(all(update["interactive"] for update in final[10:]))
            self.assertTrue(final[13]["visible"])

    def test_unexpected_error_stays_in_technical_details(self):
        with patch.object(app_2, "run_attempt", side_effect=RuntimeError("internal diagnostic")):
            final = list(app_2.analyze_recording("voice.wav", "think"))[-1]
        self.assertNotIn("internal diagnostic", final[0])
        self.assertIn("internal diagnostic", final[1])
        self.assertTrue(final[10]["interactive"])

    def test_prompt_retry_and_upload_clear_stale_results(self):
        demo = app_2.build_app()
        functions = {getattr(fn.fn, "__name__", ""): fn.fn for fn in demo.fns.values()}
        # Reference WAVs are private local assets, not required by this unit test.
        with patch.object(app_2, "reference_file", return_value="ship.wav"):
            changed = functions["change_sentence"]("ship")
        self.assertIsNone(changed[10])  # cleared recording
        self.assertEqual(changed[1:9], ("", "", "", "", "", "", "", None))
        self.assertFalse(changed[9]["visible"])
        self.assertIsNone(changed[9]["value"])
        self.assertIn("The ship is here", re.sub(r'<[^>]+>', '', changed[13]))
        self.assertIn("rachelsenglish", changed[14])
        uploaded = functions["on_recording"]("another.wav")
        self.assertEqual(uploaded[1:9], changed[1:9])
        self.assertTrue(uploaded[10]["interactive"])
        self.assertFalse(uploaded[9]["visible"])
        config = demo.get_config_file()
        accordions = [c for c in config["components"] if c["type"] == "accordion"]
        self.assertTrue(all(not c["props"]["open"] for c in accordions))
        demo.close()

    def test_text_is_escaped(self):
        self.assertNotIn("<script>", app_2.sentence_html({"text": "<script>bad</script>"}))

    def test_sound_strip_uses_lesson_targets_not_score_colors(self):
        strip = app_2.sound_strip(app_2.load_prompts()[0])
        self.assertEqual(strip.count('class="focus"'), 1)
        self.assertIn('<details', strip)
        self.assertIn('not detected mistakes', strip)
        self.assertNotIn('Clean match', strip)
        self.assertIn('Practice th', strip)
        self.assertIn('not your result', strip)

    def test_progress_forwards_stage_names_without_percentages(self):
        progress = Mock()
        def run(path, identity, **kwargs):
            kwargs['progress_callback']('Checking words')
            return result()
        with patch.object(app_2, 'run_attempt', side_effect=run):
            list(app_2.analyze_recording('voice.wav', 'think', progress=progress))
        progress.assert_called_once_with((0, None), desc='Checking words')

    def test_playback_uses_current_saved_learner_not_reference(self):
        r = result()
        r['audio_paths'] = {'original': 'current-learner.wav', 'reference': 'example.wav'}
        view = app_2.attempt_views(r)
        self.assertEqual(view[9]['value'], 'current-learner.wav')
        self.assertTrue(view[9]['visible'])
        self.assertIsNone(app_2.cleared()[9]['value'])
        self.assertFalse(app_2.cleared()[9]['visible'])

    def test_melody_normalizes_separate_durations_and_keeps_gaps(self):
        r = {"learner_audio": {"duration_sec": 2}, "reference_audio": {"duration_sec": 4},
             "learner_dsp": {"time_sec": [0, 1, 2], "pitch_semitones": [0, None, 1], "voiced_mask": [True, False, True]},
             "reference_dsp": {"time_sec": [0, 2, 4], "pitch_semitones": [0, None, 1], "voiced_mask": [True, False, True]}}
        graph = app_2.melody_html(r)
        self.assertIn('100%', graph)
        self.assertIn('does not align words', graph)
        self.assertEqual(graph.count('M60.00,130.00 M720.00,40.00'), 2)
        self.assertNotIn('background:#fff', graph)
        self.assertEqual(r['learner_dsp']['time_sec'], [0, 1, 2])

    def test_melody_without_valid_duration_does_not_invent_curve(self):
        self.assertIn('No reliable pitch', app_2.melody_html({}))

    def test_duration_is_measurement_not_pace_grade(self):
        r = result()
        r['learner_audio']['duration_sec'] = 1.8
        card = app_2.learner_notice(r)
        self.assertIn('1.80 seconds', card)
        self.assertNotIn('Good pace', card)


if __name__ == "__main__":
    unittest.main()
