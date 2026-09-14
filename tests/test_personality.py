from datetime import datetime

from services.personality import is_small_talk, reply_for_small_talk


def test_greeting_is_fast_and_contextual():
    reply = reply_for_small_talk("Привет", "Восил", datetime(2026, 9, 15, 10, 0))

    assert reply is not None
    assert "Доброе утро" in reply
    assert "Восил" in reply
    assert "на связи" in reply


def test_status_and_thanks_are_not_sent_to_command_planner():
    assert is_small_talk("Как дела")
    assert "локальный контур" in reply_for_small_talk("Как дела", "Шеф")
    assert "Всегда пожалуйста" in reply_for_small_talk("Спасибо", "Шеф")


def test_goodbye_keeps_background_services_explicit():
    reply = reply_for_small_talk("Пока", "Шеф")

    assert reply is not None
    assert "напоминания" in reply


def test_pc_command_is_not_small_talk():
    assert not is_small_talk("Перейди на рабочий стол 2")
    assert not is_small_talk("Привет, открой Chrome")
