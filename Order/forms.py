from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.images import get_image_dimensions

from .models import DeliveryType, Issue, Order


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        single_clean = super().clean
        if isinstance(data, (list, tuple)):
            cleaned_files = [single_clean(item, initial) for item in data]
            self.validate_dimensions(cleaned_files)
            return cleaned_files
        cleaned_file = single_clean(data, initial)
        self.validate_dimensions([cleaned_file] if cleaned_file else [])
        return cleaned_file

    @staticmethod
    def validate_dimensions(files):
        for uploaded_file in files:
            width, height = get_image_dimensions(uploaded_file)
            uploaded_file.seek(0)
            if width > 550 or height > 550:
                raise ValidationError("Изображение должно быть не больше 550x550 пикселей.")


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
            elif isinstance(widget, forms.ClearableFileInput):
                widget.attrs["class"] = f"{self.field_classes} image-input".strip()
                widget.attrs["accept"] = "image/*"
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
        ]


class OrderForm(BootstrapFormMixin, forms.ModelForm):
    order_photos = MultipleFileField(
        label="Фотографии заказа",
        required=False,
        help_text="Можно выбрать сразу несколько фотографий.",
    )

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
        user_model = get_user_model()
        self.fields["courier"].queryset = user_model.objects.filter(role=user_model.ROLE_COURIER)
        self.fields["courier"].required = True


class StatusUpdateForm(BootstrapFormMixin, forms.Form):
    tracking_number = forms.CharField(label="Трекинг-номер", max_length=24, required=False)
    status = forms.ChoiceField(label="Новый статус", choices=Order.STATUS_CHOICES)
    comment = forms.CharField(label="Комментарий", widget=forms.Textarea(attrs={"rows": 3}), required=False)
    delivery_report_photos = MultipleFileField(
        label="Фотоотчет доставки",
        required=False,
        help_text="Можно выбрать сразу несколько фотографий.",
    )

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
