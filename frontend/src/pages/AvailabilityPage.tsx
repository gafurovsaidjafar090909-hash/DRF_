import { useEffect, useState, type FormEvent } from 'react'
import { api } from '../api'
import { PageTitle } from '../components/Layout'
import { readableError } from '../errors'
import { dayKeys, useI18n } from '../i18n'
import type { SchoolSettings, Teacher, Unavailable } from '../types'

export function AvailabilityPage({ settings, teachers, unavailable, refresh, notify }: { settings: SchoolSettings; teachers: Teacher[]; unavailable: Unavailable[]; refresh: () => Promise<void>; notify: (message: string, error?: boolean) => void }) {
  const { t } = useI18n()
  const [days, setDays] = useState(settings.days)
  const [periods, setPeriods] = useState(settings.periods_per_day)
  const [teacherId, setTeacherId] = useState<number | ''>('')
  const [busy, setBusy] = useState(false)
  useEffect(() => { setDays(settings.days); setPeriods(settings.periods_per_day) }, [settings])
  useEffect(() => { if (!teacherId && teachers.length) setTeacherId(teachers[0].id) }, [teachers, teacherId])
  const slots = unavailable.filter(row => row.teacher === teacherId)
  const hasSlot = (day: number, period: number) => slots.some(row => row.day === day && row.period === period)
  async function saveSettings(event: FormEvent) {
    event.preventDefault()
    if (!days.length) { notify(t('diag_invalid_days'), true); return }
    setBusy(true)
    try { await api('/settings/', 'PUT', { days, periods_per_day: periods }); await refresh(); notify(t('saved')) }
    catch (error) { notify(readableError(error, t), true) }
    finally { setBusy(false) }
  }
  async function replace(next: { day: number; period: number }[]) {
    if (!teacherId || busy) return
    setBusy(true)
    try { await api(`/availability/teachers/${teacherId}/`, 'PUT', { slots: next }); await refresh(); notify(t('saved')) }
    catch (error) { notify(readableError(error, t), true) }
    finally { setBusy(false) }
  }
  function toggle(day: number, period: number) {
    const current = slots.map(row => ({ day: row.day, period: row.period }))
    void replace(hasSlot(day, period) ? current.filter(row => row.day !== day || row.period !== period) : [...current, { day, period }])
  }
  function toggleDay(day: number) {
    const current = slots.map(row => ({ day: row.day, period: row.period }))
    const allBlocked = Array.from({ length: settings.periods_per_day }, (_, index) => hasSlot(day, index + 1)).every(Boolean)
    const next = current.filter(row => row.day !== day)
    if (!allBlocked) for (let period = 1; period <= settings.periods_per_day; period++) next.push({ day, period })
    void replace(next)
  }
  return <><PageTitle eyebrow={t('schoolManagement')} title={t('availabilityTitle')} description={t('availabilityDesc')}/>
    <section className="panel form-panel"><h3>{t('settings')}</h3><form onSubmit={saveSettings}><div className="field-label">{t('schoolDays')}</div><div className="chips day-chips">{dayKeys.map((key, day) => <label className={`check-chip ${days.includes(day) ? 'selected' : ''}`} key={key}><input type="checkbox" checked={days.includes(day)} onChange={() => setDays(current => current.includes(day) ? current.filter(value => value !== day) : [...current, day].sort())}/>{t(key)}</label>)}</div><div className="settings-row"><label>{t('periods')}<input type="number" min={1} max={10} value={periods} onChange={event => setPeriods(Number(event.target.value))}/></label><span className="subtle">{days.length * periods} {t('weeklySlots')}</span><button className="button primary" disabled={busy}>{t('save')}</button></div></form></section>
    <section className="panel"><div className="panel-header"><div><h3>{t('teacher')} · {t('availability')}</h3><p>{t('availabilityHint')}</p></div><label className="picker">{t('chooseTeacher')}<select value={teacherId} onChange={event => setTeacherId(Number(event.target.value))}>{teachers.filter(row => row.is_active).map(row => <option key={row.id} value={row.id}>{row.first_name} {row.last_name}</option>)}</select></label></div>{teacherId ? <div className="availability-scroll"><div className="availability-grid" style={{ gridTemplateColumns: `78px repeat(${settings.days.length}, minmax(115px,1fr))` }}><div className="grid-corner">{t('period')}</div>{settings.days.map(day => <button className="grid-day day-toggle" onClick={() => toggleDay(day)} key={day} disabled={busy} title={t('unavailable')}>{t(dayKeys[day])} <span>↕</span></button>)}{Array.from({ length: settings.periods_per_day }, (_, index) => index + 1).flatMap(period => [<div className="grid-period" key={`p${period}`}>{period}</div>, ...settings.days.map(day => <button type="button" className={`availability-cell ${hasSlot(day, period) ? 'blocked' : ''}`} aria-pressed={hasSlot(day, period)} aria-label={`${t(dayKeys[day])} ${period}: ${t(hasSlot(day, period) ? 'unavailable' : 'available')}`} onClick={() => toggle(day, period)} disabled={busy} key={`${day}-${period}`}>{hasSlot(day, period) ? '×' : '✓'}<small>{t(hasSlot(day, period) ? 'unavailable' : 'available')}</small></button>)])}</div></div> : <p className="muted-copy">{t('noTeachers')}</p>}</section>
  </>
}
