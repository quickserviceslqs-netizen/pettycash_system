from django.db import models

class Company(models.Model):
    name = models.CharField(max_length=200, unique=True)
    code = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return self.name


class Region(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='regions')

    def __str__(self):
        return self.name


class Branch(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='branches')

    def __str__(self):
        return self.name


class Department(models.Model):
    name = models.CharField(max_length=100)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='departments')

    def __str__(self):
        return self.name


class CostCenter(models.Model):
    name = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='cost_centers')

    def __str__(self):
        return self.name


class Position(models.Model):
    title = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='positions')

    def __str__(self):
        return self.title
