"""Quick smoke test for all pages."""
import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar

BASE = 'http://127.0.0.1:8000'

# Setup cookie jar
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

def get(url):
    try:
        r = opener.open(BASE + url)
        return r.status, r.url
    except urllib.error.HTTPError as e:
        return e.code, BASE + url

def post(url, data):
    try:
        body = urllib.parse.urlencode(data).encode()
        req = urllib.request.Request(BASE + url, data=body, method='POST')
        # Get CSRF token from cookie
        csrf = None
        for c in cj:
            if c.name == 'csrftoken':
                csrf = c.value
        if csrf:
            req.add_header('X-CSRFToken', csrf)
            req.add_header('Referer', BASE + url)
        r = opener.open(req)
        return r.status, r.url
    except urllib.error.HTTPError as e:
        return e.code, e.url if hasattr(e, 'url') else BASE + url

# 1. Get login page (to get CSRF token)
s, u = get('/login/')
print(f'GET /login/         -> {s} {u}')

# 2. Post login credentials
s, u = post('/login/', {'email': 'aryaa@gmail.com', 'password': 'pass@123'})
print(f'POST /login/        -> {s} {u}')

# 3. Check dashboard
s, u = get('/dashboard/')
print(f'GET /dashboard/     -> {s} {u}')

# 4. Employees
s, u = get('/employees/')
print(f'GET /employees/     -> {s} {u}')

# 5. Employee detail
s, u = get('/employees/1/')
print(f'GET /employees/1/   -> {s} {u}')

# 6. Projects
s, u = get('/projects/')
print(f'GET /projects/      -> {s} {u}')

# 7. Project detail
s, u = get('/projects/123/')
print(f'GET /projects/123/  -> {s} {u}')

# 8. Skills
s, u = get('/skills/')
print(f'GET /skills/        -> {s} {u}')

print('\nAll tests complete!')
