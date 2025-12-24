# ExploraKodo Global Rebrand & Feature Updates

## Overview

This document describes the global rebrand from 'XploreKodo' to 'ExploraKodo' and the implementation of new features including welcome videos and performance report generation.

## Changes Implemented

### 1. Global Rebrand: XploreKodo → ExploraKodo

**Files Updated:**
- `dashboard/app.py`: All UI text, titles, and messages
- `assets/style.css`: CSS comments and branding

**Changes:**
- Main header: "ExploraKodo Global Command Center"
- Concierge Widget: "ExploraKodo Concierge"
- All welcome messages and platform references
- Error messages and user-facing text

**Note**: Some backend files (config.py, database files) may still contain 'XploreKodo' references for backward compatibility. These can be updated in a future migration if needed.

### 2. Welcome Video Integration

**Location**: Concierge Widget (Assistant Widget)

**Features:**
- Replaces static emoji/avatar with `st.video` component
- Language-based video selection:
  - English: `assets/videos/intro/intro_en.mp4`
  - Japanese: `assets/videos/intro/intro_jp.mp4`
  - Nepali: `assets/videos/intro/intro_ne.mp4`
- Auto-plays when widget is first activated
- Falls back to welcome message if video file not found

**Implementation:**
- Video plays only when `concierge_messages` is empty (first visit)
- Video path updates automatically when language is changed
- Video autoplays with `autoplay=True` parameter

**Video File Requirements:**
- Format: MP4 (recommended), WebM, or OGG
- Duration: ~1 minute (as specified)
- Location: `assets/videos/intro/`
- Naming: `intro_en.mp4`, `intro_jp.mp4`, `intro_ne.mp4`

### 3. Performance Report Generator

**Location**: `agency/training_agent/report_generator.py`

**Tool**: `GeneratePerformanceReport`

**Features:**
- Pulls data from Mastery Heatmap logic (`calculate_mastery_scores`)
- Generates PDF "Sensei Performance Report"
- Summarizes JLPT N5-N3 progress across three tracks:
  - Care-giving
  - Academic
  - Food/Tech
- Includes:
  - Executive Summary
  - Track Performance Summary (overall scores)
  - Detailed Performance by Track (skill breakdown)
  - Recommendations (weakest areas)
  - Professional formatting with ExploraKodo branding

**Dependencies:**
```bash
pip install reportlab
```

**Usage:**
```python
from agency.training_agent.report_generator import GeneratePerformanceReport

tool = GeneratePerformanceReport(candidate_id="candidate_123")
result = tool.run()  # Generates PDF and returns path
```

**Output:**
- PDF saved to `static/reports/sensei_report_{candidate_id}_{timestamp}.pdf`
- Includes candidate name, report date, and comprehensive performance analysis

### 4. Download Button in Progress Tab

**Location**: Progress Dashboard (`show_progress_dashboard()`)

**Features:**
- "📥 Download Official Report" button
- Generates PDF on-demand
- Provides download via Streamlit's `st.download_button`
- Shows generation status and summary
- Error handling with helpful messages

**User Flow:**
1. User navigates to Progress tab
2. Selects candidate
3. Views heatmap and recommendations
4. Clicks "Download Official Report"
5. PDF is generated and download button appears
6. User downloads the report

## File Structure

```
assets/
├── style.css                    # Updated branding
└── videos/
    └── intro/                   # Welcome videos
        ├── intro_en.mp4
        ├── intro_jp.mp4
        └── intro_ne.mp4

agency/training_agent/
└── report_generator.py          # NEW: PDF report generator

dashboard/
└── app.py                       # Updated: Rebrand + video + download button

static/
└── reports/                     # Generated PDF reports
    └── sensei_report_*.pdf
```

## Installation Requirements

### For PDF Report Generation:
```bash
pip install reportlab
```

### For Video Playback:
- No additional dependencies (Streamlit native support)
- Ensure video files are in correct format (MP4 recommended)

## Testing Checklist

### Rebrand Verification:
- [ ] Main dashboard header shows "ExploraKodo"
- [ ] Concierge widget shows "ExploraKodo Concierge"
- [ ] All welcome messages use "ExploraKodo"
- [ ] CSS comments updated

### Welcome Video:
- [ ] Video plays when widget first loads
- [ ] Video changes when language is switched
- [ ] Fallback message appears if video not found
- [ ] Video autoplays correctly

### Performance Report:
- [ ] Report generator tool imports successfully
- [ ] PDF generates without errors
- [ ] Download button appears in Progress tab
- [ ] PDF contains correct data from mastery scores
- [ ] PDF formatting is professional and readable

## Known Limitations

1. **ReportLab Dependency**: PDF generation requires `reportlab` package. If not installed, user will see a helpful error message.

2. **Video Files**: Video files must be manually added to `assets/videos/intro/`. The system will fall back to text messages if videos are not found.

3. **Backend References**: Some backend files (database, config) may still reference 'XploreKodo' for backward compatibility. These don't affect the UI.

## Future Enhancements

1. **Multi-language Reports**: Generate reports in Japanese and Nepali
2. **Report Customization**: Allow users to select date ranges
3. **Email Reports**: Automatically email reports to candidates
4. **Report History**: Track and display previously generated reports
5. **Video Thumbnails**: Show video thumbnails before playback

## Migration Notes

If you need to update backend references to 'ExploraKodo':
1. Update `config.py` if brand name is used in configuration
2. Update database comments if needed
3. Update API documentation
4. Update any external integrations

The UI rebrand is complete and functional. Backend references can be updated gradually without breaking functionality.

