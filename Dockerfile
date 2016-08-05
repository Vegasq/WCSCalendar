FROM python:3-onbuild
CMD ["python", "./WCSCalendar/wcsc.py", "update", "config.json"]

