# Session Reference: Guest Login + Parameter Mismatch Fix

## Guest Login Full-Stack Implementation

**Files modified (10 total):**

| Layer | File | Change |
|-------|------|--------|
| Backend | `api/v1/auth.py` | Added `POST /api/auth/guest-login` endpoint |
| Backend | `api/v1/prescriptions.py` | Added `_check_guest_role()` + guest filter (`status=未取`) |
| Backend | `api/v1/followups.py` | Added `_check_guest_role()` + 403 for `/reminders` and `/reminders/update-status` |
| Backend | `api/v1/follow_up_management.py` | Added guest 403 for `/follow-up` and `/follow-up/update` |
| Frontend | `store.js` | Added `isGuest()` and `hasRole()` methods |
| Frontend | `api.js` | Added `guestLogin()` method |
| Frontend | `router.js` | Added guest redirect guard |
| Frontend | `page-login.js` | Added guest login button + handler |
| Frontend | `page-pickup.js` | Added guest-hidden CSS classes on filter tabs |
| Frontend | `index.html` | Added `nav-guest-hidden` class on followup/reminders tabs |
| Frontend | `app.css` | Added `.btn-guest` styling |

### Verifying Guest Login

```bash
# 1. Get guest token
GUEST_TOKEN=$(curl -s http://localhost:8080/api/auth/guest-login -X POST -H 'Content-Type: application/json' -d '{}' | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")

# 2. Check prescriptions (only 未取)
curl -s "http://localhost:8080/api/prescriptions?page=1&per_page=3" \
  -H "Authorization: Bearer $GUEST_TOKEN"

# 3. Check reminders (403)
curl -s -o /dev/null -w "%{http_code}" \
  http://localhost:8080/api/reminders \
  -H "Authorization: Bearer $GUEST_TOKEN"
# → 403

# 4. Check follow-up (403)
curl -s -o /dev/null -w "%{http_code}" \
  http://localhost:8080/api/follow-up \
  -H "Authorization: Bearer $GUEST_TOKEN"
# → 403
```

## "标记已回访" Parameter Mismatch Fix

**Symptom**: Frontend sends `{prescription_id, status}`, backend expects `{patient_name, status}`.

**Debug flow**:
1. Read API call in `page-reminders.js` → sends `prescription_id`
2. Read backend in `followups.py` → requires `patient_name`
3. curl test confirms mismatch
4. Fix: backend accepts both, preferring `prescription_id` (unique) over `patient_name` (non-unique)

**Backend fix**: added `prescription_id` parameter support in `update_reminder_status()`, with fallback to `patient_name` if `prescription_id` not provided.

**Frontend fix**: added `data-name` attribute to card element, extracted `patientName` from DOM in `markVisited()`, sent both `prescription_id` and `patient_name`.
