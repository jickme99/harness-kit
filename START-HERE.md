# Start here

**This folder is harness-kit, not a product.** Do not add app code here. Do not
rename this clone into a project.

A new project is a **separate folder**. This clone stays the factory. After
stand-up, the human opens the **new** folder and works there.

## If someone just opened this repo to start work

You (the agent) stand up their project. They answer questions in plain English.
They do not run stamp, poll, harvest, or pytest — you do.

1. Read `STANDUP.md` and follow it into a **new** directory (default: a sibling
   of this clone). Never copy product files into *this* tree.
2. Ask, without kit jargon:
   - Will any of this ever be public, or shared beyond the owner?
   - Will any tool send the repo to a third party (for example an external PR
     reviewer)?
   - What are we building, and what should the new folder be called?
3. Stamp with `--kit` pointed at **this** clone. Run the gate.
4. When the gate passes, give them the new path and say: close this folder,
   open that one, continue there.

## Kit version

`kit-manifest.json` field `kit_version`. This repo is the kit source, not a
consumer stamp.

## What is not in this repo

Consumer projects, their wikis, their product code. Those live in the folder
you create.
