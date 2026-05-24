from django import forms
from django.contrib.auth import get_user_model

from .models import DeliveryType, Issue, Order


class BootstrapFormMixin:
    field_classes = "form-control"
    select_classes = "form-select"
    checkbox_classes = "form-check-input"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = self.checkbox_classes
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs["class"] = self.select_classes
            elif isinstance(widget, forms.Textarea):
                widget.attrs["class"] = self.field_classes
                widget.attrs.setdefault("rows", 3)
            else:
                widget.attrs["class"] = self.field_classes


class DeliveryTypeForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = DeliveryType
        fields = [
            "name",
            "description",
            "max_distance",
            "base_price",
            "price_per_kg",
            "price_per_m3",
            "declared_value_percent",
            "urgency_multiplier",
        ]


class OrderForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Order
        fields = [
            "pickup_city",
            "pickup_street",
            "pickup_house",
            "delivery_to_pickup_point",
            "delivery_city",
            "delivery_street",
            "delivery_house",
            "delivery_type",
            "weight_kg",
            "length_cm",
            "width_cm",
            "height_cm",
            "order_photo",
            "description",
        ]
        widgets = {
            "pickup_street": forms.TextInput(attrs={"placeholder": "Улица"}),
            "pickup_house": forms.TextInput(attrs={"placeholder": "Дом"}),
            "delivery_street": forms.TextInput(attrs={"placeholder": "Улица"}),
            "delivery_house": forms.TextInput(attrs={"placeholder": "Дом"}),
            "description": forms.Textarea(attrs={"rows": 3, "placeholder": "Необязательный комментарий"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("delivery_to_pickup_point"):
            cleaned_data["delivery_street"] = ""
            cleaned_data["delivery_house"] = ""
        return cleaned_data


class DispatcherAssignCourierForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Order
        fields = ["courier"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        User = get_user_model()
        self.fields["courier"].queryset = User.objects.filter(role=User.ROLE_COURIER)
        self.fields["courier"].required = True


class StatusUpdateForm(BootstrapFormMixin, forms.Form):
    tracking_number = forms.CharField(label="Трекинг-номер", max_length=24, required=False)
    status = forms.ChoiceField(label="Новый статус", choices=Order.STATUS_CHOICES)
    comment = forms.CharField(label="Комментарий", widget=forms.Textarea(attrs={"rows": 3}), required=False)
    delivery_report_photo = forms.FileField(label="Фотоотчет доставки", required=False)

    def __init__(self, *args, allowed_statuses=None, **kwargs):
        super().__init__(*args, **kwargs)
        if allowed_statuses is not None:
            allowed = set(allowed_statuses)
            self.fields["status"].choices = [(value, label) for value, label in Order.STATUS_CHOICES if value in allowed]


class IssueForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Issue
        fields = ["issue_type", "description"]
        widgets = {"description": forms.Textarea(attrs={"rows": 5, "placeholder": "Опишите ситуацию"})}


class IssueResolveForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Issue
        fields = ["resolved"]
