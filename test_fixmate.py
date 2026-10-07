import pytest

from fixmate import (
    calculate_service_charge,
    check_provider_availability,
    update_booking_status
)


def test_calculate_service_charge():
    assert calculate_service_charge(500, 1) == 500


def test_provider_available():
    assert check_provider_availability(5, 1) is True


def test_provider_unavailable():
    assert check_provider_availability(0, 1) is False


def test_booking_status_update():
    assert update_booking_status(
        "Requested",
        "Accepted"
    ) == "Accepted"


def test_invalid_booking_status():
    with pytest.raises(ValueError, match="Invalid new booking status"):
        update_booking_status(
            "Requested",
            "Invalid"
        )
