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
    }
    return render(request, 'index.html', context)

def location_view(request):
    data1 = City.objects.all()[:10]
    return render(request, 'location.html', {'data1': data1})

def smile_step(request):
    gallery = Gallery.objects.all().order_by("?")
    return render(request, 'smile_step.html', {'gallery':gallery,})

def search_all_usd(request):
    """
    Handles the search functionality for dentists.
    Allows filtering by city (from request or session) and search query (name).
    Supports pagination.
    """
    city_id = request.GET.get('city', '').strip()
    query = request.GET.get('q', '').strip()
    data1 = Dentist.objects.all().order_by('name')  # Default queryset
    search_message = None

    # Check for city in request; if not found, check session
    if not city_id:
        city_name = request.session.get('city')
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

    # Pagination
    paginator = Paginator(data1, 12)  # 12 dentists per page
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
        'query': query,
        'city': city_id or request.session.get('city'),
    }
    return render(request, 'list.html', context)

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
    # unique_tags = set(tag for blog in Blog.objects.all() for tag in blog.tag.all())
    # unique_categories = set(category for blog in Blog.objects.all() for category in blog.category.all())
    unique_tags = blog.tag.all()
    unique_categories = blog.category.all()
    
   
    context = {
     'cata':unique_categories,
     'blog':blog,
     'tags':unique_tags,
     'data2':data2,
     'relatedBlog':related_blog
    }
    print("relatedBlog",related_blog)
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
            print(form.errors)
        
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