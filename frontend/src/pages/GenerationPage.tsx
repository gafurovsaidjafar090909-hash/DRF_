import { useState } from 'react'
import { api } from '../api'
import { EmptyState, PageTitle } from '../components/Layout'
import { readableError } from '../errors'
import { diagnosticText, useI18n } from '../i18n'
import type { Generation, Timetable } from '../types'

export function GenerationPage({ generations, timetable, refresh, notify }: { generations: Generation[]; timetable: Timetable; refresh: () => Promise<void>; notify: (message: string, error?: boolean) => void }) {
  const { t } = useI18n()
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState<Generation | null>(null)
  async function run() {
    setRunning(true); setResult(null)
    try {
      const latest = await api<Generation>('/generations/', 'POST')
      setResult(latest); await refresh()
      notify(t(latest.status === 'completed' ? 'generationReady' : 'generationFailed'), latest.status !== 'completed')
    } catch (error) { notify(readableError(error, t), true) }
    finally { setRunning(false) }
  }
  const shown = result || generations[0] || null
  const statusLabel = (status: Generation['status']) => t(status === 'completed' ? 'completed' : status === 'infeasible' ? 'infeasible' : status === 'timeout' ? 'timeout' : status === 'error' ? 'solverError' : 'pending')
  return <><PageTitle eyebrow={t('heroEyebrow')} title={t('generationTitle')} description={t('generationDesc')}/>
    <div className="generation-hero"><div className="generation-symbol" aria-hidden="true">✦</div><div><h2>{running ? t('generating') : t('generationAction')}</h2><p>{t('generationDesc')}</p></div><button className="button primary" onClick={run} disabled={running}>{running ? <span className="spinner"/> : '✦'} {running ? t('generating') : t('generationAction')}</button></div>
    {shown && <section className={`panel generation-result ${shown.status}`} aria-live="polite"><div className="panel-header"><div><div className="eyebrow muted">{t('solverStatus')}</div><h3>{statusLabel(shown.status)}</h3></div><span className="count-badge">#{shown.id} · {shown.solver_status || shown.status}</span></div>{shown.status === 'completed' ? <p className="success-copy">{t('generationReady')} · {shown.lesson_count} {t('lessons')}</p> : <><p className="error-copy">{t('generationFailed')}</p><ul className="diagnostics">{shown.diagnostics.map((item, index) => <li key={index}>{diagnosticText(item, t)}</li>)}</ul>{timetable.generation && <p className="muted-copy">{t('previousPreserved')}</p>}</>}<small className="subtle">{t('generatedAt')}: {new Date(shown.created_at).toLocaleString()} · {shown.duration_seconds.toFixed(2)} s</small></section>}
    <section className="panel"><div className="panel-header"><h3>{t('generationHistory')}</h3><span className="count-badge">{generations.length}</span></div>{generations.length ? <div className="history-list">{generations.map(item => <div className="history-row" key={item.id}><span className={`history-dot ${item.status}`}/><strong>#{item.id}</strong><span>{statusLabel(item.status)}</span><small>{item.lesson_count} {t('lessons')}</small><time>{new Date(item.created_at).toLocaleString()}</time>{item.is_active && <span className="status on">{t('active')}</span>}</div>)}</div> : <EmptyState title={t('noHistory')}/>}</section>
  </>
}
