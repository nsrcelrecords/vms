from django.urls import path
from . import views

urlpatterns = [ \
    path('change_password', views.changePasswordView.as_view(), 
        name='change_password'), 
    path('venture/form/', views.ventureEntryView.as_view(), 
        name='venture_form'), 
    path('participant/form/', views.participantEntryView.as_view(), 
        name='participant_form'), 
    path('venture/', views.ventureTableView.as_view(), 
        name='venture_view'), 
    path('participant/', views.participantTableView.as_view(), 
        name='participant_view'), 
    path('', views.homeView.as_view(), name='home'), 
    path('venture/<int:registration_number>/', 
        views.ventureDetailView.as_view(),name='detail'),
    path('participant/<int:registration_number>/', 
        views.participantDetailView.as_view(),
        name='participant_detail'), 
    path('venture/<int:registration_number>/modify/', 
        views.ventureModifyView.as_view(),name='modify_venture'),
    path('venture/<int:registration_number>/delete/', 
        views.ventureDeleteView.as_view(),name='delete_venture'),
    path('participant/<int:registration_number>/modify/', 
        views.participantModifyView.as_view(),
        name='modify_participant'),
    path('participant/<int:registration_number>/delete/', 
        views.participantDeleteView.as_view(),
        name='delete_participant'),
    ]

