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


from .models import Vulnerability


class VulnFilterForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)

    q = forms.CharField(
        required=False,
        label="Поиск",
        widget=forms.TextInput(attrs={"placeholder": "CVE / BDU / текст…"}),
    )
    severity = forms.MultipleChoiceField(
        required=False,
        choices=Vulnerability.Severity.choices,
        widget=forms.CheckboxSelectMultiple,
        label="Критичность",
    )
    is_kev = forms.BooleanField(required=False, label="Только KEV")
    source = forms.ChoiceField(
        required=False,
        choices=[("", "Все источники")] + list(Vulnerability.Source.choices),
        label="Источник",
    )
    cwe = forms.CharField(
        required=False,
        label="CWE",
        widget=forms.TextInput(attrs={"placeholder": "CWE-79"}),
    )

    def active_chips(self) -> list[dict]:
        """Return display chips for active filters (for UI)."""
        chips = []
        if not self.is_bound:
            return chips
        cd = self.cleaned_data if self.is_valid() else {}
        if not cd and self.data:
            # best-effort before full clean
            q = self.data.get("q")
            if q:
                chips.append({"key": "q", "label": f"Поиск: {q}"})
            for sev in self.data.getlist("severity"):
                chips.append({"key": "severity", "value": sev, "label": f"Severity: {sev}"})
            if self.data.get("is_kev"):
                chips.append({"key": "is_kev", "label": "KEV"})
            if self.data.get("source"):
                chips.append({"key": "source", "label": f"Источник: {self.data.get('source')}"})
            if self.data.get("cwe"):
                chips.append({"key": "cwe", "label": f"CWE: {self.data.get('cwe')}"})
            return chips
        if cd.get("q"):
            chips.append({"key": "q", "label": f"Поиск: {cd['q']}"})
        for sev in cd.get("severity") or []:
            chips.append({"key": "severity", "value": sev, "label": f"Severity: {sev}"})
        if cd.get("is_kev"):
            chips.append({"key": "is_kev", "label": "KEV"})
        if cd.get("source"):
            chips.append({"key": "source", "label": f"Источник: {cd['source']}"})
        if cd.get("cwe"):
            chips.append({"key": "cwe", "label": f"CWE: {cd['cwe']}"})
        return chips


class LocalVulnForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)

    class Meta:
        model = Vulnerability
        fields = [
            "title",
            "description_nvd",
            "severity",
            "cwe",
            "references",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description_nvd": forms.Textarea(attrs={"rows": 6}),
            "cwe": forms.Textarea(attrs={"rows": 2, "placeholder": '["CWE-79"]'}),
            "references": forms.Textarea(attrs={"rows": 2, "placeholder": "[]"}),
        }

    def clean_cwe(self):
        value = self.cleaned_data.get("cwe")
        if value in (None, ""):
            return []
        if isinstance(value, list):
            return value
        return value

    def clean_references(self):
        value = self.cleaned_data.get("references")
        if value in (None, ""):
            return []
        return value
