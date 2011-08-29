"""
:synopsis: remaining "secondary" views for askbot

This module contains a collection of views displaying all sorts of secondary and mostly static content.
"""
from django.core.urlresolvers import reverse
from django.db.models import Max, Count
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext, Template
from django.views import static
from django.views.decorators import csrf
from django.utils.translation import ugettext as _
from askbot.forms import FeedbackForm
from django_extra_form_fields.fields import get_next_url
from askbot.utils.mail import mail_moderators
from askbot.models import BadgeData, Award, User
from askbot.models import badges as badge_data
from askbot.skins.loaders import get_template, render_text_into_skin
from askbot.conf import settings as askbot_settings
from askbot import skins

def generic_view(request, template = None, page_class = None):
    """this may be not necessary"""
    #todo - is this used anywhere besides this file?
    return render_to_response(template, RequestContext(request, {'page_class': page_class}))

def config_variable(request, variable_name = None, mimetype = None):
    """Print value from the configuration settings
    as response content. All parameters are required.
    """
    output = getattr(askbot_settings, variable_name, '')
    return HttpResponse(output, mimetype = mimetype)

def about(request, template='about.html'):
    return generic_view(request, template = template, page_class = 'meta') 

def page_not_found(request, template='404.html'):
    return generic_view(request, template) 

def server_error(request, template='500.html'):
    return generic_view(request, template) 

def faq(request):
    if getattr(askbot_settings, 'FORUM_FAQ',''):
        text = _(getattr(askbot_settings, 'FORUM_FAQ',''))
        data = {
            'gravatar_faq_url': reverse('faq') + '#gravatar',
            #'send_email_key_url': reverse('send_email_key'),
            'ask_question_url': reverse('ask'),
            'page_class': 'meta',
        }
        forum_faq = render_text_into_skin(text, data, request)
        data_out = {
            'gravatar_faq_url': reverse('faq') + '#gravatar',
            #'send_email_key_url': reverse('send_email_key'),
            'ask_question_url': reverse('ask'),
            'page_class': 'meta',
            'forum_faq' : forum_faq,
        }
        return render_to_response('faq.html', RequestContext(request, data_out))
    data = {
        'gravatar_faq_url': reverse('faq') + '#gravatar',
        #'send_email_key_url': reverse('send_email_key'),
        'ask_question_url': reverse('ask'),
        'page_class': 'meta',
    }   
    return render_to_response('faq_static.html', RequestContext(request, data))

@csrf.csrf_protect
def feedback(request):
    data = {'page_class': 'meta'}
    form = None
    if request.method == "POST":
        form = FeedbackForm(request.POST)
        if form.is_valid():
            if not request.user.is_authenticated:
                data['email'] = form.cleaned_data.get('email',None)
            data['message'] = form.cleaned_data['message']
            data['name'] = form.cleaned_data.get('name',None)
            template = get_template('feedback_email.txt', request)
            message = template.render(RequestContext(request, data))
            mail_moderators(_('Q&A forum feedback'), message)
            msg = _('Thanks for the feedback!')
            request.user.message_set.create(message=msg)
            return HttpResponseRedirect(get_next_url(request))
    else:
        form = FeedbackForm(initial={'next':get_next_url(request)})

    data['form'] = form
    return render_to_response('feedback.html', RequestContext(request, data))
feedback.CANCEL_MESSAGE=_('We look forward to hearing your feedback! Please, give it next time :)')

def privacy(request):
    return render_to_response('privacy.html', RequestContext(request, {'page_class': 'meta'}))

def badges(request):#user status/reputation system
    #todo: supplement database data with the stuff from badges.py
    known_badges = badge_data.BADGES.keys() 
    badges = BadgeData.objects.filter(slug__in = known_badges).order_by('slug')
    my_badges = []
    if request.user.is_authenticated():
        my_badges = Award.objects.filter(
                                user=request.user
                            ).values(
                                'badge_id'
                            ).distinct()
        #my_badges.query.group_by = ['badge_id']

    data = {
        'active_tab': 'badges',
        'badges' : badges,
        'page_class': 'meta',
        'mybadges' : my_badges,
        'feedback_faq_url' : reverse('feedback'),
    }
    return render_to_response('badges.html', RequestContext(request, data))

def badge(request, id):
    #todo: supplement database data with the stuff from badges.py
    badge = get_object_or_404(BadgeData, id=id)
    badge_recipients = User.objects.filter(
                            award_user__badge = badge
                        ).annotate(
                            last_awarded_at = Max('award_user__awarded_at'),
                            award_count = Count('award_user')
                        ).order_by(
                            '-last_awarded_at'
                        )

    data = {
        'active_tab': 'badges',
        'badge_recipients' : badge_recipients,
        'badge' : badge,
        'page_class': 'meta',
    }
    return render_to_response('badge.html', RequestContext(request, data))

def media(request, skin, resource):
    """view that serves static media from any skin
    uses django static serve view, where document root is
    adjusted according to the current skin selection

    in production this views should be by-passed via server configuration
    for the better efficiency of serving static files
    """
    dir = skins.utils.get_path_to_skin(skin)
    return static.serve(request, '/media/' + resource, document_root = dir)
