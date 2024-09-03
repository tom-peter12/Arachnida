from django.shortcuts import render
from .spider import Spider
import os
from django.conf import settings

# Create your views here.
def home(requests):
	context = {"data": [x for x in range(10)]}
	return render(requests, 'index.html', context)

def spider(request):
	if request.method == 'POST':
		url = request.POST.get('url')
		levels = int(request.POST.get('levels', 5))
		recursive = request.POST.get('recursive') == 'on'
		download_path = './downloaded_images/'

		spider = Spider(recursive, levels, url, download_path)
		image_links = spider.download()




		context = {
			'url': url,
			'levels': levels,
			'recursive': recursive,
			'image_links': image_links,
			'message': 'Spider started successfully!'
		}

		return render(request, 'spider.html', context)

	return render(request, 'spider.html')
