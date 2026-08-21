# handlers_modules/__init__.py
from .admin import (
    handle_admin_newvisit,
    handle_admin_command,
    delete_guest,
    list_guests,
    clear_cache,
    restore_guests
)

from .profile import handle_profile
from .registration import (
    get_agreement_keyboard,
    AGREEMENT_TEXT_OLD,
    AGREEMENT_TEXT_NEW,
    PHONE_REQUEST_MESSAGES,
    handle_registration_step
)

from .visits import handle_visit
from .promo import handle_promo
from .raffle import handle_raffle
from .reviews import handle_reviews
from .greetings import handle_greetings
from .help import handle_help
from .utils import handle_utils