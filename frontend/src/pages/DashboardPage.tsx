import { useI18n } from '../i18n'
import type { Generation, Requirement, SchoolClass, Teacher, Timetable } from '../types'
import type { Page } from '../components/Layout'
import { PageTitle } from '../components/Layout'

export function DashboardPage({ teachers, classes, requirements, timetable, onPage }: { teachers: Teacher[]; classes: SchoolClass[]; requirements: Requirement[]; timetable: Timetable; onPage: (page: Page) => void }) {
  const { t } = useI18n()
  const needed = requirements.reduce((sum, item) => sum + item.hours, 0)
  const active: Generation | null = timetable.generation
  const steps: [string, boolean, Page][] = [
    ['stepSubjects', classes.some(item => item.is_active), 'curriculum'],
    ['stepTeachers', teachers.some(item => item.is_active), 'teachers'],
    ['stepRequirements', needed > 0, 'curriculum'],
    ['stepGenerate', !!active, 'generate'],
  ]
  return <><div className="hero"><div className="hero-copy"><div className="eyebrow"><span className="pulse"/>{t('heroEyebrow')}</div><h1>{t('heroTitle')}</h1><p>{t('heroText')}</p><button className="button primary" onClick={() => onPage('generate')}>✦ {t('heroAction')}</button></div><div className="hero-art" aria-hidden="true"><div className="orbit orbit-a"/><div className="orbit orbit-b"/><div className="orb">✦</div></div></div>
    <PageTitle eyebrow={t('atGlance')} title={t('dashboardTitle')} description={t('dashboardDesc')}/>
    <div className="stats"><div className="stat-card"><div className="stat-icon violet">♧</div><span>{t('registeredTeachers')}</span><strong>{teachers.filter(item => item.is_active).length}</strong></div><div className="stat-card"><div className="stat-icon cyan">▤</div><span>{t('activeClasses')}</span><strong>{classes.filter(item => item.is_active).length}</strong></div><div className="stat-card"><div className="stat-icon pink">◷</div><span>{t('requiredLessons')}</span><strong>{needed}</strong></div><div className="stat-card"><div className="stat-icon green">✓</div><span>{t('placedLessons')}</span><strong>{timetable.lessons.length}</strong></div></div>
    <div className="overview-grid"><section className="panel"><h3>{t('setup')}</h3><div className="steps">{steps.map(([label, done, destination], index) => <div className={`step ${done ? 'done' : ''}`} key={label}><div className="step-mark">{done ? '✓' : index + 1}</div><span>{t(label)}</span><button onClick={() => onPage(destination)}>{done ? t('ready') : t('open')} →</button></div>)}</div></section><section className="panel"><h3>{t('currentTimetable')}</h3>{active ? <><p className="muted-copy">{t('version')} #{active.id} · {new Date(active.created_at).toLocaleString()}</p><div className="metric-big">{active.lesson_count}<small>{t('lessons')}</small></div><button className="button ghost" onClick={() => onPage('timetable')}>{t('open')} →</button></> : <><p className="muted-copy">{t('noTimetableHint')}</p><div className="empty-mini">{t('noTimetable')}</div></>}</section></div>
  </>
}
