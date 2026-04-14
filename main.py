import cv2, time, os, threading, requests
import numpy as np
import face_recognition
from ultralytics import YOLO
from flask import Flask, jsonify, request, Response

# ================= 🔐 ENV VARIABLES =================
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
API_KEY          = os.getenv("API_KEY", "change_this_secret")

# ================= PRIVACY CONFIG =================
SAVE_UNKNOWN_FACES = False
AUTO_LEARN_ENABLED = False
CONSENT_REQUIRED   = True
AUTO_DELETE_SECONDS = 300  # 5 minutes

# ================= FOLDERS =================
KNOWN_FOLDER = "known_faces"
SAVE_FOLDER  = "evidence"

os.makedirs(KNOWN_FOLDER, exist_ok=True)
os.makedirs(SAVE_FOLDER, exist_ok=True)

# ================= GLOBAL STATE =================
camera_on = True
alerts_on = True
latest_frame = None
latest_alert = {"status": "SAFE"}
last_alert_time = 0

known_encodings = []
known_names = []

# ================= LOAD FACES =================
def load_faces():
    global known_encodings, known_names
    known_encodings, known_names = [], []

    for file in os.listdir(KNOWN_FOLDER):
        path = os.path.join(KNOWN_FOLDER, file)
        try:
            img = face_recognition.load_image_file(path)
            enc = face_recognition.face_encodings(img)
            if enc:
                known_encodings.append(enc[0])
                known_names.append(os.path.splitext(file)[0])
        except:
            pass

load_faces()

# ================= TELEGRAM ALERT =================
def send_telegram(msg, img=None):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return

    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": TELEGRAM_CHAT_ID, "text": msg},
            timeout=5
        )

        if img and os.path.exists(img):
            with open(img, "rb") as f:
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto",
                    files={"photo": f},
                    data={"chat_id": TELEGRAM_CHAT_ID},
                    timeout=10
                )
    except:
        pass

# ================= CLEANUP =================
def cleanup_old_files():
    now = time.time()
    for f in os.listdir(SAVE_FOLDER):
        path = os.path.join(SAVE_FOLDER, f)
        if os.path.isfile(path):
            if now - os.path.getmtime(path) > AUTO_DELETE_SECONDS:
                os.remove(path)

# ================= FLASK =================
app = Flask(__name__)

@app.before_request
def auth():
    if request.path != "/":
        if request.headers.get("x-api-key") != API_KEY:
            return jsonify({"error": "Unauthorized"}), 401

@app.route("/")
def index():
    return "SecureSight AI Running"

@app.route("/status")
def status():
    return jsonify({
        "camera": camera_on,
        "alerts": alerts_on,
        "faces": known_names,
        "alert": latest_alert
    })

@app.route("/frame")
def frame():
    global latest_frame
    if latest_frame is None:
        return "No frame", 404
    _, buf = cv2.imencode(".jpg", latest_frame)
    return Response(buf.tobytes(), mimetype="image/jpeg")

# ================= STREAM =================
def generate():
    while True:
        if latest_frame is not None:
            _, buf = cv2.imencode(".jpg", latest_frame)
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n')
        time.sleep(0.05)

@app.route("/stream")
def stream():
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

# ================= START SERVER =================
threading.Thread(
    target=lambda: app.run(host="127.0.0.1", port=5000, use_reloader=False),
    daemon=True
).start()

print("🔐 Secure Flask running on http://127.0.0.1:5000")

# ================= AI =================
model = YOLO("yolov8n.pt")
cap = cv2.VideoCapture(0)

# ================= MAIN LOOP =================
while True:

    if not camera_on:
        time.sleep(0.5)
        continue

    ret, frame = cap.read()
    if not ret:
        continue

    frame = cv2.resize(frame, (640, 480))
    latest_frame = frame.copy()

    intruder = False
    face_name = "Unknown"

    # ================= YOLO =================
    results = model(frame, verbose=False)

    for r in results:
        for box in r.boxes:
            if int(box.cls[0]) == 0:
                intruder = True
                x1,y1,x2,y2 = map(int, box.xyxy[0])
                cv2.rectangle(frame,(x1,y1),(x2,y2),(0,255,0),2)

    # ================= FACE =================
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    faces = face_recognition.face_locations(rgb)
    encs  = face_recognition.face_encodings(rgb, faces)

    for (top,right,bottom,left), enc in zip(faces, encs):
        name = "Unknown"

        matches = face_recognition.compare_faces(known_encodings, enc)

        if True in matches:
            idx = matches.index(True)
            name = known_names[idx]
            face_name = name

        color = (0,200,0) if name!="Unknown" else (0,0,255)

        cv2.rectangle(frame,(left,top),(right,bottom),color,2)
        cv2.putText(frame,name,(left,top-10),
                    cv2.FONT_HERSHEY_SIMPLEX,0.5,color,1)

    # ================= ALERT =================
    now = time.time()

    if intruder and alerts_on and (now - last_alert_time > 15):

        msg = f"🚨 Intruder Alert\nFace: {face_name}\nTime: {time.strftime('%H:%M:%S')}"

        img_path = os.path.join(SAVE_FOLDER, f"alert_{int(now)}.jpg")
        cv2.imwrite(img_path, frame)

        threading.Thread(target=send_telegram, args=(msg, img_path)).start()

        latest_alert = {
            "status": "INTRUDER",
            "face": face_name,
            "time": time.strftime("%H:%M:%S")
        }

        last_alert_time = now

    else:
        if now - last_alert_time > 30:
            latest_alert = {"status": "SAFE"}

    # ================= CONSENT NOTICE =================
    if CONSENT_REQUIRED:
        cv2.putText(frame,"CONSENT MODE ACTIVE",(10,70),
                    cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,0,255),2)

    # ================= UI =================
    status = "INTRUDER" if intruder else "SAFE"
    color  = (0,0,255) if intruder else (0,255,0)

    cv2.putText(frame,f"STATUS: {status}",(10,30),
                cv2.FONT_HERSHEY_SIMPLEX,0.7,color,2)

    cv2.imshow("SecureSight AI (Privacy Mode)", frame)

    cleanup_old_files()

    if cv2.waitKey(1) == 27:
        break

cap.release()
cv2.destroyAllWindows()
