"""Backend tests.

Importing salary_api.main builds the module-level app, which needs APP_ENV (it has no
default). Tests build their own settings with tests.factories.make_settings.
"""

import os

os.environ.setdefault("APP_ENV", "test")
