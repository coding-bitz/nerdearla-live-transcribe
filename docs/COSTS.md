# Google Cloud & Gemini Pricing and Cost Estimator

Official pricing figures documented as of September 2026.

---

## 1. Official Pricing Rates

### 1.1 Google Cloud Run (Tier 1, Pay-As-You-Go)
* **vCPU**: `$0.00001800` per vCPU-second
* **Memory**: `$0.00000200` per GiB-second
* **Invocations**: `$0.40` per 1,000,000 requests
* **Monthly Free Tier (Tier 1)**:
  * 180,000 vCPU-seconds
  * 360,000 GiB-seconds
  * 2,000,000 invocations
* *Source*: [Google Cloud Run Pricing](https://cloud.google.com/run/pricing)

### 1.2 Gemini 3.5 Transcribe Live (`gemini-3.5-transcribe-live-preview`)
* **Audio Input**: `$3.50` per 1,000,000 counts
* **Text Output**: `$21.00` per 1,000,000 counts
* **Google Effective Reference Rate**: approximately `~$0.008925` per minute of processed audio.
* *Source*: [Gemini Enterprise Agent Platform Pricing](https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing)

### 1.3 Gemini 3.5 Live Translate (`gemini-3.5-live-translate-preview`)
* **Audio Input**: `$3.50` per 1,000,000 counts
* **Audio Output**: `$21.00` per 1,000,000 counts
* *Source*: [Gemini Enterprise Agent Platform Pricing](https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing)

### 1.4 Gemini 3.5 Flash-Lite (`gemini-3.5-flash-lite`)
*Used for Smart Chapters, Executive Summaries, and Accessibility.*
* **Input Tokens**: `$0.30` per 1,000,000 tokens
* **Output Tokens**: `$2.50` per 1,000,000 tokens
* *Source*: [Gemini Enterprise Agent Platform Pricing](https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing)

---

## 2. Cost Calculation Formulas

```text
Total Cost =
    Transcription Cost
  + Translation Cost (if enabled)
  + Utility Models Cost (Chapters + Summaries + Accessibility)
  + Cloud Run Compute Cost
  + Redis Storage / Networking Cost
```

### Formulas Breakdown

#### Transcription:
$$\text{Transcription Cost} = \text{Audio Minutes} \times \$0.008925$$

#### Translation:
$$\text{Translation Cost} = \left(\frac{\text{Audio Input Counts}}{10^6} \times \$3.50\right) + \left(\frac{\text{Audio Output Counts}}{10^6} \times \$21.00\right)$$

#### Utility Intelligence:
$$\text{Utility Cost} = \left(\frac{\text{Input Tokens}}{10^6} \times \$0.30\right) + \left(\frac{\text{Output Tokens}}{10^6} \times \$2.50\right)$$

#### Cloud Run Compute:
$$\text{Compute Cost} = (\text{vCPU Seconds} \times \$0.00001800) + (\text{GiB Seconds} \times \$0.00000200) + \left(\frac{\text{Requests}}{10^6} \times \$0.40\right)$$

---

## 3. Illustrative Scenario Estimate (Conference Example)

> **Important Note:** This table represents an **illustrative scenario** and does not constitute a fixed billing guarantee. Real costs depend on spoken words per minute, exact token length, and Cloud Run network egress.

| Variable | Value | Notes |
|---|---:|---|
| Total Sessions | 100 | Conference technical talks |
| Duration per Session | 45 min | Total: 4,500 audio minutes |
| Sessions with Live Translation | 100 | Simultaneous speech translation |
| Chapter Evaluations | ~90 per session | Every 30s during talk (9,000 calls total) |
| Executive Summaries | 1 per session | 100 total summary runs |
| Accessibility Requests | 20 per session | On-demand enhancements (2,000 calls total) |
| Cloud Run Backend Allocation | 1 vCPU / 1 GiB | Scaled to match concurrent traffic |

### Estimated Scenario Breakdown

| Component | Calculation Basis | Estimated Cost |
|---|---|---:|
| **Live Transcription** | 4,500 minutes $\times$ ~$0.008925 / min | ~$40.16 |
| **Live Translation** | 4,500 minutes speech-to-speech processing | ~$110.00 |
| **Chapters (Flash-Lite)** | 9,000 calls $\times$ (~800 in / ~30 out tokens) | ~$2.84 |
| **Summaries (Flash-Lite)** | 100 calls $\times$ (~6,000 in / ~600 out tokens) | ~$0.33 |
| **Accessibility (Flash-Lite)** | 2,000 calls $\times$ (~300 in / ~60 out tokens) | ~$0.48 |
| **Cloud Run Compute** | 4,500 active instance-minutes (270k sec) minus Free Tier | ~$3.60 |
| **Total Estimated Scenario** | | **~$157.41** |

---

## 4. Key Factors in Actual Billing

1. **Audio Rate**: Pauses and silence produce fewer output tokens, lowering cost.
2. **Translation Activation**: If translation is disabled, translation audio costs drop to `$0.00`.
3. **Cloud Run Inactivity**: When no sessions are active and `min-instances=0`, compute cost is `$0.00`.
4. **Managed Redis**: Google Cloud Memorystore for Redis incurs separate instance pricing if used instead of self-hosted container.
