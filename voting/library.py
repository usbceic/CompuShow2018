#####################################################
#                                                   #
#       CompuSoft - The Compushow 2017 Software     #
#                                                   #
#####################################################
#                                                   #
#  			    - Library of functions.  			#
#                                                   #
#####################################################

import ldap3
from .models import *
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.db.models import Q, Count

# Checks if student is registered in CompuSoft database
def user_is_registered(student_id):
	return Student.objects.filter(student_id = student_id).exists()

# Validate student in LDAP of USB and register in database
def validate_and_register_user(student_id):
	
	server = ldap3.Server('ldap.usb.ve', get_info=ldap3.ALL)
	conn = ldap3.Connection(server, auto_bind=True)
	conn.search('ou=People,dc=usb,dc=ve','(uid=%s)' % student_id, attributes=['uid','givenName','sn','personalId','mail','career'])
	
	if conn.entries:
		entry = conn.entries[0]
		if entry.career == 'Ingenieria de Computacion':
			register_user(entry)
			return 'successful registration'
		else:
			return 'not computer science student'
	else:
		return 'id not found'

# Register student in CompuSoft database
def register_user(entry):
	entity = Entity.objects.create(
		profile_photo = 'defaultProfilePhoto.jpg'
	)
	person = Person.objects.create(
		ci = str(entry.personalId),
		name = str(entry.givenName),
		surname = str(entry.sn),
		email = str(entry.mail),
		status = 'student',
		entity = entity,
	)
	user = User.objects.create_user(
		username = str(entry.uid),
		email = str(entry.mail),
		password = str(entry.personalId),
	)
	# Keep only first name
	user.first_name = str(entry.givenName).split()[0]
	user.last_name = str(entry.sn)
	user.save()	
	student = Student.objects.create(
		student_id = str(entry.uid),
		career = str(entry.career),
		person = person,
		user = user,
	)

# Get filename of user profile image
def get_user_image(user):
	student = user.student
	person = student.person
	entity = person.entity
	return str(entity.profile_photo)

# Get information about Compushow categories
def get_categories():
	return Category.objects.all()

# Get student names
def get_students():
	students = Student.objects.all().values(
		'student_id',
		'person__name',
		'person__surname'
	)
	return students

def get_full_name(user):

	if not Student.objects.filter(user = user).exists():
		return None

	student = Student.objects.filter(user = user).first()
	person = student.person
	return person.name + " " + person.surname

def get_full_name_from_entity(entity):

	if not Student.objects.filter(person__entity = entity).exists():
		return None

	student = Student.objects.filter(person__entity = entity).first()
	person = student.person
	return person.name + " " + person.surname

def get_student_id(username):
	students = get_students()
	for student in  students:
		if student['person__name'] + " " + student['person__surname'] == username:
			return student['student_id']
	return None

# Get all nominations user has made
def get_nominations(user):

	nomination_rows = Nominate.objects.filter(nominator = user)
	nominations = []
	categories  = dict()

	for row in nomination_rows:

		if not row.active:
			continue

		nominee_name   = get_full_name_from_entity(row.nominee)
		nominee_carnet = get_student_id(nominee_name)

		nominee_name2   = get_full_name_from_entity(row.nomineeOpt)
		nominee_carnet2 = get_student_id(nominee_name2)

		nominations.append({
			'category':row.category.name,
			'nominee' :nominee_name,
			'carnet':nominee_carnet,
			'nomineeOpt' :nominee_name2,
			'carnet2':nominee_carnet2,
			'comment':row.comment,
			'nominee_entity' :row.nominee.pk,
			'cartoon':row.extra,
		})

		categories[row.category.name] = True

		if row.nomineeOpt is None:
			nominations[-1]['nomineeOpt_entity'] = None
		else:
			nominations[-1]['nomineeOpt_entity'] = row.nomineeOpt.pk

	return nominations, categories

# Checks if user already made this nomination
def already_nominated(user, category, ID1, ID2):
	
	category = Category.objects.filter(name = category).first()
	user   = Student.objects.filter(student_id = user).first().user

	if category.name == 'CompuMaster':
		pass
	
	elif category.name == 'CompuTeam':
		pass
	
	elif category.name == 'CompuAdoptado':
		pass
	
	elif category.name == 'CompuLove':

		if ID1 > ID2:
			ID1, ID2 = ID2, ID1

		entity  = Student.objects.filter(student_id = ID1).first().person.entity
		entity2 = Student.objects.filter(student_id = ID2).first().person.entity
		
		return Nominate.objects.filter(nominator=user, nominee=entity, nomineeOpt=entity2, category=category, active=True).exists()
	
	# Regular category
	else:
		entity = Student.objects.filter(student_id = ID1).first().person.entity
		return Nominate.objects.filter(nominator=user, nominee=entity, category=category, active=True).exists()

def make_nomination_db(user, category, ID1, ID2, comment, extra=None):

	category = Category.objects.filter(name = category).first()
	user   = Student.objects.filter(student_id = user).first().user

	if category.name == 'CompuMaster':
		pass
	
	elif category.name == 'CompuTeam':
		pass
	
	elif category.name == 'CompuAdoptado':
		pass
	
	elif category.name == 'CompuLove':
		ID1	= get_student_id(ID1)
		ID2	= get_student_id(ID2)

		if ID1 > ID2:
			ID1, ID2 = ID2, ID1

		entity  = Student.objects.filter(student_id = ID1).first().person.entity
		entity2 = Student.objects.filter(student_id = ID2).first().person.entity
		Nominate.objects.create(
			nominator = user,
			nominee = entity,
			nomineeOpt = entity2,
			category = category,
			comment = comment
		)

		update_nominee(entity, category, entity2, True)
	
	# Regular category
	else:
		ID1	   = get_student_id(ID1)
		entity = Student.objects.filter(student_id = ID1).first().person.entity
		Nominate.objects.create(
			nominator = user,
			nominee = entity,
			category = category,
			comment = comment,
			extra = extra
		)
		update_nominee(entity, category, None, True, extra)

# Get nomination details
def get_nomination_info(user, category, ID1, ID2):
	
	category = Category.objects.filter(name = category).first()
	user   = Student.objects.filter(student_id = user).first().user

	if category.name == 'CompuMaster':
		pass
	
	elif category.name == 'CompuTeam':
		pass
	
	elif category.name == 'CompuAdoptado':
		pass
	
	elif category.name == 'CompuLove':
		if ID1 > ID2:
			ID1, ID2 = ID2, ID1

		entity  = Student.objects.filter(student_id = ID1).first().person.entity
		entity2 = Student.objects.filter(student_id = ID2).first().person.entity
		
		nom_id  = Nominate.objects.filter(nominator=user, nominee=entity, nomineeOpt=entity2, category=category, active=True).first().id
		comment = Nominate.objects.filter(nominator=user, nominee=entity, nomineeOpt=entity2, category=category, active=True).first().comment
		return nom_id, comment
	
	# Regular category
	else:
		entity  = Student.objects.filter(student_id = ID1).first().person.entity
		nom_id  = Nominate.objects.filter(nominator=user, nominee=entity, category=category, active=True).first().id
		comment = Nominate.objects.filter(nominator=user, nominee=entity, category=category, active=True).first().comment
		return nom_id, comment

# Get nomination cartoon
def get_cartoon(user, ID1):
	
	category = Category.objects.filter(name = 'CompuCartoon').first()
	user   = Student.objects.filter(student_id = user).first().user

	entity  = Student.objects.filter(student_id = ID1).first().person.entity
	cartoon = Nominate.objects.filter(nominator=user, nominee=entity, category=category, active=True).first().extra
	return cartoon

# Get nominee cartoon
def get_cartoon_nominee(entity):
	
	category = Category.objects.filter(name = 'CompuCartoon').first()
	cartoon = Nominate.objects.filter(nominee=entity, category=category, active=True).first().extra
	return cartoon

# Delete nomination
def delete_nomination_db(user, category, ID1, ID2):

	category = Category.objects.filter(name = category).first()
	user   = Student.objects.filter(student_id = user).first().user

	if category.name == 'CompuMaster':
		pass
	
	elif category.name == 'CompuTeam':
		pass
	
	elif category.name == 'CompuAdoptado':
		pass
	
	elif category.name == 'CompuLove':
		
		if ID1 > ID2:
			ID1, ID2 = ID2, ID1

		entity  = Student.objects.filter(student_id = ID1).first().person.entity
		entity2 = Student.objects.filter(student_id = ID2).first().person.entity

		nomination = Nominate.objects.get(nominator=user, nominee=entity, nomineeOpt=entity2, category=category, active=True)
		nomination.active = False
		nomination.save()

		update_nominee(entity, category, entity2, False)

	
	# Regular category
	else:
		entity = Student.objects.filter(student_id = ID1).first().person.entity
		nomination = Nominate.objects.get(nominator=user, nominee=entity, category=category, active=True)
		nomination.active = False
		nomination.save()

		update_nominee(entity, category, None, False)

def get_nominations_profile(studentID):
	
	entity = Student.objects.filter(student_id = studentID).first().person.entity
	nominees_per_category = get_nominees()

	nominations = []
	left = True
	right = False

	for category, nominees in nominees_per_category.items():
		for nominee in nominees:

			if category.name == 'CompuLove':
				if nominee.entity == entity or nominee.entityOpt == entity:
					nomination = dict()
					comments = get_comments(nominee.entity, nominee.entityOpt, category)
					nomination['category']  = category
					if comments:
						nomination['firstcomment'] = comments[0]
					nomination['comments']  = comments[1:]
					nomination['entity']    = get_full_name_from_entity(nominee.entity)
					nomination['entityOpt'] = get_full_name_from_entity(nominee.entityOpt)
					nomination['left'] = left
					nomination['right'] = right
					left = not left
					right = not right
					nominations.append(nomination)

			else:
				# Regular category
				if nominee.entity == entity:
					nomination = dict()
					comments = get_comments(nominee.entity, None, category)
					nomination['category']  = category
					if comments:
						nomination['firstcomment'] = comments[0]
					nomination['comments']  = comments[1:]
					nomination['left'] = left
					nomination['right'] = right

					if category.name == 'CompuCartoon':
						nomination['cartoon'] = get_cartoon_nominee(nominee.entity)

					left = not left
					right = not right
					nominations.append(nomination)

	return nominations

def get_comments(entity, entity2, category):
	
	if category.name == 'CompuLove':
		nomination_rows = Nominate.objects.filter( \
			(Q(nominee=entity) & Q(nomineeOpt=entity2) & Q(category=category)) |  \
			(Q(nomineeOpt=entity) & Q(nominee=entity2) & Q(category=category)))

	else:
		nomination_rows = Nominate.objects.filter(Q(nominee = entity) & Q(category=category))

	comments = []

	for row in nomination_rows:

		if not row.active:
			continue

		if row.comment:
			comments.append(row.comment)

	return comments

# Update nomination counter when nomination is submitted
def update_nominee(entity, category, entity2, add, extra=None):

	if add:
		cnt = 1
	else:
		cnt = -1

	if category.name == 'CompuLove':
		if not Nominee.objects.filter(Q(entity = entity) & Q(entityOpt=entity2) & Q(category = category)).exists():
			Nominee.objects.create(
				nominations = 1,
				entity = entity,
				category = category,
				entityOpt = entity2,
			)
		else:
			nomination = Nominee.objects.get(entity=entity, category=category, entityOpt=entity2)
			nomination.nominations += cnt
			nomination.save()

	else:
		if not Nominee.objects.filter(Q(entity = entity) & Q(category = category)).exists():
			Nominee.objects.create(
				nominations = 1,
				entity = entity,
				category = category,
				entityOpt = entity2,
				extra = extra,
			)
		else:
			nomination = Nominee.objects.get(entity=entity, category=category, entityOpt=entity2)
			nomination.nominations += cnt
			nomination.save()

# Get the nominees for each category
def get_nominees(top = 4):

	categories = get_categories()

	results = dict()

	for category in categories:
		nominees = Nominee.objects.filter(category=category).order_by('-nominations')[:top]
		results[category] = nominees

	return results