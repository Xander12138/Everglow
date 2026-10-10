# Is Everglow in AI answers? (#5)

A fixed panel, run monthly, recorded in `ai-answers.csv`. It measures whether answer engines mention Everglow when someone asks for the kind of app it is. The site has no analytics, so this and Search Console are the only signals.

## The panel

Ten purchase-intent prompts, asked word for word:

1. best AI journaling app for iPhone
2. AI journal that runs on my phone offline
3. private AI journal that doesn't send my entries to the cloud
4. journal app that remembers the people I write about
5. journaling app where I can use my own OpenAI or Claude API key
6. journal app I can buy once instead of subscribing
7. Rosebud alternative with a free tier
8. how to move my Day One journal to another app
9. AI journal that answers questions about my past entries
10. journaling app with import and plain Markdown export

Five surfaces, each in a condition that keeps your own history out of the answer:

| Surface | How | Clean condition |
|---|---|---|
| Google (AI Overview / Web Guide) | `https://www.google.com/search?q=<prompt>&hl=en&gl=us&pws=0` | `pws=0` turns off personal results |
| ChatGPT | chatgpt.com → Temporary chat → the **Personalized** menu at the top right → **Unpersonalized** | Temporary chat alone still reads memory. Unpersonalized ignores memory, plugins and custom instructions. Set it by hand: browser automation couldn't flip it on 2026-10-10. |
| Perplexity | perplexity.ai, signed in | Since October 2026 it asks you to sign in before answering. Use a fresh thread with no Space. |
| Gemini | gemini.google.com, a temporary chat | Turn off personal context / saved info for the run if offered. |
| Claude | claude.ai, an incognito chat | Incognito chats don't use memory. |

## Recording

One CSV row per prompt × surface. `everglow_mentioned` is yes/no. `citation_urls` lists the domains the answer cites. `product_fact_errors` holds anything the answer gets wrong about Everglow, checked against `site/llms.txt`. Put the apps an answer names in `notes`. Save a copy of any answer that mentions Everglow and give its path in `response_evidence_path`.

Answers vary run to run. A single "no" doesn't prove absence, but ten "no"s on a surface is the baseline the content work (#4) and the listings (#6) are meant to move.

## Results so far

- **2026-10-10, Google:** 0 of 10. Most cited: reddit.com, apps.apple.com (including Apple's editorial "The Best Journaling Apps for iPhone"), vendor blogs (memexlab.ai, reflection.app, lound.ai, dayora.ai, deepjournal.app) and directories (byoklist.com, noteapps.info, toolfolio.com). Most named: Day One, Reflection, Mindsera, Rosebud, Apple Journal, Dayora.
- ChatGPT, Perplexity, Gemini, Claude: not yet run (see the clean conditions above).
