import re, time, argparse
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

site = 'https://unsplash.com/'

response = requests.get(site)

soup = BeautifulSoup(response.text, 'html.parser')
img_tags = soup.find_all('img')

urls = [img['src'] for img in img_tags]


# for url in urls:
# 	print(url)
	
# 	filename = re.search(r'/([\w_-]+[.](jpg|gif|png|bmp|jpeg))$', url)
# 	if not filename:
# 		print("Regex didn't match with the url: {}".format(url))
# 		continue
# 	with open(filename.group(1), 'wb') as f:
# 		if 'http' not in url:
# 			# sometimes an image source can be relative 
# 			# if it is provide the base url which also happens 
# 			# to be the site variable atm. 
# 			url = '{}{}'.format(site, url)
# 		response = requests.get(url)
# 		f.write(response.content)

# class Spider:
# 	def __init__(self, depth, url, path):
# 		self.depth = depth
# 		self.path = path
# 		self.url = url

# 	def download(self):
# 		ALL_LINKS = {
# 			0: [self.url],
# 		}
# 		for i in range(self.depth):
# 			new_links = []
# 			for url in ALL_LINKS[i]:
# 				try:
# 					response = requests.get(url)
# 					soup = BeautifulSoup(response.text, 'html.parser')
# 					links = soup.find_all('a')
# 					urls = [link.get('href') for link in links if link.get('href')]
# 					new_links.extend(urls)
# 				except Exception as e:
# 					print(f"Error processing {url}: {e}")
# 			ALL_LINKS[i + 1] = new_links
# 		print(ALL_LINKS)

class Spider:
	def __init__(self, depth, url, path):
		self.depth = depth
		self.path = path
		self.url = url

	def fetch_links(self, url):
		try:
			response = requests.get(url)
			soup = BeautifulSoup(response.text, 'html.parser')
			links = soup.find_all('a')
			urls = [link.get('href') for link in links if link.get('href')]
			return urls
		except Exception as e:
			print(f"Error processing {url}: {e}")
			return []

	def download(self):
		ALL_LINKS = {
			0: [self.url],
		}
		with ThreadPoolExecutor(max_workers=10) as executor:
			for i in range(self.depth):
				new_links = []
				futures = {executor.submit(self.fetch_links, url): url for url in ALL_LINKS[i]}
				for future in as_completed(futures):
					try:
						result = future.result()
						new_links.extend(result)
					except Exception as e:
						print(f"Error fetching links: {e}")
				ALL_LINKS[i + 1] = new_links
		print(ALL_LINKS)



if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('-r', '--recursive', action='store_true', help="recursively downloads the images in a URL received as a parameter")
	parser.add_argument('-l', '--level', type=int, default=5, help="indicates the maximum depth level of the recursive download. If not indicated, it will be 5")
	parser.add_argument('-p', '--path', type=str, default='./data/', help=" indicates the path where the downloaded files will be saved. If not specified, ./data/ will be used")
	parser.add_argument('url', help="the URL to start downloading from")

	args = parser.parse_args()

	s = Spider(args.level, args.url, args.path)
	s.download()