import { ApiError } from './api'

export function readableError(error: unknown, t: (key: string) => string): string {
  if (!(error instanceof ApiError)) return t('requestFailed')
  if (error.status === 401 || error.status === 403) return t('forbidden')
  const codes: Record<string, string> = {
    login_failed: 'credentialsInvalid', registration_closed: 'registrationClosed',
    invalid_credentials: 'invalidCredentials', username_used: 'unique',
  }
  if (codes[error.code]) return t(codes[error.code])
  const fieldNames: Record<string, string> = { first_name: 'firstName', last_name: 'lastName', subject_ids: 'teachingSubjects', max_weekly_hours: 'maxHours', account_username: 'accountUsername', school_class: 'class', periods_per_day: 'periods', is_active: 'active', non_field_errors: 'duplicateRequirement', name: 'subjectName', hours: 'requiredHours' }
  const codeNames: Record<string, string> = { required: 'required', blank: 'required', null: 'required', unique: 'unique', unique_together: 'duplicateRequirement', max_value: 'maxValue', min_value: 'minValue', invalid: 'invalid', does_not_exist: 'invalid', max_length: 'invalid', min_length: 'invalid' }
  const fields = error.details.fields
  if (fields && typeof fields === 'object' && !Array.isArray(fields)) return Object.entries(fields as Record<string, unknown>).map(([name, codes]) => {
    const first = Array.isArray(codes) ? codes[0] : codes
    const key = typeof first === 'string' ? first : 'invalid'
    return `${t(fieldNames[name] || name)}: ${t(codeNames[key] || 'invalid')}`
  }).join(' · ')
  return t('requestFailed')
}
