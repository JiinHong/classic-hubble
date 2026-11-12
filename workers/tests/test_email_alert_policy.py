from classic_hubble_pipeline.notifications import NotificationCandidate, should_send_notification


def eligible(channel, confidence=1.0, *, email_enabled=True):
    candidate = NotificationCandidate("user", "work", "performance", channel)
    return should_send_notification(candidate, confidence, email_enabled=email_enabled)


def test_only_email_is_eligible():
    assert eligible("email", 0.85)
    assert not eligible("web_push")
    assert not eligible("unknown")


def test_email_opt_out_and_low_confidence_are_respected():
    assert not eligible("email", email_enabled=False)
    assert not eligible("email", 0.84)
