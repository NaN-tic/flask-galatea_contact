#This file is part contact blueprint for Flask.
#The COPYRIGHT file at the top level of this repository contains
#the full copyright notices and license terms.
import os
from flask import Blueprint, request, render_template, flash, current_app, abort
from flask_babel import gettext as _, lazy_gettext
from flask_wtf import FlaskForm as Form
from wtforms import StringField, TextAreaField, validators
from galatea.tryton import tryton
from trytond.sendmail import sendmail_transactional, get_smtp_server, SMTPDataManager
from smtplib import SMTPAuthenticationError
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import charset

contact = Blueprint('contact', __name__, template_folder='templates')


class ContactForm(Form):
    "Contact form"
    name = StringField(lazy_gettext('Name'), [validators.DataRequired()])
    email = StringField(lazy_gettext('Email'), [validators.DataRequired(), validators.Email()])
    phone = StringField(lazy_gettext('Phone'))
    description = TextAreaField(lazy_gettext('Description'), [validators.DataRequired()])

    def __init__(self, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)

    def validate(self):
        rv = Form.validate(self)
        if not rv:
            return False
        return True

    def reset(self):
        self.description.data = ''


class Contact(object):
    '''
    This object is used to hold the settings used for contact configuration.
    '''
    def __init__(self, app=None):
        self.contact_form = ContactForm

        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        if not hasattr(app, 'extensions'):
            app.extensions = {}
        app.extensions['Contact'] = self


def send_email(data):
    """
    Send an contact email
    :param data: dict
    """
    mail_sender = current_app.config.get('DEFAULT_MAIL_SENDER')
    contat_sender = current_app.config.get('MAIL_CONTACT')
    from_addr = os.environ.get('TRYTOND_EMAIL__FROM', mail_sender)
    to_addr = ', '.join([contat_sender, data.get('email')])
    subject =  '%s - %s' % (current_app.config.get('TITLE'), _('New request'))
    plain = render_template('emails/contact-text.jinja', data=data)
    html = render_template('emails/contact-html.jinja', data=data)

    msg = MIMEMultipart()
    charset.add_charset('utf-8', charset.QP, charset.QP)
    msg['From'] = from_addr
    msg['To'] = to_addr
    msg['Subject'] = Header(subject, 'utf-8')

    body = MIMEMultipart('alternative')
    body.attach(MIMEText(plain, 'plain', _charset='utf-8'))
    body.attach(MIMEText(html, 'html', _charset='utf-8'))
    msg.attach(body)

    try:
        datamanager = SMTPDataManager()
        datamanager._server = get_smtp_server()
        sendmail_transactional(from_addr, [to_addr], msg, datamanager=datamanager)
    except SMTPAuthenticationError as e:
        current_app.logger.error('Error send email!')
        current_app.logger.error(str(e))
        abort(500)

@contact.route("/", methods=["GET", "POST"], endpoint="contact")
@tryton.transaction()
def contact_details(lang):
    form = current_app.extensions['Contact'].contact_form()
    if form.validate_on_submit():
        data = {
            'name': request.form.get('name'),
            'email': request.form.get('email'),
            'phone': request.form.get('phone'),
            'description': request.form.get('description'),
            }
        send_email(data)
        flash(_('Your comment was submitted and will be answered to as soon ' \
            'as possible. Thank you for contacting us.'))
        form.reset()

    return render_template('contact.html', form=form)
