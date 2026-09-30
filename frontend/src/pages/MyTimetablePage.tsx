import { EmptyState, PageTitle } from '../components/Layout'
import { ScheduleGrid } from '../components/ScheduleGrid'
import { useI18n } from '../i18n'
import type { Generation, Lesson, SchoolSettings } from '../types'

type Mine = { teacher: { id: number; name: string; max_weekly_hours: number }; generation: Generation | null; assigned_hours: number; lessons: Lesson[] }
export function MyTimetablePage({ mine, settings }: { mine: Mine | null; settings: SchoolSettings | null }) {
  const { t } = useI18n()
  return <><PageTitle eyebrow={t('teacher')} title={t('teacherTimetableTitle')} description={t('teacherTimetableDesc')}/>{!mine || !settings ? <EmptyState title={t('loading')}/> : <><div className="stats personal-stats"><div className="stat-card"><span>{t('teacher')}</span><strong className="text-stat">{mine.teacher.name}</strong></div><div className="stat-card"><span>{t('assignedHours')}</span><strong>{mine.assigned_hours}</strong></div><div className="stat-card"><span>{t('capacity')}</span><strong>{mine.teacher.max_weekly_hours}</strong></div><div className="stat-card"><span>{t('remaining')}</span><strong>{mine.teacher.max_weekly_hours - mine.assigned_hours}</strong></div></div>{mine.generation ? <ScheduleGrid lessons={mine.lessons} settings={settings} personal/> : <EmptyState title={t('noTimetable')} description={t('noTimetableHint')}/>}<div className="personal-total">{t('weekTotal')}: <strong>{mine.assigned_hours} {t('hoursPerWeek')}</strong></div></>}</>
}
