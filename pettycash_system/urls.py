from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from accounts import views as account_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Django built-in auth URLs (login/logout/password reset)
    path('accounts/', include('django.contrib.auth.urls')),

    # Your own accounts app URLs
    path('accounts/', include('accounts.urls')),

    # Explicit dashboard route
    path('dashboard/', account_views.dashboard, name='dashboard'),

    # Optional: root redirects to dashboard
    path('', account_views.dashboard, name='home'),

    # Other apps
    path('transactions/', include('transactions.urls')),
    path('treasury/', include('treasury.urls')),
    path('workflow/', include('workflow.urls')),
    path('reports/', include('reports.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
