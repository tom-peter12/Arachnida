from urllib.parse import urljoin, urlparse, urlunparse
import os, logging, hashlib, argparse, asyncio, aiohttp, datetime, json
from urllib.robotparser import RobotFileParser
from lxml import html
from rich_argparse import RichHelpFormatter
from concurrent.futures import ThreadPoolExecutor
from collections import deque
from aiohttp import ClientResponseError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'bmp'}

SIGNATURE = f'''
	███████╗██████╗ ██╗██████╗ ███████╗██████╗ 
	██╔════╝██╔══██╗██║██╔══██╗██╔════╝██╔══██╗
	███████╗██████╔╝██║██║  ██║█████╗  ██████╔╝
	╚════██║██╔═══╝ ██║██║  ██║██╔══╝  ██╔══██╗
	███████║██║     ██║██████╔╝███████╗██║  ██║
	╚══════╝╚═╝     ╚═╝╚═════╝ ╚══════╝╚═╝  ╚═╝
'''

class SpiderException(Exception):
	pass

class Node:
	def __init__(self, url, depth):
		self.url = url
		self.depth = depth
		self.children = []

class Spider:
	def __init__(self, recr, depth, url, path):
		self.depth = depth if recr else 0
		self.path = path
		self.root = Node(url, 0)
		self.img_links = []
		self.recr = recr
		self.visited_urls = set()
		self.rp = RobotFileParser()

		self.create_folder()
		self.executor = ThreadPoolExecutor(max_workers=10)

	def create_folder(self):
		try:
			if os.path.exists(self.path):
				if not os.path.isdir(self.path):
					raise SpiderException(f"Path '{self.path}' is not a directory")
				if os.listdir(self.path):
					confirmation = input(f"Directory '{self.path}' is not empty. Do you want to continue? (yes/no): ").strip().lower()
					if confirmation != 'yes':
						raise SpiderException("Operation cancelled by user")
			os.makedirs(self.path, exist_ok=True)
		except Exception as e:
			raise SpiderException(f'Failed to create folder: {e}')

	@staticmethod
	async def does_robotstxt_exist(session, url):
		try:
			async with session.get(url) as response:
				if response.status < 400:
					return True
				elif response.headers.get('Content-Type', '').startswith('application/json'):
					json_response = await response.json()
					if isinstance(json_response, dict) and 'messages' in json_response:
						for message in json_response['messages']:
							if message.get('type') == 'error' and message.get('message') == 'Not Found':
								return False
				return False
		except (ClientResponseError, json.JSONDecodeError, KeyError, AttributeError):
			return False

	async def fetch_with_redirect_loop_detection(self, session, url):
		visited_urls = set()
		max_redirects = 5

		for _ in range(max_redirects):
			if url in visited_urls:
				logging.error(f"Circular redirect detected: {url}")
				return None
			visited_urls.add(url)

			async with session.get(url, allow_redirects=False) as response:
				if 300 <= response.status < 400:
					new_url = response.headers.get('Location')
					if new_url is None:
						logging.error(f"Redirect with no 'Location' header from {url}")
						return None
					url = urljoin(url, new_url)
					logging.info(f"Redirecting to {new_url}")
				else:
					return await response.text()

		logging.error(f"Too many redirects for {url}")
		return None
	
	def normalize_url(self, url):
		parsed_url = urlparse(url)
		parsed_url = parsed_url._replace(fragment='')
		if parsed_url.path in ['/index.html', '/index']:
			parsed_url = parsed_url._replace(path='/')
		return urlunparse(parsed_url)

	async def fetch_links(self, session, url):
		normalized_url = self.normalize_url(url)
		if normalized_url in self.visited_urls:
			return set()

		self.visited_urls.add(normalized_url)
		try:
			content = await self.fetch_with_redirect_loop_detection(session, normalized_url)
			if content is None:
				return set()

			tree = html.fromstring(content)

			links = {self.normalize_url(urljoin(normalized_url, a).lower()) for a in tree.xpath('//a/@href')}
			img_urls = [
				urljoin(normalized_url, img).lower()
				for img in tree.xpath('//img/@src')
				if os.path.splitext(img)[1][1:].lower() in ALLOWED_IMAGE_EXTENSIONS
			]
			self.img_links.extend(img_urls)
			logging.info(f"Found {len(img_urls)} images on {normalized_url}")
			return links
		except Exception as e:
			logging.error(f"Error fetching links from {normalized_url}: {e}")
			return set()


	async def download_image(self, session, img_url):
		try:
			parsed_url = urlparse(img_url)
			robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
			self.rp.set_url(robots_url)
			if await self.does_robotstxt_exist(session, robots_url):
				await asyncio.to_thread(self.rp.read)
				if not self.rp.can_fetch("*", img_url):
					logging.warning(f"Robots.txt disallows fetching {img_url}")
					return

			async with session.get(img_url, allow_redirects=True) as response:
				if response.status != 200:
					logging.warning(f"Failed to download {img_url}: Status {response.status}")
					return
				if 'image' not in response.headers.get('Content-Type', ''):
					logging.warning(f"Content-Type is not an image for {img_url}")
					return
				content = await response.read()

			img_name = await asyncio.get_event_loop().run_in_executor(self.executor, lambda: hashlib.md5(img_url.encode() + str(datetime.datetime.now()).encode()).hexdigest())
			img_path = os.path.join(self.path, img_name + os.path.splitext(parsed_url.path)[1])

			with open(img_path, 'wb') as img_file:
				img_file.write(content)
				logging.info(f'Downloaded {img_url}')
		except Exception as e:
			logging.error(f'Failed to download {img_url}: {e}')

	async def process_url(self, session, parent_node):
		new_links = await self.fetch_links(session, parent_node.url)
		next_depth = parent_node.depth + 1

		for link in new_links:
			if link not in self.visited_urls and next_depth <= self.depth:
				child_node = Node(link, next_depth)
				parent_node.children.append(child_node)

	async def download(self):
		timeout = aiohttp.ClientTimeout(total=60)
		async with aiohttp.ClientSession(headers={'User-Agent': 'spider/1.0'}, timeout=timeout) as session:
			queue = deque([self.root])
			image_tasks = set()

			while queue:
				current_node = queue.popleft()

				await self.process_url(session, current_node)

				for img_url in set(self.img_links):
					if img_url not in self.visited_urls:
						image_tasks.add(asyncio.create_task(self.download_image(session, img_url)))

				self.img_links.clear()

				for child in current_node.children:
					if child.url not in self.visited_urls:
						queue.append(child)

			await asyncio.gather(*image_tasks)

		print("\n🎉 **Download Completed!**")
		print(f"📂 **Downloaded Images are saved in '{self.path}'**")
		self.print_tree()


	def print_tree(self, filename="url_tree.txt"):
		def print_node(node, file, prefix="", is_last=True):
			file.write(f"{prefix}{'└── ' if is_last else '├── '}{node.url}\n")
			for i, child in enumerate(node.children):
				print_node(child, file, prefix + ('    ' if is_last else '│   '), i == len(node.children) - 1)

		with open(filename, "w") as file:
			file.write("🌳 **URL Tree Structure:**\n")
			print_node(self.root, file)


class ArgParser:
	def check_positive(self, value):
		ivalue = int(value)
		if ivalue <= 0:
			raise argparse.ArgumentTypeError("%s is an invalid positive int value" % value)
		return ivalue

	def validate_and_confirm(self, args):
		print(SIGNATURE)
		print("\n" + "=" * 64)
		print("📋 **Please Confirm Your Settings Before Starting the Download**")
		print("=" * 64)

		print(f"🔄 **Recursive**: {'Yes' if args.recursive else 'No'}")
		print(f"📊 **Level**: {args.level} (default)" if args.level == 5 else f"📊 **Level**: {args.level}")
		print(f"📂 **Path**: {args.path} (default)" if args.path == './data/' else f"📂 **Path**: {args.path}")
		print(f"🌐 **URL**: {args.URL}")

		print("=" * 64)
		while True:
			confirmation = input("✅ Is the above information correct? (yes/no): ").strip().lower()
			if confirmation == 'yes':
				print("\n✔️ **Confirmation Received. Starting Download...**\n")
				return True
			elif confirmation == 'no':
				return False
			else:
				print("\n❌ **Invalid input. Please provide a valid input.**\n")

	def __init__(self):
		self.parser = argparse.ArgumentParser(
			description="A tool to download images from a URL with optional recursive depth.",
			formatter_class=RichHelpFormatter
		)
		self.parser.add_argument(
			'-r', '--recursive',
			action='store_true',
			help="Recursively downloads the images in the specified URL."
		)
		self.parser.add_argument(
			'-l', '--level',
			type=self.check_positive,
			default=5,
			help="Depth of recursion when using the recursive flag."
		)
		self.parser.add_argument(
			'-p', '--path',
			type=str,
			default='./data/',
			help="The path to save the downloaded images."
		)
		self.parser.add_argument(
			'URL',
			type=str,
			help="The URL from which to start downloading."
		)

	def parse_args(self):
		args = self.parser.parse_args()
		if self.validate_and_confirm(args):
			return args
		else:
			raise SystemExit("\n❌ **Operation Cancelled. Please provide the correct information and try again.**\n")

async def main():
	args = ArgParser().parse_args()
	try:
		s = Spider(args.recursive, args.level, args.URL, args.path)
		await s.download()
	except SpiderException as e:
		logging.error(f"Spider failed: {e}")

if __name__ == "__main__":
	asyncio.run(main())
