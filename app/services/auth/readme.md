                    ┌─────────────────────┐
                    │    OTP API Router   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │     OTP Service     │
                    │                     │
                    │ generate / verify   │
                    │ rate limit / store │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Notification Service│
                    └──────────┬──────────┘
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
             ┌──────────────┐      ┌──────────────┐
             │ SMS Provider │      │WhatsApp      │
             │   Strategy   │      │ Provider     │
             └──────┬───────┘      └──────┬───────┘
                    │                     │
          ┌─────────┼─────────┐           │
          ▼         ▼         ▼           ▼
       Twilio    MSG91     Gupshup      Twilio
       SMS       SMS       SMS          WhatsApp