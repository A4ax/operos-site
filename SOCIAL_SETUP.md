# Social Traffic Setup Guide (free, ~30 min total)

These give you traffic *now* — before Google starts indexing. Do them in order.

---

## 1. Pinterest (BIGGEST fast win for buying guides)

1. Create a **Pinterest business account**: https://www.pinterest.com/business/create/
2. Create a board called **"Tech Buying Guides"** (or similar).
3. Get a token:
   - Go to https://developers.pinterest.com/ → **Create app**
   - Name it `operos` → complete the app setup (production status)
   - In the app, request the **`pins:read,write`** scopes
   - Generate an **Access Token** (user token). Copy it.
4. Add to `C:\Users\o2noor\Desktop\new proj act\operos\.env`:
   ```
   PINTEREST_TOKEN=YOUR_TOKEN
   PINTEREST_BOARD_ID=YOUR_BOARD_ID
   ```
   (Board ID: open your board on pinterest.com — the URL ends with the board ID.)

**Instant win without any token:** every article already has a **Pinterest share button** — anyone can pin it. The site also auto-generates beautiful 2:3 pin images at `operos.de/pins/<slug>.jpg`. As the site owner, pin your top 20 guides yourself today.

---

## 2. X / Twitter (automatic)

1. Go to https://developer.x.com → create an app
2. Get **Bearer Token** → add `X_BEARER_TOKEN=...` to `.env`

---

## 3. Facebook (automatic)

1. Create a **Facebook Page** for Operos
2. Get a **long-lived page token** (developers.facebook.com → Graph API Explorer → select your page → get token)
3. Add to `.env`:
   ```
   FACEBOOK_PAGE_ID=YOUR_PAGE_ID
   FACEBOOK_TOKEN=YOUR_TOKEN
   ```

---

## 4. LinkedIn (automatic)

1. Create a LinkedIn app: https://www.linkedin.com/developers/apps
2. Get an access token with `w_member_social`
3. Add to `.env`:
   ```
   LINKEDIN_TOKEN=YOUR_TOKEN
   LINKEDIN_URN=urn:li:person:YOUR_ID
   ```

---

## 5. Bing Webmaster (2 min)

1. https://www.bing.com/webmasters → **Import from Google Search Console**
2. Pick `operos.de` — done. IndexNow is already pushing URLs there.

---

## 6. Verify it works

After adding tokens, run:

```
cd "C:\Users\o2noor\Desktop\new proj act\operos"
.\venv\Scripts\python.exe social_share.py
```

Each platform prints its result. The engine auto-shares each **new** article after deploy.

---

## 7. Manually pin your best guides today (do this now)

Open these and click the **Pinterest** button, pick a board, done:

- https://operos.de/categories/buyers-guides.html (all buying guides)

Spend 20 minutes pinning 10–15 of them — Pinterest traffic can start arriving within days.