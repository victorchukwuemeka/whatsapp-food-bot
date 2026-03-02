# 🤖 Brida — Agentic Food Ordering WhatsApp Bot

## System Architecture

```
USER (WhatsApp)
     |
     | sends message
     ▼
┌─────────────────────────┐
│     BRIDA BOT           │  ◄── WhatsApp API (Twilio / Meta Cloud API)
│  (Orchestrator Agent)   │
└─────────────────────────┘
     |              |
     |              |
     ▼              ▼
┌──────────┐   ┌──────────────────────┐
│RESTAURANT│   │    RIDER AGENT       │
│  AGENT   │   │  (Negotiation Bot)   │
│          │   │                      │
│ - Menu   │   │ - Base delivery fee  │
│ - Price  │   │ - Accepts offers     │
│ (FIXED)  │   │ - Makes counteroffers│
│          │   │ - Min price floor    │
└──────────┘   └──────────────────────┘
     |                   |
     | fixed price       | negotiated fee
     ▼                   ▼
┌─────────────────────────────────────┐
│           ORDER SUMMARY             │
│                                     │
│  Food Total  : $XX.XX  (fixed)      │
│  Delivery Fee: $X.XX   (negotiated) │
│  ─────────────────────────────────  │
│  Grand Total : $XX.XX               │
└─────────────────────────────────────┘
     |
     ▼
USER confirms --> ORDER PLACED ✅
```

---

## Flow Breakdown

```
1. USER sends order --> BRIDA receives it
         |
         ▼
2. RESTAURANT AGENT confirms items + fixed price
         |
         ▼
3. RIDER AGENT proposes initial delivery fee
         |
         ▼
4. USER negotiates <--> RIDER AGENT (back & forth)
         |
         ▼
5. Deal reached --> BRIDA compiles final order
         |
         ▼
6. USER confirms --> ORDER DISPATCHED
```

---

## Agents Overview

| Agent               | Role                          | Price Control |
|---------------------|-------------------------------|---------------|
| Orchestrator (Brida)| Manages flow & conversation   | —             |
| Restaurant Agent    | Serves menu & order details   | FIXED         |
| Rider Agent         | Negotiates delivery fee       | FLEXIBLE      |
```
