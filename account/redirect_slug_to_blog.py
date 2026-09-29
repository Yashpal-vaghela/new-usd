import re
from django.http import HttpResponsePermanentRedirect
from account.models import RedirectRule

class DynamicRedirectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # Exclude admin panel, static assets, and media files from dynamic redirection
        if path.startswith(('/admin/', '/static/', '/media/')):
            return self.get_response(request)

        full_path = request.get_full_path()
        stripped_path = path.strip('/')

        possible_old_urls = [
            full_path,
            path,
            stripped_path,
            f"/{stripped_path}",
            f"/{stripped_path}/",
            f"{stripped_path}/"
        ]

        try:
            active_redirects = RedirectRule.objects.filter(
                is_active=True,
                old_url__in=possible_old_urls
            )
            if active_redirects.exists():
                redirect_map = {r.old_url: r for r in active_redirects}
                redirect_obj = None
                for candidate in possible_old_urls:
                    if candidate in redirect_map:
                        redirect_obj = redirect_map[candidate]
                        break

                if redirect_obj:
                    target_url = redirect_obj.new_url.strip()
                    if not (target_url.startswith('http://') or target_url.startswith('https://') or target_url.startswith('/')):
                        target_url = '/' + target_url

                    # Avoid infinite redirect loop
                    if target_url != full_path and target_url != path and target_url != stripped_path and target_url != f"/{stripped_path}/":
                        return HttpResponsePermanentRedirect(target_url)
        except Exception:
            pass

        return self.get_response(request)