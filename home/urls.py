from django.urls import path
from django.contrib import sitemaps
from django.contrib.sitemaps.views import sitemap
from home.sitemaps import *
from . import views

app_name='home'
sitemaps_dict ={
    'home': HomePageSitemap,
    'static': NormalStaticPageSitemap,
    'list': ListPageSitemap,
    'blog': BlogPageSitemap,
    'citydentist': CityDentistSitemap,
    'dentistdetails': DentistDetailsSitemap
}
urlpatterns = [
    path('', views.home, name='home'),
    # path('find-dentist/', views.find_dentist, name='find_dentist'),
    path('gallery/', views.gallery, name='gallery'),
    path('consult-with-dentist/', views.dentist, name='dentist'),
    path('certified-dentists/<str:pk>/', views.find_dentist_d, name='find_dentist_d'),
    path('blogs/', views.blogs, name='blogs'),
    path('blogs/<str:pk>/', views.blogsd, name='blogsd'),
    path('contact/', views.contact, name='contact'),
    path('thank-you/', views.thankyou, name='thankyou'),
    path('dentist-thank-you/', views.dthankyou, name='dthankyou'),
    path('quick-links/',views.quicklinks,name="quicklinks"),
    # path('sitemap.xml/',views.sitemap, name='sitemap'),
    path('robots.txt',views.robots, name='robots'),
    path('certified-dentists/', views.search_all_usd, name='search_all_usd'),
    path('certified-dentists/city/<slug:city_name>/', views.search_city_dentists, name='search_city_dentists'),
    path('receive_location/', views.receive_location, name='receive_location'),
    # path('locations/', views.location_view, name='locations'),
    path('dentist-connect/',views.dentist_connect,name='dentist_connect'),
    path('sitemap.xml/', sitemap, {'sitemaps': sitemaps_dict}, name='django.contrib.sitemaps.views.sitemap'),
    path('sitemap-static.xml/', views.staticPageSitemap, name='static_page_sitemap'),
    path('sitemap-dentists.xml/', views.dentistsSitemap, name='dentists_sitemap'),
    path('sitemap-blog.xml/', views.blogSitemap, name='blogs_sitemap'),
    path('sitemap-news.xml/', views.newsSitemap, name='news_sitemap'),
    path('sitemap-city-dentists.xml/', views.dentistCitySitemap, name="city_dentists_sitemap"),
    path('sitemap-new.xml/', views.sitemap_index, name="sitemap_index")
    # path('virtual-smile-try-on/',views.virtualsmiletryon , name="virtualsmiletryon")
    # path('smile_step/', views.smile_step, name='smile_step'),
] 
