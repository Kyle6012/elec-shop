from datetime import datetime
from django.shortcuts import redirect, render, get_object_or_404
import os
from SalesManagementSystem.settings import MEDIA_ROOT
from .forms import InvoiceFormSet
from .models import Invoice, Product, SalesRecord, Category
from django.db import connection
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test
from .helpers import deletefile, dictfetchall, render_to_pdf,savefile,filterupdates,getInvoiceDetails
from decimal import Decimal, InvalidOperation

def products(request):
    "Retrieve view for products."
    q = request.GET.get('filter', None)
    categories = Category.objects.all()  # Assuming you have a Category model
    products = {}

    with connection.cursor() as cursor:
        if q is not None:
            cursor.execute('SELECT * FROM core_product WHERE unit_price <= %s AND unit_price > 0 ORDER BY product_name', [str(q)])
        else:
            cursor.execute('SELECT * FROM core_product WHERE unit_price > 0 ORDER BY product_name')
        products = dictfetchall(cursor)

    context = {
        'products': products,
        'categories': categories,  # Add categories to context
        'q': q
    }
    return render(request, "core/products.html", context)

def productslistView(request):
    "list view for products."
    q = request.GET.get('search',None)
    products={}  
    with connection.cursor() as cursor:
        if q is not None:
            search = "%"+q+"%"
            cursor.execute("""SELECT * FROM core_product WHERE lower(product_name) LIKE %s and product_name!="deleted product" order by product_name""",[str(search)])
        else:
            cursor.execute('SELECT * FROM core_product WHERE unit_price>0 order by product_name')
        products = dictfetchall(cursor)
    context={
        'products':products,
        'q':q
    }
    return render(request,"core/productslist.html",context)
@login_required
def sales_record(request):
    products = Product.objects.all()  # This assumes stock is part of the Product model

    # Ensure you are handling products correctly
    for product in products:
        print(product.product_name, product.stock)  # Check if this field exists

    return render(request, 'sales/records.html', {'products': products})
@login_required
def createproduct(request):
    if request.method == "POST":
        # Extract POST data
        product_name = request.POST.get('product_name')
        unit_price = request.POST.get('unit_price')
        product_image = request.FILES.get('product_image')
        category_id = request.POST.get('category_id')
        product_quantity = request.POST.get('stock')  # Retrieve stock quantity
        
        # Validation for product_quantity (stock)
        if not product_quantity:
            messages.error(request, "Stock cannot be empty.")
            return render(request, 'core/createproduct.html')

        try:
            product_quantity = int(product_quantity)
        except ValueError:
            messages.error(request, "Stock must be an integer.")
            return render(request, 'core/createproduct.html')

        # Convert unit price to Decimal for accuracy
        try:
            unit_price = Decimal(unit_price)
        except InvalidOperation:
            messages.error(request, "Unit price must be a valid decimal number.")
            return render(request, 'core/createproduct.html')

        # Validate the category
        try:
            category = Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            messages.error(request, "Selected category does not exist.")
            return render(request, 'core/createproduct.html')

        # Save product
        try:
            product = Product.objects.create(
                product_name=product_name,
                unit_price=unit_price,
                product_image=product_image,
                category=category,
                product_quantity=product_quantity
            )
            messages.success(request, "Product created successfully.")
            return redirect('products')  # Redirect to product listing
        except Exception as e:
            messages.error(request, f"Error creating product: {str(e)}")
            return render(request, 'core/createproduct.html')

    # GET request: Load categories
    categories = Category.objects.all()
    return render(request, 'core/createproduct.html', {'categories': categories})

@login_required
def updateproduct(request, pk):
    """
    Update view for product for a given pk (primary key).
    """
    product = {}
    fields = {
        'normal_fields': ['product_name', 'unit_price'],
        'file_fields': ['product_image']
    }
    dir = 'products_pics/'  # Directory for product images

    if request.method == 'POST':
        # Fetch the product to update
        with connection.cursor() as cursor:
            cursor.execute('SELECT * FROM core_product WHERE id = %s', [int(pk)])
            product = dictfetchall(cursor)

        # Filter updated fields
        (filtered_dict, text_field_updated_flag, file_field_updated_flag) = filterupdates(request, product, fields, dir)
        updated_text_fields = filtered_dict['updated_text_fields']
        updated_file_fields = filtered_dict['updated_file_fields']

        # Update text fields (product_name, unit_price)
        if text_field_updated_flag:
            for field, value in updated_text_fields.items():
                query = f'UPDATE core_product SET {field} = %s WHERE id = {pk}'
                with connection.cursor() as cursor:
                    cursor.execute(query, [value])

        # Update file fields (product_image)
        if file_field_updated_flag:
            for field, value in updated_file_fields.items():
                f = request.FILES.get(field)
                filepath = dir + savefile(f, dir)
                query = f'UPDATE core_product SET {field} = %s WHERE id = {pk}'
                with connection.cursor() as cursor:
                    cursor.execute(query, [filepath])

        # Handle category update
        category_id = request.POST.get('product_category')
        if category_id:
            query = f'UPDATE core_product SET category_id = %s WHERE id = {pk}'
            with connection.cursor() as cursor:
                cursor.execute(query, [int(category_id)])

        product_name = product[0].get('product_name')

        # Provide feedback to the user if no fields were updated
        if not text_field_updated_flag and not file_field_updated_flag:
            messages.info(request, f'{product_name} has no new updates.')
            return redirect('updateproduct', pk=pk)

        messages.success(request, f'{product_name} updated successfully.')
        return redirect('updateproduct', pk=pk)

    if request.method == 'GET':
        # Fetch the product to update
        with connection.cursor() as cursor:
            cursor.execute('SELECT * FROM core_product WHERE id = %s', [int(pk)])
            product = dictfetchall(cursor)

        # Fetch all categories for the dropdown
        categories = Category.objects.all()

        context = {
            'products': product,
            'categories': categories,  # Pass categories to the template
            'pk': pk,
        }
        return render(request, "core/updateproduct.html", context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def deleteproduct(request, pk):
    """
    Delete view for product for given pk (primary key).
    """
    product = {}
    with connection.cursor() as cursor:
        cursor.execute('SELECT * FROM core_product WHERE id = %s', [int(pk)])
        product = dictfetchall(cursor)
    product_name = product[0].get('product_name')

    if request.method == 'POST':
        # Delete the product
        with connection.cursor() as cursor:
            cursor.execute('DELETE FROM core_product WHERE id = %s', [int(pk)])

        # Remove the associated image file from filesystem
        product_image = product[0].get('product_image')
        path = os.path.join(MEDIA_ROOT, product_image)
        deletefile(path)

        messages.success(request, f'{product_name} Deleted.')
        return redirect('products')

    if request.method == 'GET':
        context = {
            'product': product
        }
        return render(request, "core/product_confirm_delete.html", context)
@login_required
def createinvoice(request):
    "Create view for invoice."
    if request.method == 'POST':
        current_pk = 0
        created_by_id = request.user.id
        customer_name = request.POST.get('customer_name')
        date_created = datetime.now()

        with connection.cursor() as cursor:
            cursor.execute('INSERT INTO core_invoice (customer_name, created_by_id, date_created, total) VALUES (%s, %s, %s, %s)',
                           [str(customer_name), int(created_by_id), date_created, 0])
            current_pk = cursor.lastrowid

        messages.success(request, f'Invoice created for {customer_name}.')
        return redirect('addinvoiceitems', pk=current_pk)
    return render(request, "core/createinvoice.html")

def dictfetchall(cursor):
    # Helper function to return query results as a list of dictionaries
    desc = cursor.description
    return [
        dict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()
    ]
@login_required
def addinvoiceitems(request, pk):
    "Add invoice items view on invoice."
    form = InvoiceFormSet()
    context = {
        'form': form,
        'pk': pk
    }
    getInvoiceDetails(pk, context)

    if request.method == 'POST':
        form = InvoiceFormSet(request.POST, instance=Invoice.objects.get(invoice_number=pk))
        total = 0
        if form.is_valid():
            for data in form.cleaned_data:
                if data:
                    cleaned_dict = {}
                    item = data.get('item')
                    for k, v in data.items():
                        try:
                            if v.pk:
                                cleaned_dict[k] = v.pk
                        except:
                            cleaned_dict[k] = v

                    item_id = cleaned_dict['item']
                    unit_price = item.unit_price
                    quantity = cleaned_dict['quantity']
                    accumulated = unit_price * quantity

                    # Fetch initial stock from the Product model
                    initial_stock = item.product_quantity

                    # Update stock and create invoice item
                    sales_record, created = SalesRecord.objects.get_or_create(
                        product=item,
                        defaults={'initial_stock': initial_stock, 'remaining_stock': initial_stock}
                    )
                    
                    # Check if there's enough stock
                    if sales_record.remaining_stock >= quantity:
                        sales_record.remaining_stock -= quantity
                        sales_record.sold_quantity += quantity
                        sales_record.save()

                        # Add invoice item
                        with connection.cursor() as cursor:
                            cursor.execute(
                                'INSERT INTO core_invoiceitem (quantity, accumulated, invoice_id, item_id) VALUES (%s, %s, %s, %s)',
                                [int(quantity), int(accumulated), pk, int(item_id)]
                            )
                    else:
                        messages.error(request, f"Not enough stock for {item.product_name}. Available: {sales_record.remaining_stock}")

            # Recalculate total
            with connection.cursor() as cursor:
                cursor.execute('SELECT SUM(accumulated) AS total FROM core_invoiceitem WHERE invoice_id = %s', [int(pk)])
                total = cursor.fetchone()[0]
                cursor.execute('UPDATE core_invoice SET total = %s WHERE invoice_number = %s', [int(total), int(pk)])

            getInvoiceDetails(pk, context)
    return render(request, "core/additemstoinvoice.html", context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def deleteinvoice(request, pk):
    """Delete view for invoice for given pk."""
    invoice = None
    with connection.cursor() as cursor:
        cursor.execute('SELECT * FROM core_invoice WHERE invoice_number = %s', [int(pk)])
        invoice = dictfetchall(cursor)[0]

    customer_name = invoice.get('customer_name')

    if request.method == 'POST':
        # First, delete all related invoice items to avoid the foreign key constraint error
        with connection.cursor() as cursor:
            cursor.execute('DELETE FROM core_invoiceitem WHERE invoice_id = %s', [int(pk)])

        # Then, delete the invoice itself
        with connection.cursor() as cursor:
            cursor.execute('DELETE FROM core_invoice WHERE invoice_number = %s', [int(pk)])

        messages.success(request, f'Invoice for {customer_name} deleted.')
        return redirect('sales')

    if request.method == 'GET':
        context = {
            'invoice': invoice
        }
        return render(request, "core/invoice_confirm_delete.html", context)


@login_required
def deleteinvoiceitem(request, item_pk, invoice_number):
    """Delete view for invoice item for given pk and invoice_number."""
    if request.method == 'GET':
        # Retrieve the invoice item to restore stock
        with connection.cursor() as cursor:
            cursor.execute('SELECT item_id, quantity FROM core_invoiceitem WHERE id = %s', [int(item_pk)])
            invoice_item = cursor.fetchone()

            if invoice_item:
                item_id, quantity = invoice_item

                # Restore stock
                sales_record = SalesRecord.objects.get(product_id=item_id)
                sales_record.remaining_stock += quantity
                sales_record.sold_quantity -= quantity
                sales_record.save()

                # Delete the item from the invoice
                cursor.execute('DELETE FROM core_invoiceitem WHERE id = %s', [int(item_pk)])
                messages.success(request, 'Item deleted.')

                # Recalculate the total for the invoice
                cursor.execute('SELECT SUM(accumulated) AS total FROM core_invoiceitem WHERE invoice_id = %s', [int(invoice_number)])
                total = cursor.fetchone()[0] or 0  # Handle case where total is None

                cursor.execute('UPDATE core_invoice SET total = %s WHERE invoice_number = %s', [int(total), int(invoice_number)])

        return redirect('addinvoiceitems', pk=invoice_number)

@login_required
def invoicedetail(request,pk):
    "detail view for invoice."
    if request.method == 'GET':
        context={}
        getInvoiceDetails(pk,context)
        return render(request,"core/invoicedetails.html",context)
@login_required
def sales(request):
    "sales view for invoices."
    if request.method == 'GET':
        q = request.GET.get('search',None) 
        context={}
        invoices_dict=None
        with connection.cursor() as cursor:
            if q is not None:
                search = "%"+q+"%"
                cursor.execute('select core_invoice.invoice_number,core_invoice.customer_name,core_invoice.date_created,core_invoice.total,auth_user.username as created_by from core_invoice inner join auth_user on core_invoice.created_by_id = auth_user.id WHERE core_invoice.customer_name LIKE %s ',[str(search)])
            else:
                cursor.execute('select core_invoice.invoice_number,core_invoice.customer_name,core_invoice.date_created,core_invoice.total,auth_user.username as created_by from core_invoice inner join auth_user on core_invoice.created_by_id = auth_user.id order by core_invoice.date_created desc ')
            invoices_dict = dictfetchall(cursor)
        context['invoices_dict']=invoices_dict
        context['q']=q
        return render(request,"core/sales.html",context)

@login_required
def printinvoice(request,pk):
    "print invoice view for given pk."
    if request.method == 'GET':
        context={}
        getInvoiceDetails(pk,context)
        pdf = render_to_pdf('core/invoice_print.html', context)
        return HttpResponse(pdf, content_type='application/pdf')


@login_required
@user_passes_test(lambda u: u.is_superuser)
def sales_record(request):
    """
    View to display and automatically update sales records based on the product's stock.
    """
    # Fetch all products
    products = Product.objects.all().select_related('category')
    
    # Automatically update or create sales records for each product
    for product in products:
        initial_stock = product.product_quantity  # Use 'product_quantity' instead of 'stock'
        
        # Calculate sold and remaining stock from the SalesRecord model
        sales_record, created = SalesRecord.objects.get_or_create(product=product)
        
        sold_quantity = sales_record.sold_quantity or 0  # Check if a record exists, else 0
        remaining_stock = initial_stock - sold_quantity if initial_stock else 0
        
        # Update the existing SalesRecord or create a new one
        SalesRecord.objects.update_or_create(
            product=product,
            defaults={
                'category': product.category,
                'initial_stock': initial_stock,
                'remaining_stock': remaining_stock,
                'sold_quantity': sold_quantity,
            }
        )

    # Fetch all updated sales records
    sales_records = SalesRecord.objects.all().select_related('product', 'category')

    context = {
        'sales_records': sales_records,
    }
    return render(request, "core/records.html", context)
@login_required
@user_passes_test(lambda u: u.is_superuser)
def sales_record(request):
    """
    View to display and automatically update sales records based on the product's stock.
    """
    # Fetch all products
    products = Product.objects.all().select_related('category')

    for product in products:
        # Ensure product.product_quantity has a valid value
        initial_stock = product.product_quantity if product.product_quantity is not None else 0

        # Update the existing SalesRecord or create a new one
        sales_record, created = SalesRecord.objects.get_or_create(
            product=product,
            defaults={
                'category': product.category,
                'initial_stock': initial_stock,  # Ensure initial_stock is set here
                'remaining_stock': initial_stock,  # Initially, remaining stock equals initial stock
                'sold_quantity': 0,  # New record starts with no sales
            }
        )

        # If the record already exists, update the remaining stock and sold quantity
        if not created:
            sold_quantity = sales_record.sold_quantity or 0
            remaining_stock = initial_stock - sold_quantity
            sales_record.remaining_stock = remaining_stock
            sales_record.save()

    # Fetch all updated sales records
    sales_records = SalesRecord.objects.all().select_related('product', 'category')

    context = {
        'sales_records': sales_records,
    }
    return render(request, "core/records.html", context)
