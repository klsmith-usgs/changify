import logging

log = logging.getLogger('chipccd')
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(processName)s: %(message)s')

handler.setFormatter(formatter)

log.addHandler(handler)
log.setLevel(logging.DEBUG)
