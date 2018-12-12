import logging as logg


logg.basicConfig(filename='vms.log',
    level=logg.DEBUG,
    format='%(asctime)s [%(levelname)s][%(module)s:%(lineno)d] %(message)s',
    datefmt='%m/%d/%Y %I:%M:%S %p')


logger = logg.getLogger(__name__)

