import { dayKeys, useI18n } from '../i18n'
import type { Lesson, SchoolSettings } from '../types'
import { EmptyState } from './Layout'

export function ScheduleGrid({ lessons, settings, personal = false }: { lessons: Lesson[]; settings: SchoolSettings; personal?: boolean }) {
  const { t } = useI18n()
  if (!lessons.length) return <EmptyState title={t('noMatches')} />
  return <div className="schedule-scroll"><div className="schedule-grid" style={{ gridTemplateColumns: `66px repeat(${settings.days.length}, minmax(180px, 1fr))` }}>
    <div className="grid-corner">{t('period')}</div>
    {settings.days.map(day => <div className="grid-day" key={day}>{t(dayKeys[day])}</div>)}
    {Array.from({ length: settings.periods_per_day }, (_, index) => index + 1).flatMap(period => [
      <div className="grid-period" key={`period-${period}`}>{period}</div>,
      ...settings.days.map(day => <div className="grid-cell" key={`${day}-${period}`}>
        {lessons.filter(item => item.day === day && item.period === period).map(item => <div className="lesson-card" key={item.id}>
          <strong>{item.subject_name}</strong><span>{item.class_label}</span>{!personal && <small>{item.teacher_name}</small>}
        </div>)}
      </div>),
    ])}
  </div></div>
}
