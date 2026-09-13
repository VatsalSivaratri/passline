const BASE_URL = 'http://localhost:8000/api';
export async function createAudit() {
  const res = await fetch(`${BASE_URL}/audits`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to create audit');
  return res.json(); // { audit_id }
}
export async function saveQuestionnaire(auditId, data) {
  const res = await fetch(`${BASE_URL}/audits/${auditId}/questionnaire`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to save questionnaire');
  return res.json(); // { audit_id, applicable_modules, rule_count }
}
export async function getAudit(auditId) {
  const res = await fetch(`${BASE_URL}/audits/${auditId}`);
  if (!res.ok) throw new Error('Failed to get audit');
  return res.json();
}
export async function createModule(auditId, moduleType) {
  const res = await fetch(`${BASE_URL}/audits/${auditId}/modules`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ module_type: moduleType }),
  });
  if (!res.ok) throw new Error('Failed to create module');
  return res.json(); // { module_id, instructions }
}
export async function uploadVideo(auditId, moduleId, file) {
  const form = new FormData();
  form.append('video', file);
  const res = await fetch(`${BASE_URL}/audits/${auditId}/modules/${moduleId}/upload`, {
    method: 'POST',
    body: form,
  });
  if (!res.ok) throw new Error('Failed to upload video');
  return res.json();
}
export async function getModuleStatus(auditId, moduleId) {
  const res = await fetch(`${BASE_URL}/audits/${auditId}/modules/${moduleId}/status`);
  if (!res.ok) throw new Error('Failed to get module status');
  return res.json(); // { status, progress, module_type, violations_found, error_message }
}
export async function getModuleResults(auditId, moduleId) {
  const res = await fetch(`${BASE_URL}/audits/${auditId}/modules/${moduleId}/results`);
  if (!res.ok) throw new Error('Results not ready');
  return res.json(); // { violations, ... }
}
export async function renameModule(auditId, moduleId, roomName) {
  const res = await fetch(`${BASE_URL}/audits/${auditId}/modules/${moduleId}/name`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ room_name: roomName }),
  });
  if (!res.ok) throw new Error('Failed to rename module');
  return res.json();
}
export async function triggerReport(auditId) {
  const res = await fetch(`${BASE_URL}/audits/${auditId}/report`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to trigger report');
  return res.json();
}
export async function getReport(auditId) {
  const res = await fetch(`${BASE_URL}/audits/${auditId}/report`);
  if (!res.ok) throw new Error('Report not ready');
  return res.json(); // { overall_score, total_violations, violations, estimated_remediation_total, pdf_url }
}
// Map a backend violation object to the shape the frontend expects
export function mapViolation(v) {
  const isHighSeverity = v.severity === 'critical' || v.severity === 'high';
  const title = v.element ? `${v.element}: ${v.finding}` : v.finding;
  return {
    id: v.violation_id || String(Math.random()),
    severity: isHighSeverity ? 'violation' : 'warning',
    title,
    detail: v.finding,
    citation: v.code || '',
  };
}