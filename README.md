# Everglow website

Source for [everglow.cc](https://everglow.cc). The site is built from `site/` and deployed automatically to Cloudflare on every push to `main`.

## Layout

- `site/`: the website source.
  - `pages/` holds the page templates.
  - `locales/` holds the copy. Every text node is matched per locale, so new copy needs all five languages.
  - `assets/` holds images and icons.
  - `build.py`, `validate.py` and `make_og.py` are the build tools.
- `index.html`, `privacy.html`, `terms.html` (repo root): the original GitHub Pages copies at `xander12138.github.io/Everglow/`. Older app versions link to them, so **leave them in place**. Each carries a canonical link and a notice pointing at its everglow.cc page (#3), placed outside the policy text. `site/validate.py` pins the legal pages to the policy as published, kept in `site/sources/github-*.html` by git blob hash. If a policy changes, update the root file's policy text and its `site/sources/` copy together, then update the pinned hash.

## Build locally

```sh
cd site
pip install pillow==10.3.0
python3 build.py && python3 build.py --production --domain https://everglow.cc && python3 validate.py
```

The output goes to `site/release-candidate/` (production) and `site/dist/` (review). Both are gitignored.

After changing the home heading or the app icon, run `python3 make_og.py` to refresh the link-preview images.

## Deploy

`.github/workflows/deploy-site.yml` builds and validates every pull request. On a push to `main`, it also deploys with wrangler to the `everglow-marketing` Worker.

It needs one repository secret, `CLOUDFLARE_API_TOKEN`: a Cloudflare API token made from the **Edit Cloudflare Workers** template. Scope it to this account and to the `everglow.cc` zone, because the deploy also keeps the custom domain attached.

To deploy by hand, run `npx wrangler deploy -c wrangler.deploy.json` from `site/`.
