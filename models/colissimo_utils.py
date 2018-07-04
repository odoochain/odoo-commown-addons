from datetime import datetime
from email.parser import Parser
from cgi import parse_header
import json
from base64 import b64decode

import requests
import phonenumbers


MOBILE_TYPE = phonenumbers.PhoneNumberType.MOBILE

BASE_URL = 'https://ws.colissimo.fr/sls-ws/SlsServiceWSRest'


def normalize_phone(phone_number, country_code):
    " Colissimo only accepts french phone numbers "
    if country_code == 'FR' and phone_number:
        tel = phonenumbers.parse(phone_number, country_code)
        return phonenumbers.format_number(
            tel, phonenumbers.PhoneNumberFormat.NATIONAL).replace(' ', '')
    return ''


def parcel_data():
    "Corresponds to a Faiphone parcel right now, to be generalized when needed"
    return {
        'weight': 0.5,              # in kg
        'insuranceValue': 450*100,  # in euro cents
        }


def delivery_data(partner):
    """ Return delivery data for given partner, taking into account:

    - that mobile phone numbers may be found in partner.phone instead
      of partner.mobile: put value into mobile if pertinent
    - delivery contact may be specified on partner
    - delivery contact may not have a copy of partner's phones and address
    - the address lines must not be too long (35 characters was the limit on
      coliship): in such a case, raise ValueError

    """
    mobile, fixed = partner.mobile, partner.phone
    if not mobile and fixed and partner.country_id.code == 'FR':
        fixed_obj = phonenumbers.parse(fixed, 'FR')
        if phonenumbers.number_type(fixed_obj) == MOBILE_TYPE:
            mobile, fixed = fixed, None
    partner_data = {
        'lastName': partner.lastname,
        'firstName': partner.firstname,
        'line2': partner.street,
        'line3': partner.street2 or '',
        'countryCode': partner.country_id.code or 'FR',
        'city': partner.city,
        'zipCode': partner.zip,
        'phoneNumber': normalize_phone(fixed, partner.country_id.code) or '',
        'mobileNumber': normalize_phone(mobile, partner.country_id.code) or '',
        'email': partner.email or '',
    }
    delivery_id = partner.address_get(['delivery'])['delivery']
    if delivery_id == partner.id:
        result_data = partner_data
    else:
        result_data = delivery_data(
            partner.env['res.partner'].browse(delivery_id))
        # Add fallback contact values if not set in delivery contact:
        for attr in 'phoneNumber', 'mobileNumber', 'email':
            if not result_data[attr]:
                result_data[attr] = partner_data[attr]

    for attr in ('line2', 'line3'):
        if len(result_data[attr] or '') > 35:
            raise ValueError('Address too long for %r' % partner.name)

    return result_data


def shipping_data(sender, recipient, order_number, commercial_name,
                  deposit_date=None, format='PDF_A4_300dpi'):
    """ Return colissimo WS shipping data for given arguments.

    The `sender` and `recipient` are odoo res.partner objects.

    The `order_number` argument is a string displayed on the label (on both
    sender and recipient parts).

    The `commercial_name` argument is used in recipient email notifications.

    The `deposit_date` argument is a datetime.Date object (default is today).

    The `format` argument can be one of:
    - "PDF_A4_300dpi" (the default)
    - "PDF_10x15_300dpi"
    """

    if deposit_date is None:
        deposit_date = datetime.today()
    return {
        'outputFormat': {
            'x': 0,
            'y': 0,
            'outputPrintingType': format,
            # 'outputPrintingType': 'PDF_10x15_300dpi',  # cf. doc p27
        },
        'letter': {
            'service': {
                'orderNumber': order_number,  # for coliview
                'productCode': 'DOS',
                'depositDate': deposit_date.strftime('%Y-%m-%d'),
                'commercialName': commercial_name,
            },
            'parcel': parcel_data(),
            'sender': {
                'senderParcelRef': order_number,     # visible on the label
                'address': delivery_data(sender),
            },
            'addressee': {
                'addresseeParcelRef': order_number,  # visible on the label
                'address': delivery_data(recipient)
            }
        }
    }


def parse_multipart(data, boundary):
    # Build a fake email to use email module's multipart parser
    headers = ['From: contact@commown.fr',
               'To: contact@commown.fr',
               'Subject: colissimo',
               'MIME-Version: 1.0',
               'Content-Type: multipart/mixed; ',
               '\tboundary="%s"' % boundary,
               '',
               '',
               ]
    msg = Parser().parsestr('\r\n'.join(headers) + data)

    meta_data, label_data = None, None
    for part in msg.walk():
        ctype = part.get_content_type()
        if ctype.startswith('application/json'):
            meta_data = json.loads(part.get_payload())
        elif ctype.startswith('application/octet-stream'):
            label_data = part.get_payload()
            if part['Content-Transfer-Encoding'] == 'base64':
                label_data = b64decode(label_data)
    return meta_data, label_data


def ship(login, password, sender, recipient, order_number,
         commercial_name, debug=False):
    url = BASE_URL + ('/checkGenerateLabel' if debug else '/generateLabel')
    data = shipping_data(sender, recipient, order_number, commercial_name)
    data.update({'contractNumber': login, 'password': password})
    resp = requests.post(url, json=data)
    resp.raise_for_status()

    ctype_main, ctype_details = parse_header(resp.headers['Content-Type'])
    if ctype_main == 'multipart/mixed':
        return parse_multipart(resp.content, ctype_details['boundary'])
    elif ctype_main == 'application/json':
        return resp.json(), None
    return None, None