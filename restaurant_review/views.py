import uuid
import os
import azureproject.app_insights

from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render
from django.db.models import Avg, Count
from django.urls import reverse
from django.utils import timezone
from django.contrib import messages
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from requests import RequestException, exceptions
from azureproject.get_token import get_token
from azureproject.app_insights import *

from logging import WARNING, getLogger

from restaurant_review.models import Restaurant, Review

from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import trace

from opentelemetry.instrumentation.django import DjangoInstrumentor
# DjangoInstrumentor().instrument(is_sql_commentor_enabled=True)

appKey = os.getenv('APPLICATIONINSIGHTS_CONNECTION_STRING')

# Create your views here.

from opentelemetry.instrumentation.wsgi import collect_request_attributes
from opentelemetry.propagate import extract
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)
from opentelemetry.trace import (
    SpanKind,
    get_tracer_provider,
    set_tracer_provider,
)

import os
import requests
from opentelemetry import trace
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter

# This line causes your calls made with the requests library to be tracked.
DjangoInstrumentor().instrument(is_sql_commentor_enabled=True)

# trace.set_tracer_provider(TracerProvider())
# tracer = trace.get_tracer(__name__)
# exporter = AzureMonitorTraceExporter(
#     connection_string=os.environ["APPLICATIONINSIGHTS_CONNECTION_STRING"]
# )
# span_processor = BatchSpanProcessor(exporter)
# trace.get_tracer_provider().add_span_processor(span_processor)

logger = getLogger(__name__)
logger.setLevel(WARNING)

configure_azure_monitor(
    connection_string=appKey,
    logger_name=__name__,
    logging_level=WARNING,
    tracing_export_interval_ms=15000,
)

tracer = trace.get_tracer(__name__)

set_tracer_provider(TracerProvider())
# tracer = get_tracer_provider().get_tracer(__name__)

# get_tracer_provider().add_span_processor(
#     BatchSpanProcessor(ConsoleSpanExporter())
# )

# from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
# exporter = AzureMonitorTraceExporter(
#     connection_string=appKey
# )

# from azure.monitor.opentelemetry.exporter import AzureMonitorMetricExporter
# exporter = AzureMonitorMetricExporter(
#     connection_string=appKey
# )

# from azure.monitor.opentelemetry.exporter import AzureMonitorLogExporter
# exporter = AzureMonitorLogExporter(
#     connection_string=appKey
# )

def index(request):
    logger.warning('Request for index page received', extra={'index request': request})
    get_token()
    restaurants = Restaurant.objects.annotate(avg_rating=Avg('review__rating')).annotate(review_count=Count('review'))
    return render(request, 'restaurant_review/index.html', {'restaurants': restaurants })


def details(request, id):
    logger.warning('Request for restaurant details page received', extra={'restaurant details request': request})
    get_token()

    # Get account_url based on environment
    account_url = get_account_url()
    image_path = account_url + "/" + os.environ['STORAGE_CONTAINER_NAME']

    try: 
        restaurant = Restaurant.objects.annotate(avg_rating=Avg('review__rating')).annotate(review_count=Count('review')).get(pk=id)
    except Restaurant.DoesNotExist:
        raise Http404("Restaurant doesn't exist")
    return render(request, 'restaurant_review/details.html', {'restaurant': restaurant, 
        'image_path': image_path})


def create_restaurant(request):
    print('Request for add restaurant page received')

    return render(request, 'restaurant_review/create_restaurant.html')

def add_restaurant(request):
    get_token()
    try:
        name = request.POST['restaurant_name']
        street_address = request.POST['street_address']
        description = request.POST['description']
        if (name == "" or description == ""):
            raise RequestException()
    except (KeyError, exceptions.RequestException) as e:
        # Redisplay the restaurant entry form.
        messages.add_message(request, messages.INFO, 'Restaurant not added. Include at least a restaurant name and description.')
        return HttpResponseRedirect(reverse('create_restaurant'))  
    else:
        restaurant = Restaurant()
        restaurant.name = name
        restaurant.street_address = street_address
        restaurant.description = description
        Restaurant.save(restaurant)

        # log a new metric for a review
        # tmap = tag_map_module.TagMap()
        # tmap.insert("name", name)
        # print("tmap is", tmap)
        # record_metric_resturant(tmap)
                
        return HttpResponseRedirect(reverse('details', args=(restaurant.id,)))

def add_review(request, id):
    get_token()
    try: 
        restaurant = Restaurant.objects.annotate(avg_rating=Avg('review__rating')).annotate(review_count=Count('review')).get(pk=id)
    except Restaurant.DoesNotExist:
        raise Http404("Restaurant doesn't exist")

    try:
        user_name = request.POST['user_name']
        rating = request.POST['rating']
        review_text = request.POST['review_text']
        if (user_name == "" or rating == ""):
            raise RequestException()            
    except (KeyError, exceptions.RequestException) as e:
        # Redisplay the details page
        messages.add_message(request, messages.INFO, 'Review not added. Include at least a name and rating for review.')
        return HttpResponseRedirect(reverse('details', args=(id,)))  
    else:

        if 'reviewImage' in request.FILES:
            image_data = request.FILES['reviewImage']
            print("Original image name = " + image_data.name)
            print("File size = " + str(image_data.size))

            if (image_data.size > 2048000):
                messages.add_message(request, messages.INFO, 'Image too big, try again.')
                return HttpResponseRedirect(reverse('details', args=(id,)))  

            # Get account_url based on environment
            account_url = get_account_url()

            # Create client
            azure_credential = DefaultAzureCredential(exclude_shared_token_cache_credential=True)
            blob_service_client = BlobServiceClient(
                account_url=account_url,
                credential=azure_credential)

            # Get file name to use in database
            image_name = str(uuid.uuid4()) + ".png"
            
            # Create blob client
            blob_client = blob_service_client.get_blob_client(container=os.environ['STORAGE_CONTAINER_NAME'], blob=image_name)
            print("\nUploading to Azure Storage as blob:\n\t" + image_name)

            # Upload file
            with image_data as data:
                blob_client.upload_blob(data)
        else:
            # No image for review
            image_name=None

        review = Review()
        review.restaurant = restaurant
        review.review_date = timezone.now()
        review.user_name = user_name
        review.rating = rating
        review.review_text = review_text
        review.image_name = image_name
        Review.save(review)

        # log a new metric for a review
        # tmap = tag_map_module.TagMap()
        # tmap.insert("resturantId", str(id))
        # record_metric_review(tmap)
        
    return HttpResponseRedirect(reverse('details', args=(id,)))

def get_account_url():
    # Create LOCAL_USE_AZURE_STORAGE environment variable to use Azure Storage locally. 
    if 'WEBSITE_HOSTNAME' in os.environ or ("LOCAL_USE_AZURE_STORAGE" in os.environ):
        return "https://%s.blob.core.windows.net" % os.environ['STORAGE_ACCOUNT_NAME']
    else:
        return os.environ['STORAGE_ACCOUNT_NAME']
