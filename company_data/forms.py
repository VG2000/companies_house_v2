from django import forms

class CompanyFilterForm(forms.Form):
    sic_code_1 = forms.ChoiceField(
        choices=[], required=False, label="SIC Class"
    )
