import { useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import './ReportPage.css';
import { triggerReport, getReport } from '../api';

const MODULE_LABELS = {
  entrance: 'Entrance & Doorways', hallway: 'Corridors & Hallways',
  restroom: 'Restrooms', parking: 'Parking Lot',
  elevator: 'Elevator', stairway: 'Stairs & Handrails',
  signage: 'Signage & Wayfinding', drinking_fountain: 'Drinking Fountain',
  dining: 'Dining Area', counter: 'Service Counter',
  outdoor_seating: 'Outdoor Seating', cafeteria: 'Cafeteria / Dining Hall',
  concession: 'Concession Stand', sales_floor: 'Sales Floor & Aisles',
  checkout: 'Checkout Counter', fitting_room: 'Fitting Room',
  reception: 'Reception Desk', conference_room: 'Conference Room',
  break_room: 'Break Room / Kitchen', waiting_room: 'Waiting Room',
  exam_room: 'Examination Room', patient_room: 'Patient Room',
  pharmacy: 'Pharmacy Counter', lobby: 'Hotel Lobby',
  guest_room: 'Accessible Guest Room', pool: 'Pool & Spa Area',
  fitness_center: 'Fitness Center', classroom: 'Classroom',
  gymnasium: 'Gymnasium', auditorium: 'Auditorium',
  library: 'Library', assembly_seating: 'Assembly Seating',
  stage: 'Stage Access', ticket_booth: 'Ticket / Box Office',
};

const MODULE_ICONS = {
  entrance: '🚪', hallway: '🏛️', restroom: '🚻', parking: '🅿️',
  elevator: '🛗', stairway: '🪜', signage: '🪧', drinking_fountain: '💧',
  dining: '🍽️', counter: '🏪', outdoor_seating: '🌿', cafeteria: '🥗',
  concession: '🍿', sales_floor: '🛍️', checkout: '🧾', fitting_room: '👗',
  reception: '🗂️', conference_room: '💼', break_room: '☕',
  waiting_room: '🪑', exam_room: '🩺', patient_room: '🛏️', pharmacy: '💊',
  lobby: '🏨', guest_room: '🛎️', pool: '🏊', fitness_center: '🏋️',
  classroom: '📚', gymnasium: '🏀', auditorium: '🎭', library: '📖',
  assembly_seating: '🎪', stage: '🎤', ticket_booth: '🎟️',
};

// critical/high → violation badge, medium/low → warning badge
function sevBadge(severity) {
  return (severity === 'critical' || severity === 'high') ? 'violation' : 'warning';
}

function roomLabel(mg) {
  if (mg.room_name && mg.room_name.trim()) return mg.room_name.trim();
  const type = mg.module_type || '';
  return MODULE_LABELS[type] || type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) || 'Unknown Room';
}

function roomIcon(mg) {
  return MODULE_ICONS[mg.module_type] || '📷';
}


function ReportPage() {
  const navigate = useNavigate();
  const [reportData, setReportData] = useState(null);
  const [pdfUrl, setPdfUrl] = useState(null);
  const [generating, setGenerating] = useState(true);
  const survey = JSON.parse(localStorage.getItem('surveyAnswers') || '{}');
  const auditId = localStorage.getItem('auditId');
  const userName = localStorage.getItem('userName') || 'Auditor';

  useEffect(() => {
    if (!auditId) { setGenerating(false); return; }
    let cancelled = false;
    let intervalId = null;
    let timeoutId = null;

    async function run() {
      // Record the time we trigger so we only accept a freshly-generated report.
      const triggeredAt = new Date();
      try {
        await triggerReport(auditId);
      } catch (err) {
        console.error('trigger report:', err);
      }

      async function poll() {
        try {
          const report = await getReport(auditId);
          if (cancelled) return;
          // Accept only a report generated after we triggered it.
          const reportTime = report.generated_at ? new Date(report.generated_at) : null;
          const isFresh = reportTime && reportTime >= triggeredAt;
          if (isFresh) {
            setReportData(report);
            setGenerating(false);
            if (report.pdf_url) setPdfUrl(`http://localhost:8000${report.pdf_url}`);
            clearInterval(intervalId);
            clearTimeout(timeoutId);
          }
        } catch {
          // not ready yet — keep polling
        }
      }

      poll();
      intervalId = setInterval(poll, 3000);
      // Fallback: show whatever we have after 2 minutes
      timeoutId = setTimeout(async () => {
        clearInterval(intervalId);
        if (cancelled) return;
        try {
          const report = await getReport(auditId);
          if (!cancelled) { setReportData(report); }
        } catch { /* ignore */ }
        if (!cancelled) setGenerating(false);
      }, 120000);
    }

    run();
    return () => { cancelled = true; clearInterval(intervalId); clearTimeout(timeoutId); };
  }, [auditId]);

  const today = new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });

  if (generating || !reportData) {
    return (
      <div className="report-container">
        <div className="report-header">
          <div className="report-logo">
            <span className="logo-icon">&#10003;</span>
            <span className="logo-text">Passline</span>
          </div>
        </div>
        <div style={{ textAlign: 'center', paddingTop: '80px', color: 'var(--overlay0)' }}>
          Generating report…
        </div>
      </div>
    );
  }

  const moduleGroups = reportData.module_violations || [];
  const totalViolations = reportData.total_violations || 0;
  const totalWarnings = (reportData.violations || []).filter(v => sevBadge(v.severity) === 'warning').length;
  const costTotal = reportData.estimated_remediation_total || { low: 0, high: 0 };
  const score = reportData.overall_score ?? 100;
  const scoreColor = score >= 75 ? '#34c759' : score >= 45 ? '#ffd60a' : '#ff453a';

  return (
    <div className="report-container">
      <div className="report-header">
        <div className="report-logo">
          <span className="logo-icon">&#10003;</span>
          <span className="logo-text">Passline</span>
        </div>
        <button className="new-audit-link" onClick={() => navigate('/dashboard')}>
          &#8249; Dashboard
        </button>
      </div>

      <div className="report-content">
        <div className="report-meta">
          <div>
            <h1 className="report-title">ADA Compliance Report</h1>
            <p className="report-business">
              {survey.businessName || 'Property Audit'}
              {survey.city && survey.state ? ` — ${survey.city}, ${survey.state}` : ''}
            </p>
            <p className="report-date">
              Prepared by {userName} &middot; {today}
            </p>
          </div>
        </div>

        <div className="score-row">
          <div className="score-card">
            <div className="score-number" style={{ color: scoreColor }}>{score}</div>
            <div className="score-label">Compliance Score</div>
            <div className="score-sub">out of 100</div>
          </div>
          <div className="score-stats">
            <div className="stat-item">
              <span className="stat-number stat-violation">{totalViolations}</span>
              <span className="stat-label">Violations</span>
            </div>
            <div className="stat-divider" />
            <div className="stat-item">
              <span className="stat-number stat-warning">{totalWarnings}</span>
              <span className="stat-label">Warnings</span>
            </div>
            <div className="stat-divider" />
            <div className="stat-item">
              <span className="stat-number">{moduleGroups.length}</span>
              <span className="stat-label">Rooms Audited</span>
            </div>
          </div>
        </div>

        {(costTotal.low > 0 || costTotal.high > 0) && (
          <div className="cost-banner">
            <span className="cost-label">Estimated Remediation Cost</span>
            <span className="cost-range">
              ${Math.round(costTotal.low).toLocaleString()} – ${Math.round(costTotal.high).toLocaleString()}
            </span>
          </div>
        )}

        <div className="findings-section">
          <h2 className="section-heading">Findings by Room</h2>

          {moduleGroups.map((mg) => {
            const violations = (mg.violations || []).filter(v => sevBadge(v.severity) === 'violation');
            const warnings = (mg.violations || []).filter(v => sevBadge(v.severity) === 'warning');
            const isCompliant = mg.violations.length === 0;
            const label = roomLabel(mg);
            const icon = roomIcon(mg);
            const shortId = mg.module_id ? mg.module_id.slice(0, 8) : '';

            return (
              <div className="module-section" key={mg.module_id}>
                <div className="module-section-header">
                  <span className="module-section-icon">{icon}</span>
                  <span className="module-section-label">{label}</span>
                  {isCompliant ? (
                    <span className="module-pass-badge">&#10003; Compliant</span>
                  ) : (
                    <span className="module-count">
                      {violations.length > 0 && `${violations.length} violation${violations.length !== 1 ? 's' : ''}`}
                      {violations.length > 0 && warnings.length > 0 && ', '}
                      {warnings.length > 0 && `${warnings.length} warning${warnings.length !== 1 ? 's' : ''}`}
                    </span>
                  )}
                  {shortId && <span className="module-id-badge">{shortId}</span>}
                </div>

                {!isCompliant && (
                  <div className="module-findings">
                    {mg.violations.map((v, i) => {
                      const badge = sevBadge(v.severity);
                      const title = v.element ? `${v.element}: ${v.finding}` : v.finding;
                      return (
                        <div key={v.violation_id || i} className={`report-finding finding-${badge}`}>
                          <div className="rf-top">
                            <span className={`rf-badge badge-${badge}`}>
                              {badge === 'violation' ? 'Violation' : 'Warning'}
                            </span>
                            <span className="rf-citation">{v.code || ''}</span>
                          </div>
                          <div className="rf-title">{title}</div>
                          {v.description && <div className="rf-detail">{v.description}</div>}
                          {v.remediation && (
                            <div className="rf-detail" style={{ marginTop: '4px', fontStyle: 'italic' }}>
                              {v.remediation}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}

          {moduleGroups.length > 0 && totalViolations === 0 && (
            <div className="pass-banner">
              <span className="pass-icon">&#10003;</span>
              <div>
                <strong>No violations found!</strong>
                <p>This property appears to meet ADA standards for all audited rooms.</p>
              </div>
            </div>
          )}
        </div>

        <div className="report-actions">
          <button className="action-btn btn-secondary" onClick={() => navigate('/modules')}>
            Continue Auditing
          </button>
          <button className="action-btn btn-primary" onClick={() => window.print()}>
            &#128438; Save / Print Report
          </button>
          {pdfUrl && (
            <a
              className="action-btn btn-primary"
              href={pdfUrl}
              target="_blank"
              rel="noreferrer"
              download
            >
              &#128196; Download PDF Report
            </a>
          )}
        </div>

        <p className="report-disclaimer">
          This report is generated based on video analysis and is intended as a preliminary
          self-assessment only. It does not constitute a formal ADA compliance certification.
          Consult a certified ADA inspector for legally binding compliance verification.
        </p>
      </div>
    </div>
  );
}

export default ReportPage;
