import { useState, useRef, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import './VideoUploadPage.css';
import { createModule, uploadVideo, getModuleStatus, getModuleResults, mapViolation } from '../api';

const MODULE_INFO = {
  // Universal
  entrance: {
    label: 'Entrance & Doorways', icon: '🚪',
    instructions: [
      'Start outside, capture the full entrance area',
      'Film the door width from both sides — aim to show the full swing',
      'Capture any threshold, step, or level change at the entrance',
      'Show door hardware (handles, knobs, push plates)',
      'Pan slowly — hold each angle for at least 2 seconds',
    ],
  },
  hallway: {
    label: 'Corridors & Hallways', icon: '🏛️',
    instructions: [
      'Walk through the entire hallway at a slow, steady pace',
      'Capture both sides of the hallway to show full width',
      'Film any narrowing points, corners, or obstacles',
      'Show any protruding objects (fire extinguishers, signage)',
      'Include T-intersections and turning areas',
    ],
  },
  restroom: {
    label: 'Restrooms', icon: '🚻',
    instructions: [
      'Film the exterior signage and door',
      'Capture the accessible stall — show door width and space inside',
      'Film grab bars around the toilet',
      'Show sink, mirror, and towel dispenser heights',
      'Capture the door handle and latch mechanism',
    ],
  },
  parking: {
    label: 'Parking Lot', icon: '🅿️',
    instructions: [
      'Film all accessible parking spaces and their signage',
      'Capture the access aisle next to each space',
      'Show the curb cut and path of travel to the building entrance',
      'Film the van-accessible space (if present)',
      'Capture any slopes or uneven surfaces in the path',
    ],
  },
  elevator: {
    label: 'Elevator', icon: '🛗',
    instructions: [
      'Film the exterior call buttons — show their height',
      'Capture the floor indicator and braille signage outside',
      'Film the inside of the cab — show door width when open',
      'Capture the interior control panel and its height',
      'Show the floor of the elevator and the gap at the landing',
    ],
  },
  stairway: {
    label: 'Stairs & Handrails', icon: '🪜',
    instructions: [
      'Film the full length of the staircase',
      'Capture both handrails — show where they start and end',
      'Film the nosings/edges of each step',
      'Show the landing areas at the top and bottom',
      'Capture handrail extensions beyond the top and bottom steps',
    ],
  },
  signage: {
    label: 'Signage & Wayfinding', icon: '🪧',
    instructions: [
      'Film all room identification signs',
      'Capture the mounting height of each sign',
      'Show braille and raised characters up close',
      'Film signs near corners or doors (placement relative to door)',
      'Include exit signs and emergency signage',
    ],
  },
  drinking_fountain: {
    label: 'Drinking Fountain', icon: '💧',
    instructions: [
      'Film the spout and control height from the floor',
      'Capture knee clearance underneath (if present)',
      'Show both hi and lo units if a hi-lo fountain is installed',
      'Include a reference object for scale if possible',
    ],
  },
  // Dining / Food Service
  dining: {
    label: 'Dining Area', icon: '🍽️',
    instructions: [
      'Pan through the entire dining area',
      'Show table heights at eye level',
      'Capture aisle widths between tables',
      'Show accessible seating arrangements',
    ],
  },
  counter: {
    label: 'Service Counter', icon: '🏪',
    instructions: [
      'Film the front-facing side of the counter',
      'Capture the counter height — include a reference point if possible',
      'Show any lower section of the counter (accessible portion)',
      'Film knee clearance underneath (if applicable)',
    ],
  },
  outdoor_seating: {
    label: 'Outdoor Seating', icon: '🌿',
    instructions: [
      'Show the route from the entrance to the outdoor area',
      'Capture the surface texture (pavers, concrete, etc.)',
      'Film table heights and accessible setups',
      'Show any barriers or obstacles',
    ],
  },
  cafeteria: {
    label: 'Cafeteria / Dining Hall', icon: '🥗',
    instructions: [
      'Walk through the food service line showing counter height',
      'Film tray slide height and reach distance',
      'Show aisle widths between tables',
      'Capture accessible seating arrangements',
    ],
  },
  concession: {
    label: 'Concession Stand', icon: '🍿',
    instructions: [
      'Film the full counter height from the floor',
      'Capture any accessible lowered section',
      'Show the approach space and queue setup',
    ],
  },
  // Retail
  sales_floor: {
    label: 'Sales Floor & Aisles', icon: '🛍️',
    instructions: [
      'Walk the narrowest aisles first',
      'Show full aisle width between merchandise displays',
      'Capture any protruding objects or displays',
      'Show the accessible route to all departments',
    ],
  },
  checkout: {
    label: 'Checkout Counter', icon: '🧾',
    instructions: [
      'Film the counter height from the floor',
      'Capture any accessible lowered section',
      'Show PIN pad placement and reach distance',
      'Film queue aisle width',
    ],
  },
  fitting_room: {
    label: 'Fitting Room', icon: '👗',
    instructions: [
      'Show the door clear width',
      'Capture interior turning space',
      'Film bench height and side clearance',
      'Show hook heights on the wall',
    ],
  },
  // Office / Professional
  reception: {
    label: 'Reception Desk', icon: '🗂️',
    instructions: [
      'Film the full counter height',
      'Capture any accessible lowered section',
      'Show approach clearance',
      'Film any barriers between visitor and staff',
    ],
  },
  conference_room: {
    label: 'Conference Room', icon: '💼',
    instructions: [
      'Show door width when fully open',
      'Film table height and knee clearance',
      'Capture turning space in the room',
      'Show accessible path to all seats',
    ],
  },
  break_room: {
    label: 'Break Room / Kitchen', icon: '☕',
    instructions: [
      'Film sink and counter heights',
      'Show knee clearance under the sink',
      'Capture appliance reach distances',
      'Show overall floor clearance',
    ],
  },
  // Medical / Healthcare
  waiting_room: {
    label: 'Waiting Room', icon: '🪑',
    instructions: [
      'Show wheelchair-accessible seating spaces',
      'Capture aisle widths between chairs',
      'Film check-in counter height',
      'Show route from entrance',
    ],
  },
  exam_room: {
    label: 'Examination Room', icon: '🩺',
    instructions: [
      'Film the exam table height from the floor',
      'Show door width when open',
      'Capture turning space near the table',
      'Show any grab bars',
    ],
  },
  patient_room: {
    label: 'Patient Room', icon: '🛏️',
    instructions: [
      'Show clear floor space on each side of the bed',
      'Film bathroom door width',
      'Capture call button placement',
      'Show route from door to bed',
    ],
  },
  pharmacy: {
    label: 'Pharmacy Counter', icon: '💊',
    instructions: [
      'Film the full counter height',
      'Show the consultation area',
      'Capture accessible reach distances',
      'Film PIN pad placement',
    ],
  },
  // Hotel / Lodging
  lobby: {
    label: 'Hotel Lobby', icon: '🏨',
    instructions: [
      'Walk from entrance to the check-in desk',
      'Show check-in desk height and accessible section',
      'Capture route to elevator and amenities',
      'Film any floor surface transitions',
    ],
  },
  guest_room: {
    label: 'Accessible Guest Room', icon: '🛎️',
    instructions: [
      'Show clear floor space on each side of the bed',
      'Film bathroom with grab bars',
      'Capture roll-in shower or tub clearance',
      'Show closet rod height and accessible controls',
    ],
  },
  pool: {
    label: 'Pool & Spa Area', icon: '🏊',
    instructions: [
      'Show pool lift or entry ramp',
      'Capture deck surface (slip resistance)',
      'Film route from changing area to pool',
      'Show accessible locker and bench heights',
    ],
  },
  fitness_center: {
    label: 'Fitness Center', icon: '🏋️',
    instructions: [
      'Walk through showing aisle widths between equipment',
      'Capture accessible machine examples',
      'Show locker and bench heights',
      'Film route from entrance',
    ],
  },
  // Education
  classroom: {
    label: 'Classroom', icon: '📚',
    instructions: [
      'Show aisle width between desks',
      'Film an accessible desk with knee clearance',
      'Capture whiteboard/blackboard reach height',
      'Show door width and turning space',
    ],
  },
  gymnasium: {
    label: 'Gymnasium', icon: '🏀',
    instructions: [
      'Show accessible spectator seating area',
      'Film route from entrance to the gym floor',
      'Capture locker room door widths',
      'Show any fixed equipment clearances',
    ],
  },
  auditorium: {
    label: 'Auditorium', icon: '🎭',
    instructions: [
      'Show wheelchair seating spaces and companion seats',
      'Capture route from entrance to accessible seating',
      'Film stage access ramp or lift',
      'Show sight lines from accessible seating',
    ],
  },
  library: {
    label: 'Library', icon: '📖',
    instructions: [
      'Walk aisles showing width between shelves',
      'Film reach height of shelves',
      'Show accessible study table knee clearance',
      'Capture catalog terminal height',
    ],
  },
  // Assembly / Entertainment
  assembly_seating: {
    label: 'Assembly Seating', icon: '🎪',
    instructions: [
      'Show wheelchair space dimensions',
      'Capture companion seat placement',
      'Film route from entrance to accessible seating',
      'Show aisle widths',
    ],
  },
  stage: {
    label: 'Stage Access', icon: '🎤',
    instructions: [
      'Show ramp or lift for stage access',
      'Film handrail height and extension',
      'Capture approach clearance',
      'Show the performer/presenter area',
    ],
  },
  ticket_booth: {
    label: 'Ticket / Box Office', icon: '🎟️',
    instructions: [
      'Film counter/window height from the floor',
      'Capture any accessible lowered section',
      'Show approach clearance',
      'Film queue/line setup',
    ],
  },
};

const MOCK_FINDINGS = {
  entrance: [
    {
      id: 'e1',
      severity: 'violation',
      title: 'Door clear width insufficient',
      detail: 'Measured door opening appears to be approximately 28–30". ADA requires a minimum clear width of 32" (36" preferred).',
      citation: 'ADA Standards §404.2.3',
    },
    {
      id: 'e2',
      severity: 'warning',
      title: 'Door hardware may require tight grasping',
      detail: 'Round door knobs require tight grasping and twisting. Lever-style hardware is required.',
      citation: 'ADA Standards §404.2.7',
    },
  ],
  corridors: [
    {
      id: 'c1',
      severity: 'violation',
      title: 'Corridor width below minimum',
      detail: 'Hallway appears narrower than the required 36" minimum passable width in one section.',
      citation: 'ADA Standards §403.5.1',
    },
  ],
  restrooms: [
    {
      id: 'r1',
      severity: 'violation',
      title: 'No accessible stall detected',
      detail: 'No stall meeting the 60" × 60" turning space requirement was observed.',
      citation: 'ADA Standards §604.3.1',
    },
    {
      id: 'r2',
      severity: 'warning',
      title: 'Grab bar missing or incorrectly placed',
      detail: 'Side grab bar appears absent or not mounted at the required 33–36" height.',
      citation: 'ADA Standards §604.5.1',
    },
  ],
  stairs: [
    {
      id: 's1',
      severity: 'warning',
      title: 'Handrail does not extend beyond top riser',
      detail: 'Handrail appears to end at the top step rather than extending 12" horizontally beyond it.',
      citation: 'ADA Standards §505.10.2',
    },
  ],
  parking: [
    {
      id: 'p1',
      severity: 'violation',
      title: 'No van-accessible space identified',
      detail: 'Lots with accessible parking must include at least one van-accessible space with an 8-foot access aisle.',
      citation: 'ADA Standards §502.2',
    },
    {
      id: 'p2',
      severity: 'violation',
      title: 'Accessible space sign not visible',
      detail: 'International Symbol of Accessibility sign must be mounted at minimum 60" above the ground.',
      citation: 'ADA Standards §502.6',
    },
  ],
  counter: [
    {
      id: 'co1',
      severity: 'violation',
      title: 'No accessible lowered counter section',
      detail: 'Full counter height observed at approximately 42". A section no higher than 36" is required.',
      citation: 'ADA Standards §904.4.1',
    },
  ],
  elevator: [],
  signage: [
    {
      id: 'sg1',
      severity: 'warning',
      title: 'Signage mounted at incorrect height',
      detail: 'Room identification signs must be mounted with the centerline at 60" AFF (above finished floor).',
      citation: 'ADA Standards §703.4.1',
    },
  ],
};

function VideoUploadPage() {
  const { moduleId: moduleType } = useParams(); // e.g. "entrance"
  const navigate = useNavigate();
  const fileInputRef = useRef();
  const pollRef = useRef(null);

  const isAuto = moduleType === 'auto';
  const info = MODULE_INFO[moduleType] || {
    label: isAuto ? 'Add Room' : 'Unknown Module',
    icon: isAuto ? '🔍' : '📹',
    instructions: isAuto ? [
      'Walk slowly through the entire room at a steady pace',
      'Pan left and right to show all features — doors, walls, floor surface',
      'Capture any accessibility features: grab bars, counters, signs, ramps',
      'Hold each angle for at least 2 seconds',
      'Ensure good lighting throughout',
    ] : [],
  };

  const [phase, setPhase] = useState('upload'); // upload | recording | analyzing | results
  const [fileName, setFileName] = useState(null);
  const [progress, setProgress] = useState(0);
  const [progressLabel, setProgressLabel] = useState('');
  const [findings, setFindings] = useState([]);
  const [backendModuleId, setBackendModuleId] = useState(null);
  const [error, setError] = useState(null);
  const [detectedModuleType, setDetectedModuleType] = useState(null);

  // Recording state
  const videoPreviewRef = useRef();
  const mediaRecorderRef = useRef(null);
  const recordedChunksRef = useRef([]);
  const streamRef = useRef(null);
  const [isRecording, setIsRecording] = useState(false);
  const [recordedBlob, setRecordedBlob] = useState(null);

  const pendingFileRef = useRef(null);
  const createStartedRef = useRef(false);

  // On mount: register this module in the backend if not already done
  useEffect(() => {
    const auditId = localStorage.getItem('auditId');
    if (!auditId) return;

    // Prevent React StrictMode double-invoke from creating two module entries
    if (createStartedRef.current) return;
    createStartedRef.current = true;

    if (moduleType === 'auto') {
      // ModulesPage already called createModule and stored the id
      const existingId = localStorage.getItem('currentAutoModuleId');
      if (existingId) {
        setBackendModuleId(existingId);
      } else {
        // Fallback: create a new auto module
        createModule(auditId, 'auto')
          .then(({ module_id }) => {
            localStorage.setItem('currentAutoModuleId', module_id);
            setBackendModuleId(module_id);
          })
          .catch((err) => console.error('Failed to create auto module:', err));
      }
    } else {
      const stored = JSON.parse(localStorage.getItem('auditModuleIds') || '{}');
      if (stored[moduleType]) {
        setBackendModuleId(stored[moduleType]);
      } else {
        createModule(auditId, moduleType)
          .then(({ module_id }) => {
            const latest = JSON.parse(localStorage.getItem('auditModuleIds') || '{}');
            latest[moduleType] = module_id;
            localStorage.setItem('auditModuleIds', JSON.stringify(latest));
            setBackendModuleId(module_id);
          })
          .catch((err) => console.error('Failed to create module:', err));
      }
    }

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [moduleType]);

  // If a file was selected before backendModuleId was ready, start analysis now
  useEffect(() => {
    if (backendModuleId && pendingFileRef.current) {
      const auditId = localStorage.getItem('auditId');
      const file = pendingFileRef.current;
      pendingFileRef.current = null;
      startRealAnalysis(auditId, backendModuleId, file);
    }
  }, [backendModuleId]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setFileName(file.name);
    const auditId = localStorage.getItem('auditId');
    if (auditId && backendModuleId) {
      startRealAnalysis(auditId, backendModuleId, file);
    } else if (auditId) {
      // backendModuleId not ready yet — queue the file
      pendingFileRef.current = file;
      setPhase('analyzing');
      setProgress(5);
      setProgressLabel('Preparing module...');
    } else {
      startDemoAnalysis();
    }
  };

  const startRealAnalysis = async (auditId, bModuleId, file) => {
    setPhase('analyzing');
    setProgress(5);
    setProgressLabel('Uploading video...');
    setError(null);

    try {
      await uploadVideo(auditId, bModuleId, file);
      setProgress(15);

      pollRef.current = setInterval(async () => {
        try {
          const status = await getModuleStatus(auditId, bModuleId);
          setProgress(status.progress || 0);
          if (status.module_type && status.module_type !== 'auto') {
            setDetectedModuleType(status.module_type);
          }

          const labels = {
            extracting_frames: 'Extracting frames and removing duplicates...',
            classifying: 'Identifying room type...',
            analyzing: 'Running AI analysis...',
            checking_compliance: 'Checking against ADA guidelines...',
            complete: 'Done!',
            error: 'Analysis encountered an error.',
          };
          setProgressLabel(labels[status.status] || 'Processing...');

          if (status.status === 'complete') {
            clearInterval(pollRef.current);
            const results = await getModuleResults(auditId, bModuleId);
            const mapped = (results.violations || []).map(mapViolation);
            setFindings(mapped);

            const existing = JSON.parse(localStorage.getItem('auditModules') || '{}');
            existing[moduleType] = { status: 'complete', findings: mapped };
            localStorage.setItem('auditModules', JSON.stringify(existing));

            setProgress(100);
            setPhase('results');
          } else if (status.status === 'error') {
            clearInterval(pollRef.current);
            setError(status.error_message || 'Analysis failed. Try again.');
            setPhase('upload');
          }
        } catch (err) {
          console.error('Polling error:', err);
        }
      }, 2000);
    } catch (err) {
      console.error('Upload failed:', err);
      setError('Failed to upload video. Please try again.');
      setPhase('upload');
    }
  };

  // Demo mode: simulates progress with mock findings
  const startDemoAnalysis = () => {
    const mockFindings = MOCK_FINDINGS[moduleType] || [];
    setPhase('analyzing');
    setProgress(0);
    setProgressLabel('Extracting frames and removing duplicates...');
    const interval = setInterval(() => {
      setProgress((p) => {
        if (p >= 30 && p < 60) setProgressLabel('Running depth estimation model...');
        if (p >= 60 && p < 85) setProgressLabel('Measuring key dimensions...');
        if (p >= 85) setProgressLabel('Checking against ADA guidelines...');
        if (p >= 100) {
          clearInterval(interval);
          setFindings(mockFindings);
          const existing = JSON.parse(localStorage.getItem('auditModules') || '{}');
          existing[moduleType] = { status: 'complete', findings: mockFindings };
          localStorage.setItem('auditModules', JSON.stringify(existing));
          setPhase('results');
          return 100;
        }
        return p + 4;
      });
    }, 120);
  };

  const startRecording = async () => {
    setError(null);
    setRecordedBlob(null);
    recordedChunksRef.current = [];
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      streamRef.current = stream;

      const mimeType = MediaRecorder.isTypeSupported('video/webm;codecs=vp9')
        ? 'video/webm;codecs=vp9'
        : MediaRecorder.isTypeSupported('video/webm')
        ? 'video/webm'
        : '';
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      mediaRecorderRef.current = recorder;
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) recordedChunksRef.current.push(e.data);
      };
      recorder.onstop = () => {
        const blob = new Blob(recordedChunksRef.current, { type: mimeType || 'video/webm' });
        setRecordedBlob(blob);
        stream.getTracks().forEach((t) => t.stop());
      };
      recorder.start();
      setIsRecording(true);
      setPhase('recording');
      // videoPreviewRef is not mounted yet — srcObject is set in the useEffect below
    } catch (err) {
      console.error('Camera error:', err.name, err.message);
      if (err.name === 'NotAllowedError') {
        setError('Camera access denied. In your browser address bar, click the camera icon and allow access, then try again.');
      } else if (err.name === 'NotFoundError') {
        setError('No camera found on this device.');
      } else {
        setError(`Camera error: ${err.message}`);
      }
    }
  };

  // Attach the live stream to the video element once the recording phase renders it
  useEffect(() => {
    if (phase === 'recording' && isRecording && videoPreviewRef.current && streamRef.current) {
      videoPreviewRef.current.srcObject = streamRef.current;
      videoPreviewRef.current.play().catch(() => {});
    }
    if (phase === 'recording' && !isRecording && recordedBlob && videoPreviewRef.current) {
      videoPreviewRef.current.srcObject = null;
      videoPreviewRef.current.src = URL.createObjectURL(recordedBlob);
      videoPreviewRef.current.controls = true;
      videoPreviewRef.current.play().catch(() => {});
    }
  }, [phase, isRecording, recordedBlob]);

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    setIsRecording(false);
  };

  const submitRecording = () => {
    if (!recordedBlob) return;
    const file = new File([recordedBlob], 'recording.webm', { type: 'video/webm' });
    setFileName('recording.webm');
    const auditId = localStorage.getItem('auditId');
    if (auditId && backendModuleId) {
      startRealAnalysis(auditId, backendModuleId, file);
    } else if (auditId) {
      pendingFileRef.current = file;
      setPhase('analyzing');
      setProgress(5);
      setProgressLabel('Preparing module...');
    } else {
      startDemoAnalysis();
    }
  };

  const cancelRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    streamRef.current?.getTracks().forEach((t) => t.stop());
    setIsRecording(false);
    setRecordedBlob(null);
    setPhase('upload');
  };

  const handleConfirm = () => {
    navigate('/modules');
  };

  const violations = findings.filter((f) => f.severity === 'violation');
  const warnings = findings.filter((f) => f.severity === 'warning');

  return (
    <div className="video-container">
      <div className="video-header">
        <button
          onClick={() => navigate('/dashboard')}
          style={{ background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '10px', padding: 0, marginRight: '16px' }}
        >
          <span className="logo-icon">&#10003;</span>
          <span className="logo-text">Passline</span>
        </button>
        <button className="back-btn" onClick={() => navigate('/modules')}>
          &#8249; Back to Modules
        </button>
        <span className="module-badge">
          {detectedModuleType
            ? `${MODULE_INFO[detectedModuleType]?.icon ?? '📷'} ${MODULE_INFO[detectedModuleType]?.label ?? detectedModuleType}`
            : `${info.icon} ${info.label}`}
        </span>
      </div>

      <div className="video-content">
        {phase === 'upload' && (
          <>
            <h2 className="video-title">Upload or Record Video</h2>
            <p className="video-sub">
              Follow the instructions below, then upload your video for analysis.
            </p>

            <div className="instructions-card">
              <h3>What to capture</h3>
              <ol className="instruction-list">
                {info.instructions.map((inst, i) => (
                  <li key={i}>{inst}</li>
                ))}
              </ol>
            </div>

            <div className="upload-area" onClick={() => fileInputRef.current.click()}>
              <div className="upload-icon">&#128249;</div>
              <p className="upload-label">Click to upload a video file</p>
              <p className="upload-hint">MP4, MOV, or AVI &mdash; max 500MB</p>
              <input
                ref={fileInputRef}
                type="file"
                accept="video/*"
                style={{ display: 'none' }}
                onChange={handleFileChange}
              />
            </div>

            <div className="divider-row">
              <span className="divider-line" />
              <span className="divider-text">or</span>
              <span className="divider-line" />
            </div>

            <button className="record-btn" onClick={startRecording}>
              &#9679; Record Video
            </button>
            <p className="record-hint">Use your device camera to record directly.</p>
            {error && <p className="record-hint" style={{ color: '#ff453a' }}>{error}</p>}

            <div className="divider-row" style={{ marginTop: '12px' }}>
              <span className="divider-line" />
              <span className="divider-text">or</span>
              <span className="divider-line" />
            </div>
            <button
              className="record-btn"
              style={{ background: 'transparent', color: '#8e8e93', border: '1px solid #3a3a3c', marginTop: '8px' }}
              onClick={startDemoAnalysis}
            >
              Use Demo Analysis
            </button>
          </>
        )}

        {phase === 'recording' && (
          <div className="analyzing-section">
            <video
              ref={videoPreviewRef}
              style={{ width: '100%', maxWidth: '480px', borderRadius: '12px', marginBottom: '16px', background: '#000' }}
              muted={isRecording}
              playsInline
            />
            {isRecording ? (
              <>
                <p className="analyzing-sub" style={{ color: '#ff453a' }}>&#9679; Recording...</p>
                <button className="confirm-btn" onClick={stopRecording}>&#9646;&#9646; Stop Recording</button>
              </>
            ) : (
              <>
                <p className="analyzing-sub">Review your recording, then submit or re-record.</p>
                <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
                  <button className="confirm-btn" onClick={submitRecording}>Submit for Analysis</button>
                  <button className="back-btn" style={{ marginTop: 0 }} onClick={startRecording}>Re-record</button>
                  <button className="back-btn" style={{ marginTop: 0 }} onClick={cancelRecording}>Cancel</button>
                </div>
              </>
            )}
          </div>
        )}

        {phase === 'analyzing' && (
          <div className="analyzing-section">
            <div className="analyzing-spinner" />
            <h2 className="analyzing-title">Analyzing Video...</h2>
            <p className="analyzing-sub">{progressLabel}</p>
            <div className="progress-bar-track">
              <div
                className="progress-bar-fill"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="progress-pct">{progress}%</p>
          </div>
        )}

        {phase === 'results' && (
          <>
            <div className="results-summary">
              <h2 className="results-title">Analysis Complete</h2>
              {findings.length === 0 ? (
                <div className="results-pass">
                  <span className="pass-icon">&#10003;</span>
                  <p>No violations detected in this module. Looks good!</p>
                </div>
              ) : (
                <p className="results-sub">
                  Found{' '}
                  <span className="count-violation">{violations.length} violation{violations.length !== 1 ? 's' : ''}</span>
                  {warnings.length > 0 && (
                    <> and <span className="count-warning">{warnings.length} warning{warnings.length !== 1 ? 's' : ''}</span></>
                  )}{' '}
                  in <strong>{info.label}</strong>.
                </p>
              )}
            </div>

            {findings.length > 0 && (
              <div className="findings-list">
                {findings.map((f) => (
                  <div key={f.id} className={`finding-card finding-${f.severity}`}>
                    <div className="finding-top">
                      <span className={`finding-badge badge-${f.severity}`}>
                        {f.severity === 'violation' ? 'Violation' : 'Warning'}
                      </span>
                      <span className="finding-citation">{f.citation}</span>
                    </div>
                    <div className="finding-title">{f.title}</div>
                    <div className="finding-detail">{f.detail}</div>
                  </div>
                ))}
              </div>
            )}

            <button className="confirm-btn" onClick={handleConfirm}>
              Add to Audit &amp; Continue
            </button>
          </>
        )}
      </div>
    </div>
  );
}

export default VideoUploadPage;
