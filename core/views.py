from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import admin_required

from .models import SiteMessage


@login_required
def home(request):
    return render(request, 'core/home.html')


@admin_required
def message_list(request):
    managed_messages = SiteMessage.objects.order_by('-updated_at')
    return render(request, 'core/message_list.html', {'managed_messages': managed_messages})


@admin_required
def message_create(request):
    if request.method == 'POST':
        msg_text = request.POST.get('message', '').strip()
        msg_type = request.POST.get('message_type', SiteMessage.MessageType.INFO)
        is_active = request.POST.get('is_active') == 'on'
        if msg_text:
            SiteMessage.objects.create(message=msg_text, message_type=msg_type, is_active=is_active)
            messages.success(request, 'Message created.')
            return redirect('message_list')
    return render(request, 'core/message_form.html', {
        'form_title': 'New Message',
        'submit_label': 'Create message',
        'message_types': SiteMessage.MessageType.choices,
    })


@admin_required
def message_edit(request, pk):
    site_message = get_object_or_404(SiteMessage, pk=pk)
    if request.method == 'POST':
        msg_text = request.POST.get('message', '').strip()
        msg_type = request.POST.get('message_type', SiteMessage.MessageType.INFO)
        is_active = request.POST.get('is_active') == 'on'
        if msg_text:
            site_message.message = msg_text
            site_message.message_type = msg_type
            site_message.is_active = is_active
            site_message.save()
            messages.success(request, 'Message updated.')
            return redirect('message_list')
    return render(request, 'core/message_form.html', {
        'form_title': 'Edit Message',
        'submit_label': 'Save changes',
        'site_message': site_message,
        'message_types': SiteMessage.MessageType.choices,
    })


@admin_required
def message_toggle(request, pk):
    if request.method == 'POST':
        site_message = get_object_or_404(SiteMessage, pk=pk)
        site_message.is_active = not site_message.is_active
        site_message.save(update_fields=['is_active'])
        state = 'activated' if site_message.is_active else 'deactivated'
        messages.success(request, f'Message {state}.')
    return redirect('message_list')


@admin_required
def message_delete(request, pk):
    if request.method == 'POST':
        site_message = get_object_or_404(SiteMessage, pk=pk)
        site_message.delete()
        messages.success(request, 'Message deleted.')
    return redirect('message_list')
