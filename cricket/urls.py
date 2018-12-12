from django.urls import path
from . import views

urlpatterns = [ \
    path('token/form/', views.tokenEntryView.as_view(), 
    name='token_form'),
    path('participant/', views.iTokenTableView.as_view(), 
    name='participant_view'),
    path('visitor/', views.vTokenTableView.as_view(), 
    name='visitor_view'),
    path('approve/', views.approveView.as_view(), 
    name='approve_view'),
    path('approve/<slug:session_id>/', 
        views.approveView.as_view(),name='approve_session'),
    path('gettoken/', views.getTokenView.as_view(), 
    name='get_token'),
    path('gettokenv/', views.getTokenVisitorView.as_view(), 
    name='get_token_v'),
    ]

