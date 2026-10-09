def shell_context(request):
    if not request.user.is_authenticated:
        return {}
    data = {
        'shell_unread_notifications': request.user.notifications.filter(is_read=False).count() if hasattr(request.user, 'notifications') else 0,
        'shell_active_timer': None,
    }
    try:
        from timetracking.services import active_timer_for_user
        data['shell_active_timer'] = active_timer_for_user(request.user)
    except Exception:
        # During a first migration timetracking tables may not exist yet.
        pass
    return data
