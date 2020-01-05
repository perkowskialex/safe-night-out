from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.forms import UserCreationForm
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic import ListView, DetailView
from .models import DrinkSession, Drink, Profile, Photo, DrinkTime
from .forms import DrinkTimeForm
from bokeh.embed import components
from bokeh.plotting import figure
import uuid
import boto3

S3_BASE_URL = 'https://s3-us-east-2.amazonaws.com/'
BUCKET = 'safenightout'


# Create your views here.
class DrinksessionCreate(CreateView):
    model = DrinkSession
    fields = ['start_time', 'duration']

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class DrinksessionUpdate(UpdateView):
    model = DrinkSession
    fields = ['start_time']


class DrinksessionDelete(DeleteView):
    model = DrinkSession
    success_url = '/drinksessions/'


def home(request):
    p = Profile.objects.all()
    return render(request, 'home.html', {'profile': p})

# about page

def about(request):
    return render(request, 'about.html')

def laws_texas(request):
    return render(request, 'laws/texas.html')

def signup(request):
    error_message = ''
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('profile_create')
        else:
            error_message = 'Invalid sign up - try again'
    form = UserCreationForm()
    context = {'form': form, 'error_message': error_message}
    return render(request, 'registration/signup.html', context)

@login_required 
def drinksession_index(request):

    session = DrinkSession.objects.filter(user=request.user)
    return render(request, 'drinksessions/index.html', {'session': session})

@login_required 
def drinksession_detail(request, session_id):

    if (DrinkSession.objects.get(id=session_id).user != request.user):
        return redirect('index')
    drink_time_form = DrinkTimeForm()
    # this pulls the list of BAC every 15minutes
    data = DrinkSession.objects.get(id=session_id).bac_info()
    # seperates the list of two value lists into two seperate lists
    d1 = [item[0] for item in data]
    d2 = [item[1] for item in data]
    # this defines the type of bokeh plot
    plot = figure(plot_width=300, plot_height=200, x_axis_type="datetime", x_axis_label="time", y_axis_label="Blood Alcohol Content (BAC)")
    # this customizes the x and y axis and color of lines
    plot.line(d1, d2,  color="blue", line_width=4)

    script, div = components(plot)

    return render(request, 'drinksessions/detail.html', {
        'session': DrinkSession.objects.get(id=session_id),
        'drink_time_form': drink_time_form,
        'drink_set': DrinkSession.objects.get(id=session_id).drinktime_set.all(),
        'script': script,
        'div': div
    })


class ProfileCreate(CreateView):
    model = Profile
    fields = ['first_name', 'last_name', 'sex', 'weight']

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class ProfileUpdate(UpdateView):
    model = Profile
    fields = ['first_name', 'last_name', 'sex', 'weight']


class DrinkCreate(CreateView):
    model = Drink
    fields = '__all__'


class DrinkDelete(DeleteView):
    model = Drink
    success_url = '/drinks/'  # maybe drink session, maybe we remove drink delete


class DrinkUpdate(UpdateView):
    model = Drink
    fields = ['cost', 'abv', 'drink_type']


class DrinkList(ListView):
    model = Drink


class DrinkDetail(DetailView):
    model = Drink

@login_required 
def add_drink_time(request, session_id):

    form = DrinkTimeForm(request.POST)
    if form.is_valid():
        new_drink_time = form.save(commit=False)
        new_drink_time.session_id = session_id
        new_drink_time.save()
    return redirect('detail', session_id=session_id)

@login_required 
def add_photo(request, session_id):
    photo_file = request.FILES.get('photo-file', None)
    if photo_file:
        s3 = boto3.client('s3')
        key = uuid.uuid4().hex[:6] + \
            photo_file.name[photo_file.name.rfind('.'):]
        try:
            s3.upload_fileobj(photo_file, BUCKET, key)
            url = f"{S3_BASE_URL}{BUCKET}/{key}"
            photo = Photo(url=url, session_id=session_id)
            photo.save()
        except:
            print('An error occured uploading file to S3')
    return redirect('detail', session_id=session_id)
