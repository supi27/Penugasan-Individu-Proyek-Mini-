"""
Simulasi perangkat IoT (pengganti ESP32).

Fungsi:
1. Membaca suhu (simulasi atau DHT22 asli)
2. Mempublikasikan suhu ke topik MQTT setiap 3 detik
3. Mensimulasikan kontrol relay dan PWM dari perintah MQTT
"""

import random
import threading
import time

import paho.mqtt.client as mqtt


# Konfigurasi MQTT
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_CLIENT_ID = "PythonDevice-001"
TOPIC_SUHU = "iot/2410020001/sensor/suhu"
TOPIC_RELAY = "iot/2410020001/aktuator/led"
TOPIC_PWM = "iot/2410020001/aktuator/pwm"
TOPIC_STATUS = "iot/2410020001/status/led"
INTERVAL_PUBLISH = 3
GPIO_RELAY = 26
GPIO_PWM = 2

# State aktuator simulasi
relay_state = "OFF"
pwm_value = 0


def on_connect(client, userdata, flags, reason_code, properties):
    """Dipanggil setelah proses koneksi ke broker MQTT."""
    if reason_code == 0:
        print("[MQTT] Terhubung ke broker")
        client.subscribe(TOPIC_RELAY, qos=0)
        client.subscribe(TOPIC_PWM, qos=0)
        print(f"[MQTT] Subscribe ke topik: {TOPIC_RELAY}")
        print(f"[MQTT] Subscribe ke topik: {TOPIC_PWM}")
    else:
        print(f"[MQTT] Gagal terhubung, kode: {reason_code}")


def on_message(client, userdata, msg):
    """Dipanggil setiap ada pesan pada topik yang di-subscribe."""
    global relay_state, pwm_value

    payload = msg.payload.decode("utf-8").strip().upper()
    print(f"[MQTT] Pesan masuk [{msg.topic}]: {payload}")

    if msg.topic == TOPIC_RELAY:
        if payload in ("ON", "1"):
            relay_state = "ON"
            print(f"[AKTUATOR] Relay GPIO {GPIO_RELAY} (simulasi) MENYALA")
        elif payload in ("OFF", "0"):
            relay_state = "OFF"
            print(f"[AKTUATOR] Relay GPIO {GPIO_RELAY} (simulasi) MATI")
        else:
            print(f"[AKTUATOR] Perintah relay tidak dikenal: {payload}")
            return

        client.publish(TOPIC_STATUS, relay_state, qos=0)
        print(f"[MQTT] Publish status: {TOPIC_STATUS} -> {relay_state}")
    elif msg.topic == TOPIC_PWM:
        try:
            requested_pwm = int(payload)
        except ValueError:
            print(f"[AKTUATOR] Nilai PWM bukan bilangan bulat: {payload}")
            return

        if not 0 <= requested_pwm <= 255:
            print(f"[AKTUATOR] Nilai PWM di luar rentang 0-255: {requested_pwm}")
            return

        pwm_value = requested_pwm
        brightness = pwm_value * 100 / 255
        print(
            f"[AKTUATOR] LED GPIO {GPIO_PWM} (simulasi): "
            f"PWM {pwm_value}/255 ({brightness:.1f}%)"
        )


def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
    """Dipanggil ketika koneksi MQTT terputus."""
    print(f"[MQTT] Terputus (kode: {reason_code}). Mencoba reconnect...")


def baca_suhu():
    """
    Simulasi pembacaan suhu DHT22.

    Jika menggunakan DHT22 asli di Raspberry Pi, ganti dengan:
    import Adafruit_DHT
    sensor = Adafruit_DHT.DHT22
    pin = 4
    hum, temp = Adafruit_DHT.read_retry(sensor, pin)
    return round(temp, 2) if temp is not None else None
    """
    base = 27.0
    noise = random.uniform(-1.5, 1.5)
    return round(base + noise, 2)


def publish_loop(client):
    """Loop terpisah untuk publish data sensor setiap INTERVAL_PUBLISH detik."""
    while True:
        suhu = baca_suhu()
        if suhu is not None:
            client.publish(TOPIC_SUHU, str(suhu), qos=0)
            print(f"[SENSOR] Publish suhu: {TOPIC_SUHU} -> {suhu} °C")
        time.sleep(INTERVAL_PUBLISH)


def main():
    """Menjalankan perangkat IoT."""
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=MQTT_CLIENT_ID,
        protocol=mqtt.MQTTv311,
    )
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    print(f"[MQTT] Menghubungkan ke {MQTT_BROKER}:{MQTT_PORT}...")
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    client.loop_start()

    time.sleep(1)

    publisher = threading.Thread(
        target=publish_loop,
        args=(client,),
        daemon=True,
        name="mqtt-temperature-publisher",
    )
    publisher.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[MAIN] Menghentikan program...")
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
