from django.urls import path
from . import views

urlpatterns = [
    path('',                    views.contact_view,      name='home'),
    path('api/chat/',           views.chat_view,          name='api_chat'),
    path('api/match-resume/',   views.match_resume_view,  name='api_match_resume'),
    path('api/github-stats/',   views.github_stats_view,  name='api_github_stats'),
    path('api/track-download/', views.track_download_view,name='api_track_download'),
    path('api/endorse/',        views.endorse_view,        name='api_endorse'),
    path('api/analytics/',      views.analytics_view,      name='api_analytics'),
]