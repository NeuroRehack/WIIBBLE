"""Tests for unified tare calibration flow."""

from unittest.mock import MagicMock, patch

from wiibble.ui import calibration_flow
from wiibble.utils.state import AppState, Settings


@patch.object(calibration_flow, "update_tare_status_label")
@patch.object(calibration_flow, "tare")
@patch.object(calibration_flow, "wait_for_tare", return_value=-1)
def test_run_tare_and_persist_aborts_when_wait_fails(
    mock_wait, mock_tare, mock_update_label
):
    """Return False when empty-board wait is aborted."""
    settings = Settings()
    app_state = AppState()

    result = calibration_flow.run_tare_and_persist(
        MagicMock(), "dl", app_state, settings, 2.0
    )

    assert result is False
    mock_tare.assert_not_called()
    mock_update_label.assert_not_called()


@patch.object(calibration_flow, "update_tare_status_label")
@patch.object(calibration_flow, "tare")
@patch.object(calibration_flow, "wait_for_tare", return_value=0.0)
def test_run_tare_and_persist_saves_and_updates_label_on_success(
    mock_wait, mock_tare, mock_update_label
):
    """Persist offsets and refresh label after successful tare."""
    settings = Settings()
    app_state = AppState()
    device = MagicMock()

    with patch.object(settings, "save_tare_from_data_struct") as mock_save:
        result = calibration_flow.run_tare_and_persist(
            device, "dl", app_state, settings, 2.0, reset_mock_phase=True
        )

    assert result is True
    device.reset_calibration_phase.assert_called_once()
    mock_wait.assert_called_once()
    mock_tare.assert_called_once_with(device, app_state.data_struct)
    mock_save.assert_called_once_with(app_state.data_struct)
    mock_update_label.assert_called_once_with(settings)


@patch.object(calibration_flow, "update_tare_status_label")
@patch.object(calibration_flow, "tare", side_effect=RuntimeError("hid read failed"))
@patch.object(calibration_flow, "wait_for_tare", return_value=0.0)
def test_run_tare_and_persist_returns_false_on_tare_error(
    mock_wait, mock_tare, mock_update_label
):
    """Return False when tare measurement raises."""
    settings = Settings()
    app_state = AppState()

    result = calibration_flow.run_tare_and_persist(
        MagicMock(), "dl", app_state, settings, 2.0
    )

    assert result is False
    mock_update_label.assert_not_called()
