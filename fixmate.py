def calculate_service_charge(base_charge, quantity):
    """Calculate the total service charge."""
    if base_charge < 0 or quantity <= 0:
        raise ValueError("Service charge and quantity must be valid")

    return base_charge * quantity


def check_provider_availability(available_providers, required_providers):
    """Check whether enough service providers are available."""
    if required_providers <= 0:
        return False

    return required_providers <= available_providers


def update_booking_status(current_status, new_status):
    """Update the status of a FixMate service booking."""

    valid_statuses = [
        "Requested",
        "Accepted",
        "Assigned",
        "In Progress",
        "Completed",
        "Cancelled"
    ]

    if current_status not in valid_statuses:
        raise ValueError("Invalid current booking status")

    if new_status not in valid_statuses:
        raise ValueError("Invalid new booking status")

    return new_status


if __name__ == "__main__":

    service_name = "Plumbing"
    service_charge = 500
    quantity = 1

    available_providers = 5
    required_providers = 1

    current_status = "Requested"
    new_status = "Accepted"

    if check_provider_availability(
        available_providers,
        required_providers
    ):

        total_charge = calculate_service_charge(
            service_charge,
            quantity
        )

        booking_status = update_booking_status(
            current_status,
            new_status
        )

        print("FIXMATE HOME SERVICE MANAGEMENT SYSTEM")
        print("Service:", service_name)
        print("Total service charge: Rs.", total_charge)
        print("Booking status:", booking_status)
        print("Provider available: Yes")

    else:

        print("Booking unsuccessful: No provider available")
