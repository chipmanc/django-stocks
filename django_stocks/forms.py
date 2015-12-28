from django.forms import ModelForm

import models

class UnitChangeForm(ModelForm):
    
    class Meta:
        """Admin options."""
        model = models.Unit
        exclude = ()
    
    def __init__(self, *args, **kwargs):
        super(UnitChangeForm, self).__init__(*args, **kwargs)
        qs = models.Unit.objects.filter(master=True)
        self.fields["true_unit"].queryset = qs
        