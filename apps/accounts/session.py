"""Session helpers: who is logged in, and the ``login_required`` guard."""
from functools import wraps

from django.http import JsonResponse
from django.shortcuts import redirect

SESSION_KEY = "mraya_user"


def login_user(request, uid, email="", name="", picture="", gender=""):
    request.session.cycle_key()
    request.session[SESSION_KEY] = {
        "uid": uid, "email": email, "name": name, "picture": picture, "gender": gender,
    }


def logout_user(request):
    request.session.flush()


def current_user(request):
    return request.session.get(SESSION_KEY)


def login_required(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        user = current_user(request)
        if not user:
            if request.headers.get("Accept", "").startswith("application/json"):
                return JsonResponse({"error": "Not signed in"}, status=401)
            return redirect("accounts:login")
        request.mraya_user = user
        return view(request, *args, **kwargs)

    return wrapper
