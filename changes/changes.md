Update src/ui/components.py — color values only:

━━━━━━━━━━━━━━━━
make_card()
━━━━━━━━━━━━━━━━
bg = BG_SURFACE
Optional left accent bar:
  Was: colored (ACCENT_BLUE, ACCENT_RED etc.)
  Now: BORDER_STRONG (#444444) for all cards regardless of context
  Active/highlighted card: BORDER_WHITE (#ffffff)

━━━━━━━━━━━━━━━━
make_metric_card()
━━━━━━━━━━━━━━━━
bg = BG_SURFACE
Left border: BORDER_STRONG (#444444)
LABEL  fg = TEXT_SECONDARY (#a0a0a0)
VALUE  fg = TEXT_PRIMARY   (#ffffff)
UNIT   fg = TEXT_MUTED     (#555555)

━━━━━━━━━━━━━━━━
make_button() styles
━━━━━━━━━━━━━━━━
"primary":
  bg = "#ffffff"
  fg = "#000000"  (TEXT_INVERSE)
  activebackground = "#e0e0e0"
  font = FONT_SUBHEAD

"danger":
  bg = "#ffffff"
  fg = "#000000"
  activebackground = "#e0e0e0"
  (danger is now conveyed by context/label, not red color)

"success":
  bg = "#ffffff"
  fg = "#000000"
  activebackground = "#e0e0e0"

"ghost":
  bg = BG_ELEVATED  (#141414)
  fg = TEXT_PRIMARY (#ffffff)
  activebackground = BG_HOVER (#1e1e1e)
  relief = FLAT
  border = 1px BORDER_DEFAULT (#2e2e2e)

"disabled":
  bg = BG_ELEVATED (#141414)
  fg = TEXT_MUTED  (#555555)
  relief = FLAT

━━━━━━━━━━━━━━━━
make_tag()
━━━━━━━━━━━━━━━━
All tags regardless of passed color:
  bg = BG_ELEVATED  (#141414)
  fg = TEXT_SECONDARY (#a0a0a0)
  
Special tag variants:
  "active" tag (e.g. selected mode, success state):
    bg = "#ffffff"
    fg = "#000000"
  
  "muted" tag (placeholder state):
    bg = BG_SURFACE (#0a0a0a)
    fg = TEXT_MUTED (#555555)
    border = BORDER_SUBTLE (#1e1e1e)

━━━━━━━━━━━━━━━━
make_divider()
━━━━━━━━━━━━━━━━
bg = BORDER_DEFAULT (#2e2e2e)  ← unchanged, already neutral

━━━━━━━━━━━━━━━━
make_log_window()
━━━━━━━━━━━━━━━━
bg = BG_BASE    (#000000)
fg = TEXT_PRIMARY (#ffffff)    ← was ACCENT_GREEN
insertbackground = TEXT_PRIMARY

Log line tags (color removed, use weight/brightness instead):
  CTR lines:   fg = "#ffffff"  (bright white)
  GCM lines:   fg = "#ffffff"  (bright white)
  Info lines:  fg = "#555555"  (muted grey)
  Error lines: fg = "#ffffff"  font=bold  (white bold)
  
  Prefix tags still present for identification:
  "[CTR]" and "[GCM]" — no longer colored, just white

━━━━━━━━━━━━━━━━
make_progress_bar()
━━━━━━━━━━━━━━━━
Label fg = TEXT_SECONDARY (#a0a0a0)
ttk.Progressbar styling:
  trough   = BG_ELEVATED (#141414)
  fill bar = TEXT_PRIMARY (#ffffff)

━━━━━━━━━━━━━━━━
make_status_indicator()
━━━━━━━━━━━━━━━━
All status dots → monochrome:
  "success" → dot fg="#ffffff"  text fg=TEXT_PRIMARY
  "warning" → dot fg="#888888"  text fg=TEXT_SECONDARY
  "error"   → dot fg="#ffffff"  text fg=TEXT_PRIMARY  font=bold
  "neutral" → dot fg="#555555"  text fg=TEXT_MUTED

In app_window.py — tab bar only:

Active tab:
  bg = BG_ELEVATED  (#141414)
  fg = TEXT_PRIMARY (#ffffff)
  Bottom border: 2px solid #ffffff   ← white underline, was ACCENT_BLUE

Inactive tab:
  bg = BG_SURFACE   (#0a0a0a)
  fg = TEXT_MUTED   (#555555)
  No bottom border

Hover:
  bg = BG_ELEVATED  (#141414)
  fg = TEXT_SECONDARY (#a0a0a0)

Header bar:
  "ENTROPY" text: was ACCENT_BLUE → now TEXT_PRIMARY (#ffffff)
  Tags in header: use "ghost" style tags (bg=BG_ELEVATED fg=TEXT_SECONDARY)

In app_window.py — header bar:

bg = BG_SURFACE (#0a0a0a)
Bottom border: 1px BORDER_DEFAULT (#2e2e2e)

"🔐" icon:          fg = TEXT_PRIMARY (#ffffff)
"ENTROPY" title:    fg = TEXT_PRIMARY (#ffffff)   was ACCENT_BLUE
Divider:            bg = BORDER_DEFAULT (#2e2e2e)
Subtitle:           fg = TEXT_SECONDARY (#a0a0a0)

Right side tags:    all use ghost/muted tag style
  bg = BG_ELEVATED (#141414)
  fg = TEXT_SECONDARY (#a0a0a0)

Status bar:
  bg = BG_SURFACE (#0a0a0a)
  Top border: 1px BORDER_DEFAULT (#2e2e2e)
  Status text: TEXT_SECONDARY (#a0a0a0)
  Right text:  TEXT_MUTED (#555555)