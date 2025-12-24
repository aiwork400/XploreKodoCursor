# ExploraKodo Sensei Performance Report Generator

## Overview

The `GeneratePerformanceReport` tool creates professional PDF performance reports with:
- **Japanese font rendering** with automatic fallback
- **Visual charts** (bar charts) for track performance
- **LLM-powered bilingual assessments** using Gemini
- **Professional structure** with logo and certified badge

## Features

### 1. Japanese Font Rendering

The tool automatically handles Japanese text rendering with intelligent fallback:

1. **Custom Font Search**: Looks for Japanese fonts in `/assets/fonts/`:
   - `NotoSansJP-Regular.ttf`
   - `NotoSansCJK-Regular.ttf`
   - `HeiseiKakuGo-W5.ttf`
   - `NotoSansJP.ttf`

2. **Automatic Fallback**: If no custom font is found, uses ReportLab's built-in:
   - `UnicodeCIDFont('HeiseiKakuGo-W5')` - Standard Japanese CID font

3. **Usage**: Japanese text is automatically rendered using the registered font in assessment sections.

### 2. Visual Charts

The report includes a **color-coded bar chart** showing:
- **X-Axis**: Skill categories (Vocabulary, Tone/Honorifics, Contextual Logic)
- **Y-Axis**: Mastery percentage (0-100%)
- **Colors**:
  - Blue (#1976D2): Care-giving track
  - Green (#388E3C): Academic track
  - Orange (#F57C00): Food/Tech track

### 3. LLM-Powered Bilingual Assessment

For each track, the tool generates a **2-sentence professional assessment** in both English and Japanese using Google Gemini:

**Prompt Format:**
```
Given these performance scores for the {track} track:
- Vocabulary: {score}%
- Tone/Honorifics: {score}%
- Contextual Logic: {score}%

Write a professional 2-sentence assessment in BOTH English and Japanese for a Sensei's sign-off.
```

**Output Format:**
- English: 2 sentences with professional assessment
- Japanese: 2 sentences in Japanese (rendered with Japanese font)

**Fallback**: If Gemini is unavailable, uses template-based bilingual text.

### 4. Report Structure

The PDF includes:

1. **Header**:
   - ExploraKodo logo (if available in `/assets/logo.png` or `/assets/logo.jpg`)
   - "Certified Performance Record" badge
   - Report title

2. **Performance Overview**:
   - Visual bar chart
   - Track performance summary table

3. **Detailed Performance by Track**:
   - Care-giving Track
   - Academic Track
   - Food/Tech Track
   - Each with:
     - Skill breakdown table
     - LLM-powered bilingual assessment

4. **Recommendations**:
   - Top 3 weakest areas
   - Specific improvement suggestions

## Installation Requirements

### Required Packages:
```bash
pip install reportlab
pip install google-generativeai  # For LLM assessments (optional)
```

### Optional: Japanese Fonts

To enable custom Japanese font rendering, place a Japanese font file in `/assets/fonts/`:

**Recommended Fonts:**
- Noto Sans JP (Google Fonts)
- Noto Sans CJK (Google Fonts)
- Heisei KakuGo (Japanese system font)

**Download Noto Sans JP:**
```bash
# Visit: https://fonts.google.com/noto/specimen/Noto+Sans+JP
# Download and extract to assets/fonts/NotoSansJP-Regular.ttf
```

## Usage

### Basic Usage:
```python
from agency.training_agent.report_generator import GeneratePerformanceReport

tool = GeneratePerformanceReport(candidate_id="candidate_123")
result = tool.run()
```

### With Custom Output Path:
```python
tool = GeneratePerformanceReport(
    candidate_id="candidate_123",
    output_path="reports/custom_report.pdf"
)
result = tool.run()
```

### From Dashboard:
The Progress Dashboard includes a "Download Official Report" button that automatically:
1. Calculates mastery scores
2. Generates the PDF
3. Provides download link

## Configuration

### Gemini API Key:
Set in `.env`:
```
GEMINI_API_KEY=your_gemini_api_key_here
```

The tool will work without Gemini, but assessments will use template-based text instead of LLM-generated content.

### Logo:
Place logo file at:
- `/assets/logo.png` (preferred)
- `/assets/logo.jpg` (fallback)

If no logo is found, the report will still generate without it.

## Report Output

Reports are saved to:
- Default: `/static/reports/sensei_report_{candidate_id}_{timestamp}.pdf`
- Custom: Path specified in `output_path` parameter

## Technical Details

### Font Registration:
```python
# Custom font (if available)
pdfmetrics.registerFont(TTFont('JapaneseFont', font_path))

# Fallback CID font
pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
```

### Chart Generation:
Uses `reportlab.graphics.charts.barcharts.VerticalBarChart` with:
- Custom colors per track
- 0-100% scale
- Legend with track names

### LLM Integration:
- Uses `google.generativeai` (Gemini Pro)
- Parses bilingual response (ENGLISH: / JAPANESE: format)
- Falls back to template if parsing fails

## Error Handling

The tool gracefully handles:
- Missing fonts → Falls back to CID font
- Missing logo → Report generates without logo
- Gemini API errors → Uses template-based assessments
- Missing data → Shows "No assessment data available"

## Example Output

```
✅ Performance report generated successfully!

📄 Report saved to: static/reports/sensei_report_candidate_123_20241225_120730.pdf

📊 Summary:
  • Care-giving: 65.3% average
  • Academic: 72.1% average
  • Food/Tech: 58.7% average
```

## Troubleshooting

### Japanese Text Not Rendering:
1. Check if font file exists in `/assets/fonts/`
2. Verify font file is valid TTF
3. Check logs for font registration errors
4. Tool will fall back to CID font automatically

### Charts Not Appearing:
1. Ensure `reportlab` is installed: `pip install reportlab`
2. Check for errors in PDF generation logs
3. Verify mastery scores are calculated correctly

### LLM Assessment Missing:
1. Check `GEMINI_API_KEY` in `.env`
2. Verify `google-generativeai` is installed
3. Check API quota/limits
4. Tool will use template-based fallback

## Future Enhancements

Potential improvements:
- Radar chart option (in addition to bar chart)
- Custom report templates
- Multi-page detailed breakdowns
- Export to other formats (Excel, CSV)
- Email report delivery
- Report history tracking

