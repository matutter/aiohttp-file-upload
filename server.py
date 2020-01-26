import logging
import tempfile
import asyncio
from aiohttp import web
from aiohttp.multipart import MultipartReader, BodyPartReader
import hashlib
import sys

import coloredlogs
coloredlogs.install(level=logging.DEBUG, fmt='%(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)


def fsize_fmt(num, suffix='B'):
  for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
    if abs(num) < 1024.0:
      return "%3.1f%s%s" % (num, unit, suffix)
    num /= 1024.0
  return "%.1f%s%s" % (num, 'Yi', suffix)

async def handle_file_storage(request):
  reader: MultipartReader = await request.multipart()

  source_hashes = {}
  local_hashes = {}
  with tempfile.TemporaryDirectory() as tmpdir:
    file_count = 0
    field: BodyPartReader = await reader.next()
    while field is not None:

      form_name  = field.name
      filename   = field.filename
      if form_name != 'md5':
        raise web.HTTPBadRequest()

      source_md5 = await field.read(decode=True)
      source_md5 = source_md5.decode()
      source_hashes[filename] = source_md5

      field = await reader.next()
      if not field:
        log.critical(f'No more fields...')
        break

      form_name = field.name
      filename  = field.filename
      if form_name != "content":
        raise web.HTTPBadRequest()
      md5 = hashlib.md5()
      
      log.info(f'FORM: {form_name}, FILENAME: {filename}')

      size = 0
      with tempfile.NamedTemporaryFile(dir=tmpdir, delete=False) as tmpfile:
        while True:
          chunk = await field.read_chunk()
          if not chunk:
            break
          size += len(chunk)
          md5.update(chunk)
          tmpfile.write(chunk)

        file_count += 1
      local_md5 = md5.hexdigest()
      local_hashes[filename] = local_md5
      md5_match = local_md5 == source_md5
      log.info(f'DONE with: {filename}, TRANSFER SIZE: {fsize_fmt(size)}, MD5: {local_md5}, HASH CHECK: {md5_match}')
      field = await reader.next()

    log.info(f'DONE uploaded {file_count} files, TOTAL HASH CHECK: { local_hashes == source_hashes }')
 
async def store_many_files(request):
  # Debug to see how many coros are running at once.
  tasks = asyncio.tasks.all_tasks()
  log.debug(f'TASKS: {len(tasks)}')

  try:
    await handle_file_storage(request)
  except ConnectionResetError as e:
    log.error(f'CONNECTION RESET: {e}')
    raise
  except asyncio.CancelledError as e:
    log.error(f'CONNECTION RESET: {e}')
    raise

  return web.Response(text='OK')


app = web.Application()
app.add_routes([web.post('/', store_many_files)])
if __name__ == '__main__':
  web.run_app(app, port=8000, access_log_format='%a %t "%r" %s %b "%{Referer}i" "%{User-Agent}i" %Tfs')