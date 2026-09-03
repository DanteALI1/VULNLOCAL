from django import forms

def _style_fields(form):
    for name, field in form.fields.items():
        w = field.widget
        if isinstance(w, forms.CheckboxInput):
            w.attrs.setdefault("class", "checkbox")
        elif isinstance(w, forms.Select):
            w.attrs.setdefault("class", "select")
        elif isinstance(w, forms.Textarea):
            w.attrs.setdefault("class", "textarea")
        elif isinstance(w, forms.FileInput):
            w.attrs.setdefault("class", "input")
        elif isinstance(w, forms.HiddenInput):
            continue
        else:
            w.attrs.setdefault("class", "input")



from .db_wizard import validate_local_prefix
from .models import SystemSettings


class LicenseStepForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)

    license_file = forms.FileField(label="Файл лицензии (.novalic)", required=False)
    license_server_url = forms.URLField(label="URL License Server", required=False)
    skip_for_dev = forms.BooleanField(
        label="Dev-режим: grace 14 дней без файла",
        required=False,
        initial=True,
    )


class OrgStepForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)

    organization_name = forms.CharField(label="Организация", max_length=255)
    local_id_prefix = forms.CharField(label="Префикс локальных ID", max_length=16, widget=forms.TextInput(attrs={"id": "org-prefix", "class": "input"}))

    def clean_local_id_prefix(self):
        ok, val = validate_local_prefix(self.cleaned_data["local_id_prefix"])
        if not ok:
            raise forms.ValidationError(val)
        return val


class BrandingStepForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)

    login_title = forms.CharField(label="Заголовок login", max_length=255, initial="NovaTIP")
    login_subtitle = forms.CharField(
        label="Текст login",
        widget=forms.Textarea(attrs={"rows": 3}),
        required=False,
        initial="Threat Intelligence Platform",
    )
    logo = forms.ImageField(label="Логотип", required=False)


class DbConnectForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)

    host = forms.CharField(initial="127.0.0.1", label="Host")
    port = forms.IntegerField(initial=5432, label="Port")
    name = forms.CharField(label="Имя базы", initial="novatip")
    user = forms.CharField(label="Пользователь БД")
    password = forms.CharField(
        label="Пароль УЗ БД", widget=forms.PasswordInput(render_value=True)
    )
    sslmode = forms.ChoiceField(
        label="SSL mode",
        choices=[("disable", "disable"), ("prefer", "prefer"), ("require", "require")],
        initial="prefer",
    )


class DbCreateForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)

    host = forms.CharField(initial="127.0.0.1")
    port = forms.IntegerField(initial=5432)
    superuser = forms.CharField(label="Superuser PostgreSQL", initial="postgres")
    super_password = forms.CharField(label="Пароль superuser", widget=forms.PasswordInput)
    db_name = forms.CharField(label="Новая БД", initial="novatip")
    role_name = forms.CharField(label="Новая УЗ", initial="novatip")
    role_password = forms.CharField(label="Пароль новой УЗ", widget=forms.PasswordInput)
    sslmode = forms.ChoiceField(
        choices=[("disable", "disable"), ("prefer", "prefer"), ("require", "require")],
        initial="prefer",
    )


class AdminStepForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)

    username = forms.CharField(label="Логин администратора")
    full_name = forms.CharField(label="ФИО", required=False)
    email = forms.EmailField(label="Email")
    password1 = forms.CharField(label="Пароль", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Повтор пароля", widget=forms.PasswordInput)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password1") != cleaned.get("password2"):
            raise forms.ValidationError("Пароли не совпадают")
        return cleaned


class SourcesStepForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)

    nvd_api_key = forms.CharField(label="NVD API Key", required=False)
    kev_enabled = forms.BooleanField(
        label="Синхронизировать KEV (CISA)", required=False, initial=True
    )
    bdu_enabled = forms.BooleanField(
        label="Синхронизировать БДУ ФСТЭК", required=False, initial=True
    )


class MailStepForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)

    email_host = forms.CharField(required=False, label="SMTP host")
    email_port = forms.IntegerField(required=False, initial=587)
    email_user = forms.CharField(required=False)
    email_password = forms.CharField(
        required=False, widget=forms.PasswordInput(render_value=True)
    )
    email_use_tls = forms.BooleanField(required=False, initial=True)


class TelegramStepForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)

    telegram_bot_token = forms.CharField(required=False)
    telegram_chat_id = forms.CharField(required=False)
    skip = forms.BooleanField(label="Пропустить", required=False, initial=False)


class SettingsForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)

    class Meta:
        model = SystemSettings
        fields = [
            "organization_name",
            "local_id_prefix",
            "login_title",
            "login_subtitle",
            "logo",
            "nvd_api_key",
            "kev_enabled",
            "bdu_enabled",
            "sync_cron",
            "email_host",
            "email_port",
            "email_user",
            "email_password",
            "email_use_tls",
            "telegram_bot_token",
            "telegram_chat_id",
        ]
