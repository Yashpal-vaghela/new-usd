from django.contrib.sitemaps import Sitemap
from django.shortcuts import reverse
from account.models import *

class HomePageSitemap(Sitemap):
    priority = 1.0
    changefreq = 'daily'

    def items(self):
        return['home:home']
    def location(self, item):
        return reverse(item)

class NormalStaticPageSitemap(Sitemap):
    priority = 0.6
    changefreq = 'weekly'

    def items(self):
        return['home:contact', 'home:dentist', 'home:gallery']
    def location(self, item):
        return reverse(item)

class ListPageSitemap(Sitemap):
    priority = 0.6
    changefreq = 'daily'

    def items(self):
        return ['home:search_all_usd', 'home:blogs']
    def location(self,item):
        return reverse(item)
    
class BlogPageSitemap(Sitemap):
    priority = 0.6
    changefreq = 'weekly'

    def items(self):
        return Blog.objects.all()
    def location(self, obj):
        return reverse('home:blogsd', args=[obj.slug])

class CityDentistSitemap(Sitemap):
    priority = 0.6
    changefreq = 'weekly'

    def items(self):
        return City.objects.all()
    def location(self, obj):
        city_name = obj.city
        city_name = city_name[0].lower() + city_name[1:] if city_name else ''
        return reverse('home:search_city_dentists', args=[city_name])
    
class DentistDetailsSitemap(Sitemap):
    priority = 0.6
    changefreq = 'weekly'

    def items(self):
        return Dentist.objects.all()
    def location(self, obj):
        return reverse('home:find_dentist_d', args=[obj.slug])