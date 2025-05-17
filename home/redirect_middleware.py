from django.http import HttpResponsePermanentRedirect
from account.models import City, Dentist

class RedirectToNewUrl:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path.lower().strip('/')

        if path.startswith('best-dentist/'):
            city_slug = path.split('best-dentist/')[1].strip('/')
            try:
                # city = City.objects.get(city__iexact=city_slug.replace("-", " "))
                new_url = f'/certified-dentists/city/{city_slug}/'
                return HttpResponsePermanentRedirect(new_url)
            except City.DoesNotExist:
                pass  # Skip redirect if city doesn't exist

        if path.startswith('dentist/'):
            dentist_slug = path.split('dentist/')[1].strip('/')
            try:
                dentist = Dentist.objects.get(slug=dentist_slug)
                new_url = f'/certified-dentists/{dentist.slug}/'
                return HttpResponsePermanentRedirect(new_url)
            except Dentist.DoesNotExist:
                pass

        return self.get_response(request)