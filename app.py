from flask import Flask, request, Response, make_response
import Conga
import json
import slack

app = Flask(__name__)
party = Conga.Party()


# connect to slack via POST request (instead of slackclient)
@app.route("/", methods=['POST'])
def CongaParty():
    token = request.form.get('token')
    message = request.form.get('text')
    user_name = request.form.get('user_name')

    message = Conga.Handler(party, user_name, message)

    data = {
        "text": message,
        "response_type": 'in_channel'
    }
    return Response(response=json.dumps(data), status=200, mimetype="application/json")


# this doesn't do much
@app.route("/test", methods=['GET'])
def HelloWorld():
    return "Everything OK!"


if __name__ == '__main__':
    app.run()