---
tags: [#features, #troubleshooting, #debugging]
---

# Admin Dashboard Troubleshooting

## Admin Button Not Showing

### Step 1: Check Browser Console

1. Open the app in your browser
2. Open Developer Tools (F12 or Cmd+Option+I on Mac)
3. Go to the Console tab
4. Look for logs that say `UserMenu - ...`

You should see:
```
UserMenu - Current user: {email: "mpuerto@ashleyfurniture.com", name: "..."}
UserMenu - User email: mpuerto@ashleyfurniture.com
UserMenu - Is admin? true
UserMenu - Admin emails: ["mpuerto@ashleyfurniture.com"]
```

### Step 2: Verify Your Email

**If "Is admin?" shows `false`:**

1. Check what email is logged in the console
2. Make sure it matches **exactly**: `mpuerto@ashleyfurniture.com`
3. If your email is different (like `MPuerto@ashleyfurniture.com` or `michael.puerto@ashleyfurniture.com`), you need to:
   - Update `ADMIN_EMAILS` in both files to match your actual email
   - Or log in with the correct email

**Files to update:**
- Backend: `backend/app/api/admin.py` (line 18)
- Frontend: `frontend/src/components/UserMenu.tsx` (line 7)

### Step 3: Clear Cache and Reload

1. Hard refresh the page: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
2. If still not working, clear browser cache
3. Log out and log back in

### Step 4: Verify Frontend Build

If you made changes to the frontend:

```bash
cd frontend
npm run dev
```

Make sure the dev server reloaded after the changes.

---

## 403 Forbidden When Accessing /admin

**Error:** "Admin access required"

### Cause
Your email is not in the backend `ADMIN_EMAILS` list.

### Fix
1. Update `backend/app/api/admin.py` line 18:
   ```python
   ADMIN_EMAILS = [
       "your-actual-email@ashleyfurniture.com",  # Use your real email
   ]
   ```

2. Restart the backend:
   ```bash
   cd backend
   # Stop current server (Ctrl+C)
   uv run uvicorn app.main:app --reload
   ```

3. Hard refresh the frontend

---

## Admin Button Shows But Page Won't Load

### Check Network Tab

1. Open Developer Tools → Network tab
2. Click the Admin button
3. Look for failed requests to `/api/v1/admin/...`

**If you see 403 errors:**
- Backend email list doesn't match frontend
- Auth token is invalid (log out and back in)

**If you see 500 errors:**
- Backend has an error
- Check backend terminal for error logs

**If you see CORS errors:**
- Backend might not be running
- Check `VITE_API_BASE_URL` environment variable

---

## No Data Showing in Dashboard

### Check 1: Sessions Exist

1. Go to `/history` page
2. Verify you can see sessions
3. If no sessions exist, the dashboard will be empty (this is normal)

### Check 2: Backend Logs

Look at backend terminal for errors when loading `/api/v1/admin/personas/metrics`

### Check 3: Firestore Access

Backend needs access to Firestore. Check that:
- `GCP_PROJECT_ID` is set correctly
- `FIRESTORE_DATABASE` is set correctly
- Service account has Firestore access

---

## Quick Email Check Command

Run this in the frontend directory to see what email is stored:

```bash
# Open browser console and run:
localStorage.getItem('auth_user')
```

This will show you what user object is stored. Look for the `email` field.

---

## Manual Override (For Testing)

If you just want to test the dashboard and don't care about security:

**Option 1: Temporarily allow all users**

`frontend/src/components/UserMenu.tsx`:
```typescript
const isAdmin = true; // Temporarily allow everyone
```

**Option 2: Check what email you actually have**

`frontend/src/components/UserMenu.tsx`:
```typescript
const isAdmin = user && user.email; // Show button for any logged-in user
```

⚠️ **Don't commit these changes!** Only for local testing.

---

## Common Issues

### Issue: Email has different casing
**Example:** You're logged in as `MPuerto@ashleyfurniture.com` but ADMIN_EMAILS has `mpuerto@ashleyfurniture.com`

**Solution:** Email check is now case-insensitive, but double-check both are the same.

### Issue: Wrong OAuth provider
**Example:** You logged in with Google but your Microsoft account is the admin

**Solution:** Log out and log in with the correct provider that has `mpuerto@ashleyfurniture.com`

### Issue: Frontend not updated
**Example:** You changed ADMIN_EMAILS but button still doesn't show

**Solution:**
```bash
# Stop dev server
# Clear .vite cache
rm -rf node_modules/.vite
# Restart
npm run dev
```

---

## Getting Help

If none of these work, provide the following info:

1. What does browser console show for `UserMenu - ...` logs?
2. What email are you logged in with?
3. Does `/api/v1/admin/personas/metrics` return 403 or 200?
4. Are both backend and frontend running?

Copy the console logs and any error messages.
