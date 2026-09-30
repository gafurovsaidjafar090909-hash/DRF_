import { useState, type FormEvent } from 'react'
import { api, type AuthResult } from '../api'
import { readableError } from '../errors'
import { useI18n, type Language } from '../i18n'

export function AuthPage({ registration, onAuth }: { registration: boolean; onAuth: (result: AuthResult) => void }) {
  const { t, language, setLanguage } = useI18n()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  async function submit(event: FormEvent) {
    event.preventDefault(); setError('')
    if (registration && password !== confirm) { setError(t('passwordsMismatch')); return }
    setBusy(true)
    try { onAuth(await api<AuthResult>(registration ? '/auth/register/' : '/auth/login/', 'POST', { username, password })) }
    catch (reason) { setError(readableError(reason, t)) }
    finally { setBusy(false) }
  }
  return <div className="auth-shell"><div className="auth-glow"/><div className="auth-card"><div className="auth-top"><div className="brand"><span className="brand-mark">◈</span><span>ORBIT<small>{t('educationSystem')}</small></span></div><select aria-label={t('language')} value={language} onChange={event => setLanguage(event.target.value as Language)}><option value="tg">Тоҷикӣ</option><option value="ru">Русский</option><option value="en">English</option></select></div><div className="auth-orb" aria-hidden="true">✦</div><div className="eyebrow">{t('heroEyebrow')}</div><h1>{registration ? t('createAccount') : t('welcome')}</h1><p>{registration ? t('register') : t('login')}</p><form onSubmit={submit} className="auth-form"><label>{t('username')}<input autoComplete="username" required minLength={3} value={username} onChange={event => setUsername(event.target.value)}/></label><label>{t('password')}<input type="password" autoComplete={registration ? 'new-password' : 'current-password'} required minLength={registration ? 10 : 1} value={password} onChange={event => setPassword(event.target.value)}/></label>{registration && <label>{t('confirmPassword')}<input type="password" autoComplete="new-password" required value={confirm} onChange={event => setConfirm(event.target.value)}/><small>{t('passwordHint')}</small></label>}{error && <div className="alert error" role="alert">{error}</div>}<button className="button primary full" disabled={busy}>{busy ? t('loading') : registration ? t('register') : t('login')}</button></form></div></div>
}
