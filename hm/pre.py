import logging
import requests
from django.http import JsonResponse
from account.models import *


def get_location_info(request):
    # Retrieve latitude and longitude from session
    latitude = request.session.get('latitude')
    longitude = request.session.get('longitude')
    city = request.session.get('city', '')
    state = request.session.get('state', '')

    # Check if city and state are already in session
    if not city or not state:
        if latitude and longitude:
            try:
                # API call to get city and state
                api_key = 'AIzaSyCt-tUmu2yiONLVm0Bk4l0enFYFUJ3wbaI'
                url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={latitude},{longitude}&sensor=true&key={api_key}"
                
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    results = data.get('results', [])
                    
                    if results:
                        for component in results[0].get('address_components', []):
                            types = component.get('types', [])
                            if 'administrative_area_level_3' in types and not city:
                                city = component.get('long_name')
                            if 'administrative_area_level_1' in types and not state:
                                state = component.get('long_name')

                        # Store city and state in session
                        request.session['city'] = city
                        request.session['state'] = state
            except Exception as e:
                logging.warning(f"Reverse geocoding failed: {e}")
                # fallback values
                city = ''
                state = '' 

    # Always return a dictionary
    return {
        'city': city or 'unknown',
        'state': state or 'unknown',
    }


def allpage(request):
    a_city = City.objects.all().order_by('city') 

    context = {
        'a_city':a_city,
    }

    return context