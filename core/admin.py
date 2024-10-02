from django.contrib import admin
from .models import Product, InvoiceItem, Invoice, Category

admin.site.register(Category)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['id', 'product_name', 'unit_price', 'product_image']
    # Removed 'stock_quantity' as it's not a field in Product or fix the model if it's meant to be there.

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'customer_name', 'date_created', 'created_by', 'total']
    # Ensure this inherits from ModelAdmin, not InlineModelAdmin

@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'invoice', 'item', 'quantity', 'accumulated']
