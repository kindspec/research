# Real ID schemes embedded in a real markdown line

Baseline (no id), 56 chars:

```
The reactor scram threshold is 4.2 sigma above baseline.
```

Obsidian `^id` at end of block:

```
The reactor scram threshold is 4.2 sigma above baseline. ^7c475260-a227-4869-a31f-cb5f341b6ffe
The reactor scram threshold is 4.2 sigma above baseline. ^01a049a2-7411-7e3e-9fc6-d2767a44c46b
The reactor scram threshold is 4.2 sigma above baseline. ^01K3F9Q7ZPWXWCBYB6WK952SWA
The reactor scram threshold is 4.2 sigma above baseline. ^D0Rx432cUfC1NtksBRcxeEiv0G5
The reactor scram threshold is 4.2 sigma above baseline. ^xht5gmej146s6jr410dd
The reactor scram threshold is 4.2 sigma above baseline. ^4WKMP7nwF9BE-Odfta-5V
The reactor scram threshold is 4.2 sigma above baseline. ^YkmTmePLcMPp
The reactor scram threshold is 4.2 sigma above baseline. ^_wA0olMa
The reactor scram threshold is 4.2 sigma above baseline. ^w46qwxdkzw
The reactor scram threshold is 4.2 sigma above baseline. ^w46qwx
The reactor scram threshold is 4.2 sigma above baseline. ^29dsg0
The reactor scram threshold is 4.2 sigma above baseline. ^scram-threshold
```

| scheme | chars | id | line len | % overhead |
|---|---|---|---|---|
| UUIDv4 | 36 | `7c475260-a227-4869-a31f-cb5f341b6ffe` | 94 | 68% |
| UUIDv7 | 36 | `01a049a2-7411-7e3e-9fc6-d2767a44c46b` | 94 | 68% |
| ULID | 26 | `01K3F9Q7ZPWXWCBYB6WK952SWA` | 84 | 50% |
| KSUID | 27 | `D0Rx432cUfC1NtksBRcxeEiv0G5` | 85 | 52% |
| xid | 20 | `xht5gmej146s6jr410dd` | 78 | 39% |
| NanoID-21 | 21 | `4WKMP7nwF9BE-Odfta-5V` | 79 | 41% |
| NanoID-12 | 12 | `YkmTmePLcMPp` | 70 | 25% |
| NanoID-8 | 8 | `_wA0olMa` | 66 | 18% |
| base32 sha256-10 | 10 | `w46qwxdkzw` | 68 | 21% |
| base32 sha256-6 | 6 | `w46qwx` | 64 | 14% |
| Obsidian-style | 6 | `29dsg0` | 64 | 14% |
| human slug | 15 | `scram-threshold` | 73 | 30% |

Logseq `id::` on its own line (a whole extra line per block):

```
- The reactor scram threshold is 4.2 sigma above baseline.
  id:: 6f21512d-0b71-40a6-89d2-0b37e895d699
  collapsed:: true
```

Pandoc/kramdown attribute syntax (not CommonMark):

```
The reactor scram threshold is 4.2 sigma above baseline. {#b-NDlRio}

## Safety limits {#safety-limits}
```

HTML-comment carrier (invisible in every renderer, survives GFM):

```
The reactor scram threshold is 4.2 sigma above baseline. <!--#445dBE-->
```

## Collision probability of ANY collision among n=10^6 ids

Birthday bound  p ~= 1 - exp(-n(n-1)/(2N))  with N = alphabet^len

| scheme | bits | N | p(collision) at 10^6 | expected dup count |
|---|---|---|---|---|
| UUIDv4 | 122 | 2^122 | 0 | 9.4e-26 |
| UUIDv7 (rand part) | 74 | 2^74 | 2.65e-11 | 2.65e-11 |
| ULID (rand part) | 80 | 2^80 | 4.14e-13 | 4.14e-13 |
| NanoID-21 | 126 | 2^126 | 0 | 5.88e-27 |
| NanoID-12 | 72 | 2^72 | 1.06e-10 | 1.06e-10 |
| NanoID-10 | 60 | 2^60 | 4.34e-07 | 4.34e-07 |
| NanoID-8 | 48 | 2^48 | 0.00177 | 0.00178 |
| base32 hash-10 | 50 | 2^50 | 0.000444 | 0.000444 |
| base32 hash-8 | 40 | 2^40 | 0.365 | 0.455 |
| base32 hash-6 | 30 | 2^30 | 1 | 466 |
| base62-6 (Obsidian-ish) | 36 | 2^36 | 1 | 8.8 |
| base36-6 | 31 | 2^31 | 1 | 230 |
| base62-4 | 24 | 2^24 | 1 | 3.38e+04 |
