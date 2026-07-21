const camera = document.querySelector("#camera");
const landmarkCanvas = document.querySelector("#landmarkCanvas");
const cameraStatus = document.querySelector("#cameraStatus");
const repCount = document.querySelector("#repCount");
const startCamera = document.querySelector("#startCamera");
const calibratePose = document.querySelector("#calibratePose");
const startDrill = document.querySelector("#startDrill");
const drillCards = document.querySelectorAll(".drill-card");

let stream = null;
let drillTimer = null;
let landmarkLoopId = null;
let selectedDrill = "read";
let lastVisionRequest = 0;

function syncCameraHeight() {
  document.documentElement.style.setProperty("--camera-height", `${window.innerHeight}px`);
}

syncCameraHeight();
window.addEventListener("resize", syncCameraHeight);
window.addEventListener("orientationchange", syncCameraHeight);

function startLandmarkLoop() {
  if (landmarkLoopId) {
    cancelAnimationFrame(landmarkLoopId);
  }

  const tick = async () => {
    try {
    resizeLandmarkCanvas(camera, landmarkCanvas);

    const poseResult = await requestLandmarkAnalysis(camera);
    drawLandmarkOverlay(landmarkCanvas, poseResult);
    applyVisionState(poseResult);
    } finally {
    landmarkLoopId = requestAnimationFrame(tick);
    }
  };

  tick();
}

async function enableCamera() {
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: "environment",
        width: { ideal: 1280 },
        height: { ideal: 720 },
      },
      audio: false,
    });

    camera.srcObject = stream;
    await camera.play();
    startLandmarkLoop();
    cameraStatus.textContent = "Camera live";
    startCamera.textContent = "Camera on";
    startCamera.disabled = true;
    calibratePose.disabled = false;
    startDrill.disabled = false;
  } catch (error) {
    cameraStatus.textContent = "Camera blocked";
    console.error(error);
  }
}

async function startCalibration() {
  const calibration = await postJson("/api/calibration/start");
  applyCalibrationState(calibration);
}

async function toggleDrill() {
  if (drillTimer) {
    const state = await postJson("/api/drill/stop");
    clearInterval(drillTimer);
    drillTimer = null;
    applyDrillState(state);
    return;
  }

  const formData = new FormData();
  formData.append("drill", selectedDrill);
  const state = await postJson("/api/drill/start", formData);
  applyDrillState(state);
  drillTimer = window.setInterval(updateDrillCue, 250);
}

async function updateDrillCue() {
  const response = await fetch("/api/drill/tick");
  applyDrillState(await response.json());
}

function applyDrillState(state) {
  repCount.textContent = state.repLabel;
  startDrill.textContent = state.buttonLabel;
  cameraStatus.textContent = state.status;
}

function applyVisionState(poseResult) {
  if (poseResult.calibration) {
    applyCalibrationState(poseResult.calibration);
  }

  if (drillTimer || typeof poseResult.isLoaded !== "boolean") {
    return;
  }

  if (poseResult.calibration?.active) {
    return;
  }

  cameraStatus.textContent = poseResult.isLoaded
    ? "Loaded stance"
    : poseResult.basePose
      ? "Stand loaded"
      : poseResult.message;
}

function applyCalibrationState(calibration) {
  if (!calibration.active) {
    calibratePose.disabled = !stream;
    calibratePose.textContent = calibration.ready ? "Recalibrate" : "Calibrate";
    return;
  }

  calibratePose.disabled = true;
  if (!calibration.collecting) {
    cameraStatus.textContent = `Stand tall: ${Math.ceil(calibration.delayRemaining)}s`;
    calibratePose.textContent = "Waiting";
    return;
  }

  cameraStatus.textContent = `Calibrating: ${Math.ceil(calibration.timeRemaining)}s`;
  calibratePose.textContent = "Calibrating";
}

async function requestLandmarkAnalysis(video) {
  // Keep requests low while the Python endpoint is just boilerplate.
  const now = performance.now();
  if (now - lastVisionRequest < (1000/60)) {
    return { landmarks: [], message: "Waiting for next frame" };
  }
  lastVisionRequest = now;

  const frame = await captureFrame(video);
  const formData = new FormData();
  formData.append("frame", frame, "camera-frame.jpg");

  return postJson("/api/vision/analyze", formData);
}

async function captureFrame(video) {
  const canvas = document.createElement("canvas");
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);

  return new Promise((resolve) => {
    canvas.toBlob((blob) => resolve(blob), "image/jpeg", 0.72);
  });
}

async function postJson(url, body = undefined) {
  const response = await fetch(url, {
    method: "POST",
    body,
  });

  return response.json();
}

function resizeLandmarkCanvas(video, canvas) {
  const width = video.videoWidth || video.clientWidth;
  const height = video.videoHeight || video.clientHeight;

  if (!width || !height) {
    return;
  }

  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
  }
}

function drawLandmarkOverlay(canvas, poseResult) {
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  if (!poseResult.landmarks.length) {
    drawWaitingState(ctx, canvas, poseResult.message);
    return;
  }

  poseResult.landmarks.forEach((landmark) => {
    drawPoint(ctx, landmark.x * canvas.width, landmark.y * canvas.height);
  });
}

function drawPoint(ctx, x, y) {
  ctx.beginPath();
  ctx.arc(x, y, 5, 0, Math.PI * 2);
  ctx.fillStyle = "rgba(255, 176, 92, 0.92)";
  ctx.fill();
}

function drawWaitingState(ctx, canvas, message = "Python vision endpoint ready") {
  ctx.save();
  ctx.font = "14px Segoe UI, system-ui, sans-serif";
  ctx.fillStyle = "rgba(247, 244, 238, 0.78)";
  ctx.fillText(message, 18, 28);
  ctx.restore();
}

drillCards.forEach((card) => {
  card.addEventListener("click", () => {
    drillCards.forEach((item) => item.classList.remove("active"));
    card.classList.add("active");
    selectedDrill = card.dataset.drill;
  });
});

startCamera.addEventListener("click", enableCamera);
calibratePose.addEventListener("click", startCalibration);
startDrill.addEventListener("click", toggleDrill);

