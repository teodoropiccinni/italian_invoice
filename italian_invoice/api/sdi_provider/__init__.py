"""
API endpoints per provider SDI
Gestisce callback OAuth e webhook per diversi provider SDI
"""

from .wolters_kluwer import (
	authorize_wolters_kluwer,
	test_wolters_kluwer_connection,
	wolters_kluwer_callback,
	wolters_kluwer_webhook,
)

__all__ = [
	"authorize_wolters_kluwer",
	"test_wolters_kluwer_connection",
	"wolters_kluwer_callback",
	"wolters_kluwer_webhook",
]
