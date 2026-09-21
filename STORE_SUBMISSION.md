# Decky Plugin Store Submission Status

This file tracks the official Decky Plugin Store submission status for **Sharp Filter Selector**.

## Source of truth

The official public source for this plugin is:

https://github.com/N3ruk/Sharp-Filter-Selector

All Store review, testing and release work should refer to the files published in this repository.

## AI provenance

Generative AI (ChatGPT) was used to write a **majority of the current codebase**.

The maintainer will **not** check or claim the following current Decky Plugin Addition checklist item:

> Generative AI was NOT used to write a majority of the code I am submitting.

Full disclosure:

[AI_DISCLOSURE.md](AI_DISCLOSURE.md)

## Current Decky checklist status

### Developer

- [x] Original author / authorized maintainer of this repository.
- [x] Repository includes an explicit BSD-3-Clause license.
- [ ] "Generative AI was NOT used to write a majority of the code" — **cannot be checked truthfully**.

### Plugin

- [ ] Verified on both SteamOS Stable and Beta channels specifically for Store submission.
- [ ] Verified by Decky reviewers / third-party testers.
- [x] Plugin purpose and functionality are publicly documented.
- [x] Plugin source and release history are public.

### Backend

- **Custom backend other than Python:** No.
- **Third-party FOSS tool with non-statically-linked dependencies:** Yes — the plugin invokes the system-provided `xprop`.
- **Custom statically-linked binary:** No.
- **Patches/replaces Gamescope:** No.

## Technical purpose

Sharp Filter Selector:

- switches Gamescope scaling between AMD FSR and NVIDIA NIS from Decky's Quick Access Menu;
- exposes NIS sharpening control;
- uses Decky's Python backend;
- discovers active Gamescope/Xwayland sessions;
- updates Gamescope scaling properties using `xprop`;
- does not ship or replace Gamescope.

## Policy clarification required

The current Decky Plugin Addition template contains a checklist item requiring that generative AI was **not used to write a majority** of the submitted code.

Older Decky guidance, quoted in SteamDeckHomebrew/decky-plugin-template issue #59, describes a broader prohibition on LLM-generated code.

Because this project is majority AI-assisted, the maintainer will request an explicit policy decision before opening a normal Plugin Addition PR.

## Proposed message to Decky maintainers

> Hi Decky maintainers,
>
> I would like to ask for a policy clarification / review path before submitting **Sharp Filter Selector** to the Plugin Store:
>
> https://github.com/N3ruk/Sharp-Filter-Selector
>
> I want to be completely transparent: **generative AI (ChatGPT) was used to write a majority of the current codebase**.
>
> I therefore cannot truthfully check the current Plugin Addition checklist item:
>
> > Generative AI was NOT used to write a majority of the code I am submitting.
>
> The repository contains a permanent public provenance statement:
>
> https://github.com/N3ruk/Sharp-Filter-Selector/blob/main/AI_DISCLOSURE.md
>
> The plugin was not produced as an unreviewed one-shot generation. I defined the behavior, tested it on real systems, reproduced failures, supplied runtime/environment information, and iteratively refined the implementation based on observed behavior.
>
> The current public version has been tested during development in real Gamescope / Steam Deck / Linux environments, but I am **not** claiming Store-required Stable/Beta or third-party verification until those checks are completed.
>
> Sharp Filter Selector switches Gamescope scaling between AMD FSR and NVIDIA NIS from Decky's Quick Access Menu, exposes NIS sharpening, uses the standard Decky Python backend, and invokes the system-provided `xprop`. It does not patch or ship Gamescope.
>
> Because the project does not satisfy the current AI checklist item, I do not want to submit a normal PR that misrepresents its provenance.
>
> Would the maintainers be willing to either:
>
> 1. review this plugin under an exception or alternative process with the AI provenance fully disclosed; or
> 2. confirm that a plugin whose current codebase is majority AI-assisted is categorically ineligible for the Store?
>
> If review is possible, I am happy to satisfy the normal technical, licensing, Stable/Beta and third-party testing requirements and make any requested code changes.

## Submission blocker

The connected GitHub integration used during preparation can write to the maintainer's repositories but cannot create issues, forks, or pull requests in the external `SteamDeckHomebrew` organization without that repository/fork being accessible to the integration.

The first manual step is therefore one of:

1. post the policy clarification above to the appropriate Decky repository/community channel; or
2. fork `SteamDeckHomebrew/decky-plugin-database` into the maintainer's GitHub account, after which the submission branch can be prepared from the connected account.

No normal Plugin Addition PR should be opened until the AI-policy question is resolved.
