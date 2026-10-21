from django.apps import AppConfig


class IiotConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.iiot"
    verbose_name = "IIoT"

    def ready(self):
        from . import signals  # noqa: F401  (registra observadores de lecturas)
