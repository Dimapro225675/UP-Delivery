from django import forms
from .models import DeliveryType, Order, Payment, Issue

class BootstrapFormMixin:
    field_classes = 'form-control'
    select_classes = 'form-select'
    checkbox_classes = 'form-check-input'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs['class'] = self.checkbox_classes
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs['class'] = self.select_classes
            elif isinstance(widget, forms.Textarea):
                widget.attrs['class'] = self.field_classes
                widget.attrs.setdefault('rows', 4)
            else:
                widget.attrs['class'] = self.field_classes

class DeliveryTypeForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = DeliveryType
        fields = ['name', 'description', 'max_distance', 'base_price']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Например: Экспресс'}),
            'description': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Короткое описание тарифа'}),
            'max_distance': forms.NumberInput(attrs={'placeholder': '0'}),
            'base_price': forms.NumberInput(attrs={'placeholder': '0.00'}),
        }

class OrderForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Order
        fields = ['pickup_address', 'delivery_address', 'description', 'delivery_type', 'status', 'courier']
        widgets = {
            'pickup_address': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Адрес забора'}),
            'delivery_address': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Адрес доставки'}),
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Комментарий к заказу'}),
            'delivery_type': forms.Select(),
            'status': forms.Select(),
            'courier': forms.Select(),
        }

class PaymentForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['amount', 'payment_method', 'status', 'transaction_id']
        widgets = {
            'amount': forms.NumberInput(attrs={'placeholder': '0.00'}),
            'payment_method': forms.TextInput(attrs={'placeholder': 'Карта / наличные / перевод'}),
            'status': forms.Select(),
            'transaction_id': forms.TextInput(attrs={'placeholder': 'ID транзакции'}),
        }

class IssueForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Issue
        fields = ['issue_type', 'description']
        widgets = {
            'issue_type': forms.Select(),
            'description': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Опишите проблему подробно'}),
        }

class IssueResolveForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Issue
        fields = ['resolved']