from django.shortcuts import render, redirect ,get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.http import HttpResponseRedirect, Http404
from django.urls import reverse
from django.contrib import messages
from django.conf import settings
from django.contrib.auth.models import User
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from account.models import *
from home.forms import ContactForm, DentistConnectForm
from django.db.models import Q
from django.core.paginator import Paginator
from hm.pre import get_location_info
from geopy.distance import geodesic
from home.forms import UserSubmissionForm
import re
import requests
@csrf_exempt  # This bypasses CSRF protection for demonstration purposes only
def receive_location(request):
    if request.method == 'POST':
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')

        if latitude and longitude:  
            # Store latitude and longitude in session
            request.session['latitude'] = float(latitude)
            request.session['longitude'] = float(longitude)

            context = get_location_info(request)
            city = context.get('city', 'unknown')
            state = context.get('state', 'unknown')
            return JsonResponse({
                'status': 'success',
                'latitude': latitude,
                'longitude': longitude,
                'city': city,
                'state': state
            })
    
    return JsonResponse({'status': 'error'}, status=400)



# Create your views here.
def home(request):
    data1 = City.objects.all()[:10]
    dentist = Dentist.objects.all().order_by("?")[:6]
    gallery = Gallery.objects.all().order_by("?")
    cities = City.objects.all()
    
    city_id = request.GET.get('city', '').strip()
    query = request.GET.get('q', '').strip()
    data1 = Dentist.objects.all().order_by('name')  # Default queryset
    search_message = None
    city_name = city.city if 'city' in locals() and city else 'Surat'
    query = request.GET.get("q",'').strip()
    # mix filter doctor name or clinic name
    # if request.headers.get('x-requested-with') == 'XMLHttpRequest':
    #     results = []
    #     if query:
    #         matching_doctor = Dentist.objects.filter(Q(name__icontains=query) | Q(clinic_name__icontains=query)).distinct()[:5]
    #         print("matching_doctor",matching_doctor)
    #         results = [{'name': dentist.name, 'id': dentist.id, 'slug': dentist.slug ,'clinic_name':dentist.clinic_name} for dentist in matching_doctor]
    #     return JsonResponse({'results': results})
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        suggestion = []
        if query:
            # search doctors by name
            doctor_matches = Dentist.objects.filter(name__icontains=query)

            # search clinices by clinic name
            clinic_matches = Dentist.objects.filter(clinic_name__icontains=query)

            # Perpare response
            for doc in doctor_matches:
                suggestion.append({
                    'type':"dentist",
                    'id':doc.id,
                    'name':doc.name,
                    'slug':doc.slug
                })
            
            for clinic in clinic_matches:
                suggestion.append({
                    "type": "clinic",
                    "id": clinic.id,
                    "clinic_name": clinic.clinic_name,
                    "slug": clinic.slug
                })
            return JsonResponse(suggestion, safe=False)


    reviews = [
        {id:1,'doctor_name':'Dr. Priyanka Sharma','review':"I never imagined my smile could look this great. The entire process was smooth and tailored to my needs. I'm so grateful to the team and my smile designer!"},
        {id:2,'doctor_name':'Dr. Anjali Mehta','review':'My experience was beyond my expectations. The attention to detail and personalized care I received was truly outstanding. Highly recommend!'},
        {id:3,'doctor_name':'Dr. Rahul Kumar','review':"The transformation has been incredible. I feel more confident and love my new smile. Thank you to my dentist for such an amazing experience!"},
        {id:4,'doctor_name':'Dr. Ankita V','review':"I had the pleasure of working with Advance Dental Lab for over 8 years. It is such a joy to have a lab that can provide helpful and successful alternative options for extremely difficult cases and export level quality . Ultimate smile Designing is best. Support Digital dentistry . They have skilled technicians to provide Fast work. Ultimate smile designer"},
        {id:5,'doctor_name':'Dr. Manali Rajyguru','review':'The bestest lab i have worked with in my 14years of practice.  each n every crown they deliver is perfect. no adjustments no high points.support team is also best.  Anilbhai gives humble ans anytime u call.scan facilities they started is best thing. vishalbhai provide good service always on time and finishes scan within 10 to 15 mins.overall satisfied with all the work n services.'}
    ]

    # Check for city in request; if not found, check session
    if not city_id:
            try:
                city = City.objects.get(city__iexact='Surat')
                data1 = data1.filter(city=city)
            except City.DoesNotExist:
                search_message = f"No Ultimate Designers Found in Surat."

    else:
        # Filter by city from request
        city = get_object_or_404(City, id=city_id)
        data1 = data1.filter(city=city)

    # Filter by search query if provided
    if query:
        data1 = data1.filter(name__icontains=query)

    # Check if the query returned results
    if not data1.exists():
        search_message = "No Ultimate Designers Found Based On Your Query."

    data = data1[:3] 

    context = {
      'data1':data1,
      'dentist':dentist,
      'gallery':gallery,
      'cities': cities,
      'data': data,
      'search_message': search_message,
      'query': query,
      'city': city_id or request.session.get('city'),
      'review': reviews,
      'city_name': city_name,
    }
    return render(request, 'index.html', context)

def location_view(request):
    data1 = City.objects.all()[:10]
    return render(request, 'location.html', {'data1': data1})


def smile_step(request):
    gallery = Gallery.objects.all().order_by("?")
    return render(request, 'smile_step.html', {'gallery':gallery,})

def search_all_usd(request, city_name=None):
    city = None
    query = request.GET.get('q', '').strip()
    
    # AJAX search (for autocomplete or live suggestions)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        suggestion = []
        if query:
            # search doctors by name
            doctor_matches = Dentist.objects.filter(name__icontains=query)

            # search clinices by clinic name
            clinic_matches = Dentist.objects.filter(clinic_name__icontains=query)

            # matching_doctor = Dentist.objects.filter(Q(name__icontains=query)).distinct()[:5]
            # results = [{'name': dentist.name, 'id': dentist.id, 'slug': dentist.slug} for dentist in matching_doctor]
          # Perpare response
            for doc in doctor_matches:
                suggestion.append({
                    'type':"dentist",
                    'id':doc.id,
                    'name':doc.name,
                    'slug':doc.slug
                })
            
            for clinic in clinic_matches:
                suggestion.append({
                    "type": "clinic",
                    "id": clinic.id,
                    "clinic_name": clinic.clinic_name,
                    "slug": clinic.slug
                })
        return JsonResponse(suggestion, safe=False)

    city_id = request.GET.get('city', '').strip()
    data1 = Dentist.objects.all().order_by('name')
    search_message = None

    user_latitude = request.session.get('latitude')
    user_longitude = request.session.get('longitude')

    # Try casting session coordinates to float
    try:
        if user_latitude and user_longitude:
            user_latitude = float(user_latitude)
            user_longitude = float(user_longitude)
        else:
            user_latitude = user_longitude = None
    except ValueError:
        user_latitude = user_longitude = None

    # Location filtering by city
    if city_id:
        city = get_object_or_404(City, id=city_id)
        data1 = data1.filter(city=city)
        city_name = city.city
    elif city_name:
        try:
            city = City.objects.get(city__iexact=city_name.replace("-", " "))
            data1 = data1.filter(city=city)
        except City.DoesNotExist:
            search_message = f"No Ultimate Designers Found in {city_name}."
    else:
        session_city = request.session.get('city')
        if session_city:
            try:
                city = City.objects.get(city=session_city)
                data1 = data1.filter(city=city)
                city_name = city.city
            except City.DoesNotExist:
                search_message = f"No Ultimate Designers Found in {session_city}."
        else:
            search_message = "No city selected."

    # Location-based sorting using dentist.lat and dentist.long
    if user_latitude and user_longitude:
        doctors_with_location = []
        doctors_without_location = []

        for doctor in data1:
            if doctor.lat is not None and doctor.long is not None:
                try:
                    doctor_distance = geodesic(
                        (user_latitude, user_longitude), 
                        (doctor.lat, doctor.long)
                    ).km
                    doctors_with_location.append((doctor_distance, doctor))
                except Exception:
                    doctors_without_location.append(doctor)
            else:
                doctors_without_location.append(doctor)

        doctors_with_location.sort(key=lambda x: x[0])
        sorted_doctors = [doc for _, doc in doctors_with_location] + doctors_without_location
    else:
        sorted_doctors = list(data1)

    # Apply name search filter
    if query:
        sorted_doctors = data1.filter(name__icontains=query)

    # Fallback to nearest city with dentists if current city has no data
    if not data1.exists() and city and city.latitude and city.longitude:
        user_location = (city.latitude, city.longitude)

        nearby_cities = City.objects.exclude(id=city.id).exclude(latitude__isnull=True, longitude__isnull=True)

        nearby_city_distances = []
        for c in nearby_cities:
            if Dentist.objects.filter(city=c).exists():
                dist = geodesic(user_location, (c.latitude, c.longitude)).km
                nearby_city_distances.append((dist, c))

        nearby_city_distances.sort(key=lambda x: x[0])

        if nearby_city_distances:
            nearest_city = nearby_city_distances[0][1]
            city = nearest_city
            city_name = nearest_city.city
            data1 = Dentist.objects.filter(city=nearest_city)
            sorted_doctors = list(data1)
            search_message = (
                f"No Ultimate Designers Found in {user_location[0]}, {user_location[1]}. "
                f"Showing nearest city: {nearest_city.city}, {nearest_city.state}."
            )
        else:
            search_message = "No Ultimate Designers Found Nearby."

    # Pagination
    paginator = Paginator(sorted_doctors, 12)
    page = request.GET.get('page', 1)
    try:
        data = paginator.page(page)
    except PageNotAnInteger:
        data = paginator.page(1)
    except EmptyPage:
        data = paginator.page(paginator.num_pages)

    context = {
        'sorted_doctors': sorted_doctors,
        'data': data,
        'search_message': search_message,
        'query': query,
        'city': city.city if city else 'all',
        'city_id': city.id if city else '',
        'total': len(data),
        'city_name': city_name,
    }

    return render(request, 'list.html', context)


def search_city_dentists(request, city_name):
    """
    Displays the list of dentists specific to a given city using city-dentist.html template.
    """

    query = request.GET.get('q', '').strip()
    user_latitude = request.session.get('latitude')
    user_longitude = request.session.get('longitude')

    city = None
    search_message = None

    try:
        city = City.objects.get(city__iexact=city_name.replace("-", " "))
        data1 = Dentist.objects.filter(city=city).order_by('name')
    except City.DoesNotExist:
        data1 = Dentist.objects.none()
        search_message = f"No Ultimate Designers Found in {city_name}."

    # Location-based sorting if available
    if user_latitude and user_longitude:
        doctors_with_location = []
        doctors_without_location = []

        for doctor in data1:
            if doctor.iframe:
                match = re.search(r"!2d(-?\d+\.\d+)!3d(-?\d+\.\d+)", doctor.iframe)
                if match:
                    doctor_longitude = float(match.group(1))
                    doctor_latitude = float(match.group(2))
                    distance = geodesic((user_latitude, user_longitude), (doctor_latitude, doctor_longitude)).km
                    doctors_with_location.append((distance, doctor))
                else:
                    doctors_without_location.append(doctor)
            else:
                doctors_without_location.append(doctor)

        doctors_with_location.sort(key=lambda x: x[0])
        sorted_doctors = [doc for _, doc in doctors_with_location] + doctors_without_location
    else:
        sorted_doctors = list(data1)

    # Apply search query if provided
    if query:
        sorted_doctors = [doc for doc in sorted_doctors if query.lower() in doc.name.lower()]

    if not data1.exists():
        search_message = f"No Ultimate Designers Found in {city.city if city else city_name}."

    paginator = Paginator(sorted_doctors, 12)
    page = request.GET.get('page', 1)

    try:
        data = paginator.page(page)
    except PageNotAnInteger:
        data = paginator.page(1)
    except EmptyPage:
        data = paginator.page(paginator.num_pages)

    context = {
        'data': data,
        'city': city.city if city else city_name,
        'city_name': city_name,
        'query': query,
        'search_message': search_message,
    }

    return render(request, 'city-dentist.html', context)


def all_usd(request):
    """
    Displays all dentists without filtering, with pagination.
    If a city exists in the session, filters dentists by that city.
    """
    city_name = request.session.get('city', '')
    data1 = Dentist.objects.all().order_by('name')  # Default queryset

    if city_name:
        try:
            city = City.objects.get(city=city_name)
            data1 = data1.filter(city=city)
        except City.DoesNotExist:
            pass  # If city doesn't exist, show all dentists

    paginator = Paginator(data1, 32)  # 32 dentists per page
    page = request.GET.get('page', 1)

    try:
        data = paginator.page(page)
    except PageNotAnInteger:
        data = paginator.page(1)
    except EmptyPage:
        data = paginator.page(paginator.num_pages)

    context = {
        'data': data,
    }
    return render(request, 'list.html', context)

# def find_dentist(request):
#     """
#     Displays dentists for the city stored in the session.
#     If no city is found in the session, shows all dentists.
#     """
#     city_name = request.GET.get('city') or request.session.get('city', '')
#     data1 = Dentist.objects.all().order_by('name')  # Default queryset
#     search_message = None

#     if city_name:
#         try:
#             city = City.objects.get(city=city_name)
#             data1 = Dentist.objects.filter(city=city).order_by('name')
#         except City.DoesNotExist:
#             search_message = f"No Ultimate Designers Found in {city_name}."
#             data1 = Dentist.objects.all().order_by('name')
#     print("dentist",data1,"data",data)
    
#     # Pagination
#     paginator = Paginator(data1, 6)  # 12 dentists per page
#     page = request.GET.get('page', 1)

#     try:
#         data = paginator.page(page)
#     except PageNotAnInteger:
#         data = paginator.page(1)
#     except EmptyPage:
#         data = paginator.page(paginator.num_pages)

#     context = {
#         'data': data,
#         'search_message': search_message,
#         'city_name': city_name,
#     }
#     return render(request, 'list.html', context)

def find_dentist_d(request, pk):
    try:
        # Try to get Dentist by slug
        data = Dentist.objects.get(slug=pk)
    except Dentist.DoesNotExist:
        # If not found, check DentistRedirect
        redirect_entry = get_object_or_404(DentistRedirect, old_slug=pk)
        city = redirect_entry.city  

        # Check if city still has active dentists
        if Dentist.objects.filter(city=city).exists():
            city_name = city.city  # <-- using City model's "city" field
            return redirect(f"/certified-dentists/city/{city_name}/", permanent=True)
        else:
            # No dentists in this city → fallback to main certified dentists page
            return redirect("/certified-dentists/", permanent=True)

    gallery = Gallery.objects.all().order_by("?")[:10]
    reviews = data.reviews.all().order_by('-created_at')
    query = request.GET.get("q", '').strip()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        suggestion = []
        if query:
            doctor_matches = Dentist.objects.filter(name__icontains=query)
            clinic_matches = Dentist.objects.filter(clinic_name__icontains=query)

            for doc in doctor_matches:
                suggestion.append({
                    'type': "dentist",
                    "id": doc.id,
                    'name': doc.name,
                    'slug': doc.slug
                })
            for clinic in clinic_matches:
                suggestion.append({
                    "type": "clinic",
                    "id": clinic.id,
                    "clinic_name": clinic.clinic_name,
                    "slug": clinic.slug
                })

            return JsonResponse(suggestion, safe=False)

    context = {
        'data': data,
        'gallery': gallery,
        'reviews': reviews,
    }
    return render(request, 'detail.html', context)

def gallery(request):
    data = Gallery.objects.all().order_by("?")
    data1 = Hgallery.objects.all().order_by("?")
    context = {
        'data':data,
        'data1':data1,
        
    }
    return render(request, 'gallery.html', context)

def blogs(request):
    all_blogs = Blog.objects.all().order_by('-published')  # Fetch all blogs
    first_blog = all_blogs.first()
    remaining_blogs = all_blogs[1:]
    paginator = Paginator(remaining_blogs, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'first_blog': first_blog,
        'page_obj': page_obj,
    }
    return render(request, 'blogs.html', context)
    # per_page = request.GET.get('per_page', 3)  # Default to the first page
    # try:
    #     per_page = int(per_page)
    # except ValueError:
    #     per_page = 3  # Default to page 1 if invalid

    # # Set per_page dynamically
    # blog_list = Blog.objects.all().order_by('-published') # Get all blogs sorted by published date
    # paginator = Paginator(blog_list, per_page)
    # page_number = request.GET.get('page')
    # page_obj = paginator.get_page(page_number)
    # current_blog = Blog.objects.all().order_by('-id')[:1]  # Get the latest blog

    # context = {
    #     'page_obj': page_obj,
    #     'current_blog': current_blog,
    #     'is_first_page': page_number == 1
    # }
    # return render(request, 'blogs.html', context)

def blogsd(request, pk):
    blog = Blog.objects.get(slug=pk)
    data2 = Blog.objects.all().order_by('-id')
    related_blog = Blog.objects.all().order_by('-id')[1:4]
    unique_tags = blog.tag.all()
    unique_categories = blog.category.all()
    
   
    context = {
     'cata':unique_categories,
     'blog':blog,
     'tags':unique_tags,
     'data2':data2,
     'relatedBlog':related_blog
    }
    # print("relatedBlog",related_blog)
    return render(request, 'blogsd.html', context)

def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)

        recaptcha_response = request.POST.get('g-recaptcha-response')
        data = {
            'secret': settings.RECAPTCHA_SECRET_KEY,
            'response': recaptcha_response,
        }
        r = requests.post("https://www.google.com/recaptcha/api/siteverify", data=data)  # <-- FIXED
        result = r.json()

        if not result.get('success'):
            messages.error(request, 'Invalid reCAPTCHA. Please try again.')
            return redirect(request.META.get('HTTP_REFERER','contact'))
        
        if form.is_valid():
            form.save()
            messages.success(request, 'Your data is sent successfully.')
            # return redirect('home:thankyou')
            full_name = request.POST.get("name", "").strip()
            first_name, last_name = (full_name.split(" ", 1) + [""])[:2]

            payload = {
                "firstName": first_name or "Visitor",
                "lastName": last_name,
                "designation": "",
                "email": request.POST.get("email", ""),
                "countryCode": "91",
                "mobile": request.POST.get("phone", ""),
                "phoneCountryCode": "91",
                "phone": request.POST.get("phone", ""),
                "expectedRevenue": "0",
                "description": request.POST.get("message", ""),
                "companyName": "",
                "companyState": "",
                "companyStreet": "",
                "companyCity": request.POST.get("city", ""),
                "companyCountry": "India",
                "companyPincode": "",
                "leadPriority": "1",
            }
            headers = {
                "Content-Type": "application/json",
                "authToken": "79atXvY2ZVZXs32Tbnw89A==.icG8H90dELRwyW3euMFdTg==", 
                "timeZone": "Asia/Calcutta",  
            }
            try:
                crm_response = requests.post(
                    "https://crm.my-company.app/api/v1/lead/webhook",
                    json=payload,
                    headers=headers,
                    timeout=10,
                )
                crm_response.raise_for_status()
                messages.success(
                    request,
                    "Thanks for contacting the Ultimate Smile Design Team. We will get back to you shortly."
                )
            except requests.exceptions.RequestException as e:
                messages.warning(request, f"Form saved but CRM sync failed: {str(e)}")

            return redirect('home:thankyou')
        else:
            messages.error(request, 'Your query is not sent! Try Again.')
            return redirect(request.META.get('HTTP_REFERER', 'contact'))

    context = {
        "RECAPTCHA_SITE_KEY": settings.RECAPTCHA_SITE_KEY
    }
    return render(request, 'contact.html', context)

def dentist_connect(request):
    if request.method == 'POST':
        form = DentistConnectForm(request.POST)

        recaptcha_response = request.POST.get('g-recaptcha-response')
        data = {
            'secret' : settings.RECAPTCHA_SECRET_KEY,
            'response' : recaptcha_response,     
        }
        r = requests.post("https://www.google.com/recaptcha/api/siteverify", data=data)
        result = r.json()

        if not result.get('success'):
            messages.error(request, 'Invalid reCAPTCHA. Please try again.')
            return redirect(request.META.get('HTTP_REFERER','dentist-connect'))
        
        if form.is_valid():
            form.save()
            messages.success(request, 'Your data has been submitted successfully!')
        
            # --- Prepare CRM Payload ---
            full_name = request.POST.get("name", "").strip()
            first_name, last_name = (full_name.split(" ", 1) + [""])[:2]

            payload = {
                "firstName": first_name or "Visitor",
                "lastName": last_name,
                "designation": request.POST.get("designation", ""),
                "email": request.POST.get("email", ""),
                "countryCode": "91",
                "mobile": request.POST.get("phone", ""),
                "phoneCountryCode": "91",
                "phone": request.POST.get("phone", ""),
                "expectedRevenue": "0",
                "description": request.POST.get("message", ""),
                "companyName": request.POST.get("clinic_name", ""),
                "companyState": request.POST.get("state", ""),
                "companyStreet": "",
                "companyCity": request.POST.get("city", ""),
                "companyCountry": "India",
                "companyPincode": "",
                "leadPriority": "1",
            }

            headers = {
                "Content-Type": "application/json",
                "authToken": "79atXvY2ZVZXs32Tbnw89A==.icG8H90dELRwyW3euMFdTg==", 
                "timeZone": "Asia/Calcutta",
            }

            # --- Send to CRM ---
            try:
                crm_response = requests.post(
                    "https://crm.my-company.app/api/v1/lead/webhook",
                    json=payload,
                    headers=headers,
                    timeout=10,
                )
                crm_response.raise_for_status()
                messages.success(
                    request,
                    "Thanks for connecting with Ultimate Smile Design. Our team will reach out shortly!"
                )
            except requests.exceptions.RequestException as e:
                messages.warning(request, f"Data saved but CRM sync failed: {str(e)}")

            return redirect('home:thankyou')
        
        else:
            messages.error(request, 'Something went wrong! Please try again.')
            return redirect(request.META.get('HTTP_REFERER', 'dentist-connect'))
    context = {
        "RECAPTCHA_SITE_KEY": settings.RECAPTCHA_SITE_KEY
    }
    return render(request, 'dentist-connect.html', context)

def sitemap(request):
    return render(request, 'sitemap.xml', content_type='text/xml')

#end
def robots(request):
    return render(request, 'robots.txt', content_type='text')   
    
def thankyou(request):
    return render(request, 'pthankyou.html')

def dentist(request):
    if request.method == 'POST':
        form = UserSubmissionForm(request.POST)

        # reCAPTCHA validation
        recaptcha_response = request.POST.get('g-recaptcha-response')
        data = {
            "secret": settings.RECAPTCHA_SECRET_KEY,
            "response": recaptcha_response,
        }
        r = requests.post("https://www.google.com/recaptcha/api/siteverify", data=data)
        result = r.json()

        if not result.get("success"):
            messages.error(request, "Invalid reCAPTCHA. Please try again.")
            return redirect(request.META.get("HTTP_REFERER", "dentist"))

        if form.is_valid():
            user_submission = form.save()  # doctor_name is handled by form
            messages.success(
                request,
                f"Form submitted successfully! Thank you, {user_submission.first_name} {user_submission.last_name}."
            )
            form = UserSubmissionForm()
            return redirect('home:thankyou')
        else:
            messages.error(request, "Something went wrong! Please check your details.")
            return render(
                request,
                'request.html',
                {'form': form, 'error_message': 'Please correct the errors below.'}
            )
    else:
        form = UserSubmissionForm()

    return render(request, 'request.html', {'form': form})
