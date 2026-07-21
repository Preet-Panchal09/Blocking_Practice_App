const camera = document.querySelector("#camera");
const landmarkCanvas = document.querySelector("#landmarkCanvas");
const cameraStatus = document.querySelector("#cameraStatus");
const repCount = document.querySelector("#repCount");
const startCamera = document.querySelector("#startCamera");
const calibratePose = document.querySelector("#calibratePose");
const startDrill = document.querySelector("#startDrill");
const drillCards = document.querySelectorAll(".drill-card");

let stream = null;
let drillActive = false;
let landmarkLoopId = null;
let landmarkDetectionTimerId = null;
let landmarkLoopGeneration = 0;
let selectedDrill = "read";
let latestPoseResult = { landmarks: [], message: "Waiting for pose detection" };
let jumpStatusUntil = 0;
let calibrationReady = false;

const CAPTURE_WIDTH = 640;
const JUMP_STATUS_DURATION_MS = 750;
const captureCanvas = document.createElement("canvas");
const captureContext = captureCanvas.getContext("2d");

function syncCameraHeight() {
  document.documentElement.style.setProperty("--camera-height", `${window.innerHeight}px`);
}

syncCameraHeight();
window.addEventListener("resize", syncCameraHeight);
window.addEventListener("orientationchange", syncCameraHeight);

function startLandmarkLoop() {
  stopLandmarkLoop();
  const generation = landmarkLoopGeneration;

  const draw = () => {
    if (generation !== landmarkLoopGeneration) {
      return;
    }

    resizeLandmarkCanvas(camera, landmarkCanvas);
    drawLandmarkOverlay(landmarkCanvas, latestPoseResult);
    landmarkLoopId = requestAnimationFrame(draw);
  };

  const detect = async () => {
    let retryDelay = 0;
    try {
      latestPoseResult = await requestLandmarkAnalysis(camera);
      applyVisionState(latestPoseResult);
    } catch (error) {
      console.error("Landmark detection failed", error);
      cameraStatus.textContent = "Vision reconnecting";
      retryDelay = 500;
    } finally {
      if (generation === landmarkLoopGeneration) {
        // Start the next capture as soon as this request finishes, without
        // allowing multiple expensive vision requests to overlap.
        landmarkDetectionTimerId = window.setTimeout(detect, retryDelay);
      }
    }
  };

  draw();
  detect();
}

function stopLandmarkLoop() {
  landmarkLoopGeneration += 1;

  if (landmarkLoopId) {
    cancelAnimationFrame(landmarkLoopId);
    landmarkLoopId = null;
  }

  if (landmarkDetectionTimerId) {
    clearTimeout(landmarkDetectionTimerId);
    landmarkDetectionTimerId = null;
  }
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
    startDrill.disabled = true;
  } catch (error) {
    cameraStatus.textContent = "Camera blocked";
    console.error(error);
  }
}

async function startCalibration() {
  try {
    const calibration = await postJson("/api/calibration/start");
    applyCalibrationState(calibration);
  } catch (error) {
    cameraStatus.textContent = error.message;
  }
}

async function toggleDrill() {
  try {
    if (drillActive) {
      applyDrillState(await postJson("/api/drill/stop"));
      return;
    }

    const formData = new FormData();
    formData.append("drill", selectedDrill);
    applyDrillState(await postJson("/api/drill/start", formData));
  } catch (error) {
    cameraStatus.textContent = error.message;
  }
}

function applyDrillState(state) {
  drillActive = state.active;
  repCount.textContent = state.repLabel;
  startDrill.textContent = state.buttonLabel;
  calibratePose.disabled = drillActive || !stream;

  if (performance.now() >= jumpStatusUntil) {
    cameraStatus.textContent = state.status;
  }
}

function applyVisionState(poseResult) {
  if (poseResult.calibration) {
    applyCalibrationState(poseResult.calibration);
  }

  if (
    typeof poseResult.isLoaded !== "boolean" ||
    typeof poseResult.isJumped !== "boolean"
  ) {
    return;
  }

  if (poseResult.calibration?.active) {
    return;
  }

  if (!poseResult.calibration?.ready) {
    return;
  }

  if (poseResult.drill) {
    applyDrillState(poseResult.drill);
  }

  if (poseResult.isJumped) {
    jumpStatusUntil = performance.now() + JUMP_STATUS_DURATION_MS;
  }

  if (performance.now() < jumpStatusUntil) {
    cameraStatus.textContent = "Jumped";
    return;
  }

  if (drillActive) {
    return;
  }

  cameraStatus.textContent = poseResult.isLoaded
    ? "Loaded stance"
    : poseResult.basePose
      ? "Stand loaded"
      : poseResult.message;
}

function applyCalibrationState(calibration) {
  calibrationReady = calibration.ready;

  if (!calibration.active) {
    calibratePose.disabled = !stream || drillActive;
    calibratePose.textContent = calibration.ready ? "Recalibrate" : "Calibrate";
    startDrill.disabled = !stream || !calibrationReady;
    if (calibration.message && performance.now() >= jumpStatusUntil) {
      cameraStatus.textContent = calibration.message;
    }
    return;
  }

  calibratePose.disabled = true;
  startDrill.disabled = true;
  if (!calibration.collecting) {
    cameraStatus.textContent = `Stand tall: ${Math.ceil(calibration.delayRemaining)}s`;
    calibratePose.textContent = "Waiting";
    return;
  }

  cameraStatus.textContent = `Calibrating: ${Math.ceil(calibration.timeRemaining)}s`;
  calibratePose.textContent = "Calibrating";
}

async function requestLandmarkAnalysis(video) {
  const frame = await captureFrame(video);
  const formData = new FormData();
  formData.append("frame", frame, "camera-frame.jpg");

  return postJson("/api/vision/analyze", formData);
}

async function captureFrame(video) {
  const sourceWidth = video.videoWidth;
  const sourceHeight = video.videoHeight;
  if (!sourceWidth || !sourceHeight) {
    throw new Error("Camera frame is not ready");
  }

  const captureHeight = Math.round(CAPTURE_WIDTH * (sourceHeight / sourceWidth));

  if (captureCanvas.width !== CAPTURE_WIDTH || captureCanvas.height !== captureHeight) {
    captureCanvas.width = CAPTURE_WIDTH;
    captureCanvas.height = captureHeight;
  }

  captureContext.drawImage(video, 0, 0, CAPTURE_WIDTH, captureHeight);

  return new Promise((resolve, reject) => {
    captureCanvas.toBlob((blob) => {
      if (blob) {
        resolve(blob);
      } else {
        reject(new Error("Unable to capture camera frame"));
      }
    }, "image/jpeg", 0.6);
  });
}

async function postJson(url, body = undefined) {
  const response = await fetch(url, {
    method: "POST",
    body,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Request failed (${response.status})`);
  }

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

document.addEventListener("visibilitychange", () => {
  if (document.hidden) {
    stopLandmarkLoop();
  } else if (stream) {
    startLandmarkLoop();
  }
});

window.addEventListener("pagehide", () => {
  stopLandmarkLoop();
  stream?.getTracks().forEach((track) => track.stop());
});

