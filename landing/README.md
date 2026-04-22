# recrut.marketing — Landing pages

Static recruitment-marketing site for `www.recrut.marketing`. Each vacancy has its own page under its own path, so ad traffic can be tracked per role.

## Structure

```
landing/
├── index.html                    → homepage  (https://www.recrut.marketing/)
├── creative-producer/
│   ├── index.html                → vacancy   (https://www.recrut.marketing/creative-producer)
│   └── thanks.html               → thanks    (https://www.recrut.marketing/creative-producer/thanks)
└── vercel.json                   → clean URLs + security headers
```

No build step — plain HTML/CSS/JS.

## Local preview

```bash
python -m http.server 8080 --directory landing
# homepage:   http://localhost:8080/
# vacancy:    http://localhost:8080/creative-producer/
```

## Deploy to Vercel (recommended)

1. Push this repo to GitHub (already done).
2. Go to [vercel.com/new](https://vercel.com/new) → **Import Git Repository** → pick `Vicky`.
3. In the **Configure Project** step:
   - **Root Directory** → `landing`
   - Framework Preset → **Other**
   - Build & Output Settings → leave defaults (no build command)
4. **Deploy**.
5. After deploy → **Settings → Domains** → add `recrut.marketing` and `www.recrut.marketing`.
6. Configure DNS at your domain registrar:
   - `recrut.marketing` → **A** record to `76.76.21.21`
   - `www.recrut.marketing` → **CNAME** to `cname.vercel-dns.com`
   - (Vercel will show exact values in the Domains tab — use those.)
7. SSL is issued automatically within a minute.

### Alternative: Cloudflare Pages

1. [dash.cloudflare.com](https://dash.cloudflare.com) → Workers & Pages → Create → Pages → Connect to Git.
2. Build command: *(empty)*. Build output directory: `landing`.
3. Add custom domain in Pages → Custom domains.

### Alternative: Netlify

1. [app.netlify.com/start](https://app.netlify.com/start) → connect Git repo.
2. Base directory: `landing`. Publish directory: `landing`. Build command: *(empty)*.
3. Domain management → add `recrut.marketing`.
4. Create `landing/_redirects` if you want clean URLs:
   ```
   /creative-producer/        /creative-producer/index.html   200
   /creative-producer/thanks  /creative-producer/thanks.html  200
   ```

## Form submissions

The form posts to **FormSubmit** (zero-config) and forwards submissions (with CV attachment) to `olganewlife99@gmail.com`. After submit, candidate is redirected to `/creative-producer/thanks`.

**Activation (one-time, after first deploy):**

1. Open the live page and submit one test application.
2. FormSubmit sends a confirmation link to `olganewlife99@gmail.com` — click **Activate**.
3. All further submissions arrive in that inbox with the attached CV.

### Data captured per application

- Full name, Email, Phone / Telegram, LinkedIn / Portfolio, Message
- CV file (PDF / DOC / DOCX)
- UTM params: `utm_source`, `utm_medium`, `utm_campaign`, `utm_content`, `utm_term`
- Landing URL

## Ads setup (Meta + Google)

### UTM template

Use this in every ad destination URL so you know which campaign drove the candidate:

```
https://www.recrut.marketing/creative-producer?utm_source=meta&utm_medium=paid_social&utm_campaign=creative_producer_q2&utm_content=video_a
https://www.recrut.marketing/creative-producer?utm_source=google&utm_medium=cpc&utm_campaign=creative_producer_search&utm_content=ad_group_edtech
```

### Pixels & conversion tracking

The vacancy page has placeholder comments in `<head>` where you paste:
- **Meta Pixel base code** (both on vacancy and homepage)
- **Google Tag Manager** or **GA4** tag

The `thanks.html` page has **ready-to-uncomment snippets** for:
- Meta Pixel `Lead` event
- Google Ads conversion event
- GA4 `generate_lead` event

Replace the `YOUR_PIXEL_ID`, `AW-CONVERSION_ID`, `G-MEASUREMENT_ID` placeholders with real IDs from your Meta Events Manager and Google Ads accounts, then uncomment the blocks.

### Recommended minimum ad stack

1. **Meta Ads** — campaign objective **Leads**, Advantage+ Audience, lookalike of your existing hires if you have them, CAPI via Meta Pixel → Conversions API.
2. **Google Ads** — Search campaign on job-seeker keywords (`creative producer remote`, `edtech marketing jobs cyprus`, etc.) + Performance Max.
3. Test budget: **$20–50/day per channel for 3–5 days**, then optimize by CPL.

## Adding a new vacancy later

1. Duplicate the `creative-producer/` folder → rename to e.g. `growth-marketer/`.
2. Edit the copy, form `_subject`, and `_next` URL (point to the new thanks page).
3. Add a card for it on `landing/index.html`.
