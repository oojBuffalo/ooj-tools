---
name: asd-ste100
description: This skill should be used when the user asks to "write in Simplified Technical English", "use STE", "convert this to ASD-STE100", "make this documentation plain/unambiguous", "controlled English", or otherwise wants prose (newly generated or existing/quoted text) rendered in ASD-STE100 Simplified Technical English. In Codex, use when the user invokes $asd-ste100.
---

# ASD-STE100 Simplified Technical English

Render language in [ASD-STE100 Simplified Technical English (STE)](https://www.asd-ste100.org/)
— a controlled language for technical documentation that removes ambiguity so a
sentence has exactly one reading, even for a non-native reader. STE has two
parts: a **dictionary** of approved words and a set of **writing rules**.

## When this applies

Once invoked, render **all prose you generate** into STE, and **convert any
existing text you are asked to rewrite, quote, or summarize** into STE. Meaning
comes first: never drop technical content to satisfy a rule — restructure the
sentence instead.

Do **not** rewrite, and leave byte-for-byte unchanged: code, commands,
identifiers, file paths, UI labels, proper names, and verbatim quotations that
must stay exact. Convert only the surrounding prose. STE targets technical
instructions and descriptions — do not force it on marketing copy, narrative, or
creative writing unless the user asks.

## The dictionary principle

STE ships ~900 approved general words, each with **one part of speech and one
approved meaning**. The rule is *one word, one meaning; one meaning, one word* —
no synonyms for the same idea, and no word used as more than one part of speech.
Everything else is unapproved and must be replaced by an approved equivalent.
Technical names (nouns) and technical verbs specific to a domain are allowed but
must be used consistently.

The dictionary itself is copyright ASD and is not reproduced here. For an
authoritative lookup, use the official specification (see Source). These common
substitutions are illustrative, not the dictionary:

| Unapproved | Approved |
|---|---|
| commence, initiate, start up | start |
| terminate, cease, discontinue | stop |
| prior to | before |
| in the event that, in case | if |
| in order to | to |
| utilize | use |
| obtain | get |
| assist | help |
| accomplish, perform, carry out | do |
| indicate, illustrate | show |
| depress (a button) | push |
| about (meaning "roughly") | approximately |
| enough | sufficient |
| a number of | some, or a specific number |

## Writing rules

The standard groups its 53 rules into areas. The ones that change most text:

**Words**
- Use only approved words in their approved part of speech and meaning.
- Use one term for one thing, every time — no elegant variation.
- No slang, jargon, idioms, or contractions.

**Noun phrases**
- Do not string more than three words together in a noun cluster — count every
  word, not only the nouns (`main fuel pump assembly` is four words and breaks
  the rule). Break longer clusters with prepositions or hyphens (`the position
  of the control lever`, not `the control lever position adjustment`).
- Keep articles (`a`, `an`, `the`) — never drop them to save words.

**Verbs**
- Use active voice. In instructions, use the imperative: start with the verb
  (`Remove the panel.`). Two exceptions: **descriptive** text may use the
  passive when the agent is unknown or unimportant (`The panel is held by four
  bolts.`), and a **past participle may serve as an adjective**
  (`the removed panel`, `a damaged wire`).
- Use only simple tenses: infinitive, imperative, simple present, simple past,
  and `will` future. No perfect or compound tenses.
- Do not use the `-ing` form as a verb (no continuous tenses). It is allowed
  only inside an approved technical name or as an adjective.

**Sentences**
- Procedural (instruction) sentences: **≤ 20 words**.
- Descriptive sentences: **≤ 25 words**.
- One instruction per sentence. Put the condition first: `If X, do Y.`
- Do not omit the subject, verb, or article to shorten a sentence — split it.
- Use a vertical list when steps or conditions get complex.

**Descriptive text**
- One topic per paragraph; **≤ 6 sentences** per paragraph.
- Put the key information at the start of the sentence.

**Warnings and cautions**
- Put the warning or caution **before** the step it applies to.
- Start it with a clear command (what to do or not do); state the consequence
  after, not before.

## Quick reference

| Limit | Value |
|---|---|
| Procedural sentence | ≤ 20 words |
| Descriptive sentence | ≤ 25 words |
| Paragraph (descriptive) | ≤ 6 sentences, one topic |
| Noun cluster | ≤ 3 words |
| Verb tenses | infinitive, imperative, simple present/past, `will` future |
| Voice | active; imperative for instructions — passive OK in descriptive text when the agent is unknown; past participle OK as an adjective |

## Process

1. **Set scope.** New prose → write it in STE from the start. Existing/quoted
   text → convert it, preserving every technical fact. Mark anything that must
   stay verbatim (code, labels, quotes) and leave it untouched.
2. **Split into short sentences** — one instruction each; enforce the ≤ 20 / ≤ 25
   word limits.
3. **Replace unapproved words** with their single approved equivalent. Keep a
   running project list for the technical names and verbs you reuse.
4. **Fix the verbs** — active voice, imperative for instructions, simple tenses
   only, no `-ing` verb forms. Keep the passive in descriptive sentences whose
   agent is unknown, and keep a past participle used as an adjective.
5. **Fix noun phrases** — break clusters over three words; restore dropped
   articles.
6. **Place warnings and cautions** before their step, each leading with a
   command.
7. **Re-check** against the limits and the "do not omit words" rule; split
   anything still too long rather than compressing it.

## Example

Before:

> Prior to commencing the disassembly procedure, it should be ensured that the
> hydraulic system pressure has been fully released, as failure to do so may
> result in serious injury.

After (STE):

> **Warning: Release all the hydraulic pressure before you start. Hydraulic
> pressure can cause injuries.**
>
> 1. Make sure that the hydraulic system pressure is zero.
> 2. Start the disassembly procedure.

## Source

ASD-STE100 is maintained by ASD (AeroSpace, Security and Defence Industries
Association of Europe). The specification is copyright ASD and has been free to
download since Issue 6 (2013): <https://www.asd-ste100.org/>. This skill states
the publicly documented principles in its own words and does not reproduce the
dictionary or the rule text; use the official specification for authoritative
approved-word lookups.
