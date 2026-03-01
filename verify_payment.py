import paho.mqtt.client as mqtt
import json
import time

MQTT_BROKER = "157.173.101.159"
TEAM_ID = "amani"
TOPIC_STATUS = f"rfid/{TEAM_ID}/card/status"
TOPIC_BALANCE = f"rfid/{TEAM_ID}/card/balance"

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.connect(MQTT_BROKER, 1883, 60)

def simulate_tap(uid, balance):
    payload = {"uid": uid, "balance": balance, "team": TEAM_ID}
    print(f"Simulating tap: {payload}")
    client.publish(TOPIC_STATUS, json.dumps(payload))

def simulate_balance_update(uid, new_balance):
    payload = {"uid": uid, "new balance": new_balance}
    print(f"Simulating balance update: {payload}")
    client.publish(TOPIC_BALANCE, json.dumps(payload))

if __name__ == "__main__":
    # 1. Simulate a card tap
    simulate_tap("0x12345678", 50000)
    time.sleep(2)
    
    # 2. Simulate a balance update (e.g., after top-up or checkout)
    simulate_balance_update("0x12345678", 55000)
    
    print("Verification signals sent.")
    client.disconnect()
