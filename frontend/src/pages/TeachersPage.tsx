import { useState, type FormEvent } from 'react'
import { api } from '../api'
import { EmptyState, PageTitle } from '../components/Layout'
import { readableError } from '../errors'
import { useI18n } from '../i18n'
import type { Subject, Teacher } from '../types'

type Form = { first_name: string; last_name: string; username: string; password: string; subject_ids: number[]; max_weekly_hours: number; is_active: boolean }
const blank: Form = { first_name: '', last_name: '', username: '', password: '', subject_ids: [], max_weekly_hours: 18, is_active: true }

export function TeachersPage({ teachers, subjects, refresh, notify }: { teachers: Teacher[]; subjects: Subject[]; refresh: () => Promise<void>; notify: (message: string, error?: boolean) => void }) {
  const { t } = useI18n()
  const [form, setForm] = useState<Form>(blank)
  const [editing, setEditing] = useState<number | null>(null)
  const [busy, setBusy] = useState(false)
  function startEdit(teacher: Teacher) {
    setEditing(teacher.id)
    setForm({ first_name: teacher.first_name, last_name: teacher.last_name, username: teacher.account_username, password: '', subject_ids: teacher.subject_ids, max_weekly_hours: teacher.max_weekly_hours, is_active: teacher.is_active })
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
  function clear() { setEditing(null); setForm(blank) }
  function toggleSubject(id: number) { setForm(current => ({ ...current, subject_ids: current.subject_ids.includes(id) ? current.subject_ids.filter(value => value !== id) : [...current.subject_ids, id] })) }
  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!form.subject_ids.length) { notify(t('required'), true); return }
    setBusy(true)
    try {
      const payload = { ...form, ...(!form.password ? { password: undefined } : {}) }
      await api(editing ? `/teachers/${editing}/` : '/teachers/', editing ? 'PATCH' : 'POST', payload)
      await refresh(); clear(); notify(t('saved'))
    } catch (error) { notify(readableError(error, t), true) }
    finally { setBusy(false) }
  }
  async function toggleActive(teacher: Teacher) {
    try { await api(`/teachers/${teacher.id}/`, 'PATCH', { is_active: !teacher.is_active }); await refresh(); notify(t('saved')) }
    catch (error) { notify(readableError(error, t), true) }
  }
  return <><PageTitle eyebrow={t('schoolManagement')} title={t('teacherTitle')} description={t('teacherDesc')}/>
    <section className="panel form-panel"><h3>{editing ? t('editTeacher') : t('addTeacher')}</h3><form onSubmit={submit} className="form-grid"><label>{t('firstName')}<input required maxLength={80} value={form.first_name} onChange={event => setForm({ ...form, first_name: event.target.value })}/></label><label>{t('lastName')}<input maxLength={80} value={form.last_name} onChange={event => setForm({ ...form, last_name: event.target.value })}/></label><label>{t('accountUsername')}<input required minLength={3} autoComplete="off" value={form.username} onChange={event => setForm({ ...form, username: event.target.value })}/></label><label>{t('accountPassword')}<input type="password" autoComplete="new-password" required={!editing} value={form.password} onChange={event => setForm({ ...form, password: event.target.value })}/></label><label>{t('maxHours')}<input type="number" min={1} max={60} required value={form.max_weekly_hours} onChange={event => setForm({ ...form, max_weekly_hours: Number(event.target.value) })}/></label><div className="field full-width"><span className="field-label">{t('teachingSubjects')}</span><div className="chips">{subjects.filter(subject => subject.is_active).map(subject => <label className={`check-chip ${form.subject_ids.includes(subject.id) ? 'selected' : ''}`} key={subject.id}><input type="checkbox" checked={form.subject_ids.includes(subject.id)} onChange={() => toggleSubject(subject.id)}/>{subject.name}</label>)}</div></div><div className="form-actions full-width"><span className="form-hint">{t('accountHint')}</span>{editing && <button type="button" className="button ghost" onClick={clear}>{t('cancel')}</button>}<button className="button primary" disabled={busy}>{busy ? t('saving') : editing ? t('save') : t('addTeacher')}</button></div></form></section>
    <section className="panel table-panel"><div className="panel-header"><h3>{t('teacherDirectory')}</h3><span className="count-badge">{teachers.length}</span></div>{teachers.length ? <div className="table-scroll"><table><thead><tr><th>{t('teacher')}</th><th>{t('subjects')}</th><th>{t('capacity')}</th><th>{t('assigned')}</th><th>{t('remaining')}</th><th>{t('status')}</th><th>{t('actions')}</th></tr></thead><tbody>{teachers.map(teacher => <tr key={teacher.id}><td><div className="person"><span className="person-badge">{teacher.first_name.slice(0, 1)}</span><span>{teacher.first_name} {teacher.last_name}<small>@{teacher.account_username}</small></span></div></td><td>{teacher.subject_ids.map(id => subjects.find(subject => subject.id === id)?.name).filter(Boolean).join(', ')}</td><td>{teacher.max_weekly_hours}</td><td><strong>{teacher.assigned_hours}</strong></td><td>{teacher.remaining_hours}</td><td><span className={`status ${teacher.is_active ? 'on' : 'off'}`}>{t(teacher.is_active ? 'active' : 'inactive')}</span></td><td><div className="row-actions"><button className="icon-button" onClick={() => startEdit(teacher)} aria-label={t('edit')}>✎</button><button className="icon-button" onClick={() => toggleActive(teacher)} aria-label={t(teacher.is_active ? 'deactivate' : 'active')}>{teacher.is_active ? '⊘' : '✓'}</button></div></td></tr>)}</tbody></table></div> : <EmptyState title={t('noTeachers')}/>}</section>
  </>
}
