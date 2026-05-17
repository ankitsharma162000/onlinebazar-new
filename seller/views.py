from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
import re
import json

from .models import Seller
from store.models import Product, ProductImage, Order, OrderItem, StockAlert, CATEGORY_CHOICES
from ml.sales_prediction import get_seasonal_prediction
from ml.regional_analysis import get_regional_data
from ml.stock_alert import check_and_generate_stock_alerts


def seller_register(request):
    if request.session.get('seller_id'): return redirect('seller_dashboard')
    if request.method == 'POST':
        d = request.POST; errors = []
        if not re.match(r'^\d{10}$', d.get('phone_number','')): errors.append('Phone must be 10 digits.')
        if not re.match(r'^\d{6}$', d.get('pincode','')): errors.append('Pincode must be 6 digits.')
        if d.get('password') != d.get('confirm_password'): errors.append('Passwords do not match.')
        if Seller.objects.filter(email=d.get('email','').lower()).exists(): errors.append('Email already registered.')
        if errors:
            for e in errors: messages.error(request, e)
            return render(request, 'seller/register.html', {'data': d})
        Seller.objects.create(
            name=d['name'].strip(), email=d['email'].lower().strip(),
            phone_number=d['phone_number'].strip(), password=make_password(d['password']),
            address_line=d['address_line'].strip(), district=d['district'].strip(),
            state=d['state'].strip(), pincode=d['pincode'].strip(),
        )
        messages.success(request, 'Seller account created! Please login.')
        return redirect('seller_login')
    return render(request, 'seller/register.html')


def seller_login(request):
    if request.session.get('seller_id'): return redirect('seller_dashboard')
    if request.method == 'POST':
        email = request.POST.get('email','').lower().strip()
        pw    = request.POST.get('password','')
        try:
            seller = Seller.objects.get(email=email, is_active=True)
            if seller.is_blacklisted:
                messages.error(request, f'Account suspended. Reason: {seller.blacklist_reason or "Contact SuperAdmin."}')
                return render(request, 'seller/login.html')
            if check_password(pw, seller.password):
                request.session['seller_id']   = str(seller.seller_id)
                request.session['seller_name'] = seller.name
                request.session['role']        = 'seller'
                messages.success(request, f'Welcome, {seller.name}!')
                return redirect('seller_dashboard')
            messages.error(request, 'Incorrect password.')
        except Seller.DoesNotExist:
            messages.error(request, 'No seller account with this email.')
    return render(request, 'seller/login.html')


def seller_logout(request):
    request.session.flush()
    messages.success(request, 'Logged out successfully.')
    return redirect('seller_login')


def seller_dashboard(request):
    if not request.session.get('seller_id') or request.session.get('role') != 'seller':
        return redirect('seller_login')
    seller  = get_object_or_404(Seller, seller_id=request.session['seller_id'])
    products= Product.objects.filter(seller=seller, is_active=True)
    ago30   = timezone.now() - timedelta(days=30)

    total_products = products.count()
    oi_qs = OrderItem.objects.filter(product__seller=seller)
    total_orders = oi_qs.values('order').distinct().count()
    revenue = oi_qs.filter(order__order_date__gte=ago30).aggregate(t=Sum('price_at_purchase'))['t'] or 0

    check_and_generate_stock_alerts(seller)
    alerts = StockAlert.objects.filter(product__seller=seller, is_resolved=False).select_related('product')

    # Chart: last 7 days
    labels, data_rev = [], []
    for i in range(6, -1, -1):
        day = (timezone.now() - timedelta(days=i)).date()
        rev = oi_qs.filter(order__order_date__date=day).aggregate(t=Sum('price_at_purchase'))['t'] or 0
        labels.append(day.strftime('%d %b')); data_rev.append(float(rev))

    cat_data = [
        {'product__category': d['product__category'], 'total': float(d['total'] or 0)}
        for d in oi_qs.values('product__category').annotate(total=Sum('price_at_purchase')).order_by('-total')[:6]
    ]

    predictions  = get_seasonal_prediction()
    regional_data= get_regional_data(seller)
    recent_orders= Order.objects.filter(items__product__seller=seller).distinct().order_by('-order_date')[:8]

    # Pending order requests count for badge
    try:
        from .models import SellerOrderRequest
        pending_requests_count = SellerOrderRequest.objects.filter(seller=seller, status='pending').count()
    except Exception:
        pending_requests_count = 0

    return render(request, 'seller/dashboard.html', {
        'seller': seller, 'total_products': total_products,
        'total_orders': total_orders, 'revenue': revenue,
        'alerts': alerts, 'labels': labels, 'data_rev': data_rev,
        'cat_data': cat_data, 'predictions': predictions,
        'regional_data': regional_data, 'recent_orders': recent_orders,
        'products': products[:6],
        'pending_requests_count': pending_requests_count,
    })


def seller_products(request):
    if not request.session.get('seller_id') or request.session.get('role') != 'seller':
        return redirect('seller_login')
    seller   = get_object_or_404(Seller, seller_id=request.session['seller_id'])
    products = Product.objects.filter(seller=seller, is_active=True)
    return render(request, 'seller/products.html', {'seller': seller, 'products': products})


def product_add(request):
    if not request.session.get('seller_id') or request.session.get('role') != 'seller':
        return redirect('seller_login')
    seller = get_object_or_404(Seller, seller_id=request.session['seller_id'])
    if request.method == 'POST':
        d = request.POST; f = request.FILES
        product = Product.objects.create(
            seller=seller,
            product_name=d['product_name'], category=d['category'],
            price=d['price'], description=d.get('description',''),
            manufacturing_date=d.get('manufacturing_date') or None,
            expiry_date=d.get('expiry_date') or None,
            stock_quantity=int(d['stock_quantity']),
            product_image=f.get('product_image'),
        )
        for i, img in enumerate(request.FILES.getlist('extra_images')[:4]):
            ProductImage.objects.create(product=product, image=img, is_primary=(i == 0))
        messages.success(request, f'Product "{product.product_name}" added!')
        return redirect('seller_products')
    return render(request, 'seller/product_form.html', {'seller': seller, 'categories': CATEGORY_CHOICES})


def product_edit(request, product_id):
    if not request.session.get('seller_id') or request.session.get('role') != 'seller':
        return redirect('seller_login')
    seller  = get_object_or_404(Seller, seller_id=request.session['seller_id'])
    product = get_object_or_404(Product, product_id=product_id, seller=seller)
    if request.method == 'POST':
        d = request.POST
        product.product_name=d['product_name']; product.category=d['category']
        product.price=d['price']; product.description=d.get('description','')
        product.manufacturing_date=d.get('manufacturing_date') or None
        product.expiry_date=d.get('expiry_date') or None
        product.stock_quantity=int(d['stock_quantity'])
        if request.FILES.get('product_image'): product.product_image=request.FILES['product_image']
        product.save()
        StockAlert.objects.filter(product=product, is_resolved=False).update(is_resolved=True)
        messages.success(request, 'Product updated!')
        return redirect('seller_products')
    return render(request, 'seller/product_form.html', {
        'seller': seller, 'product': product,
        'categories': CATEGORY_CHOICES, 'edit': True,
    })


def product_delete(request, product_id):
    if not request.session.get('seller_id') or request.session.get('role') != 'seller':
        return redirect('seller_login')
    seller  = get_object_or_404(Seller, seller_id=request.session['seller_id'])
    product = get_object_or_404(Product, product_id=product_id, seller=seller)
    product.is_active = False; product.save()
    messages.success(request, f'"{product.product_name}" removed from listing.')
    return redirect('seller_products')


def seller_orders(request):
    if not request.session.get('seller_id') or request.session.get('role') != 'seller':
        return redirect('seller_login')
    seller = get_object_or_404(Seller, seller_id=request.session['seller_id'])
    orders = Order.objects.filter(items__product__seller=seller).distinct().order_by('-order_date')
    return render(request, 'seller/orders.html', {'seller': seller, 'orders': orders})


def update_order_status(request, order_id):
    if not request.session.get('seller_id') or request.session.get('role') != 'seller':
        return redirect('seller_login')
    order = get_object_or_404(Order, order_id=order_id)
    if request.method == 'POST':
        status = request.POST.get('status')
        if status in ['Placed','Confirmed','Shipped','Out for Delivery','Delivered','Cancelled']:
            order.order_status = status
            if status == 'Delivered': order.payment_status = 'Paid'
            order.save()
            messages.success(request, f'Order status updated to "{status}".')
    return redirect('seller_orders')


def seller_profile(request):
    if not request.session.get('seller_id') or request.session.get('role') != 'seller':
        return redirect('seller_login')
    seller = get_object_or_404(Seller, seller_id=request.session['seller_id'])
    if request.method == 'POST':
        d = request.POST
        seller.name=d['name']; seller.phone_number=d['phone_number']
        seller.address_line=d['address_line']; seller.district=d['district']
        seller.state=d['state']; seller.pincode=d['pincode']; seller.save()
        request.session['seller_name'] = seller.name
        messages.success(request, 'Profile updated!')
        return redirect('seller_dashboard')
    return render(request, 'seller/profile.html', {'seller': seller})


# ═══════════════════════════════════════════════════════════════
# SELLER ORDER REQUESTS — Accept / Reject / Ship
# ═══════════════════════════════════════════════════════════════

def _get_seller(request):
    sid = request.session.get('seller_id')
    if sid:
        try:
            return Seller.objects.get(seller_id=sid, is_active=True)
        except Seller.DoesNotExist:
            pass
    return None


def seller_order_requests(request):
    """Main page — shows all order requests to this seller"""
    seller = _get_seller(request)
    if not seller:
        return redirect('seller_login')

    from .models import SellerOrderRequest
    status_filter = request.GET.get('status', 'all')

    requests_qs = SellerOrderRequest.objects.filter(
        seller=seller
    ).select_related('order', 'order__user', 'order_item', 'order_item__product')

    if status_filter != 'all':
        requests_qs = requests_qs.filter(status=status_filter)

    counts = {
        'all':      SellerOrderRequest.objects.filter(seller=seller).count(),
        'pending':  SellerOrderRequest.objects.filter(seller=seller, status='pending').count(),
        'accepted': SellerOrderRequest.objects.filter(seller=seller, status='accepted').count(),
        'shipped':  SellerOrderRequest.objects.filter(seller=seller, status='shipped').count(),
        'delivered':SellerOrderRequest.objects.filter(seller=seller, status='delivered').count(),
        'rejected': SellerOrderRequest.objects.filter(seller=seller, status='rejected').count(),
    }

    from .models import DELIVERY_PARTNERS
    return render(request, 'seller/order_requests.html', {
        'seller': seller,
        'requests': requests_qs,
        'status_filter': status_filter,
        'counts': counts,
        'delivery_partners': DELIVERY_PARTNERS,
        'request_statuses': [
            ('all',      'All Orders'),
            ('pending',  '⏳ Pending'),
            ('accepted', '✅ Accepted'),
            ('shipped',  '🚚 Shipped'),
            ('delivered','📦 Delivered'),
            ('rejected', '❌ Rejected'),
        ],
    })


def accept_order_request(request, req_id):
    """Seller accepts a request"""
    seller = _get_seller(request)
    if not seller:
        return redirect('seller_login')

    from .models import SellerOrderRequest
    from django.http import JsonResponse

    try:
        req = SellerOrderRequest.objects.get(id=req_id, seller=seller, status='pending')
        req.status = 'accepted'
        req.accepted_at = timezone.now()
        req.save()
        # Update main order status
        req.order.order_status = 'Confirmed'
        req.order.save(update_fields=['order_status'])
        return JsonResponse({'success': True, 'message': 'Order accepted! Please choose delivery partner and ship.'})
    except SellerOrderRequest.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Request not found.'})


def reject_order_request(request, req_id):
    """Seller rejects a request"""
    seller = _get_seller(request)
    if not seller:
        return redirect('seller_login')

    from .models import SellerOrderRequest
    from django.http import JsonResponse
    import json

    data = json.loads(request.body)
    reason = data.get('reason', 'Seller rejected the order.')

    try:
        req = SellerOrderRequest.objects.get(id=req_id, seller=seller, status='pending')
        req.status = 'rejected'
        req.rejection_reason = reason
        req.save()
        # Restore stock
        product = req.order_item.product
        product.stock_quantity += req.order_item.quantity
        product.save(update_fields=['stock_quantity'])
        # Update order status
        req.order.order_status = 'Cancelled'
        req.order.save(update_fields=['order_status'])
        return JsonResponse({'success': True, 'message': 'Order rejected and stock restored.'})
    except SellerOrderRequest.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Request not found.'})


def ship_order_request(request, req_id):
    """Seller selects delivery partner and marks as shipped"""
    seller = _get_seller(request)
    if not seller:
        return redirect('seller_login')

    from .models import SellerOrderRequest, DELIVERY_PARTNERS
    from django.http import JsonResponse
    import json, random, string

    data = json.loads(request.body)
    partner  = data.get('delivery_partner', '')
    valid_partners = [p[0] for p in DELIVERY_PARTNERS]

    if partner not in valid_partners:
        return JsonResponse({'success': False, 'error': 'Invalid delivery partner.'})

    try:
        req = SellerOrderRequest.objects.get(id=req_id, seller=seller, status='accepted')

        # Generate mock tracking ID
        tracking_id = partner.upper()[:3] + ''.join(random.choices(string.digits, k=10))

        req.status           = 'shipped'
        req.delivery_partner = partner
        req.tracking_id      = tracking_id
        req.shipped_at       = timezone.now()
        req.save()

        # Update order status to Shipped
        req.order.order_status = 'Shipped'
        req.order.save(update_fields=['order_status'])

        partner_name = dict(DELIVERY_PARTNERS).get(partner, partner)
        return JsonResponse({
            'success': True,
            'message': f'Shipped via {partner_name}!',
            'tracking_id': tracking_id,
            'partner_name': partner_name,
        })
    except SellerOrderRequest.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Request not found or not in accepted state.'})


def mark_delivered(request, req_id):
    """Mark order as delivered"""
    seller = _get_seller(request)
    if not seller:
        return redirect('seller_login')

    from .models import SellerOrderRequest
    from django.http import JsonResponse

    try:
        req = SellerOrderRequest.objects.get(id=req_id, seller=seller, status='shipped')
        req.status       = 'delivered'
        req.delivered_at = timezone.now()
        req.save()
        req.order.order_status = 'Delivered'
        req.order.payment_status = 'Paid'
        req.order.save(update_fields=['order_status', 'payment_status'])
        return JsonResponse({'success': True, 'message': 'Order marked as delivered!'})
    except SellerOrderRequest.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Request not found.'})
