from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect, render

from .decorators import admin_required
from .forms import UserCreateForm, UserEditForm

User = get_user_model()


@admin_required
def user_list(request):
    role_filter = request.GET.get('role', '')
    users = User.objects.all()
    if role_filter in User.Role.values:
        users = users.filter(role=role_filter)
    return render(request, 'accounts/user_list.html', {
        'users': users,
        'role_filter': role_filter,
        'roles': User.Role,
    })


@admin_required
def user_create(request):
    form = UserCreateForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'User created successfully.')
        return redirect('accounts:user_list')
    return render(request, 'accounts/user_form.html', {
        'form': form,
        'form_title': 'Create User',
        'submit_label': 'Create user',
    })


@admin_required
def user_edit(request, pk):
    edited_user = get_object_or_404(User, pk=pk)
    form = UserEditForm(request.POST or None, instance=edited_user)
    if form.is_valid():
        form.save()
        messages.success(request, f'{edited_user} updated successfully.')
        return redirect('accounts:user_list')
    return render(request, 'accounts/user_form.html', {
        'form': form,
        'edited_user': edited_user,
        'form_title': f'Edit {edited_user}',
        'submit_label': 'Save changes',
    })


@admin_required
def user_deactivate(request, pk):
    if request.method != 'POST':
        return redirect('accounts:user_list')
    edited_user = get_object_or_404(User, pk=pk)
    if edited_user == request.user:
        messages.error(request, 'You cannot deactivate your own account.')
        return redirect('accounts:user_list')
    edited_user.is_active = False
    edited_user.save(update_fields=['is_active'])
    messages.success(request, f'{edited_user} has been deactivated.')
    return redirect('accounts:user_list')
