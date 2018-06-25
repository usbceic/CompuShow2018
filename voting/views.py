#####################################################
#                                                   #
#       CompuSoft - The Compushow 2017 Software     #
#                                                   #
#####################################################
#                                                   #
#  	  		 - Views file of the CompuSoft.  		#
#                                                   #
#####################################################

import json
from functools import reduce
from random import shuffle, randint
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, Http404
from django.contrib.auth.decorators import login_required
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string
from .tokens import account_activation_token
from django.contrib.auth.models import User, update_last_login
from django.core.mail import EmailMessage

from pprint import pprint
from .forms import LoginForm
from .library import *

from .models import *
from django.core import serializers

from django.views.decorators.csrf import csrf_exempt

from django.core.exceptions import ObjectDoesNotExist

import os
TOKEN_BOT = os.environ.get('TOKEN_BOT')
##############################################
# Flag to enable voting modules (important!) #
##############################################
enable_voting = True                        #
##############################################

@login_required()
def index(request):
    students = get_students()
    return render(request, 'voting/index.html', {
        'home':True,
        'students':students,
        'enable_voting':enable_voting,
        'safari': browser_safari(request.META['HTTP_USER_AGENT'])
    })

def log_in(request):

    # Redirect if user already logged in
    if request.user.is_authenticated():
        return HttpResponseRedirect('/')

    if request.method == 'POST':

        if request.user.is_authenticated():
            return HttpResponseRedirect('/')

        form = LoginForm(request.POST)
        if form.is_valid():
            student_id = form.cleaned_data['student_id']
            password = form.cleaned_data['password']
            print(student_id)
            print(password)

            if not user_is_registered(student_id):
                print(student_id)
                print(password)
                result = validate_and_register_user(student_id)
                if result == 'id not found':
                    # student id not found in ldap
                    return render(request, 'voting/login.html', {'form':form, 'invalid':True, 'notfound':True})
                    
                elif result == 'not computer science student':
                    return render(request, 'voting/login.html', {'form':form, 'invalid':True, 'notcs':True})					
            print('aqui')
            user = authenticate(username=student_id, password=password)

            if user is not None:

                if account_activated(user):
                    login(request, user)
                    request.session['profileimage'] = '/voting/images/profilePhotos/' + get_user_image(user) + '.jpg'
                else:
                    account_activation_email(request, user)
                    return render(request, 'voting/login.html', {'form':form, 'not_activated':True})

                return HttpResponseRedirect('/')
            
            else:
                return render(request, 'voting/login.html', {'form':form, 'invalid':True, 'invalidpasswd':True})

        else:
            return render(request, 'voting/login.html', {'form':form})

    else:
        form = LoginForm()
        return render(request, 'voting/login.html', {'form':form})

@login_required()
def nominate(request):

    categories  = get_categories()
    students    = get_students()
    nominations, categories_exist = get_nominations(request.user)
    categories = [categories[0:6], categories[6:12], categories[12:]]
    return render(request, 'voting/nominate.html', {
        'nominate':True,
        'categories':categories,
        'students':students,
        'nominations':nominations,
        'categories_exist':categories_exist,
        'enable_voting':enable_voting,
        'safari': browser_safari(request.META['HTTP_USER_AGENT'])
    })

@login_required()
def log_out(request):
    logout(request)
    return HttpResponseRedirect('/login/')

@login_required()
def get_student_info(request):
    
    user = request.user
    category = request.GET.get('category')
    studentID = request.GET.get('studentID')
    studentID2 = request.GET.get('studentID2')
    comment = request.GET.get('comment')
    cartoon = request.GET.get('cartoon')
    print(user)
    data = dict()
    data['category'] = category

    # Get student ID's
    freeFieldCategories = ['CompuMaster', 'CompuAdoptado', 'CompuTeam']
    if category not in freeFieldCategories:
        studentID = get_student_id(studentID)

    # Student not found
    if studentID is None:
        data['not_found'] = True
        data['nominate'] = False
        data['already_nominated'] = False
        return HttpResponse(json.dumps(data))

    if studentID2 is not None:
        studentID2 = get_student_id(studentID2)
        if studentID2 is None:
            data['not_found_2'] = True
            data['nominate'] = False
            data['already_nominated'] = False
            return HttpResponse(json.dumps(data))

    # Check if not repeating nomination
    if already_nominated(user, category, studentID, studentID2):
        print(studentID)
        print(studentID2)
        data['already_nominated'] = True
        data['nominate'] = False
        data['nom_id'], data['comment'] = get_nomination_info(user, category, studentID, studentID2)
        
        if category not in freeFieldCategories:
            data['nominee_entity'] = Student.objects.filter(student_id = studentID ).first().person.entity.pk
        else:
            data['nominee_entity'] = studentID

        if category not in freeFieldCategories:
            data['carnet'] = studentID
        else:
            data['carnet'] = ""
        
        data['carnet2']  = studentID2
        data['comment']  = comment
        
        if category == 'CompuCartoon':
            data['cartoon']  = get_cartoon(user, studentID)
        
        if studentID2 is not None:
            data['nomineeOpt_entity'] = Student.objects.filter(student_id = studentID2).first().person.entity.pk

    # Then prepre for nomination
    else:
        # Get nomination info (user, category, studentID, studentID2, comment)
        data['nominate'] = True
        data['already_nominated'] = False
        data['comment']  = comment
        
        if category not in freeFieldCategories:
            data['carnet'] = studentID
        else:
            data['carnet'] = ""

        data['carnet2']  = studentID2
        data['cartoon']  = cartoon

    return HttpResponse(json.dumps(data))


@login_required()
def delete_nomination(request):

    user = request.user
    category = request.GET.get('category')
    studentID = request.GET.get('studentID')
    studentID2 = request.GET.get('studentID2')

    # Get student ID's
    freeFieldCategories = ['CompuMaster', 'CompuAdoptado', 'CompuTeam']
    if category not in freeFieldCategories:
        studentID = get_student_id(studentID)

    if studentID2 is not None:
        studentID2 = get_student_id(studentID2)

    delete_nomination_db(user, category, studentID, studentID2)

    data = dict()

    freeFieldCategories = ['CompuMaster', 'CompuAdoptado', 'CompuTeam']
    if category not in freeFieldCategories:
        data['nominee_entity'] = Student.objects.filter(student_id = studentID ).first().person.entity.pk
        
        if studentID2 is not None:
            data['nomineeOpt_entity'] = Student.objects.filter(student_id = studentID2).first().person.entity.pk
        else:
            data['nomineeOpt_entity'] = None

    else:
        data['nominee_entity'] = studentID
        data['nomineeOpt_entity'] = None		

    return HttpResponse(json.dumps(data))

@login_required()
def make_nomination(request):

    if request.method == "POST":

        user = request.user
        category = request.POST.get('category')
        studentID = request.POST.get('studentID')
        studentID2 = request.POST.get('studentID2')
        comment = request.POST.get('comment')
        cartoon = request.POST.get('cartoon')
        
        if not already_nominated(user, category, get_student_id(studentID), get_student_id(studentID2)):
            make_nomination_db(user, category, studentID, studentID2, comment, cartoon)
    
        data = dict()

        freeFieldCategories = ['CompuMaster', 'CompuAdoptado', 'CompuTeam']
        if category in freeFieldCategories:
            data['nominee_entity'] = studentID
            data['carnet'] = None
            data['comment'] = comment
            data['cartoon'] = None
            data['nomineeOpt_entity'] = None
            data['carnet2'] = None

        else:
            data['nominee_entity'] = Student.objects.filter(student_id = get_student_id(studentID) ).first().person.entity.pk
            data['carnet'] = get_student_id(studentID)
            data['comment'] = comment
            data['cartoon'] = cartoon
    
            if studentID2 is not None:
                data['nomineeOpt_entity'] = Student.objects.filter(student_id = get_student_id(studentID2) ).first().person.entity.pk
                data['carnet2'] = get_student_id(studentID2)
            else:
                data['nomineeOpt_entity'] = None
                data['carnet2'] = None

        return HttpResponse(json.dumps(data))

@login_required()
def view_profile(request):

    name = request.GET.get('search-bar')
    studentID = get_student_id(name)

    if studentID is None:
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

    students = get_students()

    nominations = []
    if enable_voting:
        nominations = get_nominations_profile(studentID)


    return render(request, 'voting/profile.html', {
        'profile':True,
        'student_name': name,
        'student_id': studentID,
        'students':students,
        'enable_voting':enable_voting,
        'my_profile':False,
        'nominations':nominations,
        'safari': browser_safari(request.META['HTTP_USER_AGENT'])
    })

@login_required()
def vote(request):

    user = request.user
    students = get_students()
    categories = get_categories()
    category = get_category(request.GET.get('category'))
    # Get nominees and shuffle (because they come already sorted)
    nominees, voted = get_nominees_from_category(category, user)
    all_comments = []
    print(nominees)
    for nominee in nominees:
        comments = nominee['comments']
        try:
            comments +=  [nominee['firstcomment']]
        except KeyError:
            pass
        name = nominee['name']
        rotated = ['rotated', ''][randint(0, 1)]
        try:
            nameOpt = nominee['nameOpt']
        except:
            nameOpt = None
        try:
            extra = nominee['extra']
        except:
            extra = None
        for comment in comments:
            all_comments.append({
                'name': name, 'extra': extra, 'nameOpt':nameOpt, 'comment': comment, 'rotated': rotated
            })
    shuffle(nominees)
    shuffle(all_comments)
    all_comments = all_comments[:12]
    order = randint(0, 1)
    nominees_lower = nominees[:3]
    nominees_upper = nominees[3:]
    return render(request, 'voting/vote.html', {
        'voting':True,
        'order': order,
        'voted':voted,
        'students':students,
        'enable_voting':enable_voting,
        'category':category,
        'categories':categories,
        'nominees_upper': nominees_upper,
        'nominees_lower': nominees_lower,
        'all_comments': all_comments,
        'nominees_count':len(nominees),
        'safari': browser_safari(request.META['HTTP_USER_AGENT']),
    })


@login_required()
def upd_pswd(request):

    user = request.user
    new_pswd = request.POST.get('new_pswd')
    
    upd_pswd_db(user, new_pswd)

    return HttpResponse(json.dumps(dict()))

def activate(request, uidb64, token):
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and account_activation_token.check_token(user, token):
        update_last_login(None, user)
        return render(request, 'voting/registration_success.html')
    else:
        return render(request, 'voting/registration_success.html', {'invalid':True})

@login_required()
def get_vote_info(request):

    category = request.GET.get('category')
    studentID = request.GET.get('studentID')
    studentIDOpt = request.GET.get('studentIDOpt')
    extra = request.GET.get('extra')

    data = dict()
    data['comments'] = get_comments_from_nomination(category, studentID, studentIDOpt, extra)
    
    return HttpResponse(json.dumps(data))

@login_required()
@csrf_exempt
def voting(request):

    user = request.user
    category = request.POST.get('category')
    studentID = request.POST.get('studentID')
    studentIDOpt = request.POST.get('studentIDOpt')
    extra = request.POST.get('extra')
    
    data = dict()

    if not already_voted(user, category):
        data['valid'] = True
        process_voting(user, studentID, studentIDOpt, category, extra)
    else:
        data['valid'] = False

    return HttpResponse(json.dumps(data))


@csrf_exempt
def voting_from_bot(request):
    if request.method == "POST":
        try:
            pk = request.POST.get('nominee')
            student_id = request.POST.get('student_id')
            categoria = request.POST.get('categoria')
			person = request.POST.get('person')
			personOpt = request.POST.get('personOpt')
			extra = request.POST.get('extra')
            token = request.POST.get('token')
            assert token == TOKEN_BOT, 'Parece que no has enviado esta request desde el bot de Telegram.'

            print('already_voted', already_voted(student_id, categoria))

            if not already_voted(student_id, categoria):
                category = Category.objects.filter(name = categoria).first()
                user = Student.objects.filter(student_id = student_id).first().user

                nominee = Nominee.objects.get(pk=pk, category=category)
                nominee.votes += 1
                nominee.save()

				if person:
					person = Entity.objects.get(pk=person)
				if personOpt:
					personOpt = Entity.objects.get(pk=personOpt)
                Vote.objects.create(nominator=user, category=category, nominee=person, nomineeOpt=personOpt, extra=extra)
                return HttpResponse(json.dumps({'success': 1}), content_type='application/json')

            else:
                return HttpResponse(json.dumps({'success': 0}), content_type='application/json')

        except Exception as e:
            return HttpResponse(json.dumps({'error': str(e)}), content_type='application/json')

## Función que retorna las categorías:
def categories(request):
    if request.method == 'GET':
        categories = Category.objects.all()
        return HttpResponse(serializers.serialize('json', categories), content_type='application/json')

def category(request):
    if request.method == 'GET':
        pk = request.GET.get('pk')
        cat = Category.objects.filter(pk=pk)
        nominates = cat[0].nominee_set.all()
        nominados = []

        for nom in nominates:
            person = None
            personOpt = None
            nominate = None
            if nom.entity:
                person = json.loads(serializers.serialize('json',Person.objects.filter(entity=nom.entity)))
                nominate = json.loads(serializers.serialize('json', Nominate.objects.filter(nominee=nom.entity)))

            if nom.entityOpt:
                personOpt = json.loads(serializers.serialize('json',Person.objects.filter(entity=nom.entityOpt)))

            nominado = {
                'person': person,
                'personOpt': personOpt,
                'nominee': json.loads(serializers.serialize('json', Nominee.objects.filter(pk=nom.pk))),
                'nominate': nominate
            }
            nominados.append(nominado)

        data = {
            'categoria': json.loads(serializers.serialize('json', cat)),
            'nominados': nominados
        }
        return HttpResponse(json.dumps(data), content_type='application/json')


## Vista para validar usuario y contraseña 
@csrf_exempt
def login_bot(request):
    if request.method == 'POST':
        carnet = request.POST.get('carnet')
        password = request.POST.get('password')
        token = request.POST.get('token')
        try:
            assert token == TOKEN_BOT, 'Parece que no has enviado esta request desde el bot de Telegram.'
            user = Student.objects.get(student_id=carnet).user
            return HttpResponse(json.dumps({'valid': user.check_password(password)}), content_type="application/json")
        except Student.DoesNotExist as e:
            return HttpResponse(json.dumps({'valid': False, 'error': 'No existe un estudiante con ese carnet'}), content_type="application/json")
        except Exception as e:
            return HttpResponse(json.dumps({'valid': False, 'error': str(e)}), content_type="application/json")

