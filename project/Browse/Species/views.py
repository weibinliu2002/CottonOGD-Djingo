from django.shortcuts import render
from django.http import HttpResponse
# Create your views here.
def browse_species(request):
    context = {
        'title': '物种浏览',
        'species_list': [
            'Gossypium herbaceum',
            'Gossypium arboreum',
            'Gossypium anomalum',
            'Gossypium sturtianum',
            'Gossypium thurberi',
            'Gossypium armourianum',
            'Gossypium harknessii',
            'Gossypium davidsonii',
            'Gossypium klotzschianum',
            'Gossypium aridum',
            'Gossypium raimondii',
            'Gossypium gossypioides',
            'Gossypium lobatum',
            'Gossypium trilobum',
            'Gossypium laxum',
            'Gossypium turneri',
            'Gossypium schwendimanii',
            'Gossypium stocksii',
            'Gossypium longicalyx',
            'Gossypium bickii',
            'Gossypium australe',
            'Gossypium hirsutum',
            'Gossypium barbadense',
            'Gossypium tomentosum',
            'Gossypium mustelinum',
            'Gossypium darwinii',
            'Gossypium ekmanianum',
            'Gossypium stephensii',
            'Kokia cookei',
            'Kokia drynarioides',
            'Kokia kauaiensis',
            'Gossypioides kirkii'
        ],
    }
    return render(request, 'Species/index.html', context)
    #return HttpResponse("Hello, world. You're at the Species browse.")
