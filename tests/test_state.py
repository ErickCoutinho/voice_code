from voice_code.state import VoiceState


def test_app_is_not_running_without_lock(tmp_path):
    assert not VoiceState(tmp_path / "estado").is_app_running()


def test_app_is_running_while_lock_is_held(tmp_path):
    app = VoiceState(tmp_path)
    hook = VoiceState(tmp_path)

    assert app.acquire_app_lock()
    assert hook.is_app_running()

    app.release_app_lock()
    assert not hook.is_app_running()


def test_second_instance_cannot_acquire_lock(tmp_path):
    first = VoiceState(tmp_path)
    second = VoiceState(tmp_path)

    assert first.acquire_app_lock()
    assert not second.acquire_app_lock()
    first.release_app_lock()


def test_checking_status_does_not_take_the_lock(tmp_path):
    VoiceState(tmp_path).is_app_running()

    app = VoiceState(tmp_path)
    assert app.acquire_app_lock()
    app.release_app_lock()


def test_new_speech_replaces_previous_one(tmp_path):
    state = VoiceState(tmp_path)

    first = state.claim_speech()
    second = state.claim_speech()

    assert not state.is_current_speech(first)
    assert state.is_current_speech(second)


def test_cancel_stops_current_speech(tmp_path):
    state = VoiceState(tmp_path)
    token = state.claim_speech()

    state.cancel_speech()

    assert not state.is_current_speech(token)


def test_cancel_without_any_speech_does_not_fail(tmp_path):
    VoiceState(tmp_path / "inexistente").cancel_speech()
