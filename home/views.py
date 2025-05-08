from django.shortcuts import render, redirect ,get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from account.models import *
from account.forms import ContactForm
from django.db.models import Q
from django.core.paginator import Paginator
from hm.pre import get_location_info
from geopy.distance import geodesic
import re

@csrf_exempt  # This bypasses CSRF protection for demonstration purposes only
def receive_location(request):
    if request.method == 'POST':
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')

        if latitude and longitude:
            # Store latitude and longitude in session
            request.session['latitude'] = latitude
            request.session['longitude'] = longitude

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

    reviews = [
        {id:1,'doctor_name':'Dr. Priyanka Sharma','review':"I never imagined my smile could look this great. The entire process was smooth and tailored to my needs. I'm so grateful to the team and my smile designer!"},
        {id:2,'doctor_name':'Dr. Anjali Mehta','review':'My experience was beyond my expectations. The attention to detail and personalized care I received was truly outstanding. Highly recommend!'},
        {id:3,'doctor_name':'Dr. Rahul Kumar','review':"The transformation has been incredible. I feel more confident and love my new smile. Thank you to my dentist for such an amazing experience!"},
        {id:4,'doctor_name':'Dr. Ankita V','review':"I had the pleasure of working with Advance Dental Lab for over 8 years. It is such a joy to have a lab that can provide helpful and successful alternative options for extremely difficult cases and export level quality . Ultimate smile Designing is best. Support Digital dentistry . They have skilled technicians to provide Fast work. Ultimate smile designer"},
        {id:5,'doctor_name':'Dr. Manali Rajyguru','review':'The bestest lab i have worked with in my 14years of practice.  each n every crown they deliver is perfect. no adjustments no high points.support team is also best.  Anilbhai gives humble ans anytime u call.scan facilities they started is best thing. vishalbhai provide good service always on time and finishes scan within 10 to 15 mins.overall satisfied with all the work n services.'}
    ]

    # Check for city in request; if not found, check session
    if not city_id:
        city_name = request.session.get('city','Surat')
        if city_name:
            try:
                city = City.objects.get(city=city_name)
                data1 = data1.filter(city=city)
            except City.DoesNotExist:
                search_message = f"No Ultimate Designers Found in {city_name}."
        else:
            search_message = "No city selected."

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
      'review': reviews
    }
    return render(request, 'index.html', context)

def location_view(request):
    data1 = City.objects.all()[:10]
    return render(request, 'location.html', {'data1': data1})

def smile_step(request):
    gallery = Gallery.objects.all().order_by("?")
    return render(request, 'smile_step.html', {'gallery':gallery,})

def search_all_usd(request, city_name=None):
    """
    Handles the search functionality for dentists.
    Allows filtering by city name (from URL), or city ID (from GET), or session.
    Supports pagination and location-based sorting.
    """

    city = None
    query = request.GET.get('q', '').strip()
    city_id = request.GET.get('city', '').strip()
    data1 = Dentist.objects.all().order_by('name')
    search_message = None

    user_latitude = request.session.get('latitude')
    user_longitude = request.session.get('longitude')

    # Priority: city_id from GET > city_name from URL > session city
    if city_id:
        city = get_object_or_404(City, id=city_id)
        data1 = data1.filter(city=city)
        city_name = city.city  # Update city_name from DB
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

    # Location-based sorting
    if user_latitude and user_longitude:
        doctors_with_location = []
        doctors_without_location = []

        for doctor in data1:
            if doctor.iframe:
                match = re.search(r"!2d(-?\d+\.\d+)!3d(-?\d+\.\d+)", doctor.iframe)
                if match:
                    doctor_longitude = float(match.group(1))
                    doctor_latitude = float(match.group(2))
                    doctor_distance = geodesic((user_latitude, user_longitude), (doctor_latitude, doctor_longitude)).km
                    doctors_with_location.append((doctor_distance, doctor))
                else:
                    doctors_without_location.append(doctor)
            else:
                doctors_without_location.append(doctor)

        doctors_with_location.sort(key=lambda x: x[0])
        sorted_doctors = [doc for _, doc in doctors_with_location] + doctors_without_location
    else:
        sorted_doctors = list(data1)

    # Apply search query
    if query:
        sorted_doctors = data1.filter(name__icontains=query)

    if not data1.exists():
        search_message = "No Ultimate Designers Found Based On Your Query."

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

def find_dentist(request):
    """
    Displays dentists for the city stored in the session.
    If no city is found in the session, shows all dentists.
    """
    city_name = request.GET.get('city') or request.session.get('city', '')
    data1 = Dentist.objects.all().order_by('name')  # Default queryset
    search_message = None

    if city_name:
        try:
            city = City.objects.get(city=city_name)
            data1 = Dentist.objects.filter(city=city).order_by('name')
        except City.DoesNotExist:
            search_message = f"No Ultimate Designers Found in {city_name}."
            data1 = Dentist.objects.all().order_by('name')
    print("dentist",data1,"data",data)
    
    # Pagination
    paginator = Paginator(data1, 6)  # 12 dentists per page
    page = request.GET.get('page', 1)

    try:
        data = paginator.page(page)
    except PageNotAnInteger:
        data = paginator.page(1)
    except EmptyPage:
        data = paginator.page(paginator.num_pages)

    context = {
        'data': data,
        'search_message': search_message,
        'city_name': city_name,
    }
    return render(request, 'list.html', context)

def find_dentist_d(request, pk):
    data = Dentist.objects.get(slug=pk)
    gallery = Gallery.objects.all().order_by("?")[:10]
    context = {
        'data':data,
        'gallery':gallery,
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
    related_blog = Blog.objects.all().order_by('-id')[:3]
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
        if form.is_valid():
            form.save()
            messages.success(request, 'Your data is sent successfully.')
            # Redirect to the thank you page after form submission
            return redirect('home:thankyou')
        else:
            messages.error(request, 'Your query is not sent! Try Again.')
            # print(form.errors)
        
        # If the form is invalid, stay on the contact page
        return redirect(request.META.get('HTTP_REFERER', 'contact'))

    context = {}
    return render(request, 'contact.html', context)
def sitemap(request):
    return render(request, 'sitemap.xml', content_type='text/xml')

#end
def robots(request):
    return render(request, 'robots.txt', content_type='text')   
    
def thankyou(request):
    return render(request, 'pthankyou.html')
