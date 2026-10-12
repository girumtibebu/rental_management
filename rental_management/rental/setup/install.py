from rental_management.rental.setup.custom_fields import setup_custom_fields


def after_install():
    setup_custom_fields()


def after_migrate():
    setup_custom_fields()
