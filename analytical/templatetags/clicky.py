"""
Clicky template tags and filters.
"""

from __future__ import absolute_import

import re

from django.template import Library, Node, TemplateSyntaxError
from django.utils import simplejson

from analytical.utils import get_identity, is_internal_ip, disable_html, \
        get_required_setting


SITE_ID_RE = re.compile(r'^\d{8}$')
TRACKING_CODE = """
    <script type="text/javascript">
    var clicky = { log: function(){ return; }, goal: function(){ return; }};
    var clicky_site_id = %(site_id)s;
    var clicky_custom = %(custom)s;
    (function() {
      var s = document.createElement('script');
      s.type = 'text/javascript';
      s.async = true;
      s.src = ( document.location.protocol == 'https:' ? 'https://static.getclicky.com/js' : 'http://static.getclicky.com/js' );
      ( document.getElementsByTagName('head')[0] || document.getElementsByTagName('body')[0] ).appendChild( s );
    })();
    </script>
    <noscript><p><img alt="Clicky" width="1" height="1" src="http://in.getclicky.com/%(site_id)sns.gif" /></p></noscript>
"""


register = Library()


@register.tag
def clicky(parser, token):
    """
    Clicky tracking template tag.

    Renders Javascript code to track page visits.  You must supply
    your Clicky Site ID (as a string) in the ``CLICKY_SITE_ID``
    setting.
    """
    bits = token.split_contents()
    if len(bits) > 1:
        raise TemplateSyntaxError("'%s' takes no arguments" % bits[0])
    return ClickyNode()

class ClickyNode(Node):
    def __init__(self):
        self.site_id = get_required_setting('CLICKY_SITE_ID', SITE_ID_RE,
                "must be a string containing an eight-digit number")

    def render(self, context):
        custom = {}
        for dict_ in context:
            for var, val in dict_.items():
                if var.startswith('clicky_'):
                    custom[var[7:]] = val
        if 'username' not in custom.get('session', {}):
            identity = get_identity(context, 'clicky')
            if identity is not None:
                custom.setdefault('session', {})['username'] = identity

        html = TRACKING_CODE % {'site_id': self.site_id,
                'custom': simplejson.dumps(custom)}
        if is_internal_ip(context, 'CLICKY'):
            html = disable_html(html, 'Clicky')
        return html


def contribute_to_analytical(add_node):
    ClickyNode()  # ensure properly configured
    add_node('body_bottom', ClickyNode)