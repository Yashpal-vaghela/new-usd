from django.contrib.sitemaps import Sitemap
from django.shortcuts import reverse
from django.db.models import Count, Q
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
        return['home:contact', 'home:dentist', 'home:gallery', 'virtualsmileAI:smile', 'home:dentist_connect']
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
    
class StaticPageSitemap(Sitemap):
    def items(self):
        return [
            {
                'name': 'home:home',
                'priority': 1.0,
                'changefreq': 'daily',
                'images': [{
                    'loc': 'https://ultimatesmiledesign.com/static/usdlog.webp',
                    'title': 'Ultimate Smile Design | Cosmetic Smile Makeover in India',
                    'caption': 'Get a perfect smile with Ultimate Smile Design. Our expert cosmetic dentists provide premium smile makeover solutions in India. Schedule your consultation now!',
                }]
            },
            {
                'name': 'home:contact',
                'priority': 0.8,
                'changefreq': 'weekly',
                'images': []
            },
            {
                'name': 'home:dentist',
                'priority':0.8,
                'changefreq': 'weekly',
                'images': []
            },
            {
                'name': 'home:gallery',
                'priority': 0.8,
                'changefreq': 'weekly',
                'images': []
            },
            {
                'name': 'virtualsmileAI:smile',
                'priority': 0.8,
                'changefreq': 'weekly',
                'images': []
            },
            {
                'name': 'home:dentist_connect',
                'priority': 0.8,
                'changefreq': 'weekly',
                'images': []
            }
        ]
    
    def location(self, item):
        return reverse(item['name'])

    def changefreq(self, item):
        return item.get('changefreq', 'monthly')

    def priority(self, item):
        return item.get('priority', 0.5)

    def image_urls(self, item):
        return [
            {
                'loc': img['loc'],
                'title': img.get('title'),
                'caption': img.get('caption'),
            }
            for img in item.get('images', [])
        ]
    
class DentistsSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.8

    def items(self):
        return(
            Dentist.objects.filter(status=True).exclude(slug__isnull=True).exclude(slug="").order_by("id")
        )
    
    def location(self, obj):
        return reverse("home:find_dentist_d", kwargs={"pk": obj.slug})
    
    def lastmod(self, obj):
        return obj.updated_at
    
    def image_urls(self, obj):
        images = []
        if obj.profile:
            images.append({
                "loc": f"https://ultimatesmiledesign.com{obj.profile.url}",
                "title": f"{obj.name} - Smile Design Expert Dentist in {obj.city}",
                "caption": f"{obj.name} - Smile Design Expert Dentist in {obj.city}"
            })
        return images
    
class BlogsSitemap(Sitemap):
    changefreq = 'daily'
    priority = 0.8

    def items(self):
        return Blog.objects.all().order_by('-updated')
    
    def location(self, obj):
        return obj.get_absolute_url()
    
    def lastmod(self, obj):
        return obj.updated
    
    def image_urls(self, obj):
        images = []
        if obj.image:
            images.append({
                "loc": f"https://ultimatesmiledesign.com{obj.image.url}",
                "title": obj.h1,
                "caption": obj.title
            })
        return images
    
class NewsSitemap(Sitemap):
    changefreq = 'daily'
    priority = 0.8

    def items(self):
        return Blog.objects.all().order_by('-updated')
    
    def location(self, obj):
        return obj.get_absolute_url()
    
    def lastmod(self, obj):
        return obj.updated
    
    def image_urls(self, obj):
        images = []
        if obj.image:
            images.append({
                "loc": f"https://ultimatesmiledesign.com{obj.image.url}",
                "title": obj.h1,
                "caption": obj.title
            })
        return images
    
class BestDentistcitiesSitemap(Sitemap):
    changefreq = 'daily'
    priority = 0.8

    def items(self):
        return (
            City.objects
            .annotate(
                active_dentist_count=Count(
                    'dentist',
                    filter=Q(dentist__status=True)
                )
            )
            .filter(active_dentist_count__gt=0)
            .order_by('city')
        )

    def location(self, obj):
        return reverse(
            "home:search_city_dentists",
            kwargs={
                "city_name": obj.city.replace(" ", "-").lower()
            }
        )
    
    def lastmod(self, obj):
        return (
            obj.dentist_set
            .filter(status=True)
            .exclude(updated_at__isnull=True)
            .order_by("-updated_at")
            .values_list("updated_at", flat=True)
            .first()
        )
    
    def image_urls(self, obj):
        city = obj.city
        return [{
            "loc": "https://ultimatesmiledesign.com/static/usdlog.webp",
            "title": f"Top Dentists in {city} - List of Professional Dentists Near You",
            "caption": f"Best Dentists in {city} | Ultimate Smile Design",
        }]
