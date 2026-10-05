# ZIP code bench leaderboard

Exact 5-digit ZIP accuracy. Tiers: **easy** = town has 1 ZIP, **medium** = city has 2-9 ZIPs, **hard** = city has 10+ ZIPs.
Generated from `summary.csv`; latest run per model in each sample. Runs with failed requests are left out.

## 40 per tier, seed 7

| # | model | exact | easy | medium | hard | first 3 digits | cost | details |
|---|---|---|---|---|---|---|---|---|
| 1 | openai/gpt-6.1-sol | **84.2%** | 100.0% | 82.5% | 70.0% | 100.0% | $0.1185 | [log](runs/20261004-145212_openai_gpt-6.1-sol_default_n120_s7.jsonl) |
| 2 | google/gemini-3.8-flash | **84.2%** | 92.5% | 90.0% | 70.0% | 99.2% | $0.2170 | [log](runs/20261004-140900_google_gemini-3.8-flash_default_n120_s7.jsonl) |
| 3 | openai/gpt-6-luna | **75.0%** | 95.0% | 85.0% | 45.0% | 99.2% | $0.0120 | [log](runs/20261004-140943_openai_gpt-6-luna_default_n120_s7.jsonl) |
| 4 | google/gemini-3.1-flash-lite | **71.7%** | 95.0% | 75.0% | 45.0% | 99.2% | $0.0027 | [log](runs/20261004-140907_google_gemini-3.1-flash-lite_default_n120_s7.jsonl) |
| 5 | deepseek/deepseek-v4.1-flash | **69.2%** | 90.0% | 80.0% | 37.5% | 95.0% | $0.1886 | [log](runs/20261004-144735_deepseek_deepseek-v4.1-flash_default_n120_s7.jsonl) |
| 6 | qwen/qwen3.8-max-0902 | **67.5%** | 92.5% | 80.0% | 30.0% | 96.7% | $1.5972 | [log](runs/20261004-150809_qwen_qwen3.8-max-0902_default_n120_s7.jsonl) |
| 7 | x-ai/grok-4.7 | **66.7%** | 95.0% | 67.5% | 37.5% | 96.7% | $0.3314 | [log](runs/20261004-145354_x-ai_grok-4.7_default_n120_s7.jsonl) |
| 8 | anthropic/claude-sonnet-5.5 | **65.0%** | 92.5% | 67.5% | 35.0% | 98.3% | $0.2225 | [log](runs/20261004-145129_anthropic_claude-sonnet-5.5_default_n120_s7.jsonl) |
| 9 | z-ai/glm-5.3 | **60.8%** | 85.0% | 70.0% | 27.5% | 96.7% | $0.4133 | [log](runs/20261004-150941_z-ai_glm-5.3_default_n120_s7.jsonl) |
| 10 | mistralai/mistral-small-2603 | **57.5%** | 85.0% | 72.5% | 15.0% | 97.5% | $0.0018 | [log](runs/20261004-141003_mistralai_mistral-small-2603_default_n120_s7.jsonl) |
| 11 | z-ai/glm-5.3-flash | **55.8%** | 90.0% | 65.0% | 12.5% | 93.3% | $0.0350 | [log](runs/20261004-144436_z-ai_glm-5.3-flash_default_n120_s7.jsonl) |
| 12 | anthropic/claude-haiku-4.5 | **55.0%** | 77.5% | 60.0% | 27.5% | 92.5% | $0.0134 | [log](runs/20261004-140957_anthropic_claude-haiku-4.5_default_n120_s7.jsonl) |
| 13 | openai/gpt-5.4-nano | **54.2%** | 72.5% | 70.0% | 20.0% | 90.8% | $0.0024 | [log](runs/20261004-140950_openai_gpt-5.4-nano_default_n120_s7.jsonl) |
| 14 | qwen/qwen3.8-flash | **50.0%** | 72.5% | 60.0% | 17.5% | 93.3% | $0.0959 | [log](runs/20261004-141646_qwen_qwen3.8-flash_default_n120_s7.jsonl) |
| 15 | google/gemma-4-31b-it | **20.8%** | 17.5% | 35.0% | 10.0% | 81.7% | $0.0033 | [log](runs/20261004-141009_google_gemma-4-31b-it_default_n120_s7.jsonl) |

## 40 random, seed 42

| # | model | exact | easy | medium | hard | first 3 digits | cost | details |
|---|---|---|---|---|---|---|---|---|
| 1 | google/gemini-3.8-flash | **87.5%** | 100.0% | 84.6% | 66.7% | 100.0% | $0.0676 | [log](runs/20261004-134952_google_gemini-3.8-flash_default_n40_s42.jsonl) |
| 2 | google/gemini-3.1-flash-lite | **87.5%** | 100.0% | 92.3% | 55.6% | 100.0% | $0.0009 | [log](runs/20261004-135032_google_gemini-3.1-flash-lite_default_n40_s42.jsonl) |
| 3 | openai/gpt-6-luna | **75.0%** | 100.0% | 76.9% | 22.2% | 100.0% | $0.0034 | [log](runs/20261004-135024_openai_gpt-6-luna_default_n40_s42.jsonl) |
| 4 | deepseek/deepseek-v4.1-flash | **75.0%** | 100.0% | 76.9% | 22.2% | 95.0% | $0.0481 | [log](runs/20261004-135614_deepseek_deepseek-v4.1-flash_default_n40_s42.jsonl) |
| 5 | mistralai/mistral-small-2603 | **67.5%** | 94.4% | 69.2% | 11.1% | 100.0% | $0.0006 | [log](runs/20261004-140121_mistralai_mistral-small-2603_default_n40_s42.jsonl) |
| 6 | anthropic/claude-haiku-4.5 | **65.0%** | 88.9% | 76.9% | 0.0% | 95.0% | $0.0041 | [log](runs/20261004-135003_anthropic_claude-haiku-4.5_default_n40_s42.jsonl) |
| 7 | z-ai/glm-5.3-flash | **62.5%** | 100.0% | 53.8% | 0.0% | 100.0% | $0.0067 | [log](runs/20261004-140116_z-ai_glm-5.3-flash_default_n40_s42.jsonl) |
| 8 | qwen/qwen3.8-flash | **57.5%** | 72.2% | 69.2% | 11.1% | 95.0% | $0.0187 | [log](runs/20261004-135903_qwen_qwen3.8-flash_default_n40_s42.jsonl) |
| 9 | openai/gpt-5.4-nano | **57.5%** | 72.2% | 61.5% | 22.2% | 87.5% | $0.0008 | [log](runs/20261004-135028_openai_gpt-5.4-nano_default_n40_s42.jsonl) |
| 10 | google/gemma-4-31b-it | **25.0%** | 22.2% | 38.5% | 11.1% | 82.5% | $0.0006 | [log](runs/20261004-140128_google_gemma-4-31b-it_default_n40_s42.jsonl) |
