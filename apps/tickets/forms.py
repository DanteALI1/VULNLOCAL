from django import forms

def _style_fields(form):
    from django import forms as djforms
    for name, field in form.fields.items():
        w = field.widget
        if isinstance(w, djforms.CheckboxInput):
            w.attrs.setdefault("class", "checkbox")
        elif isinstance(w, djforms.Select):
            w.attrs.setdefault("class", "select")
        elif isinstance(w, djforms.SelectMultiple):
            w.attrs.setdefault("class", "select")
        elif isinstance(w, djforms.Textarea):
            w.attrs.setdefault("class", "textarea")
        elif isinstance(w, djforms.FileInput):
            w.attrs.setdefault("class", "input")
        elif isinstance(w, djforms.HiddenInput):
            continue
        else:
            w.attrs.setdefault("class", "input")

from django.contrib.auth import get_user_model

from apps.accounts.models import User
from apps.vulns.models import Vulnerability

from .models import Ticket

UserModel = get_user_model()


class TicketFilterForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)

    q = forms.CharField(required=False, label="Поиск")
    status = forms.MultipleChoiceField(
        required=False,
        choices=Ticket.Status.choices,
        widget=forms.CheckboxSelectMultiple,
    )
    priority = forms.ChoiceField(
        required=False,
        choices=[("", "Любой")] + list(Ticket.Priority.choices),
    )
    assignee = forms.ModelChoiceField(
        required=False,
        queryset=UserModel.objects.filter(role=User.Role.TICKET_ASSIGNEE),
        empty_label="Любой исполнитель",
    )


class TicketCreateForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ["title", "description", "vulnerability", "priority", "assignee"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["vulnerability"].queryset = Vulnerability.objects.all().order_by("-id")
        self.fields["assignee"].queryset = UserModel.objects.filter(
            role=User.Role.TICKET_ASSIGNEE,
            is_active=True,
        )
        self.fields["assignee"].required = False


class TicketAssignForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)

    assignee = forms.ModelChoiceField(
        queryset=UserModel.objects.filter(role=User.Role.TICKET_ASSIGNEE, is_active=True),
        label="Исполнитель",
    )


class TicketTransitionForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)

    new_status = forms.ChoiceField(choices=Ticket.Status.choices)
    waiting_reason = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    resolution_notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    reject_reason = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    reopen_reason = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    confirm_close = forms.BooleanField(required=False, label="Подтверждаю закрытие")
    force = forms.BooleanField(required=False)
    force_reason = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))
