import { useState } from 'react'
import { EmptyState, PageTitle } from '../components/Layout'
import { ScheduleGrid } from '../components/ScheduleGrid'
import { dayKeys, useI18n } from '../i18n'
import type { SchoolClass, SchoolSettings, Subject, Teacher, Timetable } from '../types'

export function TimetablePage({ timetable, settings, teachers, classes, subjects }: { timetable: Timetable; settings: SchoolSettings; teachers: Teacher[]; classes: SchoolClass[]; subjects: Subject[] }) {
  const { t } = useI18n()
  const [teacher, setTeacher] = useState('')
  const [schoolClass, setSchoolClass] = useState('')
  const [subject, setSubject] = useState('')
  const [day, setDay] = useState('')
  const filtered = timetable.lessons.filter(item => (!teacher || item.teacher === Number(teacher)) && (!schoolClass || item.school_class === Number(schoolClass)) && (!subject || item.subject === Number(subject)) && (!day || item.day === Number(day)))
  const visibleSettings = day ? { ...settings, days: [Number(day)] } : settings
  return <><PageTitle eyebrow={t('schoolWeek')} title={t('timetableTitle')} description={t('timetableDesc')} action={timetable.generation && <span className="version-pill">{t('version')} #{timetable.generation.id}</span>}/>
    {!timetable.generation ? <EmptyState title={t('noTimetable')} description={t('noTimetableHint')}/> : <><section className="panel filters"><label>{t('teacher')}<select value={teacher} onChange={event => setTeacher(event.target.value)}><option value="">{t('all')}</option>{teachers.map(item => <option value={item.id} key={item.id}>{item.first_name} {item.last_name}</option>)}</select></label><label>{t('class')}<select value={schoolClass} onChange={event => setSchoolClass(event.target.value)}><option value="">{t('all')}</option>{classes.map(item => <option value={item.id} key={item.id}>{item.label}</option>)}</select></label><label>{t('subject')}<select value={subject} onChange={event => setSubject(event.target.value)}><option value="">{t('all')}</option>{subjects.map(item => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label><label>{t('day')}<select value={day} onChange={event => setDay(event.target.value)}><option value="">{t('all')}</option>{settings.days.map(value => <option value={value} key={value}>{t(dayKeys[value])}</option>)}</select></label><button className="button ghost" onClick={() => { setTeacher(''); setSchoolClass(''); setSubject(''); setDay('') }}>{t('clearFilters')}</button></section><div className="result-count">{t('visibleLessons')}: <strong>{filtered.length}</strong></div><ScheduleGrid lessons={filtered} settings={visibleSettings}/></>}
  </>
}
