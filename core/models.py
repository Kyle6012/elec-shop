from django.db import models
from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from PIL import Image
from django.urls import reverse

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    
    def __str__(self):
        return self.name
    
class Product(models.Model):
    product_name = models.CharField(max_length=255)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    product_quantity = models.IntegerField(default=0)
    product_image = models.ImageField(upload_to='products_pics/', blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, default=0)
   # is_finished = models.BooleanField(default=False)  # Optional flag
    

    def __str__(self):
        return self.product_name

    def save(self, *args, **kwargs):
        super(Product, self).save(*args, **kwargs)
        # Resize the image if it's too large
        img = Image.open(self.product_image.path)
        if img.height > 300 or img.width > 300:
            output_size = (300, 300)
            img.thumbnail(output_size)
            img.save(self.product_image.path)



def get_sentinel_user():
    return get_user_model().objects.get_or_create(username='deleted user')[0]

def get_sentinel_user_id():
    return get_sentinel_user().id 
class Invoice(models.Model):
    invoice_number = models.BigAutoField(primary_key=True)
    customer_name = models.CharField(max_length=100)
    created_by = models.ForeignKey(User,on_delete=models.SET(get_sentinel_user),default=get_sentinel_user_id)
    date_created = models.DateTimeField(auto_now=True)
    total = models.PositiveBigIntegerField(default=0)

    def __str__(self):
        return self.customer_name+'(Inv_no.'+str(self.invoice_number)+')'
    
    def get_absolute_url(self):
        return reverse('add_items_on_invoice', kwargs={'pk': self.pk})
    
    def save(self, *args, **kwargs):
        self.total =  sum(item.accumulated for item in self.invoiceitem.all())
        super(Invoice, self).save(*args, **kwargs)

def get_sentinel_product():
    return Product.objects.get_or_create(product_name='deleted product',unit_price=0)[0]

class SalesRecord(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, default=0)
    initial_stock = models.PositiveIntegerField(null=False)  # Ensure null=False
    remaining_stock = models.PositiveIntegerField()
    sold_quantity = models.PositiveIntegerField(default=0)
    def __str__(self):
        return f"{self.product.product_name} Sales Record"

def get_sentinel_product_id():
    return get_sentinel_product().id

class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="invoice_items")
    item = models.ForeignKey(Product, on_delete=models.SET(get_sentinel_product), default='', null=True, blank=True)
    quantity = models.PositiveIntegerField()
    accumulated = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.item.product_name} - Invoice: {self.invoice.id}"

    def save(self, *args, **kwargs):
        # Calculate the accumulated price for this invoice item
        self.accumulated = self.item.unit_price * self.quantity
        super(InvoiceItem, self).save(*args, **kwargs)

        # Update the sales record for the item
        sales_record, created = SalesRecord.objects.get_or_create(product=self.item)

        # Deduct the quantity sold from the SalesRecord
        sales_record.sold_quantity += self.quantity
        sales_record.remaining_stock -= self.quantity

        # Ensure remaining_stock does not go negative
        if sales_record.remaining_stock < 0:
            raise ValueError(f"Cannot deduct {self.quantity} from stock for {self.item.product_name}. Not enough stock available.")

        sales_record.save()  # Save the updated sales record

