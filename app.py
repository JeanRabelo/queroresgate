import json
import sys
import urllib

import elasticsearch
from flask_recaptcha import ReCaptcha
import requests as requests
from flask import Flask, render_template, flash
from flask import request
from datetime import datetime
from forms import VacinaForm
from defs import es, ES_VACINEI_INDEX, body_settings_vacinei, APP_PORT, DASHBOARD_URL, DEBUG, SECRET_KEY
import dateutil.parser
from flask_bootstrap import Bootstrap


def check_or_create_index(esc, index, settings):
    response = esc.indices.exists(index)
    if response is True:
        return "EXISTED"
    else:
        esc.indices.create(index, body=settings)
        return "CREATED"


try:
    check_or_create_index(es, ES_VACINEI_INDEX, body_settings_vacinei)
except elasticsearch.exceptions.ConnectionError as e:
    print(e)
    pass

app = Flask(__name__)
recaptcha = ReCaptcha(app=app)
Bootstrap(app)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['RECAPTCHA_ENABLED'] = True
app.config['RECAPTCHA_PUBLIC_KEY'] = '6Lc9Y1obAAAAAM-7g3G29a_-CHg2O0Cl81YAR-0l'
app.config['RECAPTCHA_PRIVATE_KEY'] = '6Lc9Y1obAAAAAN6YQEC1nLkyAp03FQMpemNiKc7M'
app.config['RECAPTCHA_THEME'] = 'white'
app.config['RECAPTCHA_TYPE'] = 'image'
app.config['RECAPTCHA_SIZE'] = 'compact'
app.config['RECAPTCHA_USE_SSL'] = False
app.config['RECAPTCHA_RTABINDEX'] = 10
brasilia = [-15.7801, -47.9292]


def get_geolocation(ip):
    url = 'http://freegeoip.net/json/{}'.format(ip)
    r = requests.get(url)
    j = json.loads(r.text)


@app.route('/', methods=['GET', 'POST'])
def index():
    current_hour = datetime.utcnow().hour
    inappropriate_time = current_hour > 21 or current_hour < 15
    if request.method == "POST":
        form = VacinaForm(request.form)
        if form.validate_on_submit():
            latlong = form.latlong.data
            data_vacinacao = dateutil.parser.parse(form.data.data)
            es.index(ES_VACINEI_INDEX,
                     body={"location": latlong, "idade": form.idade.data, "data_vacinacao": data_vacinacao, "desperdicio": form.desperdicio.data == 1,
                           "vacina": form.vacina.data, "date": datetime.utcnow().isoformat()}, id=form.email.data, doc_type="_doc")
            orig = [float(f) for f in latlong.split(',')]
            return render_template('index.html', form=form, torecaptcha=DEBUG == False, tosubmit=False, popup_message="Me vacinei aqui",
                                   email=form.email.data, inappropriate_time=inappropriate_time, origem=orig)
        else:
            flash('Todos os campos são obrigatórios', category='error')
            return render_template('index.html', form=form, torecaptcha=DEBUG == False, tosubmit=True, popup_message="Informar aqui",
                                   inappropriate_time=inappropriate_time)

    else:
        form = VacinaForm()
        return render_template('index.html', form=form, torecaptcha=DEBUG == False, tosubmit=True, popup_message="Informar aqui",
                               inappropriate_time=inappropriate_time)


@app.route('/visualizar', methods=['GET'])
def visualizar():
    return render_template('visualizar.html', dashboard_url=DASHBOARD_URL)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        pass
    else:
        if DEBUG:
            app.run(debug=True, host='0.0.0.0', port=APP_PORT, ssl_context='adhoc')
        else:
            app.run(debug=True, host='0.0.0.0', port=APP_PORT)  # , ssl_context='adhoc')
