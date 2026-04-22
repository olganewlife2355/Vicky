# Creative Producer — Job Landing Page

Single-page landing for the Creative Producer (EdTech) vacancy. Designed to be used as a destination URL for Meta Ads / Google Ads recruitment campaigns.

## Files

- `index.html` — self-contained landing page (HTML + CSS + minimal JS, no build step).

## Quick start

Just open `landing/index.html` in a browser, or serve it with any static host:

```bash
# local preview
python -m http.server 8080 --directory landing
# → http://localhost:8080
```

Deploy-ready on any static host: **Vercel**, **Netlify**, **Cloudflare Pages**, **GitHub Pages**, **S3**, etc. — just upload the `landing/` folder.

## How the form works

The application form posts to **FormSubmit** (https://formsubmit.co), which forwards submissions (with CV attachment) to `olganewlife99@gmail.com`.

**Activation (one-time):**

1. Deploy the page and open it in a browser.
2. Submit one test application.
3. You'll receive a confirmation email from FormSubmit — click the activation link inside.
4. All future submissions arrive directly in your inbox with the attached CV.

No signup, no API key, free tier is enough for typical recruitment volume.

### Fields captured

- Full name, Email, Phone / Telegram, LinkedIn / Portfolio
- CV file upload (PDF / DOC / DOCX)
- Short message
- UTM params (`utm_source`, `utm_medium`, `utm_campaign`, `utm_content`) — auto-captured from URL

## Hooking up to recruitment ads

**UTM example** for a Meta campaign:

```
https://your-domain.com/?utm_source=meta&utm_medium=cpc&utm_campaign=creative_producer_q2&utm_content=video_a
```

These are stored as hidden fields and arrive with every application, so you can see which ad brought each candidate.

### Next steps (optional)

- Add **Meta Pixel** + **Conversions API** — paste the pixel snippet before `</head>` and fire a `Lead` event on the FormSubmit thank-you page (or add a custom `_next` URL under your domain with the pixel fire on load).
- Add **Google Tag Manager** — one container tag to manage Meta Pixel, GA4, and Google Ads conversion tracking.
- Set up an **A/B test** on the hero headline and the benefits ordering to improve CR.
