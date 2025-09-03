from functools import wraps
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required as django_login_required

def login_required(view_func=None):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            if request.path.startswith('/patient/'):
                return redirect(f'/patient/login/?next={request.path}')
            elif request.path.startswith('/doctor/'):
                return redirect(f'/doctor/login/?next={request.path}')
            else:
                return redirect('/')
        return view_func(request, *args, **kwargs)
    return _wrapped_view