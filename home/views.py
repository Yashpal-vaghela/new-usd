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
from django.db.models import Count,Q
from django.core.paginator import Paginator
from hm.pre import get_location_info
from geopy.distance import geodesic
from home.forms import UserSubmissionForm
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string
from .utils import send_mail
import re
import requests
import random
import threading
from django.utils import timezone

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

def send_contact_email_async(context_dict):
    send_mail(
        to_email="vaghela9632@gmail.com",  # company email
        subject=f"New Contact Form Submission from {context_dict['Name']}",
        context_dict=context_dict
    )

# Create your views here.
def home(request):
    # data1 = City.objects.all()[:10]
    dentist = Dentist.objects.all().order_by("?")[:6]
    gallery = Gallery.objects.all().order_by("?")
    cities = City.objects.annotate(
        countdr=Count('dentist', filter=Q(dentist__status=True))
    ).filter(countdr__gt=0).order_by('-countdr')[:6]
    a_city = City.objects.annotate(
        active_dentist_count=Count('dentist', filter=Q(dentist__status=True))
    ).filter(active_dentist_count__gt=0).order_by('city')
    city_id = request.GET.get('city', '').strip()
    query = request.GET.get('q', '').strip()
    data1 = Dentist.objects.filter(status=True).order_by('name')
    search_message = None
    city_name = city.city if 'city' in locals() and city else 'Surat'
    query = request.GET.get("q",'').strip()
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

    context = {
      'data1':data1,
      'gallery':gallery,
      'cities': cities,
      'search_message': search_message,
      'query': query,
      'city': city_id or request.session.get('city'),
      'review': reviews,      
      'city_name': city_name,
      'a_city': a_city,
    }
    return render(request, 'index.html', context)
# def home(request):
#     # REMOVE CITY FILTER → load ALL dentists
#     data1 = Dentist.objects.all().order_by('name')
#     gallery = Gallery.objects.all().order_by("?")
#     cities = City.objects.annotate(
#         dentist_count=Count('dentist')
#     ).filter(dentist_count__gt=0).order_by('-dentist_count')[:6]
#     city_id = request.GET.get('city', '').strip()
#     query = request.GET.get("q", '').strip()
#     search_message = None
#     # DEFAULT CITY NAME (for UI only, not filtering)
#     city_name = "Surat"
#     # AJAX suggestions
#     if request.headers.get('x-requested-with') == 'XMLHttpRequest':
#         suggestion = []
#         if query:
#             # Search doctors by name
#             doctor_matches = Dentist.objects.filter(name__icontains=query)
#             # Search clinics by clinic name
#             clinic_matches = Dentist.objects.filter(clinic_name__icontains=query)
#             # Prepare response
#             for doc in doctor_matches:
#                 suggestion.append({
#                     'type': "dentist",
#                     'id': doc.id,
#                     'name': doc.name,
#                     'slug': doc.slug
#                 })
#             for clinic in clinic_matches:
#                 suggestion.append({
#                     "type": "clinic",
#                     "id": clinic.id,
#                     "clinic_name": clinic.clinic_name,
#                     "slug": clinic.slug
#                 })
#         return JsonResponse(suggestion, safe=False)
#     # SEARCH FILTER (dentist name only)
#     if query:
#         data1 = data1.filter(name__icontains=query)
#     # Show search message only if search applied
#     if query and not data1.exists():
#         search_message = "No Ultimate Designers Found Based On Your Query."
#     reviews = [
#         {id:1,'doctor_name':'Dr. Priyanka Sharma','review':"I never imagined my smile could look this great. The entire process was smooth and tailored to my needs. I'm so grateful to the team and my smile designer!"},
#         {id:2,'doctor_name':'Dr. Anjali Mehta','review':'My experience was beyond my expectations. The attention to detail and personalized care I received was truly outstanding. Highly recommend!'},
#         {id:3,'doctor_name':'Dr. Rahul Kumar','review':"The transformation has been incredible. I feel more confident and love my new smile. Thank you to my dentist for such an amazing experience!"},
#         {id:4,'doctor_name':'Dr. Ankita V','review':"I had the pleasure of working with Advance Dental Lab for over 8 years. It is such a joy to have a lab that can provide helpful and successful alternative options for extremely difficult cases and export level quality . Ultimate smile Designing is best. Support Digital dentistry . They have skilled technicians to provide Fast work. Ultimate smile designer"},
#         {id:5,'doctor_name':'Dr. Manali Rajyguru','review':'The bestest lab i have worked with in my 14years of practice. each n every crown they deliver is perfect. no adjustments no high points.support team is also best. Anilbhai gives humble ans anytime u call.scan facilities they started is best thing. vishalbhai provide good service always on time and finishes scan within 10 to 15 mins.overall satisfied with all the work n services.'}
#     ]
#     data1_list = [
#         { id:1,'doctor_name':'Dr. M Jaydev','city':'Hyderabad','image':"/media/SEO/Group_1000006053.png","slug":"dr-m-jaydev"},
#         { id:2,'doctor_name':'Dr. Janu Shah','city':'Ahmedabad','image':"/media/SEO/Group_1000006035.png","slug":"dr-janu-shah"},
#         { id:3,'doctor_name':'Dr. Alap D shah','city':'Ahmedabad','image':"/media/SEO/Group 1000006082.png","slug":"dr-alap-d-shah"},
#         { id:4,'doctor_name':'Dr. Moez Khakiani','city':'Mumbai','image':"/media/SEO/Group_1000006056.png","slug":"dr-moez-khakiani"},
#         { id:5,'doctor_name':'Dr. Abbas Noorani','city':'Ahmedabad','image':"/media/SEO/Group_1000006033.png","slug":"dr-abbas-noorani"},
#             # { id:6,'doctor_name':'Dr. Neerav Jhaveni','city':'Hyderabad','image':"/media/SEO/Group_1000006053.png"},
#         { id:7,'doctor_name':'Dr. Nitesh Motwani','city':'Mumbai','image':"/media/SEO/Group_1000006064.png","slug":"dr-nitesh-motwani"},
#             # { id:8,'doctor_name':'Dr. Janu Shah','city':'Ahmedabad','image':"/media/SEO/Group_1000006035.png"},
#             # { id:9,'doctor_name':'Dr. Pathik Patel','city':'Hyderabad','image':"/media/SEO/Group_1000006053.png"},
#         { id:10,'doctor_name':'Dr. Praneeth Kumar','city':'Gunturu','image':"/media/SEO/Group_1000006073.png","slug":"dr-praneeth-kumar"},
#         { id:11,'doctor_name':'Dr. Purvesh Chauhan','city':'Ahmedabad','image':"/media/SEO/Group_1000006031.png","slug":"dr-purvesh-chauhan"},
#             # { id:12,'doctor_name':'Dr. Rajesh Desai','city':'Hyderabad','image':"/media/SEO/Group_1000006053.png"},
#             # { id:13,'doctor_name':'Dr. Rajesh survashe','city':'Mumbai','image':"/media/SEO/Group_1000006064.png"},
#         { id:14,'doctor_name':'Dr. Ravi Shah','city':'Ahmedabad','image':"/media/SEO/Group_1000006032_ZxamElW.png","slug":"dr-ravi-shah"},
#         { id:15,'doctor_name':'Dr. Reuben Joseph','city':'Chennai','image':"/media/SEO/Group_1000006051.png","slug":"dr-reuben-joseph"},
#         { id:16,'doctor_name':'Dr. Rohan Bandi','city':'Mumbai','image':"/media/SEO/Group_1000006065.png","slug":"dr-rohan-bandi"},
#             # { id:17,'doctor_name':'Dr. Purvesh Chauhan','city':'Ahmedabad','image':"/media/SEO/Group_1000006031.png"},
#             # { id:18,'doctor_name':'Dr. M Jaydev','city':'Hyderabad','image':"/media/SEO/Group_1000006053.png"},
#             # { id:19,'doctor_name':'Dr. Praneeth Kumar','city':'Gunturu','image':"/media/SEO/Group_1000006073.png"},
#             # { id:20,'doctor_name':'Dr. Vanita Keshav','city':'Ahmedabad','image':"/media/SEO/Group_1000006031.png"},
#             # { id:21,'doctor_name':'Dr. Surangana Gupta','city':'Hyderabad','image':"/media/SEO/Group_1000006053.png"},
#         { id:22,'doctor_name':'Dr. Viren K Savani','city':'Surat','image':"/media/SEO/Group_1000005999.png","slug":"dr-viren-k-savani"},
#         { id:23,'doctor_name':'Dr. Anubhav Sood','city':'Palampur','image':"/media/SEO/Group_1000006077.png","slug":"dr-anubhav-sood"},
#             # { id:24,'doctor_name':'Dr. Apeksha Maheswari','city':'Hyderabad','image':"/media/SEO/Group_1000006053.png"},
#         { id:25,'doctor_name':'Dr. Ashok Mashru','city':'Bhavnagar','image':"/media/SEO/Group_1000006021.png","slug":"dr-ashok-mashru"},
#         { id:26,'doctor_name':'Dr. Bharat Katarmal','city':'Jamnagar','image':"/media/SEO/Group_1000006026.png","slug":"dr-bharat-katarmal"},
#         { id:27,'doctor_name':'Dr. Abhay Shukla','city':'Ambikapur','image':"/media/SEO/Group_1000006071.png","slug":"dr-abhay-shukla"},
#         { id:28,'doctor_name':'Dr. Deepika Dalal','city':'Mumbai','image':"/media/SEO/Group_1000006067.png","slug":"dr-deepika-dalal"},
#         { id:29,'doctor_name':'Dr. Abhishek Shah','city':'Surat','image':"/media/SEO/Group_1000006048_YzCRH0O.png","slug":"dr-abhishek-shah"},
#         { id:30,'doctor_name':'Dr. Digvijay Deshpande','city':'Sangli','image':"/media/SEO/Group_1000006014.png","slug":"dr-digvijay-deshpande"},
#         { id:31,'doctor_name':'Dr. Jay Patel','city':'Surat','image':"/media/SEO/Group_1000006055.png","slug":"dr-jay-patel"},
#         { id:32,'doctor_name':'Dr. Hetal Buch','city':'Rajkot','image':"/media/SEO/Group_1000006022.png","slug":"dr-hetal-buch"},
#     ]
#     # /media/SEO/Group_1000006032_ZxamElW.png
#     return render(request, 'index.html', {
#         'data1': data1,               # NOW contains ALL dentists
#         'data_list1':data1_list,
#         'gallery': gallery,
#         'cities': cities,
#         'search_message': search_message,
#         'query': query,
#         'city': city_id,              # only for UI dropdown
#         'review': reviews,
#         'city_name': city_name,
#     })


def location_view(request):
    cities = City.objects.annotate(
        dentist_count=Count('dentist', filter=Q(dentist__status=True))
    ).filter(dentist_count__gt=0).order_by('-dentist_count')[:6]
    return render(request, 'location.html', {'cities': cities})


# def smile_step(request):
#     gallery = Gallery.objects.all().order_by("?")
#     return render(request, 'smile_step.html', {'gallery':gallery,})

def search_all_usd(request, city_name=None):
    city = None
    a_city = City.objects.annotate(
        active_dentist_count=Count(
            'dentist',
            filter=Q(dentist__status=True)
        )
    ).filter(active_dentist_count__gt=0).order_by('city')

    query = request.GET.get('q', '').strip()
    # mari mate 10 valie crunchx, 10 vala singbajiya
    # AJAX search (for autocomplete or live suggestions)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        suggestion = []
        if query:
            # search doctors by name
            doctor_matches = Dentist.objects.filter(status=True, name__icontains=query)

            # search clinices by clinic name
            clinic_matches = Dentist.objects.filter(status=True, clinic_name__icontains=query)

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
    data1 = Dentist.objects.filter(status=True).order_by('name')
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
            if Dentist.objects.filter(city=c, status=True).exists():
                dist = geodesic(user_location, (c.latitude, c.longitude)).km
                nearby_city_distances.append((dist, c))

        nearby_city_distances.sort(key=lambda x: x[0])

        if nearby_city_distances:
            nearest_city = nearby_city_distances[0][1]
            city = nearest_city
            city_name = nearest_city.city
            data1 = Dentist.objects.filter(city=nearest_city, status=True)
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
        'a_city': a_city,
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
        data1 = Dentist.objects.filter(city=city, status=True).order_by('name')
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
    all_ids = list(Gallery.objects.values_list("id",flat=True))

    random_ids = random.sample(all_ids,min(5,len(all_ids)))
    gallery = Gallery.objects.filter(id__in=random_ids)
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

    if request.method == 'POST':
        form = UserSubmissionForm(request.POST)

        if form.is_valid():
            user_submission = form.save()
            current_datetime_ist = timezone.localtime(timezone.now())
            formatted_datetime = current_datetime_ist.strftime("%d-%m-%Y %I:%M %p")
            context_dict ={
                "Name": user_submission.first_name + " " + user_submission.last_name,
                "Email": user_submission.email,
                "Phone": user_submission.phone,
                "City": user_submission.city,
                "Message": user_submission.message,
                "Doctor_name": user_submission.doctor_name or "NA",
                "Page URL": request.META.get("HTTP_REFERER", "Not available")
            }

            # Send email to company
            threading.Thread(
                target=send_contact_email_async,
                args=(context_dict,),
                daemon=True
            ).start()

            bikai_payload ={
                "First_name": user_submission.first_name,
                "Last_name": user_submission.last_name,
                "Email": user_submission.email,
                "Phone": user_submission.phone,
                "Email": user_submission.email,
                "City": user_submission.city,
                "Message": user_submission.message,
                "Doctor_name": user_submission.doctor_name,
                "DateTime": formatted_datetime,
            }
            bikai_url ="https://bikapi.bikayi.app/chatbot/webhook/N8eHI9BWzqVPK7RnXu2xs5qIQt23?flow=webpatient3834"
            headers ={
                "Content-Type": "application/json",
            }
            try: 
                crm_response = requests.post(
                    bikai_url,
                    json=bikai_payload,
                    headers=headers,
                    timeout=10,
                )
                crm_response.raise_for_status()
            except requests.exceptions.RequestException as e:
                messages.warning(request, f"Form saved but CRM sync failed: {str(e)}")
            # messages.success(
            #     request,
            #     f"Form submitted successfully! Thank you, {user_submission.first_name} {user_submission.last_name}."
            # )
            # form = UserSubmissionForm()
            return redirect('home:thankyou')
        else:
            messages.error(request,"Something went wrong! Please check your details.")
            return render(request,'detail.html',{'form':form,'error_message':'Please correct the errors below.'})
    else:
        form = UserSubmissionForm()

    context = {
        'data': data,
        'gallery': gallery,
        'reviews': reviews,
        'form':form
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

def inject_multiple_sections(html_content, inserts):
    # Remove tags → count words
    text_only = re.sub('<[^<]+?>', '', html_content)
    words = text_only.split()
    total_words = len(words)

    if total_words < 50:
        return html_content

    cutoffs = { int(total_words * pct): html for pct, html in inserts }

    current = 0
    result = ""
    pending_blocks = {}
    injected_blocks = set()
    inside_table = False

    tokens = re.split(r"(<[^>]+>)", html_content)

    closing_tags = [
        "</p>", "</ul>", "</ol>", "</li>", "</div>",
        "</section>", "</br>", "</h1>", "</h2>", "</h3>",
        "</h4>", "</table>"
    ]

    for token in tokens:

        # CASE 1 → HTML TAG
        if token.startswith("<"):

            # Detect entering table
            if token.lower().startswith("<table"):
                inside_table = True

            # Detect leaving table
            if token.lower().startswith("</table"):
                inside_table = False

            result += token

            # Try injection only if NOT inside table
            if not inside_table:
                for cutoff, html in list(pending_blocks.items()):
                    if cutoff not in injected_blocks:
                        if any(token.startswith(tag) for tag in closing_tags):
                            result += html
                            injected_blocks.add(cutoff)
                            pending_blocks.pop(cutoff, None)

        # CASE 2 → TEXT
        else:
            if token.strip():
                for w in token.split():
                    current += 1

                    # Mark pending cutoff
                    if current in cutoffs and current not in injected_blocks:
                        pending_blocks[current] = cutoffs[current]

                    result += w + " "
            else:
                result += token

    return result

def blogsd(request, pk):
    if request.method == 'POST':
        form = ContactForm(request.POST)

        # Validate Recaptcha
        # recaptcha_response = request.POST.get('g-recaptcha-response')
        # data = {
        #     'secret': settings.RECAPTCHA_SECRET_KEY,
        #     'response': recaptcha_response,
        # }
        # r = requests.post("https://www.google.com/recaptcha/api/siteverify", data=data)
        # result = r.json()

        # if not result.get('success'):
        #     messages.error(request, 'Invalid reCAPTCHA. Please try again.')
        #     return redirect(request.META.get('HTTP_REFERER', 'home:blogs'))

        # Save Data + CRM Webhook
        if form.is_valid():
            submission = form.save()
            current_datetime_ist = timezone.localtime(timezone.now())
            formatted_datetime = current_datetime_ist.strftime("%d-%m-%Y %I:%M %p")
            context_dict = {
                "Name": submission.name,
                "Email":  submission.email,
                "Phone": submission.phone,
                "City": submission.city,
                "Message": submission.message,
                "Page URL": request.META.get("HTTP_REFERER", "Not available")
            }
            threading.Thread(
                target=send_contact_email_async,
                args=(context_dict,),
                daemon=True
            ).start()
            # messages.success(request, 'Your data is sent successfully.')
            bikai_payload  ={
               "Name": submission.name,
               "Email": submission.email,
               "Contact": submission.phone,
               "City": submission.city,
               "Subject": submission.subject,
               "Message": submission.message,
               "DateTime": formatted_datetime,
            }
            bikai_url ="https://bikapi.bikayi.app/chatbot/webhook/N8eHI9BWzqVPK7RnXu2xs5qIQt23?flow=webleads3220"
            headers = {
                "Content-Type": "application/json",
            }
            try:
                crm_response = requests.post(
                    bikai_url,
                    json=bikai_payload,
                    headers=headers,
                    timeout=10,
                )
                crm_response.raise_for_status()
                # messages.success(
                #     request,
                #     "Thanks for contacting the Ultimate Smile Design Team. We will get back to you shortly."
                # )
            except requests.exceptions.RequestException as e:
                messages.warning(request, f"Form saved but CRM sync failed: {str(e)}")

            return redirect('home:thankyou')
        else:
            messages.error(request, "Your query is not sent! Try again.")
            return redirect(request.META.get('HTTP_REFERER', 'home:blogs'))
        

    blog = Blog.objects.get(slug=pk)
    data2 = Blog.objects.all().order_by('-id')
    related_blog = Blog.objects.all().order_by('-id')[1:4]
    before_after_images = BeforeAfter.objects.all().order_by('-id')
    unique_tags = blog.tag.all()
    unique_categories = blog.category.all()

    form_30_html = render_to_string("custom-search-form.html", {
        "a_city": City.objects.annotate(
                    active_dentist_count=Count('dentist', filter=Q(dentist__status=True))
                ).filter(active_dentist_count__gt=0).order_by('city'),
    })

    section_70_html = render_to_string("custom-contact-form.html", {
        "a_city": City.objects.annotate(
                    active_dentist_count=Count('dentist', filter=Q(dentist__status=True))
                ).filter(active_dentist_count__gt=0).order_by('city'),
    })
    blog.content = mark_safe(
        inject_multiple_sections(
            blog.content,
            inserts=[
                (0.30, form_30_html),
                (0.70, section_70_html),
            ]
        )
    )
   
    context = {
     'cata':unique_categories,
     'blog':blog,
     'tags':unique_tags,
     'data2':data2,
     'relatedBlog':related_blog,
     'before_after_images':before_after_images,
    #  'RECAPTCHA_SITE_KEY': settings.RECAPTCHA_SITE_KEY
    }
    # print("relatedBlog",related_blog)
    return render(request, 'blogsd.html', context)

def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)

        # recaptcha_response = request.POST.get('g-recaptcha-response')
        # data = {
        #     'secret': settings.RECAPTCHA_SECRET_KEY,
        #     'response': recaptcha_response,
        # }
        # r = requests.post("https://www.google.com/recaptcha/api/siteverify", data=data)  # <-- FIXED
        # result = r.json()

        # if not result.get('success'):
        #     messages.error(request, 'Invalid reCAPTCHA. Please try again.')
        #     return redirect(request.META.get('HTTP_REFERER','contact'))
        
        if form.is_valid():
            submission = form.save()
            current_datetime_ist = timezone.localtime(timezone.now())
            formatted_datetime = current_datetime_ist.strftime("%d-%m-%Y %I:%M %p")
            context_dict = {
                "Name": submission.name,
                "Email":  submission.email,
                "Phone": submission.phone,
                "City": submission.city,
                "Message": submission.message,
                "Page URL": request.META.get("HTTP_REFERER", "Not available")
            }
            threading.Thread(
                target=send_contact_email_async,
                args=(context_dict,),
                daemon=True
            ).start()

            #messages.success(request, 'Your data is sent successfully.')
            # return redirect('home:thankyou')
            bikai_payload  ={
               "Name": submission.name,
               "Email": submission.email,
               "Contact": submission.phone,
               "City": submission.city,
               "Subject": submission.subject,
               "Message": submission.message,
               "DateTime": formatted_datetime,
            }
            bikai_url ="https://bikapi.bikayi.app/chatbot/webhook/N8eHI9BWzqVPK7RnXu2xs5qIQt23?flow=webleads3220"
            headers = {
                "Content-Type": "application/json",
            }
            try:
                crm_response = requests.post(
                    bikai_url,
                    json=bikai_payload,
                    headers=headers,
                    timeout=10,
                )
                crm_response.raise_for_status()
                # messages.success(
                #     request,
                #     "Thanks for contacting the Ultimate Smile Design Team. We will get back to you shortly."
                # )
            except requests.exceptions.RequestException as e:
                messages.warning(request, f"Form saved but CRM sync failed: {str(e)}")

            return redirect('home:thankyou')
        else:
            messages.error(request, 'Something went wrong! Please try again.')
            return redirect(request.META.get('HTTP_REFERER', 'contact'))

    context = {
        # "RECAPTCHA_SITE_KEY": settings.RECAPTCHA_SITE_KEY
    }
    return render(request, 'contact.html', context)

def dentist_connect(request):
    if request.method == 'POST':
        form = DentistConnectForm(request.POST)

        # recaptcha_response = request.POST.get('g-recaptcha-response')
        # data = {
        #     'secret' : settings.RECAPTCHA_SECRET_KEY,
        #     'response' : recaptcha_response,     
        # }
        # r = requests.post("https://www.google.com/recaptcha/api/siteverify", data=data)
        # result = r.json()

        # if not result.get('success'):
        #     messages.error(request, 'Invalid reCAPTCHA. Please try again.')
        #     return redirect(request.META.get('HTTP_REFERER','dentist-connect'))
        
        if form.is_valid():
            submission = form.save()
            # messages.success(request, 'Your data has been submitted successfully!')
            current_datetime_ist = timezone.localtime(timezone.now())
            formatted_datetime = current_datetime_ist.strftime("%d-%m-%Y %I:%M %p")
            context_dict = {
                "Name": submission.name,
                "Email": submission.email,
                "Phone": submission.phone,
                "ClinicName": submission.clinic_name,
                "City": submission.city,
                "DateTime": formatted_datetime,
            }
            threading.Thread(
                target=send_contact_email_async,
                args=(context_dict,),
                daemon=True
            ).start()
            bikai_payload  ={
               "Name": submission.name,
               "Email": submission.email,
               "Contact": submission.phone,
               "ClinicName": submission.clinic_name,
               "City": submission.city,
               "DateTime": formatted_datetime,
            }
            bikai_url = "https://bikapi.bikayi.app/chatbot/webhook/N8eHI9BWzqVPK7RnXu2xs5qIQt23?flow=webdentist7060"
            headers = {
                "Content-Type": "application/json",
            }

            # --- Send to CRM ---
            try:
                crm_response = requests.post(
                    bikai_url,
                    json=bikai_payload,
                    headers=headers,
                    timeout=10,
                )
                crm_response.raise_for_status()
                # messages.success(
                #     request,
                #     "Thanks for connecting with Ultimate Smile Design. Our team will reach out shortly!"
                # )
            except requests.exceptions.RequestException as e:
                messages.warning(request, f"Data saved but CRM sync failed: {str(e)}")

            return redirect('home:dthankyou')
        
        else:
            messages.error(request, 'Something went wrong! Please try again.')
            return redirect(request.META.get('HTTP_REFERER', 'dentist-connect'))
    context = {
        # "RECAPTCHA_SITE_KEY": settings.RECAPTCHA_SITE_KEY
    }
    return render(request, 'dentist-connect.html', context)

def sitemap(request):
    return render(request, 'sitemap.xml', content_type='text/xml')

#end
def robots(request):
    return render(request, 'robots.txt', content_type='text')   
    
def thankyou(request):
    return render(request, 'pthankyou.html')

def dthankyou(request):
    return render(request, 'dthankyou.html')

def quicklinks(request):
    return render(request,'quick-links.html')

def dentist(request):
    if request.method == 'POST':
        form = UserSubmissionForm(request.POST)

        # reCAPTCHA validation
        # recaptcha_response = request.POST.get('g-recaptcha-response')
        # data = {
        #     "secret": settings.RECAPTCHA_SECRET_KEY,
        #     "response": recaptcha_response,
        # }
        # r = requests.post("https://www.google.com/recaptcha/api/siteverify", data=data)
        # result = r.json()

        # if not result.get("success"):
        #     messages.error(request, "Invalid reCAPTCHA. Please try again.")
        #     return redirect(request.META.get("HTTP_REFERER", "dentist"))

        if form.is_valid():
            user_submission = form.save()
            current_datetime_ist = timezone.localtime(timezone.now())
            formatted_datetime = current_datetime_ist.strftime("%d-%m-%Y %I:%M %p")
            context_dict ={
                "Name": user_submission.first_name + " " + user_submission.last_name,
                "Email": user_submission.email,
                "Phone": user_submission.phone,
                "City": user_submission.city,
                "Message": user_submission.message,
                "Doctor_name": user_submission.doctor_name or "NA",
                "Page URL": request.META.get("HTTP_REFERER", "Not available")
            }
            threading.Thread(
                target=send_contact_email_async,
                args=(context_dict,),
                daemon=True
            ).start()

            bikai_payload ={
                "First_name": user_submission.first_name,
                "Last_name": user_submission.last_name,
                "Email": user_submission.email,
                "Phone": user_submission.phone,
                "Email": user_submission.email,
                "City": user_submission.city,
                "Message": user_submission.message,
                "Doctor_name": user_submission.doctor_name,
                "DateTime": formatted_datetime,
            }
            # Send email to company
            # send_mail(
            #     to_email="tukadiyabhargav5@gmail.com", 
            #     subject=f"New Contact Form Submission from {context_dict['Name']}",
            #     context_dict=context_dict
            # )
            bikai_url ="https://bikapi.bikayi.app/chatbot/webhook/N8eHI9BWzqVPK7RnXu2xs5qIQt23?flow=webpatient3834"
            headers ={
                "Content-Type": "application/json",
            }
            try: 
                crm_response = requests.post(
                    bikai_url,
                    json=bikai_payload,
                    headers=headers,
                    timeout=10,
                )
                crm_response.raise_for_status()
            # messages.success(
            #     request,
            #     f"Form submitted successfully! Thank you, {user_submission.first_name} {user_submission.last_name}."
            # )
            except requests.exceptions.RequestException as e:
                messages.warning(request, f"Form saved but CRM sync failed: {str(e)}")
            # form = UserSubmissionForm()
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

def quicklinks(request):
	return render(request,'quick-links.html')

def virtualsmiletryon(request):
    return render(request,"virtual-smile-try-on.html")