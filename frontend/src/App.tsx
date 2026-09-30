import { useCallback, useEffect, useRef, useState } from 'react'
import { api, auth, type AuthResult } from './api'
import { Layout, type Page } from './components/Layout'
import { readableError } from './errors'
import { LanguageProvider, useI18n } from './i18n'
import { AuthPage } from './pages/AuthPage'
import { AvailabilityPage } from './pages/AvailabilityPage'
import { CurriculumPage } from './pages/CurriculumPage'
import { DashboardPage } from './pages/DashboardPage'
import { GenerationPage } from './pages/GenerationPage'
import { MyTimetablePage } from './pages/MyTimetablePage'
import { TeachersPage } from './pages/TeachersPage'
import { TimetablePage } from './pages/TimetablePage'
import type { Generation, Lesson, Requirement, SchoolClass, SchoolSettings, Subject, Teacher, Timetable, Unavailable, User } from './types'

type DirectorData = { teachers: Teacher[]; subjects: Subject[]; classes: SchoolClass[]; requirements: Requirement[]; unavailable: Unavailable[]; settings: SchoolSettings; timetable: Timetable; generations: Generation[] }
type Mine = { teacher: { id: number; name: string; max_weekly_hours: number }; generation: Generation | null; assigned_hours: number; lessons: Lesson[] }
const initial: DirectorData = { teachers: [], subjects: [], classes: [], requirements: [], unavailable: [], settings: { days: [0,1,2,3,4,5], periods_per_day: 6, updated_at: '' }, timetable: { generation: null, lessons: [] }, generations: [] }

function Application() {
  const { t } = useI18n()
  const [user, setUser] = useState<User | null>(null)
  const [registration, setRegistration] = useState(false)
  const [booting, setBooting] = useState(true)
  const [page, setPage] = useState<Page>('overview')
  const [data, setData] = useState<DirectorData>(initial)
  const [mine, setMine] = useState<Mine | null>(null)
  const [teacherSettings, setTeacherSettings] = useState<SchoolSettings | null>(null)
  const [toast, setToast] = useState<{ message: string; error: boolean } | null>(null)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const notify = useCallback((message: string, error = false) => { setToast({ message, error }); if (timer.current) clearTimeout(timer.current); timer.current = setTimeout(() => setToast(null), 4200) }, [])
  useEffect(() => {
    let active = true
    async function initialize() {
      try {
        const bootstrap = await api<{ needs_registration: boolean }>('/auth/bootstrap/')
        if (!active) return
        setRegistration(bootstrap.needs_registration)
        if (auth.token()) {
          try { const current = await api<User>('/auth/me/'); if (active) { setUser(current); setPage(current.role === 'director' ? 'overview' : 'myTimetable') } }
          catch { auth.clear() }
        }
      } catch { if (active) notify(t('requestFailed'), true) }
      finally { if (active) setBooting(false) }
    }
    void initialize()
    return () => { active = false }
  }, [])
  const refresh = useCallback(async () => {
    if (!user) return
    if (user.role === 'teacher') {
      const [schedule, settings] = await Promise.all([api<Mine>('/my-timetable/'), api<SchoolSettings>('/settings/')])
      setMine(schedule); setTeacherSettings(settings)
      return
    }
    const [teachers, subjects, classes, requirements, unavailable, settings, timetable, generations] = await Promise.all([
      api<Teacher[]>('/teachers/'), api<Subject[]>('/subjects/'), api<SchoolClass[]>('/classes/'), api<Requirement[]>('/requirements/'),
      api<Unavailable[]>('/unavailable/'), api<SchoolSettings>('/settings/'), api<Timetable>('/timetable/'), api<Generation[]>('/generations/'),
    ])
    setData({ teachers, subjects, classes, requirements, unavailable, settings, timetable, generations })
  }, [user])
  useEffect(() => { if (user) void refresh().catch(error => notify(readableError(error, t), true)) }, [user, refresh])
  function onAuth(result: AuthResult) { auth.set(result.token); setUser(result.user); setRegistration(false); setPage(result.user.role === 'director' ? 'overview' : 'myTimetable') }
  async function logout() { try { await api('/auth/logout/', 'POST') } catch { /* Local token is still cleared. */ } auth.clear(); setUser(null); setMine(null); setData(initial) }
  if (booting) return <div className="boot-screen"><span className="brand-mark">◈</span><span>{t('loading')}</span></div>
  if (!user) return <AuthPage registration={registration} onAuth={onAuth}/>
  return <Layout user={user} page={page} onPage={setPage} onLogout={logout}>
    {user.role === 'director' ? <>
      {page === 'overview' && <DashboardPage teachers={data.teachers} classes={data.classes} requirements={data.requirements} timetable={data.timetable} onPage={setPage}/>}
      {page === 'teachers' && <TeachersPage teachers={data.teachers} subjects={data.subjects} refresh={refresh} notify={notify}/>}
      {page === 'curriculum' && <CurriculumPage subjects={data.subjects} classes={data.classes} requirements={data.requirements} refresh={refresh} notify={notify}/>}
      {page === 'availability' && <AvailabilityPage settings={data.settings} teachers={data.teachers} unavailable={data.unavailable} refresh={refresh} notify={notify}/>}
      {page === 'generate' && <GenerationPage generations={data.generations} timetable={data.timetable} refresh={refresh} notify={notify}/>}
      {page === 'timetable' && <TimetablePage timetable={data.timetable} settings={data.settings} teachers={data.teachers} classes={data.classes} subjects={data.subjects}/>}
    </> : <MyTimetablePage mine={mine} settings={teacherSettings}/>}
    {toast && <div className={`toast ${toast.error ? 'error' : ''}`} role={toast.error ? 'alert' : 'status'}>{toast.message}</div>}
  </Layout>
}

export default function App() { return <LanguageProvider><Application/></LanguageProvider> }
