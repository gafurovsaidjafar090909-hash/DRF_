import type { ReactNode } from 'react'
import { useI18n, type Language } from '../i18n'
import type { User } from '../types'

export type Page = 'overview' | 'teachers' | 'curriculum' | 'availability' | 'generate' | 'timetable' | 'myTimetable'

export function Layout({ user, page, onPage, onLogout, children }: { user: User; page: Page; onPage: (page: Page) => void; onLogout: () => void; children: ReactNode }) {
  const { language, setLanguage, t } = useI18n()
  const directorPages: { id: Page; icon: string; label: string }[] = [
    { id: 'overview', icon: '▦', label: 'overview' }, { id: 'teachers', icon: '♧', label: 'teachers' },
    { id: 'curriculum', icon: '▤', label: 'curriculum' }, { id: 'availability', icon: '◷', label: 'availability' },
    { id: 'generate', icon: '✦', label: 'generate' }, { id: 'timetable', icon: '▦', label: 'timetable' },
  ]
  const pages = user.role === 'director' ? directorPages : [{ id: 'myTimetable' as Page, icon: '▦', label: 'myTimetable' }]
  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><span className="brand-mark">◈</span><span>ORBIT<small>{t('educationSystem')}</small></span></div>
      <span className="workspace-label">{t('schoolManagement')}</span>
      <nav className="nav" aria-label={t('schoolManagement')}>{pages.map(item => <button key={item.id} type="button" onClick={() => onPage(item.id)} className={`nav-item ${page === item.id ? 'active' : ''}`}><span className="nav-icon" aria-hidden="true">{item.icon}</span>{t(item.label)}</button>)}</nav>
      <div className="sidebar-bottom"><span className="system-dot"/><span>{user.role === 'director' ? t('director') : t('teacher')}</span><strong>{user.username}</strong></div>
    </aside>
    <main className="main">
      <header className="topbar"><div className="breadcrumb"><span>{t('schoolManagement')}</span><span className="slash">/</span><strong>{t(page)}</strong></div><div className="top-actions"><select aria-label={t('language')} value={language} onChange={event => setLanguage(event.target.value as Language)}><option value="tg">Тоҷикӣ</option><option value="ru">Русский</option><option value="en">English</option></select><button className="text-button" onClick={onLogout}>{t('logout')}</button><div className="avatar" aria-hidden="true">{user.username.slice(0, 1).toUpperCase()}</div></div></header>
      <div className="content">{children}</div>
    </main>
  </div>
}

export function PageTitle({ eyebrow, title, description, action }: { eyebrow?: string; title: string; description?: string; action?: ReactNode }) {
  return <div className="page-title"><div>{eyebrow && <div className="eyebrow muted">{eyebrow}</div>}<h1>{title}</h1>{description && <p>{description}</p>}</div>{action}</div>
}

export function EmptyState({ title, description, action }: { title: string; description?: string; action?: ReactNode }) {
  return <div className="empty-state"><div className="empty-icon">✧</div><h3>{title}</h3>{description && <p>{description}</p>}{action}</div>
}
