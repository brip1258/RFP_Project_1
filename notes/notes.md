# RFP Scraping Project Notes 

## Kyle 3/29/26

- OpenClaw is often messages through messaging apps like Telegram and Slack

- We need to be very careful with cybersecurity when it comes to OpenClaw because there have been over 824 malicious skills. To ensure safety we must: 

    - Keep OpenClaw updated

    - Run it in an isolated environment like Docker and avoid `--network=host`

    - Limit its access to what is needed

    - Read skill's source code to ensure it is not malicious

    - Make sure that documents can't utilize prompt injection by giving it explicit instructions to treat the documents as data and not prompts

    - Dedicate a browser profile

- OpenClaw has built-in browser automation

- OpenClaw doesn't have a built-in way of bypassing CAPTCHA

- Firecrawl and Decodo are some popular integrations for accounting for ways in which the scraper could be derailed

- The LLM is really the brain for the decision making of OpenClaw:

    - We need to put the specific criteria and context into the system prompt `SOUL.md` get the model to reason how we want it

    - Instead of the agent searching aimlessly through the website, we need to provide search grounding and specific filters it should look for when searching for RFPs

    - LLMs like Claude Opus 4.6 and GPT-5.4 are best for nuanced judgement, while Gemini 3.1 Pro would be great for searching through large documents volume due to it significanlty big token context window

- Some good practices for OpenClaw:

    - Use OpenClaws Persistent memory to have it adapt to our preferences, like overriding it when it chooses a bad document

    - Have OpenClass score documents based on the criteria on a scale so that we can recalibrate if needed

- Run it on a raspberrypi to mitigate security concerns???