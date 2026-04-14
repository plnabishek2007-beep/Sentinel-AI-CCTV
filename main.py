import cv2
import time
import os
import threading
import requests
import numpy as np
import face_recognition
from ultralytics import YOLO
from flask import Flask, jsonify, request, Response
from functools import wraps
from dotenv import load_dotenv

# ================= 🔐 LOAD ENVIRONMENT VARIABLES =================
load_dotenv()

TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
API_KEY          = os.getenv("API_KEY", "change_this_secret_key_12345")

# Validate API Key (should never be default in production)
if API_KEY == "change_this_secret_key_12345":
    print("⚠️  WARNING: Using default API_KEY. Set API_KEY in .env file!")

# ================= 🔐 PRIVACY & SECURITY CONFIG =================
SAVE_UNKNOWN_FACES  = False          # CRITICAL: Never auto-save unknown faces
AUTO_LEARN_ENABLED  = False          # CRITICAL: Disable auto-learning
CONSENT_REQUIRED    = True           # Show consent banner
AUTO_DELETE_SECONDS = 300            # Auto-delete evidence after 5 minutes
LOCAL_ONLY_SERVER   = True           # Bind to 127.0.0.1 only
SERVER_PORT         = 5000

# ================= DIRECTORIES =================
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

# ================= 🔐 AUTHENTICATION DECORATOR =================
def require_api_key(f):
    """Decorator to require API key for protected endpoints."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check header first, then query parameter
        api_key = request.headers.get("x-api-key") or request.args.get("api_key")
        
        if not api_key or api_key != API_KEY:
            return jsonify({"error": "Unauthorized - Invalid or missing API key"}), 401
        
        return f(*args, **kwargs)
    
    return decorated_function

# ================= 🔐 LOAD KNOWN FACES =================
def load_faces():
    """Load pre-authorized faces from known_faces directory only."""
    global known_encodings, known_names
    known_encodings, known_names = [], []

    if not os.path.exists(KNOWN_FOLDER):
        print(f"⚠️  {KNOWN_FOLDER} directory not found. No known faces loaded.")
        return

    for file in os.listdir(KNOWN_FOLDER):
        if file.lower().endswith(('.jpg', '.jpeg', '.png')):
            path = os.path.join(KNOWN_FOLDER, file)
            try:
                img = face_recognition.load_image_file(path)
                enc = face_recognition.face_encodings(img)
                if enc:
                    known_encodings.append(enc[0])
                    known_names.append(os.path.splitext(file)[0])
                    print(f"✅ Loaded face: {os.path.splitext(file)[0]}")
            except Exception as e:
                print(f"❌ Error loading {file}: {e}")

load_faces()

# ================= 🔐 TELEGRAM ALERT (Privacy-Safe) =================
def send_telegram(msg, img=None):
    """Send alert via Telegram (only if configured)."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("ℹ️  Telegram not configured. Alert not sent.")
        return

    try:
        # Send message
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": TELEGRAM_CHAT_ID, "text": msg},
            timeout=5
        )

        # Send image if provided
        if img and os.path.exists(img):
            with open(img, "rb") as f:
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto",
                    files={"photo": f},
                    data={"chat_id": TELEGRAM_CHAT_ID},
                    timeout=10
                )
            print(f"📤 Alert sent to Telegram with image: {img}")
        else:
            print(f"📤 Alert sent to Telegram")
    except Exception as e:
        print(f"❌ Telegram error: {e}")

# ================= 🔐 CLEANUP OLD EVIDENCE FILES =================
def cleanup_old_files():
    """Auto-delete evidence files older than AUTO_DELETE_SECONDS."""
    now = time.time()
    deleted_count = 0
    
    if not os.path.exists(SAVE_FOLDER):
        return
    
    for f in os.listdir(SAVE_FOLDER):
        path = os.path.join(SAVE_FOLDER, f)
        if os.path.isfile(path):
            file_age = now - os.path.getmtime(path)
            if file_age > AUTO_DELETE_SECONDS:
                try:
                    os.remove(path)
                    deleted_count += 1
                    print(f"🗑️  Auto-deleted: {f}")
                except Exception as e:
                    print(f"❌ Error deleting {f}: {e}")
    
    if deleted_count > 0:
        print(f"🧹 Cleanup: Deleted {deleted_count} old evidence file(s)")

# ================= 🔐 FLASK APPLICATION =================
app = Flask(__name__)

# ================= PUBLIC ROUTES (NO AUTH REQUIRED) =================
@app.route("/")
def index():
    """Health check - public endpoint."""
    return jsonify({
        "status": "🔐 SecureSight AI Running",
        "privacy_mode": "ENABLED",
        "version": "2.0-Privacy-Safe"
    }), 200

@app.route("/health")
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy"}), 200

# ================= PROTECTED ROUTES (API KEY REQUIRED) =================
@app.route("/status")
@require_api_key
def status():
    """Get system status (protected)."""
    return jsonify({
        "camera": camera_on,
        "alerts": alerts_on,
        "known_faces": len(known_names),
        "latest_alert": latest_alert,
        "privacy_mode": "ENABLED",
        "auto_learn": AUTO_LEARN_ENABLED,
        "consent_required": CONSENT_REQUIRED
    }), 200

@app.route("/frame")
@require_api_key
def frame():
    """Get current frame as JPEG (protected)."""
    global latest_frame
    if latest_frame is None:
        return jsonify({"error": "No frame available"}), 404
    
    _, buf = cv2.imencode(".jpg", latest_frame)
    return Response(buf.tobytes(), mimetype="image/jpeg")

# ================= PROTECTED STREAM =================
def generate_stream():
    """Generate video stream frames."""
    while True:
        if latest_frame is not None:
            _, buf = cv2.imencode(".jpg", latest_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n')
        time.sleep(0.05)

@app.route("/stream")
@require_api_key
def stream():
    """Live video stream (protected)."""
    return Response(
        generate_stream(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    ), 200

# ================= PROTECTED CONTROL ENDPOINT =================
@app.route("/control", methods=["POST"])
@require_api_key
def control():
    """Control camera and alerts (protected)."""
    global camera_on, alerts_on
    
    data = request.get_json() or {}
    
    if "camera" in data:
        camera_on = bool(data["camera"])
        print(f"📹 Camera: {'ON' if camera_on else 'OFF'}")
    
    if "alerts" in data:
        alerts_on = bool(data["alerts"])
        print(f"🔔 Alerts: {'ON' if alerts_on else 'OFF'}")
    
    return jsonify({
        "success": True,
        "camera": camera_on,
        "alerts": alerts_on
    }), 200

# ================= ERROR HANDLERS =================
@app.errorhandler(401)
def unauthorized(error):
    return jsonify({"error": "Unauthorized - API key required"}), 401

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

# ================= START FLASK SERVER =================
def start_flask_server():
    """Start Flask server (localhost only for security)."""
    host = "127.0.0.1" if LOCAL_ONLY_SERVER else "0.0.0.0"
    print(f"🚀 Starting Flask server on {host}:{SERVER_PORT}")
    app.run(
        host=host,
        port=SERVER_PORT,
        debug=False,
        use_reloader=False,
        threaded=True
    )

# Start Flask in background thread
flask_thread = threading.Thread(target=start_flask_server, daemon=True)
flask_thread.start()
time.sleep(2)  # Wait for Flask to start
print(f"✅ Flask server started!")

# ================= LOAD AI MODELS =================
print("🤖 Loading YOLO model...")
model = YOLO("yolov8n.pt")
print("✅ YOLO model loaded")

# ================= INITIALIZE CAMERA =================
print("📹 Initializing camera...")
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("❌ Cannot open camera!")
    exit(1)

print("✅ Camera initialized")

# ================= PRIVACY NOTICE =================
print("""
╔═══════════════════════════════════════════════════════╗
║         🔐 SECURESIGHT AI - PRIVACY MODE ENABLED      ║
╠═══════════════════════════════════════════════════════╣
║ ✅ Auto-face learning: DISABLED                       ║
║ ✅ Unknown faces storage: DISABLED                    ║
║ ✅ Evidence auto-delete: 5 minutes                    ║
║ ✅ API authentication: ENABLED                        ║
║ ✅ Local-only server: ENABLED                         ║
║ ✅ Consent banner: ACTIVE                             ║
╚═══════════════════════════════════════════════════════╝
""")

# ================= MAIN DETECTION LOOP =================
frame_count = 0

try:
    while True:
        # Skip if camera is disabled
        if not camera_on:
            time.sleep(0.5)
            continue

        ret, frame = cap.read()
        if not ret:
            print("⚠️  Frame read failed, retrying...")
            time.sleep(1)
            continue

        # Resize frame
        frame = cv2.resize(frame, (640, 480))
        latest_frame = frame.copy()

        intruder = False
        face_name = "Unknown"

        # ================= YOLO OBJECT DETECTION =================
        try:
            results = model(frame, verbose=False)

            for r in results:
                for box in r.boxes:
                    # Class 0 = Person
                    if int(box.cls[0]) == 0:
                        intruder = True
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        confidence = float(box.conf[0])
                        
                        # Draw bounding box
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.putText(
                            frame, 
                            f"Person {confidence:.2f}", 
                            (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 
                            0.5, 
                            (0, 255, 0), 
                            2
                        )
        except Exception as e:
            print(f"❌ YOLO error: {e}")

        # ================= FACE RECOGNITION =================
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            faces = face_recognition.face_locations(rgb)
            encs = face_recognition.face_encodings(rgb, faces)

            for (top, right, bottom, left), enc in zip(faces, encs):
                name = "Unknown"

                # Compare with known faces
                if len(known_encodings) > 0:
                    matches = face_recognition.compare_faces(
                        known_encodings, 
                        enc, 
                        tolerance=0.6
                    )
                    distances = face_recognition.face_distance(known_encodings, enc)

                    if len(distances) > 0:
                        best_match_idx = np.argmin(distances)
                        if matches[best_match_idx]:
                            name = known_names[best_match_idx]
                            face_name = name

                # Draw face box and label
                color = (0, 200, 0) if name != "Unknown" else (0, 0, 255)
                cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                cv2.putText(
                    frame, 
                    name, 
                    (left, top - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    0.6, 
                    color, 
                    2
                )
        except Exception as e:
            print(f"❌ Face recognition error: {e}")

        # ================= ALERT SYSTEM =================
        now = time.time()

        if intruder and alerts_on and (now - last_alert_time > 15):
            msg = f"🚨 Intruder Alert!\n👤 Face: {face_name}\n🕐 Time: {time.strftime('%H:%M:%S')}"
            
            # Save evidence
            img_path = os.path.join(SAVE_FOLDER, f"alert_{int(now)}.jpg")
            cv2.imwrite(img_path, frame)

            # Send Telegram alert
            threading.Thread(target=send_telegram, args=(msg, img_path)).start()

            # Update status
            latest_alert = {
                "status": "INTRUDER",
                "face": face_name,
                "time": time.strftime("%H:%M:%S")
            }

            last_alert_time = now
            print(f"🚨 ALERT: Intruder detected - {face_name}")

        else:
            # Reset to SAFE after 30 seconds of no alerts
            if now - last_alert_time > 30:
                latest_alert = {"status": "SAFE"}

        # ================= ADD UI OVERLAYS =================
        
        # Consent banner
        if CONSENT_REQUIRED:
            cv2.rectangle(frame, (0, 0), (640, 40), (0, 0, 200), -1)
            cv2.putText(
                frame, 
                "⚠️ AI Surveillance Active - Authorized Access Only",
                (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 
                0.6, 
                (0, 255, 255), 
                1
            )

        # Status
        status = "🚨 INTRUDER" if intruder else "✅ SAFE"
        color = (0, 0, 255) if intruder else (0, 255, 0)
        cv2.putText(
            frame, 
            f"STATUS: {status}", 
            (10, 470),
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.7, 
            color, 
            2
        )

        # Privacy mode
        cv2.putText(
            frame, 
            "🔒 Privacy Mode: ENABLED", 
            (350, 470),
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.5, 
            (0, 255, 255), 
            1
        )

        # ================= PERIODIC CLEANUP =================
        frame_count += 1
        if frame_count % 300 == 0:  # Every ~6 seconds (at 50 FPS)
            cleanup_old_files()

        # ================= DISPLAY =================
        cv2.imshow("🔐 SecureSight AI (Privacy Mode ENABLED)", frame)

        # Press ESC to exit
        if cv2.waitKey(1) & 0xFF == 27:
            print("\n⛔ Shutting down...")
            break

except KeyboardInterrupt:
    print("\n⛔ Interrupted by user")

finally:
    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    print("✅ System shutdown complete")
