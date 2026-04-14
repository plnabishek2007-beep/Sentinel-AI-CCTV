# 🚀 SecureSight AI - Quick Setup Guide

## ⚡ 5-Minute Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Create Environment File
```bash
cp .env.example .env
```

### 3. Generate API Key
```bash
# Option A: Using Python
python3 -c "import secrets; print('API_KEY=' + secrets.token_hex(16))" >> .env

# Option B: Manual (copy this)
# Then edit .env and change API_KEY to:
# API_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
```

### 4. Run System
```bash
python main.py
```

### 5. Open Dashboard
- Browser: `http://127.0.0.1:5000`
- Enter API key when prompted (check your `.env`)

---

## 🎯 What to Show Judges

### Feature Demo (2 minutes)
1. **Show API Authentication**
   - Explain `.env` file (don't show actual secrets)
   - Demo: "API key is required for all endpoints"

2. **Show Consent Banner**
   - Point to red banner at top
   - "Users always know they're being recorded"

3. **Show Live Detection**
   - Stand in front of camera
   - System detects you as "Person"
   - If face is in `known_faces/`, shows name

4. **Show Privacy Features**
   - Explain: "Unknown faces are NOT stored"
   - Explain: "Evidence auto-deletes in 5 minutes"
   - Explain: "Auto-learning is DISABLED"

5. **Show GitHub Safety**
   - Open `.gitignore`
   - Point out: `.env`, `evidence/`, `known_faces/` are blocked
   - "Secrets never commit to Git"

### Code Walkthrough (3 minutes)

**Show in `main.py`:**
```python
# 1. Environment variables (no hardcoding)
load_dotenv()
API_KEY = os.getenv("API_KEY")

# 2. Authentication decorator
@require_api_key
def protected_endpoint():
    return jsonify(data), 200

# 3. Privacy settings
SAVE_UNKNOWN_FACES = False
AUTO_LEARN_ENABLED = False
AUTO_DELETE_SECONDS = 300

# 4. Cleanup function
def cleanup_old_files():
    # Auto-delete old evidence
```

**Show in `index.html`:**
```javascript
// 1. Secure API key handling
const API_KEY = prompt("🔐 Enter API Key:");

// 2. All requests include header
headers: { "x-api-key": API_KEY }

// 3. Consent banner visible at top
```

---

## 📊 Key Statistics for Judges

| Feature | Status |
|---------|--------|
| Face Recognition | ✅ Working |
| Intruder Detection | ✅ Working |
| Telegram Alerts | ✅ Optional |
| API Authentication | ✅ Enforced |
| Privacy Mode | ✅ Enabled |
| Hardcoded Secrets | ✅ None |
| Auto-learning | ✅ Disabled |
| Unknown Face Storage | ✅ Disabled |
| Evidence Auto-delete | ✅ 5 minutes |
| GitHub Safe | ✅ Yes |

---

## 🎤 What to Say

> "SecureSight AI is a **privacy-first surveillance system**. Unlike most CCTV projects, we've prioritized security from day one:
>
> **1. API Authentication** - Every endpoint requires a secure API key
> 
> **2. No Hardcoded Secrets** - All credentials in `.env`, never in code
> 
> **3. Privacy Compliance** - We disable auto-learning and never store unknown faces
> 
> **4. Data Protection** - Evidence files auto-delete in 5 minutes
> 
> **5. User Consent** - Visible warning banner so users know they're being recorded
> 
> **6. GitHub Safe** - Our `.gitignore` prevents accidental secret commits
>
> This demonstrates **responsible AI deployment** at a hackathon scale."

---

## 🔐 Quick Security Check

Run this before showing judges:

```bash
# 1. Verify .env exists and is in .gitignore
ls -la .env
grep ".env" .gitignore

# 2. Verify no secrets in code
grep -r "TELEGRAM_TOKEN =" *.py
# Should return nothing

# 3. Verify API key is set
python3 -c "from dotenv import load_dotenv; load_dotenv(); import os; print('✅ API_KEY set' if os.getenv('API_KEY') else '❌ API_KEY missing')"
```

---

## 🎬 Live Demo Script

```bash
#!/bin/bash
# demo.sh - Run this for live demo

echo "🔐 SecureSight AI - Demo Mode"
echo "=============================="
echo ""

# Start system
echo "1️⃣  Starting system..."
python main.py &
PYTHON_PID=$!

# Wait for startup
sleep 3

# Show status
echo ""
echo "2️⃣  Testing API authentication..."
API_KEY=$(grep "^API_KEY=" .env | cut -d= -f2)

echo "Without API key (should fail):"
curl http://127.0.0.1:5000/status 2>/dev/null | head -c 100

echo ""
echo ""
echo "With API key (should work):"
curl -H "x-api-key: $API_KEY" http://127.0.0.1:5000/status 2>/dev/null | jq .

echo ""
echo "3️⃣  Open http://127.0.0.1:5000 in browser"
echo "4️⃣  Enter API key: $API_KEY"
echo ""
echo "Press CTRL+C to stop"

# Keep running
wait $PYTHON_PID
```

---

## ✅ Pre-Demo Checklist

Before showing judges:

- [ ] `.env` file created
- [ ] API key is strong (16+ chars)
- [ ] `python main.py` runs without errors
- [ ] Browser opens `http://127.0.0.1:5000`
- [ ] Console shows "✅ Flask server started!"
- [ ] Dashboard loads after entering API key
- [ ] Live stream shows camera feed
- [ ] Consent banner is visible
- [ ] `.gitignore` blocks `.env`

---

## 🚨 If Something Breaks

### Flask won't start
```bash
# Check if port is in use
lsof -i :5000

# Use different port
# Edit main.py: SERVER_PORT = 5001
```

### Camera not working
```bash
# Check available cameras
python3 -c "import cv2; print('Cameras:', cv2.VideoCapture(0).isOpened())"
```

### API key issues
```bash
# Regenerate in .env
python3 -c "import secrets; print(secrets.token_hex(16))"
```

---

## 📝 Talking Points

**For Judges Asking About...**

**"Why disable auto-learning?"**
> "Auto-learning in biometric systems can perpetuate bias and privacy violations. By disabling it, we ensure only authorized persons are recognized - no unauthorized data collection."

**"Why auto-delete evidence?"**
> "GDPR and privacy laws require data minimization. We keep evidence only as long as needed for alerts, then automatically purge it."

**"Why API authentication?"**
> "Camera feeds are sensitive. We treat this like any enterprise API - requires authentication to prevent unauthorized access."

**"Why environment variables?"**
> "Industry standard practice. Keeps secrets out of code, prevents accidental public GitHub commits, and works with CI/CD pipelines."

---

## 🏆 Expected Judge Reaction

✅ "Wow, they actually thought about privacy"  
✅ "This is production-ready code"  
✅ "They understand security best practices"  
✅ "This should be the standard for AI projects"  

---

## 🎯 Success Criteria

After your demo, judges should say:

- [x] "This is more secure than most production systems"
- [x] "They understand privacy compliance"
- [x] "The code is clean and well-documented"
- [x] "This deserves an award"

---

**Good luck with your demo! 🚀**
