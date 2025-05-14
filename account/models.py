from django.db import models
from ckeditor_uploader.fields import RichTextUploadingField
from django.contrib.auth.models import User
# Create your models here.
class Location(models.Model):
    state = models.CharField(max_length=300)
    short_code =  models.CharField(max_length=300)

    def __str__(self):
        return self.state



class City(models.Model):
    state = models.ForeignKey(Location, on_delete=models.CASCADE)    
    city = models.CharField(max_length=300)
    def __str__(self):
        return str(self.city)

    def countdr(self):
        return Dentist.objects.filter(city=self.id).count()

class Specializations(models.Model):
    name = models.CharField(max_length=300)

    def __str__(self):
        return self.name


class Dentist(models.Model):
    h1  = models.CharField(max_length = 156)
    slug =models.CharField(max_length = 1256,blank=True, null=True)
    page_name = models.CharField(max_length = 1256,blank=True, null=True)
    keyword = models.CharField(max_length = 156,blank=True, null=True)
    description = models.CharField(max_length = 900,blank=True, null=True)
    seo_title = models.CharField(max_length = 156,blank=True, null=True)
    breadcrumb = models.CharField(max_length = 156,blank=True, null=True)
    canonical = models.CharField(max_length = 900,blank=True, null=True)
    og_type =models.CharField(max_length = 156,blank=True, null=True)
    og_card = models.CharField(max_length = 156,blank=True, null=True)
    og_site = models.CharField(max_length = 156,blank=True, null=True)

    user = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='User', blank=True, null=True )    

    city = models.ForeignKey(City, on_delete=models.CASCADE,blank=True, null=True)   
    state = models.CharField(max_length=300,blank=True, null=True)
      
    profile  = models.ImageField(upload_to="SEO",blank=True, null=True)
    
    name = models.CharField(max_length=300)
    title = models.CharField(max_length=300)
    sub_title = models.CharField(max_length=300,blank=True, null=True)
    email = models.CharField(max_length=300, blank=True, null=True)
    contact = models.CharField(max_length=300)
    bio = models.TextField(max_length=1300,blank=True, null=True)
    address = models.TextField(max_length = 15622, blank=True, null=True)
    education = RichTextUploadingField(blank=True, null=True)
    awards = RichTextUploadingField(blank=True, null=True)
    experience = RichTextUploadingField(blank=True, null=True)
    Coffee_table_book_Adimplant = models.CharField(max_length=300, default='1')
    Advance_zirconia  = models.CharField(max_length=300, default='1')
    Adaligner = models.CharField(max_length=300, default='1')
    USD_box = models.CharField(max_length=300, default='1')
    delivered_date = models.DateField( blank=True, null=True)

    specializations = models.ManyToManyField(Specializations, null=True, blank=True)
    iframe = models.TextField(max_length=1300,blank=True, null=True)

    status = models.BooleanField(default=False)
    treding = models.BooleanField(default=False)
    in_home = models.BooleanField(default=False)

    lat =  models.TextField(max_length=1300,blank=True, null=True)
    long =  models.TextField(max_length=1300,blank=True, null=True)
    schema = models.TextField(max_length = 15622, blank=True, null=True)


    Mon   = models.CharField(max_length=300, default='open',blank=True, null=True)
    Tue = models.CharField(max_length=300, default='open',blank=True, null=True)
    Wed = models.CharField(max_length=300, default='open',blank=True, null=True)
    Thu = models.CharField(max_length=300, default='open',blank=True, null=True)
    Fri = models.CharField(max_length=300, default='open',blank=True, null=True)
    Sat = models.CharField(max_length=300, default='open',blank=True, null=True)
    Sun = models.CharField(max_length=300, default='close',blank=True, null=True)
    

    def __str__(self):
        return self.name
class PatientReview(models.Model):
    dentist = models.ForeignKey(Dentist, on_delete=models.CASCADE, related_name='reviews')
    patient_name = models.CharField(max_length=300)
    review = models.TextField(max_length=2000)
    rating = models.PositiveIntegerField(default=5)  # Optional: scale of 1-5
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient_name} - {self.dentist.name}"

class Image(models.Model):
    dentist = models.ForeignKey(Dentist, on_delete=models.CASCADE)    
    image = models.ImageField(upload_to="Dentist")

class Rating(models.Model):
    dentist = models.ForeignKey(Dentist, on_delete=models.CASCADE)    
    star = models.CharField(max_length=300)
    said = models.TextField(max_length=1300)
    by =   models.CharField(max_length=300)
    date =  models.CharField(max_length=300)



class Category(models.Model):
    category = models.CharField(max_length = 156)
    def __str__(self):
        return self.category

class Tags(models.Model):
    tags = models.CharField(max_length = 156)
    def __str__(self):
        return self.tags    

class Author(models.Model):
    description = RichTextUploadingField()
    name = models.CharField(max_length = 156)
    position = models.CharField(max_length = 156)
    fb =models.CharField(max_length = 156,blank=True, null=True)
    insta = models.CharField(max_length = 156, blank=True, null=True)
    linkedin = models.CharField(max_length = 156, blank=True, null=True)
    image  = models.ImageField(upload_to="SEO")
    def __str__(self):
        return self.name     
               
# Create your models here.
class Blog(models.Model):
    status  = models.BooleanField(default=True)
    
    h1  = models.CharField(max_length = 156)
    slug =models.CharField(max_length = 1256,blank=True, null=True)
    page_name = models.CharField(max_length = 1256,blank=True, null=True)
    keyword = models.CharField(max_length = 156)
    description = models.CharField(max_length = 900)
    title = models.CharField(max_length = 156)
    breadcrumb = models.CharField(max_length = 156)
    canonical = models.CharField(max_length = 900)
    og_type =models.CharField(max_length = 156)
    og_card = models.CharField(max_length = 156)
    og_site = models.CharField(max_length = 156)
    image  = models.ImageField(upload_to="SEO")
    
    category = models.ManyToManyField(Category)
    tag  = models.ManyToManyField(Tags)
    updated  = models.DateField(auto_now=True)
    

    blog_banner_lg = models.ImageField(upload_to="Page Data", blank=True, null=True)
    blog_banner_sm = models.ImageField(upload_to="Page Data", blank=True, null=True)
    
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    published  = models.DateField()
    content = RichTextUploadingField()
    active = True
    edits = RichTextUploadingField( blank=True, null=True)
    
    
    def __str__(self):
        return self.h1


class Team(models.Model):   
    image  = models.ImageField(upload_to="SEO")
    name = models.CharField(max_length = 156)
    position = models.CharField(max_length = 156)
    fb = models.CharField(max_length = 156)
    insta = models.CharField(max_length = 156)
    twitter = models.CharField(max_length = 156)
    youtube = models.CharField(max_length = 156)

    def __str__(self):
        return self.name



class Testimonials(models.Model):   
    image  = models.ImageField(upload_to="SEO")
    name = models.CharField(max_length = 156)
    position = models.CharField(max_length = 156)
    review = models.TextField()
 
    def __str__(self):
        return self.name
   

class Gallery(models.Model):   
    image  = models.ImageField(upload_to="SEO")
    
 
    def __str__(self):
        return str(self.id)

class Hgallery(models.Model):
    image = models.ImageField(upload_to="SEO")

    def __str__(self):
        return str(self.id)

class Contact(models.Model):
    name =models.CharField(max_length = 1256,blank=True, null=True)
    email = models.CharField(max_length = 1256,blank=True, null=True)
    phone = models.CharField(max_length = 156)
    subject = models.CharField(max_length = 156)
    message =RichTextUploadingField()
    date = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
        
        

class UserSubmission(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone = models.CharField(max_length=15)
    email = models.EmailField()
    agree_to_terms = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    
    
    
    
    
     

