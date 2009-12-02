from __future__ import with_statement

import decimal
import socket
import urllib
import urllib2
import urlparse

try:
    from lxml import etree
except ImportError:
    try:
        import xml.etree.cElementTree as etree
    except ImportError:
        import xml.etree.ElementTree as etree

from conf import (MOLLIE_TEST, MOLLIE_API_URL, MOLLIE_BANKS_FILE, MOLLIE_TIMEOUT,
                  MOLLIE_BTW, MOLLIE_TRANSACTION_FEE)

socket.setdefaulttimeout(MOLLIE_TIMEOUT)

def get_mollie_banklist(file=MOLLIE_BANKS_FILE):
    with open(file, 'r') as f:
        tree = etree.parse(f)
        banks = tree.getiterator('bank')
        choices = ((bank.findtext('bank_id'), bank.findtext('bank_name')) for bank in banks)
    return tuple(choices)

def query_mollie(request_dict,
                 base_url=MOLLIE_API_URL,
                 testmode=MOLLIE_TEST,
                 mode=None, valid_modes=('check', 'fetch')):
    response_dict = {}
    scheme, netloc, path, query, fragment = urlparse.urlsplit(base_url)
    if testmode:
        request_dict['testmode'] = 'true'
    if mode in valid_modes:
        request_dict['a'] = mode
    else:
        err = "Invalid mode '%s'. Valid modes are '%s' and '%s'." % (mode, valid_modes)
        raise ValueError(err)
    query = urllib.urlencode(request_dict)
    url = urlparse.urlunsplit((scheme, netloc, path, query, fragment))
    data = urllib2.urlopen(url)
    tree = etree.parse(data)
    order = tree.find('order')
    response_dict['amount'] = decimal.Decimal(order.findtext('amount')) / 100
    response_dict['transaction_id'] = order.findtext('transaction_id')
    if mode == 'fetch':
        response_dict['order_url'] = order.findtext('URL')
    elif mode == 'check':
        response_dict['paid'] = order.findtext('payed') # sic!
        if response_dict['paid'] == 'true':
            consumer = order.find('consumer')
            response_dict['consumerAcount'] = consumer.findtext('consumerAccount')
            response_dict['consumerCity'] = consumer.findtext('consumerCity')
            response_dict['consumerName'] = consumer.findtext('consumerName')
    return response_dict

def get_mollie_fee(btw=MOLLIE_BTW, fee=MOLLIE_TRANSACTION_FEE):
    if not isinstance(btw, int):
        err = "%s is type '%s'. It should be type 'int'." % (btw, type(btw).__name__)
        raise TypeError(err)
    if not isinstance(fee, str):
        err = "%s is type '%s'. It should be type 'str'." % (fee, type(fee).__name__)
        raise TypeError(err)
    btw = decimal.Decimal(btw)
    fee = decimal.Decimal(fee)
    fee += ((btw / 100) * fee)
    return fee.quantize(decimal.Decimal(10) ** -2)
