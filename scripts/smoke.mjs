import { readFileSync } from 'node:fs'

const env = Object.fromEntries(readFileSync(new URL('../.env', import.meta.url), 'utf8').split(/\r?\n/).filter(line => line && !line.startsWith('#')).map(line => { const index = line.indexOf('='); return [line.slice(0, index), line.slice(index + 1)] }))
const backend = 'http://127.0.0.1:8000'
const frontend = 'http://127.0.0.1:5173'

async function call(path, token, method = 'GET', data) {
  const response = await fetch(`${backend}/api${path}`, { method, headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Token ${token}` } : {}) }, body: data ? JSON.stringify(data) : undefined })
  const raw = await response.text()
  let body
  try { body = JSON.parse(raw) } catch { throw new Error(`${path} returned ${response.status} ${response.headers.get('content-type')}: ${raw.slice(0, 120)}`) }
  return { status: response.status, body }
}
function expect(condition, message) { if (!condition) throw new Error(message) }

const page = await fetch(frontend)
expect(page.ok && (await page.text()).includes('root'), 'Frontend did not load')
const director = await call('/auth/login/', null, 'POST', { username: 'director', password: env.DEMO_DIRECTOR_PASSWORD })
expect(director.status === 200, 'Director login failed')
const directorToken = director.body.token
const [teachers, classes, requirements, timetable] = await Promise.all([
  call('/teachers/', directorToken), call('/classes/', directorToken), call('/requirements/', directorToken), call('/timetable/', directorToken),
])
expect(teachers.status === 200 && teachers.body.length === 5, 'Teacher API failed')
expect(classes.status === 200 && classes.body.length >= 7, 'Class API failed')
expect(requirements.status === 200 && requirements.body.length >= 21, 'Requirements API failed')
expect(timetable.status === 200 && timetable.body.lessons.length === 72, 'Active timetable incomplete')
const teacher = await call('/auth/login/', null, 'POST', { username: 'ali', password: env.DEMO_TEACHER_PASSWORD })
expect(teacher.status === 200, 'Teacher login failed')
const teacherToken = teacher.body.token
const own = await call('/my-timetable/', teacherToken)
expect(own.status === 200 && own.body.assigned_hours <= 18, 'Personal timetable failed')
const forbidden = await call('/timetable/', teacherToken)
expect(forbidden.status === 403, 'Teacher could access director timetable')
console.log('Smoke passed: frontend, director login, 72 active lessons, teacher timetable and API permissions.')
