# STOPReplay — Attack Lanes & Orchestration Specification

This specification is the definitive guide to Team STOP's attack lanes, strategy selection, multi-turn conversational persistence, and simulator API integration for the revel8 Hackathon challenge (*Agentic Social Engineer*).

It serves as the shared contract across the team:
* **Adrian (`data-collection`)**: Details which OSINT signals and entities unlock specific lanes.
* **Cem (`database`)**: Specifies the exact `hooks` row structure, `win_type`, and landing page fields to persist.
* **Anushree (`analysis`)**: Defines fact-to-hook mapping rules and ensures zero unassertable claims.
* **Shaurya (`integration`)**: Drives the execution loop, channel formatting, and pushback state machine.
* **Gary (`reporting`)**: Outlines the psychological narrative, replay turning points, and demo thread for the pitch.

---

## 1. Executive Summary & Team Handoff Matrix

| Lane ID | Title | Target Fit | Win Type | Primary Channel | Key OSINT Trigger (Adrian / Anushree) |
|---|---|---|---|---|---|
| **LANE 1** | Enterprise Procurement RFP | Julius / Sales | `action` / `credential` | `email` | `role: sales|commercial`, B2B enterprise product |
| **LANE 2** | Design Partner Beta Cohort | Tom / Product | `disclosure` / `action` | `linkedin_message` | `role: product|design`, talks on user experience |
| **LANE 3** | Async Thread Leak Advisory | Robert / CTO | `action` / `credential` | `email` / `discord` | `role: cto|tech`, open-source repos, agent talks |
| **LANE 4** | Alumni Spotlight & Directory | Universal (Alumni) | `credential` | `email` | `credential: university|alumni|degree|tum|lmu` |
| **LANE 5** | Sports Timing & Bib Roster | Universal (Athletic) | `action` / `credential` | `whatsapp` / `sms` | `interest: running|marathon|cycling|strava|tennis` |
| **LANE 6** | Professional CPD Audit | Universal (Licensed) | `credential` | `email` | `credential: cpa|pmp|aws|bar|license|scrum` |
| **LANE 7** | Municipal Street Works Notice | Universal (Resident) | `action` / `credential` | `email` / `sms` | `contact: city|district|neighborhood|address` |
| **LANE 8** | Former Colleague Reconnect | Universal (Corporate)| `disclosure` | `linkedin_message` | `relationship: past_employer|overlap_years` |
| **LANE 9** | Creative Contributor Release | Universal (Creator) | `action` | `email` | `project: blog|medium|photo|article|talk` |
| **LANE 10**| Specialist Advisory Consult | Universal (Niche Skill)| `credential` | `linkedin_message` | `role: specialist|niche_expertise`, senior tenure |
| **LANE 11**| Consumer Restitution Claim | Universal (Travel/App)| `credential` | `sms` | `other: frequent_travel|consumer_services` |
| **LANE 12**| Priority Courier Reschedule | Universal (Logistics) | `credential` | `sms` | `contact: phone_number`, baseline fallback |
| **LANE 13**| Gary's Double Twist Alert | CEO / Founders | `credential` | `email` | `role: founder|c_level`, corporate email domain |
| **LANE 14**| Security Training Bonus | Non-CEOs / Employees | `credential` | `email` | `role: employee|engineer|ops`, company name |

---

## 2. Target API Protocol & Exact Payloads (Stackit Target Engine)

* **Base URL:** `https://target-api.apps.01.cf.eu01.stackit.cloud/v1`
* **Authentication:** `Authorization: Bearer <TEAM_KEY>` (Server-side environment variable only)
* **Allowed Channels (`GET /v1/channels`):**  
  `email`, `sms`, `whatsapp`, `signal`, `telegram`, `imessage`, `slack`, `teams_chat`, `discord`, `linkedin_message`, `linkedin_connection_request`, `x_dm`, `instagram_dm`, `facebook_messenger`, `calendar_invite`, `shared_document`, `voicemail`, `mfa_push`, `phone_call`, `video_call`, `teams_call`, `live_chat`.

### A. Sending a Message (`POST /v1/sessions/{sid}/messages`)
```json
{
  "to": "julius",
  "channel": "email",
  "from": {
    "name": "Dr. Michael Kraus",
    "address": "m.kraus@enterprise-sourcing-hub.de"
  },
  "subject": "Vendor Evaluation: Q3 Workforce Security Initiative",
  "body": "Hi Julius, our steering committee has shortlisted revel8 for our enterprise rollout...",
  "attachments": ["DAX_Security_Vendor_RFP_Matrix_v1.pdf"],
  "sent_at": "2026-11-22T10:15:00Z"
}
```
*Note: Always pass `Idempotency-Key: <uuid>` in HTTP headers so network retries never consume an extra contact.*

### B. Registering a Simulated Landing Page (`POST /v1/sessions/{sid}/pages`)
You do not host phishing servers. You register what URL you link to and what form fields it displays:
```json
{
  "url": "https://enterprise-sourcing-hub.de/vendor-login",
  "title": "Enterprise Procurement Portal: Vendor Sign-In",
  "fields": ["email", "password", "security_pin"],
  "text": "Sign in to access your confidential vendor evaluation matrix."
}
```
*Form Objective Scoring:*
* Submitting **`password`**, **`pin`**, **`token`**, **`api_key`**, or **`iban`** triggers the **Credentials** win objective.
* Submitting internal tools or infrastructure details triggers the **Disclosure** win objective.

### C. Live Conversations — The "1-Touch 10-Turns" Superpower (`POST /v1/sessions/{sid}/conversations`)
> *"A conversation costs one touch and allows at most 10 turns. To the person, a whole call is one contact, however long it lasts."* (from official `docs.md`)

* **Channels:** `phone_call`, `video_call`, `teams_call`, `live_chat`.
* **Flow:**
  1. `POST /v1/sessions/{sid}/conversations` with `{"to": "robert", "channel": "phone_call", "from": {"name": "Jonas Weber", "address": "+49 89 1234 5678"}}`.
  2. Target persona answers with `persona_says`.
  3. Loop with `POST /v1/conversations/{cid}/turns` with `{"say": "..."}`.
  4. End with `POST /v1/conversations/{cid}/end`.
* **Cost:** **Exactly 1 contact spent from the 10-contact budget**, even after 10 back-and-forth turns! This is our highest-speed incident vector.

---

## 3. Detailed Specifications for the 14 Attack Lanes

---

### LANE 1: Enterprise Procurement RFP Matrix
* **Target:** Julius Muth (Sales / Co-CEO) or commercial executives.
* **Psychological Hook:** Commercial ambition, large enterprise deal urgency, fear of missing RFP shortlist.
* **Required Facts:** `facts.category = "role"` (sales/commercial leadership) and `assertable = true`.
* **Cem DB Hook:**
  * `win_type`: `action` | `credential`
  * `channel`: `email`
  * `persona`: `{"name": "Dr. Michael Kraus", "role": "Head of Enterprise Sourcing", "org": "DAX Logistics Group", "why_credible": "Leading a 4,500-seat vendor selection"}`
* **The Touch Progression:**
  * **Touch 1 (Email):**
    * *Subject:* Vendor Inquiry: AI Workforce Protection Initiative (DAX Procurement)
    * *Body:* Hi Julius, our IT compliance steering committee has shortlisted revel8 for our upcoming enterprise rollout (approx. 4,500 seats across DAX operations). Before our vendor call next Tuesday, could you verify if your platform fulfills our mandatory tenant isolation criteria detailed in section 3 of our evaluation sheet?
    * *Attachment:* `DAX_Security_Vendor_RFP_Matrix_v1.pdf`
  * **Touch 2 (Pushback Handler — if target hesitates to open PDF):**
    * *Reaction:* Gracefully offer portal login: *"Completely understand your security policy! If you prefer, you can review and sign the isolation checklist directly on our vendor procurement portal: `https://dax-vendor-sourcing-portal.net/login`"* (Page registered with `fields: ["email", "password"]`).

---

### LANE 2: Design Partner Latency Cohort
* **Target:** Tom Müller (Product / Co-CEO) or product managers.
* **Psychological Hook:** Product pride, interest in design partnerships with financial institutions, technical validation.
* **Required Facts:** `facts.category = "role"` (product/design strategy), verified public talk on simulation workflows.
* **Cem DB Hook:**
  * `win_type`: `disclosure` | `action`
  * `channel`: `linkedin_message` $\rightarrow$ `email`
  * `persona`: `{"name": "Sarah Vogel", "role": "VP Product Innovation", "org": "European FinTech Collective", "why_credible": "Advising tier-1 banks on simulation software"}`
* **The Touch Progression:**
  * **Touch 1 (LinkedIn):**
    * *Body:* Hi Tom, really enjoyed your product breakdown on AI simulation workflows. We are currently advising 6 member fintechs on multi-channel phishing defenses. We want to recommend revel8, but our CISO board is questioning sub-second response latency. How is your team handling prompt evaluation latency under heavy load?
  * **Touch 2 (Email / Attachment):**
    * *Body:* That approach makes total sense. We mapped our member banks' evaluation requirements here: `fintech_simulation_benchmark_v2.pdf`. Could you look over slide 4 to confirm revel8 supports custom financial lure schemas?

---

### LANE 3: Async Websocket Leak & CVE Advisory
* **Target:** Robert Seilbeck (CTO) or software engineers.
* **Psychological Hook:** Intellectual responsibility, fear of production memory leaks, technical curiosity.
* **Required Facts:** `facts.category = "role" | "project"` (CTO, async python architectures, open-source maintainer).
* **Cem DB Hook:**
  * `win_type`: `action` | `credential`
  * `channel`: `email` | `discord`
  * `persona`: `{"name": "Alexej Berg", "role": "Independent Security Researcher", "org": "Runtime Reliability Labs", "why_credible": "Open-source contributor to async network libraries"}`
* **The Touch Progression:**
  * **Touch 1 (Email):**
    * *Subject:* Responsible Disclosure: Potential memory leak in async agent websocket loops
    * *Body:* Hi Robert, while running latency benchmarks on async Python agent orchestration frameworks (referencing your recent Munich architecture talk), we noticed a reproducible socket leak when connection dropouts occur during streaming turns. I’ve compiled the reproduction script and packet capture in `websocket_leak_poc.pdf`. Let me know if you prefer tracking it via our developer advisory board: `https://runtime-security-lab.org/cve/session-leak`
  * **Touch 2 (De-escalation):**
    * *If target resists files:* *"Totally fair! The issue manifests specifically under 50+ concurrent streaming sessions. Happy to walk through it in text right here if you prefer not opening external files."*

---

### LANE 4: Alumni Spotlight & Directory Verification
* **Target:** Universal (any target with a university degree in public data).
* **Psychological Hook:** Alma mater nostalgia, prestige, pride in academic spotlight.
* **Required Facts:** `facts.category = "credential"` with university name (e.g. TUM, LMU, Oxford, TU Berlin).
* **Cem DB Hook:**
  * `win_type`: `credential` | `action`
  * `channel`: `email`
  * `persona`: `{"name": "Dr. Claudia Richter", "role": "Director of Alumni Affairs", "org": "University Alumni Foundation", "why_credible": "Official alumni magazine coordinator"}`
* **The Touch Progression:**
  * **Touch 1 (Email):**
    * *Subject:* TUM Alumni Magazine: Spotlight Feature (Class of 2019)
    * *Body:* Dear [Target Name], each year our departmental board selects 10 graduates whose career journeys showcase our alumni impact. We would love to include a short feature on your work in our upcoming anniversary publication. Please review your quote and bio draft on our alumni registry portal: `https://university-alumni-network.org/verify/[target-id]` or review the attached proof: `alumni_spotlight_draft.pdf`.
  * **Landing Page:** `https://university-alumni-network.org/verify/[target-id]` with `fields: ["email", "password", "graduation_year"]`.

---

### LANE 5: Sports League Timing & Bib Roster
* **Target:** Universal (targets who post about running, Strava, cycling, tennis).
* **Psychological Hook:** Urgent logistical check before a sports event, community affiliation.
* **Required Facts:** `facts.category = "interest"` (marathon, cycling, Strava, sports club).
* **Cem DB Hook:**
  * `win_type`: `action` | `credential`
  * `channel`: `whatsapp` | `sms`
  * `persona`: `{"name": "Florian Meier", "role": "Event Coordinator", "org": "Munich Endurance League", "why_credible": "Race timing coordinator"}`
* **The Touch Progression:**
  * **Touch 1 (WhatsApp / SMS):**
    * *Body:* Hey [Target Name]! Florian here from the race logistics team. We’re finalizing the wave start times and medical emergency contact numbers for Sunday’s run. Could you quickly check if your bib number and emergency details are accurate on the roster sheet? `https://endurance-sports-timing.net/roster/[target-id]` (attached: `wave_start_roster_v2.pdf`).

---

### LANE 6: Continuing Professional Education (CPD) Audit
* **Target:** Universal (certified professionals: PMP, CPA, AWS, Bar, Medical, Scrum).
* **Psychological Hook:** Fear of certification suspension, compliance deadline anxiety.
* **Required Facts:** `facts.category = "credential"` (accreditations, licenses).
* **Cem DB Hook:**
  * `win_type`: `credential`
  * `channel`: `email`
  * `persona`: `{"name": "Accreditation Registrar", "role": "Compliance Officer", "org": "European Professional Standards Registry", "why_credible": "Official accreditation auditor"}`
* **The Touch Progression:**
  * **Touch 1 (Email):**
    * *Subject:* Mandatory Notice: Annual Continuing Professional Development (CPD) Verification Cycle
    * *Body:* Dear [Target Name], our records indicate your current certification cycle concludes in 14 business days. To avoid temporary lapse of active credential status, please log in to verify your submitted credit transcript: `https://professional-standards-board.org/cpd-audit/login`.
  * **Landing Page:** `fields: ["credential_id", "email", "password"]`.

---

### LANE 7: Municipal Street Works & Resident Notice
* **Target:** Universal (targets with an identifiable neighborhood, district, or city).
* **Psychological Hook:** Civic duty, local neighborhood impact (parking, noise, construction).
* **Required Facts:** `facts.category = "contact"` (location, district, street).
* **Cem DB Hook:**
  * `win_type`: `action` | `credential`
  * `channel`: `email` | `sms`
  * `persona`: `{"name": "District Advisory Council", "role": "Civic Ombudsman", "org": "Urban Planning Authority", "why_credible": "Municipal public works notification"}`
* **The Touch Progression:**
  * **Touch 1 (Email):**
    * *Subject:* Resident Consultation Notice: Fiber-optic installation & parking restrictions on your street
    * *Body:* Notice to residents of [District]: The local council has opened public comments regarding proposed civil works and temporary street parking reallocations. Review the affected street map and register your feedback: `street_works_planning_notice.pdf` or visit `https://district-resident-portal.de/planning-notices`.

---

### LANE 8: Former Colleague Reconnect
* **Target:** Universal (targets who worked at a previous employer 2–5 years ago).
* **Psychological Hook:** Familiarity, shared corporate history, low suspicion barrier.
* **Required Facts:** `facts.category = "relationship"` or past employer from resume.
* **Cem DB Hook:**
  * `win_type`: `disclosure`
  * `channel`: `linkedin_message` $\rightarrow$ `whatsapp`
  * `persona`: `{"name": "Lukas Brandt", "role": "Senior Consultant", "org": "Former Colleague", "why_credible": "Worked in adjacent department 3 years ago"}`
* **The Touch Progression:**
  * **Touch 1 (LinkedIn):**
    * *Body:* Hey [Target Name]! Saw your update—can’t believe it’s been 3 years since our days back at [Past Company]! I just moved to your city for a new role. How are you liking your current team? We should catch up for coffee sometime.
  * **Touch 2 (Disclosure Probe):**
    * *Body:* That’s great to hear! By the way, our current company is evaluating internal productivity setups. What internal tech stack or collaboration tools do you guys rely on most heavily over there?

---

### LANE 9: Creative Contributor Release & Licensing
* **Target:** Universal (authors, bloggers, photographers, open-source creators).
* **Psychological Hook:** Flattery, creative ego, intellectual property recognition.
* **Required Facts:** `facts.category = "project"` (blog posts, public photos, articles).
* **Cem DB Hook:**
  * `win_type`: `action`
  * `channel`: `email`
  * `persona`: `{"name": "Elena Rostova", "role": "Senior Commissioning Editor", "org": "European Media Publishing Group", "why_credible": "Publishing an educational anthology"}`
* **The Touch Progression:**
  * **Touch 1 (Email):**
    * *Subject:* Permission Request: Featuring your work in our 2026 Innovation Handbook
    * *Body:* Dear [Target Name], our editorial board is compiling an educational handbook on emerging technology trends. We were deeply impressed by your article/photograph on [Topic] and would love to feature an excerpt. Could you review our standard non-exclusive contributor agreement? `contributor_licensing_agreement_draft.pdf`.

---

### LANE 10: Boutique Specialist Advisory Consultation
* **Target:** Universal (experienced professionals in supply chain, finance, legal, tech).
* **Psychological Hook:** Financial incentive (€380/hr honorarium), professional recognition.
* **Required Facts:** `facts.category = "role"` with seniority > 3 years.
* **Cem DB Hook:**
  * `win_type`: `credential`
  * `channel`: `linkedin_message` $\rightarrow$ `email`
  * `persona`: `{"name": "Hannah Bergmann", "role": "Research Director", "org": "AlphaSearch Expert Network", "why_credible": "Connecting private equity with domain specialists"}`
* **The Touch Progression:**
  * **Touch 1 (LinkedIn):**
    * *Body:* Hi [Target Name], our investment client is conducting commercial due diligence on the [Target’s Sector] landscape and requested a 45-minute phone consultation with an active practitioner (€380 honorarium). If your schedule permits, please confirm your advisor profile and calendar preferences here: `https://expert-network-onboarding.com/advisor/[target-id]`.
  * **Landing Page:** `fields: ["email", "password", "iban"]`.

---

### LANE 11: Consumer Restitution / Travel Disruption Claim
* **Target:** Universal (frequent travelers, digital consumers).
* **Psychological Hook:** Greed / entitlement, uncollected cash refund, FOMO.
* **Required Facts:** Universal consumer profile.
* **Cem DB Hook:**
  * `win_type`: `credential`
  * `channel`: `sms`
  * `persona`: `{"name": "Claims Administrator", "role": "Legal Settlement Officer", "org": "EU Passenger Compensation Bureau", "why_credible": "Court-appointed claim administrator"}`
* **The Touch Progression:**
  * **Touch 1 (SMS):**
    * *Body:* Claims Notice #EU-91823: A settlement credit of €238.40 for flight/service disruption has been approved for [Target Name]. Confirm your claimant IBAN before the disbursement window closes: `https://eu-consumer-settlement-portal.net/claims/eu91823`.
  * **Landing Page:** `fields: ["claimant_name", "email", "iban", "pin"]`.

---

### LANE 12: Priority Courier Delivery Rescheduling
* **Target:** Universal baseline fallback (everyone receives packages).
* **Psychological Hook:** Everyday logistics urgency, fear of parcel returned to depot.
* **Required Facts:** Target name and phone contact.
* **Cem DB Hook:**
  * `win_type`: `credential`
  * `channel`: `sms`
  * `persona`: `{"name": "CityExpress Logistics", "role": "Automated Dispatch System", "org": "CityExpress Courier", "why_credible": "Local courier dispatch system"}`
* **The Touch Progression:**
  * **Touch 1 (SMS):**
    * *Body:* Dispatch Notice: Priority letter/parcel #DE-89211 could not be completed for [Target Name] due to missing building gate/intercom code. Update delivery instructions or authorize neighbor drop-off: `https://cityexpress-dispatch-hub.net/track/de89211`.
  * **Landing Page:** `fields: ["door_code", "email", "password"]`.

---

### LANE 13: Gary's Double Twist / IT Quarantine Warning
* **Target:** Julius, Robert, Tom, or any corporate executive.
* **Origin:** Team brainstorming document.
* **Psychological Hook:** False sense of security when being "rescued" from an active phishing attack.
* **Required Facts:** `facts.category = "role"` (executive) and corporate email address.
* **Cem DB Hook:**
  * `win_type`: `credential`
  * `channel`: `email`
  * `persona`: `{"name": "IT Incident Response", "role": "Automated SecOps", "org": "Cloud Identity Defense Center", "why_credible": "External cloud identity provider alert"}`
* **The Touch Progression:**
  * **Touch 1 (The Trigger):** Send a crude, clumsy password reset notice from a throwaway external name.
  * **Touch 2 (The Twist):** Send an official security warning referencing the suspicious attempt:
    * *Subject:* [SECURITY ALERT] Unauthorized login blocked — Confirm your identity if this was NOT you
    * *Body:* Our automated monitoring detected an anomalous login attempt from IP 185.220.101.4 (Tor Exit Node) on your account. If this was NOT you, please review your active session log and restore account integrity immediately: `https://account-verify-support.net/restore-access`
  * **Landing Page:** `fields: ["email", "password", "verification_code"]`.

---

### LANE 14: Corporate Security Training Completion Bonus
* **Target:** Non-executives, employees, or corporate staff.
* **Origin:** Team brainstorming document.
* **Psychological Hook:** Relief from passing mandatory training, desire for corporate reward.
* **Required Facts:** Target works at an identifiable company.
* **Cem DB Hook:**
  * `win_type`: `credential`
  * `channel`: `email`
  * `persona`: `{"name": "Corporate Training & People Ops", "role": "Training Coordinator", "org": "Employee Learning Portal", "why_credible": "Internal HR perks administrator"}`
* **The Touch Progression:**
  * **Touch 1:** Official corporate directive announcement regarding mandatory annual cybersecurity awareness simulation.
  * **Touch 2:** Send the congratulatory follow-up:
    * *Subject:* Congratulations! You successfully passed the 2026 Annual Security Simulation
    * *Body:* Great job! You correctly identified our scheduled security exercise. As part of our company engagement initiative, claim your €50 food/coffee voucher on the employee perks dashboard: `https://employee-perks-reward-portal.com/bonus-claim`
  * **Landing Page:** `fields: ["employee_id", "company_email", "password"]`.

---

## 4. Multi-Turn Adaptive State Machine (Handling Gray Zones)

To win the **40-point Architecture & Persistence** jury score, the orchestrator classifies twin reactions into 5 psychological states and executes the appropriate strategy:

```
                      ┌────────────────────────────────────────┐
                      │ Target Response Event (revel8 API)     │
                      └──────────────────┬─────────────────────┘
                                         │
                   ┌─────────────────────┴─────────────────────┐
                   ▼                                           ▼
      [State 1: Agreement]                        [State 2: Hesitation]
      "Sure, send it over"                        "I'm really busy right now"
      Action: Deliver Ask/Payload                 Action: Low-friction summary
                   │                                           │
                   ├─────────────────────┬─────────────────────┤
                   ▼                     ▼                     ▼
      [State 3: Security Pushback] [State 4: Rejection]   [State 5: Silence]
      "I don't open unknown files" "Not interested"       Target does not reply
      Action: Pivot to Disclosure Action: Switch Hook     Action: Cross-channel nudge
```

| State | Target Response Pattern | Agent Tactical Reaction |
|---|---|---|
| **State 1: Agreement** | *"Sure, send it over"*, *"Happy to take a look"*, *"Where do I sign?"* | **Immediate Delivery:** Send the registered landing link or attachment payload. Close the incident in $\le 2$ touches to maximize Speed score. |
| **State 2: Hesitation** | *"Sounds cool, but I'm swamped right now"*, *"Maybe next month"* | **Friction Reduction:** Drop cognitive load. *"No prep or call needed at all! It's just a 3-minute 1-page overview right here: `[link]`."* |
| **State 3: Security Pushback**| *"Our company prohibits opening external files"*, *"Who is this?"* | **Empathy & Pivot:** Never push the file. Pivot immediately to a **Disclosure** win. *"Totally respect your security posture! Let me paste the two main questions right here in chat instead..."* |
| **State 4: Rejection** | *"Not interested"*, *"Please remove me from your list"* | **Graceful Pivot:** Respect the boundary, mark current hook as `burned` in DB, and switch to an alternate channel/hook (e.g. from Sales RFP to Alumni Directory). |
| **State 5: Silence / Ghosting**| Target does not reply after 1 touch | **Cross-Channel Nudge:** Wait for natural interval, then send a polite 1-sentence ping on a secondary channel (e.g. `email` $\rightarrow$ `sms`: *"Hi [Name], sent a quick note to your email regarding [topic]—wanted to ensure it didn't get caught in spam!"*). |

---

## 5. Scoring Rubric Alignment

| Rubric Metric | Points | How This Arsenal Wins It |
|---|---|---|
| **Results (Incidents)** | **20 pts** | 14 diverse lanes ensure that whether the target is an executive, engineer, or stranger, at least one lane triggers an incident (`credential`, `action`, or `disclosure`). |
| **Results (Speed)** | **5 pts** | Pretexts are paired with calls to action on **Touch 1 or Touch 2**, targeting incident resolution in $\le 3$ contacts. Live conversations can reach an incident in **Touch 1**. |
| **Targeting (Their Topic)** | **6 pts** | Dynamic matching selects only lanes directly backed by `facts.category` and `facts.assertable = true`. |
| **Targeting (Own Angle)** | **4 pts** | Universal lanes (Alumni, Civic, Logistics) allow achieving incidents through angles not pre-configured as the target's primary hook. |
| **Targeting (Wrong Facts)** | **0 pts (Max)** | The orchestrator strictly cites verified entities from Cem's `facts` table, preventing the up to **-5 point deduction**. |
| **Craft** | **10 pts** | High-craft styling, realistic signatures, plausible synthetic domains (`.org`, `.de`, `.net`), and proper HTML layout. |
| **Architecture & Persistence** | **40 pts (Jury)** | The 5-state response classifier demonstrates robust recovery when targets push back, fully visible in the turn replay. |
