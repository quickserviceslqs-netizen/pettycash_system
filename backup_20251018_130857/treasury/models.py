from django.db import models
from transactions.models import Requisition

class Payment(models.Model):
    requisition = models.ForeignKey(Requisition, on_delete=models.CASCADE)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_at = models.DateTimeField(auto_now_add=True)
    processed_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    
    def __str__(self):
        return f"{self.requisition} - Paid {self.paid_amount}"
