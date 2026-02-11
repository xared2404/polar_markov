# Polar Markov Report

## Divergence (KL)
- KL(conservative || liberal): 4.0319
- KL(liberal || conservative): 3.9446

## CONSERVATIVE
- Sequences: 49
- Mean entropy: 2.432
- Mean loop: 0.153

### Top transitions
- S13 → S13: 0.411
- S0 → S0: 0.379
- S2 → S2: 0.286
- S1 → S1: 0.277
- S2 → S1: 0.250
- S4 → S1: 0.235
- S8 → S1: 0.226
- S1 → S0: 0.213
- S0 → S8: 0.212
- S3 → S8: 0.211
- S4 → S0: 0.206
- S7 → S6: 0.200

## LIBERAL
- Sequences: 34
- Mean entropy: 2.549
- Mean loop: 0.131

### Top transitions
- S12 → S12: 0.295
- S11 → S13: 0.238
- S0 → S0: 0.234
- S6 → S0: 0.233
- S13 → S13: 0.217
- S5 → S5: 0.206
- S6 → S6: 0.200
- S1 → S1: 0.172
- S2 → S2: 0.171
- S4 → S2: 0.167
- S10 → S1: 0.150
- S14 → S6: 0.150

## Actor-level Markov availability
- Saved actor matrices: 4 (min_seqs=5)

## Most rigid actors (low mean entropy)
- [conservative] Fox News | seqs=24 | mean_entropy=2.458 | mean_loop=0.135
- [liberal] Jacobin | seqs=18 | mean_entropy=2.585 | mean_loop=0.116
- [conservative] Fox News (US RSS) | seqs=25 | mean_entropy=2.621 | mean_loop=0.105
- [liberal] The Intercept | seqs=16 | mean_entropy=2.639 | mean_loop=0.101
