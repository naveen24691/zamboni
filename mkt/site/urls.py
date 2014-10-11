from django.conf.urls import include, patterns, url
from django.views.decorators.cache import never_cache

import csp.views
from waffle.views import wafflejs

from . import views


services_patterns = patterns('',
    url('^monitor(.json)?$', never_cache(views.monitor), name='mkt.monitor'),
    url('^loaded$', never_cache(views.loaded), name='mkt.loaded'),
    url('^csp/policy$', csp.views.policy, name='mkt.csp.policy'),
    url('^csp/report$', views.cspreport, name='mkt.csp.report'),
    url('^timing/record$', views.record, name='mkt.timing.record'),
)


urlpatterns = patterns('',
    url('^robots.txt$', views.robots, name='robots.txt'),

    # Replace opensearch.xml from amo with a specific one for Marketplace.
    url('^opensearch.xml$', views.OpensearchView.as_view(), name='opensearch'),

    # These are the new manifest URLs going forward.
    url('^packaged.webapp$', views.package_minifest, name='packaged.webapp'),
    url('^marketplace-package.webapp$', views.yogafire_minifest,
        name='packaged-marketplace.webapp'),

    url(r'^wafflejs$', wafflejs, name='wafflejs'),
    ('^services/', include(services_patterns)),
)
