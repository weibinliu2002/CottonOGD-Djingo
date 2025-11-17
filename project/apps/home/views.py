from django.shortcuts import render
from django.views import View

class HomeView(View):
    def get(self, request):
        news_items = [
            {'title': '111111', 'date': '2023-06-01', 'content': '222222222'},
            {'title': '333333333', 'date': '2023-05-15', 'content': '44444444444'},
        ]
        
        context = {
            'news_items': news_items,
        }
        return render(request, 'home/home.html', context)