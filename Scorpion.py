from rich_argparse import RichHelpFormatter
import os, exifread, argparse
from colorama import Fore, Style
from PIL import Image
import tkinter as tk
import tkinter.font as tkFont
import tkinter.ttk as ttk

ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'bmp'}

SIGNATURE = f'''

	███████╗ ██████╗ ██████╗ ██████╗ ██████╗ ██╗ ██████╗ ███╗   ██╗
	██╔════╝██╔════╝██╔═══██╗██╔══██╗██╔══██╗██║██╔═══██╗████╗  ██║
	███████╗██║     ██║   ██║██████╔╝██████╔╝██║██║   ██║██╔██╗ ██║
	╚════██║██║     ██║   ██║██╔══██╗██╔═══╝ ██║██║   ██║██║╚██╗██║
	███████║╚██████╗╚██████╔╝██║  ██║██║     ██║╚██████╔╝██║ ╚████║
	╚══════╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═══╝

'''

class ExifGUI(object):
	header = ['EXIFTag', 'Value']

	def __init__(self, exif_data):
		self.tree = None
		self.exif_data = exif_data
		self._setup_widgets()
		self._build_tree()

	def _setup_widgets(self):

		msg = ttk.Label(wraplength="10i", justify="left", anchor="n")
		msg.pack(fill='x')

		container = ttk.Frame()
		container.pack(fill='both', expand=True)

		self.tree = ttk.Treeview(columns=ExifGUI.header, show="headings")
		vsb = ttk.Scrollbar(orient="vertical",
			command=self.tree.yview)
		hsb = ttk.Scrollbar(orient="horizontal",
			command=self.tree.xview)
		self.tree.configure(yscrollcommand=vsb.set,
			xscrollcommand=hsb.set)
		self.tree.grid(column=0, row=0, sticky='nsew', in_=container)
		vsb.grid(column=1, row=0, sticky='ns', in_=container)
		hsb.grid(column=0, row=1, sticky='ew', in_=container)

		container.grid_columnconfigure(0, weight=1)
		container.grid_rowconfigure(0, weight=1)

	def _build_tree(self):
		for col in ExifGUI.header:
			self.tree.heading(col, text=col.title())
			self.tree.column(col, width=tkFont.Font().measure(col.title() + '        '))

		for item in self.exif_data:
			self.tree.insert('', 'end', values=item)
			for ix, val in enumerate(item):
				col_w = tkFont.Font().measure(val)
				if self.tree.column(ExifGUI.header[ix], width = None) < col_w:
					self.tree.column(ExifGUI.header[ix], width = col_w)

class ExtractExifException(Exception):
	pass

class ExtractExif:
	def __init__(self, img_files):
		self.img_files = set(img_files)


	def prettified_display(self, img_file, img_exif_data):
		default_width = 60
		file_name_width = len(img_file) + 2
		card_width = max(default_width, file_name_width)
		total_width = card_width + 25

		print(Fore.YELLOW + "╔" + "═" * total_width + "╗" + Fore.WHITE)
		print(Fore.YELLOW + "║" + " " * ((total_width - 12) // 2) + "EXIF DATA CARD" + " " * ((total_width - 14) // 2) + "║" + Fore.WHITE)
		print(Fore.YELLOW + "╠" + "═" * 31 + "╦" + "═" * (card_width - 8) + "═╣" + Fore.WHITE)

		print(f"║ File Name                     ║ {Fore.BLUE}{img_file:{card_width - 8}}{Fore.YELLOW}║{Fore.WHITE}")
		print(Fore.YELLOW + "╠" + "═" * 31 + "╬" + "═" * (card_width - 7) + "╣" + Fore.WHITE)

		for tag, value in img_exif_data.items():
			if tag == "JPEGThumbnail":
				continue
			tag_str = str(tag)

			val = str(value) if value is not None else ""
			lines = [val[i:i+card_width] for i in range(0, len(val), card_width)]

			if not lines:
				lines = [""]

			print(f"║ {tag_str[:29]:<30}║ {Fore.GREEN}{lines[0]:{card_width - 9}}{Fore.YELLOW}║{Fore.WHITE}")

			for line in lines[1:]:
				print(f"║       {'':<24}║ {Fore.GREEN}{line:{(card_width - 10)}} {Fore.YELLOW}║{Fore.WHITE}")

			print(Fore.YELLOW + "╠" + "═" * 31 + "╬" + "═" * (card_width - 8) + "╣" + Fore.WHITE)

		print(Fore.YELLOW + "╚" + "═" * total_width + "╝" + Fore.WHITE)
		print(Style.RESET_ALL)

	def extract_all(self, graphical):
		try:
			for img_file in self.img_files:
				if not (os.path.splitext(img_file)[1][1:].lower() in ALLOWED_IMAGE_EXTENSIONS):
					raise ExtractExifException('Brev please provide a valid filetype')
				else:
					with open(img_file, 'rb') as f:
						img_exif = exifread.process_file(f)
						if not graphical:
							self.prettified_display(img_file, img_exif)
						else:
							exif_array = []
							for tag, value in img_exif.items():
								if tag == "JPEGThumbnail":
									continue
								tag_str = str(tag)
								val = str(value) if value is not None else ""
								exif_array.append([tag_str, val])
							root = tk.Tk()
							root.wm_title("Scorpion")
							mc_listbox = ExifGUI(exif_array)
							root.mainloop()
		except Exception as e:
			print(e)


	def delete_exif(self):
		try:
			for img_file in self.img_files:
				if not (os.path.splitext(img_file)[1][1:].lower() in ALLOWED_IMAGE_EXTENSIONS):
					raise ExtractExifException('Brev please provide a valid filetype')
				else:
					image = Image.open(img_file)
					data = list(image.getdata())
					image_without_exif = Image.new(image.mode, image.size)
					image_without_exif.putdata(data)
					image_without_exif.save(os.path.splitext(img_file)[0] + "_no_exif" + os.path.splitext(img_file)[1])
					print(f"{Fore.GREEN}Exif data deleted successfully from {img_file}{Fore.WHITE}")
		except Exception as e:
			print(e)
	
	def edit_exif(self):
		try:
			with open(self.img_files.pop(), 'rb') as f:
				img_exif = exifread.process_file(f)
				print(f"{Fore.RED}Note: Please provide the Tag first and then value{Fore.WHITE}")
				tag = input(f"{Fore.RED}Enter the tag to edit: {Fore.WHITE}")
				if tag in img_exif.keys():
					value = input(f"{Fore.RED}Enter the value: {Fore.WHITE}")
					img_exif[tag] = value
					print(f"{Fore.GREEN}Exif data edited successfully{Fore.WHITE}")
				else:
					print(f"{Fore.RED}Tag not found{Fore.WHITE}")

		except Exception as e:
			print(e)

def main():
	parser = argparse.ArgumentParser(
		description="A tool to manage exif data of image/images",
		formatter_class=RichHelpFormatter
	)
	group = parser.add_mutually_exclusive_group()
	parser.add_argument(
		'imagefiles',
		metavar='F',
		type=str,
		nargs='+',
		help='A list of image files to process'
	)
	parser.add_argument(
		'-v', '--version',
		action='version',
		version='%(prog)s 1.0'
	)

	group.add_argument(
		'-d', '--delete',
		action='store_true',
		help='Delete the the exif data from the image/images'
	)

	group.add_argument(
		'-e', '--edit',
		action='store_true',
		help='Edit the exif data of the image/images'
	)

	group.add_argument(
		'-g', '--graphical',
		action='store_true',
		help='Display the exif data in a graphical format'
	)

	args = parser.parse_args()
	extractor = ExtractExif(args.imagefiles)
	if args.graphical and len(args.imagefiles) > 1:
		print(f"{Fore.RED}Sorry, Scorpion can only display exif data of one image in graphical format{Fore.WHITE}")
		return
	print(SIGNATURE)
	if args.delete:
		extractor.delete_exif()
		return
	if args.edit:
		extractor.edit_exif()
		return
	confirmation = input(f"{Fore.RED}Do you want to extract exif data from the image/images? (yes/n): {Fore.WHITE}")
	if confirmation.lower() == 'yes':
		extractor.extract_all(args.graphical)
	else:
		print(f"{Fore.RED}Exiting...{Fore.WHITE}")


if __name__ == "__main__":
	try:
		main()
	except Exception as e:
		print(e)
