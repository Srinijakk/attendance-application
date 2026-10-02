// Clock & Date (IST)
function updateClock() {
    const now = new Date();
    // Format for IST
    const optionsTime = { timeZone: 'Asia/Kolkata', hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' };
    const optionsDate = { timeZone: 'Asia/Kolkata', year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' };
    
    document.getElementById('clock').innerText = now.toLocaleTimeString('en-IN', optionsTime);
    document.getElementById('dateDisplay').innerText = now.toLocaleDateString('en-IN', optionsDate);
}
setInterval(updateClock, 1000);
updateClock();

// State
let currentAction = null;
let videoStreamObj = null;
let currentLoc = { lat: 0, lon: 0 };

const btnCheckIn = document.getElementById('btnCheckIn');
const btnCheckOut = document.getElementById('btnCheckOut');
const mainActions = document.getElementById('mainActions');
const cameraActions = document.getElementById('cameraActions');
const btnCaptureSubmit = document.getElementById('btnCaptureSubmit');
const btnCancel = document.getElementById('btnCancel');
const video = document.getElementById('videoStream');
const canvas = document.getElementById('captureCanvas');
const cameraWrapper = document.getElementById('cameraWrapper');
const messageBox = document.getElementById('messageBox');

// Fetch Status
async function loadStatus() {
    try {
        const res = await fetch('/api/status');
        if (!res.ok) {
            if(res.status === 401) window.location.href = '/login';
            return;
        }
        const data = await res.json();
        
        document.getElementById('lblCheckIn').innerText = data.check_in ? data.check_in + ' IST' : '--';
        document.getElementById('lblCheckOut').innerText = data.check_out ? data.check_out + ' IST' : '--';
        
        const dot = document.getElementById('statusDot');
        const lbl = document.getElementById('lblStatus');
        
        dot.className = 'status-dot';
        btnCheckIn.disabled = false;
        btnCheckOut.disabled = false;
        
        if (data.state === 'in') {
            dot.classList.add('in');
            lbl.innerText = 'Checked In';
            btnCheckIn.disabled = true; // already checked in
        } else if (data.state === 'out') {
            dot.classList.add('out');
            lbl.innerText = 'Checked Out';
            btnCheckIn.disabled = true;
            btnCheckOut.disabled = true;
        } else {
            lbl.innerText = 'Not Checked In';
            btnCheckOut.disabled = true; // must check in first
        }
    } catch(err) {
        console.error(err);
    }
}

function showMessage(msg, isError = true) {
    messageBox.style.display = 'block';
    messageBox.innerText = msg;
    messageBox.className = isError ? 'err' : 'err btn-success';
    if (!isError) setTimeout(() => { messageBox.style.display = 'none'; }, 3000);
}

// Camera & Location
async function startAction(action) {
    const branchSelect = document.getElementById('branchSelect');
    if (!branchSelect.value) {
        showMessage('Please select your branch first.', true);
        return;
    }

    currentAction = action;
    messageBox.style.display = 'none';
    
    // Get Location First
    if (!navigator.geolocation) {
        showMessage('Geolocation is not supported by your browser');
        return;
    }
    
    try {
        const pos = await new Promise((resolve, reject) => {
            navigator.geolocation.getCurrentPosition(resolve, reject, { enableHighAccuracy: true, timeout: 5000 });
        });
        currentLoc.lat = pos.coords.latitude;
        currentLoc.lon = pos.coords.longitude;
    } catch (err) {
        showMessage('Location access is required for attendance.');
        return;
    }
    
    // Start Camera
    try {
        videoStreamObj = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' }, audio: false });
        video.srcObject = videoStreamObj;
        cameraWrapper.classList.add('active');
        mainActions.style.display = 'none';
        cameraActions.style.display = 'flex';
    } catch (err) {
        showMessage('Camera access is required for attendance.');
    }
}

function stopCamera() {
    if (videoStreamObj) {
        videoStreamObj.getTracks().forEach(t => t.stop());
        videoStreamObj = null;
    }
    cameraWrapper.classList.remove('active');
    mainActions.style.display = 'flex';
    cameraActions.style.display = 'none';
    currentAction = null;
}

btnCheckIn.addEventListener('click', () => startAction('in'));
btnCheckOut.addEventListener('click', () => startAction('out'));
btnCancel.addEventListener('click', stopCamera);

btnCaptureSubmit.addEventListener('click', async () => {
    btnCaptureSubmit.disabled = true;
    btnCaptureSubmit.innerText = 'Submitting...';
    
    // Capture Image
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0);
    
    canvas.toBlob(async (blob) => {
        const formData = new FormData();
        formData.append('selfie', blob, 'selfie.jpg');
        formData.append('lat', currentLoc.lat);
        formData.append('lon', currentLoc.lon);
        formData.append('branch', document.getElementById('branchSelect').value);
        
        try {
            const endpoint = currentAction === 'in' ? '/api/check-in' : '/api/check-out';
            const res = await fetch(endpoint, { method: 'POST', body: formData });
            const data = await res.json();
            
            if (res.ok) {
                showMessage('Attendance recorded successfully!', false);
                stopCamera();
                loadStatus();
            } else {
                showMessage(data.detail || 'Failed to record attendance');
            }
        } catch (err) {
            showMessage('Network error. Try again.');
        } finally {
            btnCaptureSubmit.disabled = false;
            btnCaptureSubmit.innerText = '📸 Capture & Submit';
        }
    }, 'image/jpeg', 0.8);
});

// Init
loadStatus();
