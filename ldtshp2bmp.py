#!/usr/bin/env python

__libname__ = 'ldtshp2bmp'
__description__ = 'LEGO Desktop Toy SHP To BMP Converter'
__version__ = '1.0.0'
__copyright__ = 'Copyright (c) 2019 JrMasterModelBuilder'
__license__ = 'Licensed under the Mozilla Public License, v. 2.0'

import os
import sys
import errno
import struct
import argparse

def mkdirp(path):
	try:
		os.makedirs(path)
	except OSError as ex:
		if ex.errno == errno.EEXIST and os.path.isdir(path):
			pass
		else:
			raise ex

def openp(path, mode):
	base = os.path.dirname(path)
	if base:
		mkdirp(base)
	return open(path, mode)

class Error(Exception):
	pass

class Process():
	def __init__(self, options):
		self.options = options

	def aligned(self, size, mod):
		if size % mod:
			return size + (mod - (size % mod))
		return size

	def read_pal(self, path):
		r = []
		with open(path, 'r') as fp:
			header = fp.readline().strip()
			if header != 'JASC-PAL':
				raise Error('Invalid header: %s' % (header))

			unknown = fp.readline().strip()
			if unknown != '0100':
				raise Error('Invalid unknown: %s' % (unknown))

			depth = int(fp.readline().strip())
			for i in range(depth):
				line = fp.readline().strip()
				pieces = line.split()
				if len(pieces) != 3:
					raise Error('Invalid line: %s' % (line))
				rgb = (int(pieces[0]), int(pieces[1]), int(pieces[2]))
				r.append(rgb)

			fp.close()
		return r

	def read_shp(self, path):
		r = None
		with open(path, 'rb') as fp:
			[width, height] = struct.unpack('<II', fp.read(8))
			data = fp.read(width * height)
			r = ((width, height), data)
			fp.close()
		return r

	def write_bmp(self, path, pal_data, shp_data):
		align = 4
		((width, height), pixels) = shp_data
		pal_data_len = len(pal_data)
		pal_data_size = pal_data_len * 4
		width_aligned = self.aligned(width, align)
		width_pad_size = width_aligned - width
		pixel_data_padded_size = width_aligned * height
		header_size = 54
		pixel_offset = pal_data_size + header_size
		file_size = pixel_offset + pixel_data_padded_size
		file_size_padded = self.aligned(file_size, align)
		file_size_pad_size = file_size_padded - file_size
		pixel_data_padded_size += file_size_pad_size
		header = struct.pack(
			''.join([
				'<',  # little endia
				'cc', # 'MZ'
				'I',  # File size in bytes
				'I',  # Reserved, 0
				'I',  # Offset of pixel data
				'I',  # Size of header, 40
				'I',  # Pixel width
				'I',  # Pixel height
				'H',  # Image planes count, 1
				'H',  # Bits per pixel (1, 4, 8, 24)
				'I',  # Compression type
				'I',  # Size of compressed image (pixel data plus padding)
				'I',  # Horizontal resolution, in pixels/meter
				'I',  # Vertical resolution, in pixels/meter
				'I',  # Colors used
				'I'   # Important used
			]),
			b'B',
			b'M',
			file_size_padded,
			0,
			pixel_offset,
			40,
			width,
			height,
			1,
			8,
			0,
			pixel_data_padded_size,
			2834,
			2834,
			pal_data_len,
			pal_data_len
		)
		with openp(path, 'wb') as fp:
			fp.write(header)

			# Write pallet, B G R null.
			for (r, g, b) in pal_data:
				fp.write(struct.pack('<BBBB', b, g, r, 0))

			# Write rows, last row to first.
			for i in range(height):
				o = (height - (i + 1)) * width
				d = pixels[o:o+width]
				fp.write(d)

				# Pad up to 4 byte alignment.
				for i in range(width_pad_size):
					fp.write(b'\x00')

			# Pad to final size.
			for i in range(file_size_pad_size):
				fp.write(b'\x00')
			fp.close()

	def run(self):
		pal = self.options.pal
		shp = self.options.shp
		bmp = self.options.bmp

		pal_data = self.read_pal(pal)
		shp_data = self.read_shp(shp)
		self.write_bmp(bmp, pal_data, shp_data)

		return 0

def main():
	parser = argparse.ArgumentParser(
		description=os.linesep.join([
			'%s - %s' % (__libname__, __description__),
			'Version: %s' % (__version__)
		]),
		epilog=os.linesep.join([
			__copyright__,
			__license__
		]),
		formatter_class=argparse.RawTextHelpFormatter
	)
	parser.add_argument(
		'-v', '--version',
		action='version',
		version=__version__
	)

	parser.add_argument('pal', help='in pal file')
	parser.add_argument('shp', help='in shp file')
	parser.add_argument('bmp', help='out bmp file')

	return Process(parser.parse_args()).run()

if __name__ == '__main__':
	sys.exit(main())
