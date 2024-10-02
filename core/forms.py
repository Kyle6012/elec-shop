from django import forms
from .models import Invoice, InvoiceItem
from django.forms.models import inlineformset_factory

# Custom form for InvoiceItems
class InvoiceItemForm(forms.ModelForm):
    class Meta:
        model = InvoiceItem
        fields = ['item', 'quantity']
        # Add custom widgets for form styling (optional)
        widgets = {
            'item': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
        }

    # Optional: Add custom validation
    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity <= 0:
            raise forms.ValidationError("Quantity must be greater than 0.")
        return quantity


# Inline formset to handle multiple InvoiceItems in an Invoice
InvoiceFormSet = inlineformset_factory(
    Invoice,
    InvoiceItem,
    form=InvoiceItemForm,  # Use the custom form for InvoiceItem
    fields=('item', 'quantity',),  # Add fields that you want to include in the formset
    extra=5,  # Number of extra empty forms
    can_delete=True,  # Allow users to delete individual items
)
