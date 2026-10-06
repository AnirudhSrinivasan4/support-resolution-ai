"""Default telecom complaint labels; settings can replace the class lists."""

from app.domain.models import ComplaintTaxonomy

DEFAULT_COMPLAINT_TAXONOMY = ComplaintTaxonomy(
    intents=(
        "connectivity_issue",
        "esim_activation",
        "payment_failed",
        "duplicate_charge",
        "billing_dispute",
        "roaming_issue",
        "account_access",
        "security_concern",
        "device_issue",
        "general_inquiry",
        "unknown",
    ),
    categories=(
        "network",
        "esim",
        "sim",
        "billing",
        "payments",
        "roaming",
        "account",
        "device",
        "outage",
        "general_inquiry",
        "unknown",
    ),
    products=(
        "broadband",
        "mobile_data",
        "fifth_generation_mobile",
        "esim",
        "sim",
        "voice",
        "payments",
        "roaming",
        "account",
        "device",
        "unknown",
    ),
)
