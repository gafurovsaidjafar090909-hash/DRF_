import { useState, type FormEvent } from 'react'
import { api } from '../api'
import { EmptyState, PageTitle } from '../components/Layout'
import { readableError } from '../errors'
import { useI18n } from '../i18n'
import type { Requirement, SchoolClass, Subject } from '../types'

export function CurriculumPage({ subjects, classes, requirements, refresh, notify }: { subjects: Subject[]; classes: SchoolClass[]; requirements: Requirement[]; refresh: () => Promise<void>; notify: (message: string, error?: boolean) => void }) {
  const { t } = useI18n()
  const [subjectName, setSubjectName] = useState('')
  const [subjectEdit, setSubjectEdit] = useState<number | null>(null)
  const [grade, setGrade] = useState(5)
  const [section, setSection] = useState('A')
  const [classEdit, setClassEdit] = useState<number | null>(null)
  const [requirementClass, setRequirementClass] = useState<number | ''>('')
  const [requirementSubject, setRequirementSubject] = useState<number | ''>('')
  const [hours, setHours] = useState(3)
  const [requirementEdit, setRequirementEdit] = useState<number | null>(null)
  async function submitSubject(event: FormEvent) {
    event.preventDefault()
    try { await api(subjectEdit ? `/subjects/${subjectEdit}/` : '/subjects/', subjectEdit ? 'PATCH' : 'POST', { name: subjectName, is_active: true }); setSubjectName(''); setSubjectEdit(null); await refresh(); notify(t('saved')) }
    catch (error) { notify(readableError(error, t), true) }
  }
  async function submitClass(event: FormEvent) {
    event.preventDefault()
    try { await api(classEdit ? `/classes/${classEdit}/` : '/classes/', classEdit ? 'PATCH' : 'POST', { grade, section: section.trim().toUpperCase(), is_active: true }); setGrade(5); setSection('A'); setClassEdit(null); await refresh(); notify(t('saved')) }
    catch (error) { notify(readableError(error, t), true) }
  }
  async function submitRequirement(event: FormEvent) {
    event.preventDefault()
    if (!requirementClass || !requirementSubject) { notify(t('required'), true); return }
    try { await api(requirementEdit ? `/requirements/${requirementEdit}/` : '/requirements/', requirementEdit ? 'PATCH' : 'POST', { school_class: requirementClass, subject: requirementSubject, hours }); setRequirementClass(''); setRequirementSubject(''); setHours(3); setRequirementEdit(null); await refresh(); notify(t('saved')) }
    catch (error) { notify(readableError(error, t), true) }
  }
  async function toggle(path: string, active: boolean) {
    try { await api(path, 'PATCH', { is_active: !active }); await refresh(); notify(t('saved')) }
    catch (error) { notify(readableError(error, t), true) }
  }
  async function removeRequirement(id: number) {
    try { await api(`/requirements/${id}/`, 'DELETE'); await refresh(); notify(t('deleted')) }
    catch (error) { notify(readableError(error, t), true) }
  }
  return <><PageTitle eyebrow={t('schoolManagement')} title={t('curriculumTitle')} description={t('curriculumDesc')}/>
    <div className="two-col"><section className="panel"><h3>{t('subjects')}</h3><form onSubmit={submitSubject} className="compact-form"><label>{t('subjectName')}<input required maxLength={100} value={subjectName} onChange={event => setSubjectName(event.target.value)}/></label><button className="button primary">{subjectEdit ? t('save') : t('addSubject')}</button>{subjectEdit && <button type="button" className="button ghost" onClick={() => { setSubjectEdit(null); setSubjectName('') }}>{t('cancel')}</button>}</form>{subjects.length ? <div className="simple-list">{subjects.map(subject => <div className="simple-row" key={subject.id}><span className={subject.is_active ? '' : 'faded'}>{subject.name}</span><div className="row-actions"><span className={`status ${subject.is_active ? 'on' : 'off'}`}>{t(subject.is_active ? 'active' : 'inactive')}</span><button className="icon-button" onClick={() => { setSubjectEdit(subject.id); setSubjectName(subject.name) }} aria-label={t('edit')}>✎</button><button className="icon-button" onClick={() => toggle(`/subjects/${subject.id}/`, subject.is_active)} aria-label={t('deactivate')}>{subject.is_active ? '⊘' : '✓'}</button></div></div>)}</div> : <EmptyState title={t('noSubjects')}/>}</section>
    <section className="panel"><h3>{t('classes')}</h3><form onSubmit={submitClass} className="compact-form"><label>{t('grade')}<select value={grade} onChange={event => setGrade(Number(event.target.value))}>{Array.from({ length: 7 }, (_, index) => index + 5).map(value => <option key={value} value={value}>{value}</option>)}</select></label><label>{t('section')}<input required maxLength={5} value={section} onChange={event => setSection(event.target.value)}/></label><button className="button primary">{classEdit ? t('save') : t('addClass')}</button>{classEdit && <button type="button" className="button ghost" onClick={() => { setClassEdit(null); setGrade(5); setSection('A') }}>{t('cancel')}</button>}</form>{classes.length ? <div className="simple-list">{classes.map(schoolClass => <div className="simple-row" key={schoolClass.id}><span className={schoolClass.is_active ? '' : 'faded'}>{schoolClass.label}</span><div className="row-actions"><span className={`status ${schoolClass.is_active ? 'on' : 'off'}`}>{t(schoolClass.is_active ? 'active' : 'inactive')}</span><button className="icon-button" onClick={() => { setClassEdit(schoolClass.id); setGrade(schoolClass.grade); setSection(schoolClass.section) }} aria-label={t('edit')}>✎</button><button className="icon-button" onClick={() => toggle(`/classes/${schoolClass.id}/`, schoolClass.is_active)} aria-label={t('deactivate')}>{schoolClass.is_active ? '⊘' : '✓'}</button></div></div>)}</div> : <EmptyState title={t('noClasses')}/>}</section></div>
    <section className="panel form-panel"><h3>{t('requirements')}</h3><form onSubmit={submitRequirement} className="inline-form"><label>{t('class')}<select required value={requirementClass} onChange={event => setRequirementClass(Number(event.target.value))}><option value="">{t('select')}</option>{classes.filter(item => item.is_active).map(item => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label><label>{t('subject')}<select required value={requirementSubject} onChange={event => setRequirementSubject(Number(event.target.value))}><option value="">{t('select')}</option>{subjects.filter(item => item.is_active).map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label>{t('requiredHours')}<input type="number" min={1} max={60} value={hours} onChange={event => setHours(Number(event.target.value))}/></label><button className="button primary">{requirementEdit ? t('save') : t('addRequirement')}</button>{requirementEdit && <button type="button" className="button ghost" onClick={() => { setRequirementEdit(null); setRequirementClass(''); setRequirementSubject(''); setHours(3) }}>{t('cancel')}</button>}</form></section>
    <section className="panel table-panel"><div className="panel-header"><h3>{t('requirements')}</h3><span className="count-badge">{requirements.reduce((sum, item) => sum + item.hours, 0)} {t('hours')}</span></div>{requirements.length ? <div className="table-scroll"><table><thead><tr><th>{t('class')}</th><th>{t('subject')}</th><th>{t('requiredHours')}</th><th>{t('actions')}</th></tr></thead><tbody>{requirements.map(item => <tr key={item.id}><td>{item.class_label}</td><td>{item.subject_name}</td><td><strong>{item.hours}</strong></td><td><div className="row-actions"><button className="icon-button" onClick={() => { setRequirementEdit(item.id); setRequirementClass(item.school_class); setRequirementSubject(item.subject); setHours(item.hours) }} aria-label={t('edit')}>✎</button><button className="icon-button" onClick={() => removeRequirement(item.id)} aria-label={t('remove')}>×</button></div></td></tr>)}</tbody></table></div> : <EmptyState title={t('noRequirements')}/>}</section>
  </>
}
