from django.http import JsonResponse
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
import logging
import json
from .models import CarMake, CarModel
from .restapis import get_request, analyze_review_sentiments, post_review
from .populate import initiate

logger = logging.getLogger(__name__)

@csrf_exempt
def login_user(request):
    """Handle user login and return authentication status"""
    data = json.loads(request.body)
    username = data['userName']
    password = data['password']
    user = authenticate(username=username, password=password)
    
    if user is not None:
        login(request, user)
        return JsonResponse({"userName": username, "status": "Authenticated"}, status=200)
    return JsonResponse({"error": "Invalid credentials"}, status=401)

@csrf_exempt
def logout_request(request):
    """Handle user logout"""
    logout(request)
    return JsonResponse({"userName": ""}, status=200)

@csrf_exempt
def registration(request):
    """Handle new user registration"""
    data = json.loads(request.body)
    username = data['userName']
    
    if User.objects.filter(username=username).exists():
        return JsonResponse({"error": "Username already exists"}, status=409)
        
    user = User.objects.create_user(
        username=username,
        password=data['password'],
        first_name=data['firstName'],
        last_name=data['lastName'],
        email=data['email']
    )
    login(request, user)
    return JsonResponse({"userName": username, "status": "Authenticated"}, status=201)

def get_cars(request):
    """Return all vehicles with make/model information"""
    if CarMake.objects.count() == 0:
        initiate()
    
    cars = [{
        "CarModel": model.name, 
        "CarMake": model.car_make.name
    } for model in CarModel.objects.select_related('car_make')]
    
    return JsonResponse({"CarModels": cars}, status=200)

def get_dealerships(request, state="All"):
    """Return dealerships by state (all if no state specified)"""
    endpoint = f"/fetchDealers/{state}" if state != "All" else "/fetchDealers"
    dealerships = get_request(endpoint)
    return JsonResponse({"dealers": dealerships}, status=200)

def get_dealer_details(request, dealer_id):
    """Return details for a specific dealer"""
    if not dealer_id:
        return JsonResponse({"error": "Dealer ID required"}, status=400)
        
    endpoint = f"/fetchDealer/{dealer_id}"
    dealer = get_request(endpoint)
    return JsonResponse({"dealer": dealer}, status=200)

def get_dealer_reviews(request, dealer_id):
    """Return reviews for a specific dealer with sentiment analysis"""
    if not dealer_id:
        return JsonResponse({"error": "Dealer ID required"}, status=400)
    
    endpoint = f"/fetchReviews/dealer/{dealer_id}"
    reviews = get_request(endpoint)
    
    for review in reviews:
        review['sentiment'] = analyze_review_sentiments(review['review'])['sentiment']
    
    return JsonResponse({"reviews": reviews}, status=200)

@csrf_exempt
def add_review(request):
    """Submit a new review for a dealership"""
    if request.user.is_anonymous:
        return JsonResponse({"error": "Authentication required"}, status=403)
    
    try:
        data = json.loads(request.body)
        post_review(data)
        return JsonResponse({"status": "Review posted"}, status=201)
    except Exception as e:
        logger.error(f"Review post error: {str(e)}")
        return JsonResponse({"error": "Failed to post review"}, status=500)