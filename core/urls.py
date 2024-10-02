from django.urls import path
from . import views

urlpatterns = [
    # Product-related URLs
    path("", views.products, name="products"),
    path("productlist/", views.productslistView, name="productslist"),
    path("createproduct/", views.createproduct, name="createproduct"),
    path("products/<int:pk>/update/", views.updateproduct, name="updateproduct"),
    path("product/<int:pk>/delete/", views.deleteproduct, name="deleteproduct"),
    
    # Invoice-related URLs
    path("createinvoice/", views.createinvoice, name="createinvoice"),
    path("addinvoiceitems/<int:pk>/", views.addinvoiceitems, name="addinvoiceitems"),
    path("invoices/<int:pk>/delete/", views.deleteinvoice, name="deleteinvoice"),
    path("invoices/<int:invoice_number>/deleteitem/<int:item_pk>/", views.deleteinvoiceitem, name="deleteinvoiceitem"),
    path("invoices/<int:pk>/details/", views.invoicedetail, name="invoice_details"),
    path("invoices/<int:pk>/print/", views.printinvoice, name="print_invoice"),
    
    # Sales-related URLs
    path("sales/", views.sales, name="sales"),
    path("sales/records/", views.sales_record, name="sales_records"),  # View sales records
]
