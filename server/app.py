import sqlite3
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt
import json

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('nexus_pos.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS cards 
                      (uid TEXT PRIMARY KEY, balance INTEGER, last_seen DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS transactions 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, uid TEXT, amount INTEGER, type TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

# --- MQTT SETUP ---
MQTT_BROKER = "157.173.101.159"
TEAM_ID = "amani"

TOPIC_STATUS = f"rfid/{TEAM_ID}/card/status"
TOPIC_TOPUP = f"rfid/{TEAM_ID}/card/topup"
TOPIC_BALANCE = f"rfid/{TEAM_ID}/card/balance"

checkout_queue = {"active": False, "amount": 0}

# ✅ FIXED (VERSION2 requires 5 parameters)
def on_connect(client, userdata, flags, reason_code, properties):
    print("Connected to MQTT Broker")
    client.subscribe(TOPIC_STATUS)
    client.subscribe(TOPIC_BALANCE)

def on_message(client, userdata, msg):
    global checkout_queue
    
    data = json.loads(msg.payload.decode())
    uid = data.get('uid')
    bal = data.get('balance') or data.get('new balance')

    conn = sqlite3.connect('nexus_pos.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO cards (uid, balance) VALUES (?, ?)", (uid, bal))
    conn.commit()
    conn.close()

    if checkout_queue["active"]:
        if bal >= checkout_queue["amount"]:
            deduction = -checkout_queue["amount"]
            client.publish(TOPIC_TOPUP, json.dumps({"uid": uid, "amount": deduction}))
            socketio.emit('checkout_result', {
                'status': 'success',
                'uid': uid,
                'new_balance': bal + deduction
            })
        else:
            socketio.emit('checkout_result', {
                'status': 'insufficient',
                'uid': uid,
                'needed': checkout_queue["amount"]
            })

        checkout_queue["active"] = False

    socketio.emit('card_tapped', data)

mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, 1883, 60)
mqtt_client.loop_start()

# --- ROUTES ---
@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/checkout', methods=['POST'])
def start_checkout():
    global checkout_queue
    data = request.json
    checkout_queue["active"] = True
    checkout_queue["amount"] = data['amount']
    return jsonify({"status": "waiting_for_tap"})

@app.route('/api/topup', methods=['POST'])
def topup():
    data = request.json
    mqtt_client.publish(TOPIC_TOPUP, json.dumps(data))
    return jsonify({"status": "command_sent"})

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=9234)