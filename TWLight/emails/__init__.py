# We have to import signal receivers into __init__.py or they won't be
# registered at the proper time by Django, and then the signals will not be
# received, and emails won't get sent, and there will be nothing but a lone
# and level field of yaks stretching far away.
import tasks
