#!/use/bin/bash
Manage=/data/web/CottonOGD/OGD/backend/manage.py
Venv=/data/web/CottonOGD/OGD/backend/venv/Scripts/activate
source $Venv
python3 $Manage runserver 0.0.0:8000
