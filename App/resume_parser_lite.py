"""
Resume parser using pdfminer layout API for positional text extraction.
Sorts text elements by Y-coordinate so the first element is always
the visually topmost content (i.e., the person's name).
"""

import re
import io
from pdfminer.high_level import extract_text_to_fp, extract_text, extract_pages
from pdfminer.layout import LAParams, LTTextBox, LTTextLine


# ─── Skills database ──────────────────────────────────────────────────────────

SKILLS_DB = [
    'python', 'java', 'javascript', 'js', 'c++', 'c#', 'ruby', 'go', 'swift',
    'kotlin', 'php', 'typescript', 'scala', 'r', 'matlab', 'perl', 'rust', 'dart',
    'html', 'css', 'react', 'react js', 'angular', 'angular js', 'vue', 'vue js',
    'node', 'node js', 'nodejs', 'express', 'django', 'flask', 'fastapi', 'spring',
    'asp.net', 'laravel', 'wordpress', 'magento', 'bootstrap', 'jquery',
    'penetration testing', 'vulnerability assessment', 'siem', 'wireshark', 'nmap',
    'burp suite', 'metasploit', 'threat detection', 'incident response',
    'network security', 'ethical hacking', 'cryptography', 'intrusion detection',
    'tesseract', 'ocr',
    'machine learning', 'deep learning', 'tensorflow', 'keras', 'pytorch', 'scikit-learn',
    'pandas', 'numpy', 'matplotlib', 'seaborn', 'plotly', 'nlp', 'computer vision',
    'data science', 'data analysis', 'data visualization', 'statistical modeling',
    'data mining', 'predictive analysis', 'neural networks', 'transformers',
    'sql', 'mysql', 'postgresql', 'sqlite', 'mongodb', 'redis', 'cassandra',
    'firebase', 'oracle', 'nosql', 'dbms',
    'aws', 'azure', 'gcp', 'google cloud', 'docker', 'kubernetes', 'jenkins',
    'terraform', 'ansible', 'ci/cd', 'git', 'github', 'gitlab', 'linux',
    'android', 'android development', 'flutter', 'kotlin', 'xml', 'kivy',
    'ios', 'ios development', 'swift', 'cocoa', 'xcode', 'objective-c',
    'figma', 'adobe xd', 'sketch', 'zeplin', 'balsamiq', 'photoshop',
    'illustrator', 'after effects', 'ui', 'ux', 'prototyping', 'wireframes',
    'agile', 'scrum', 'jira', 'rest api', 'graphql', 'microservices',
    'streamlit', 'hadoop', 'spark', 'power bi', 'tableau', 'excel',
    'full stack', 'full-stack', 'object oriented', 'oop', 'system design',
    'normalization', 'algorithms', 'data structures', 'blockchain', 'web3',
]

# ─── Regex patterns ───────────────────────────────────────────────────────────

# TLD lowercase-only: stops at .com before uppercase LINKS/GITHUB etc.
EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-z]{2,6}(?![a-z])')

PHONE_RE = re.compile(
    r'(?:\+91[\-\s]?)?(?:\d{5}[\-\s]?\d{5}|\d{10}|\(\d{3}\)\s?\d{3}[\-\s]?\d{4}|\d{3}[\-\s]?\d{3}[\-\s]?\d{4})'
)

DEGREE_RE = re.compile(
    r'\b(B\.?\s*Tech|M\.?\s*Tech|B\.?\s*E\b|M\.?\s*E\b|B\.?\s*Sc|M\.?\s*Sc|'
    r'B\.?\s*Com|M\.?\s*Com|BCA|MCA|B\.?\s*A\b|M\.?\s*A\b|MBA|PhD|Ph\.?\s*D|'
    r'Bachelor|Master|Associate|Diploma)\b',
    re.IGNORECASE
)

# Non-name words for filtering
SKIP_WORDS = {
    'contact', 'links', 'github', 'linkedin', 'skills', 'experience',
    'education', 'projects', 'certifications', 'achievements', 'internship',
    'languages', 'profile', 'summary', 'objective', 'address', 'phone',
    'email', 'mobile', 'analyst', 'engineer', 'developer', 'manager',
    'intern', 'student', 'undergraduate', 'science', 'technology',
    'information', 'computer', 'engineering', 'cyber', 'security',
    'hackathon', 'india', 'smart', 'system', 'specialist',
}


# ─── PDF layout extraction (sorted by Y position) ────────────────────────────

def _get_page1_lines_by_position(pdf_path: str) -> list:
    """
    Extract text lines from page 1 sorted top-to-bottom by Y coordinate.
    This is the most reliable way to get the name — it's always visually first.
    Returns list of (y_from_top, text) tuples sorted ascending (top first).
    """
    lines = []
    try:
        laparams = LAParams(line_margin=0.5, word_margin=0.1)
        for page_layout in extract_pages(pdf_path, laparams=laparams):
            page_height = page_layout.height
            for element in page_layout:
                if isinstance(element, LTTextBox):
                    for line in element:
                        if isinstance(line, LTTextLine):
                            text = line.get_text().strip()
                            if text:
                                # y_from_top: smaller = higher on page
                                y_from_top = page_height - line.y1
                                lines.append((round(y_from_top, 1), text))
            break  # only first page
    except Exception:
        pass
    lines.sort(key=lambda x: x[0])  # sort top-to-bottom
    return lines


def extract_text_from_pdf(pdf_path: str) -> str:
    """Fallback full-text extraction."""
    try:
        laparams = LAParams(line_margin=0.3, word_margin=0.1, boxes_flow=None)
        text = extract_text(pdf_path, laparams=laparams)
        if text and len(text.strip()) > 20:
            return text
    except Exception:
        pass
    output = io.StringIO()
    with open(pdf_path, 'rb') as f:
        extract_text_to_fp(f, output, laparams=LAParams(), output_type='text', codec='utf-8')
    return output.getvalue()


def count_pages(pdf_path: str) -> int:
    try:
        return sum(1 for _ in extract_pages(pdf_path))
    except Exception:
        return 1


# ─── Name extraction using positional lines ──────────────────────────────────

def _name_from_text(text: str) -> str:
    """
    Try to extract a person's name from a single line of text.
    Handles: 'Deepesh Kumar Mahawar, Cyber Security Analyst'
             'DEEPESH KUMAR MAHAWAR'
             'Deepesh Kumar Mahawar'
             'Stuti Agrawal'
    """
    t = EMAIL_RE.sub('', text)
    t = PHONE_RE.sub('', t)
    t = re.sub(r'\d+', '', t)
    t = t.strip()

    # Split on comma — name is before the comma
    candidate = t.split(',')[0].strip()
    # Split on '|' or '-' too (some resumes: 'Name | Job Title')
    candidate = re.split(r'[|\-–—]', candidate)[0].strip()

    # Normalize to Title-Case (handles ALL-CAPS bold text)
    candidate = candidate.title()

    words = candidate.split()
    if not (2 <= len(words) <= 5):
        return ''
    # All words must be alphabetic
    if not all(re.match(r'^[A-Za-z]+$', w) for w in words):
        return ''
    # Must not contain skip words
    if any(w.lower() in SKIP_WORDS for w in words):
        return ''
    return candidate


def _extract_name_from_lines(positional_lines: list) -> str:
    """Walk positional lines (top→bottom) and try each as a name."""
    for _, line_text in positional_lines[:8]:
        name = _name_from_text(line_text)
        if name:
            return name
    return ''


def _extract_name_from_raw(raw_text: str) -> str:
    """
    Fallback name extraction from raw text.
    Key insight: the email is always in the header near the name.
    So we look at text BEFORE the first email occurrence.
    """
    # Strategy A: find email, take text before it, look for name
    email_match = EMAIL_RE.search(raw_text)
    if email_match:
        pre_email = raw_text[:email_match.start()]
        # Split into lines, try each going backwards (closest to email first)
        lines = [l.strip() for l in re.split(r'[\n\r|,;]+', pre_email) if l.strip()]
        for line in reversed(lines[-10:]):
            name = _name_from_text(line)
            if name:
                return name
        # Also try from the beginning
        for line in lines[:5]:
            name = _name_from_text(line)
            if name:
                return name

    # Strategy B: scan first 200 chars of raw text line by line
    for line in re.split(r'[\n\r]+', raw_text[:300]):
        line = line.strip()
        if not line:
            continue
        name = _name_from_text(line)
        if name:
            return name

    return 'Unknown'


# ─── Section-break injection for raw text ────────────────────────────────────

SECTION_KEYWORDS_CAPS = [
    'LINKS', 'CONTACT', 'SKILLS', 'EDUCATION', 'EXPERIENCE', 'SUMMARY',
    'PROJECTS', 'CERTIFICATIONS', 'ACHIEVEMENTS', 'INTERNSHIP', 'OBJECTIVE',
    'LANGUAGES', 'PROFILE', 'HOBBIES', 'INTERESTS',
]


def _clean_raw_text(text: str) -> str:
    for kw in SECTION_KEYWORDS_CAPS:
        text = re.sub(r'(?<=[^\n])(' + re.escape(kw) + r')', r'\n\1', text)
    return text


# ─── Main parser class ────────────────────────────────────────────────────────

class ResumeParser:
    """Position-aware resume parser."""

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        # Get text lines sorted by Y position on page 1
        self._pos_lines = _get_page1_lines_by_position(pdf_path)
        # Full raw text for regex searches
        self._raw_text  = extract_text_from_pdf(pdf_path)
        self._raw_text  = _clean_raw_text(self._raw_text)

    def get_extracted_data(self) -> dict:
        # Try positional (layout API) extraction first, fall back to raw text
        name = _extract_name_from_lines(self._pos_lines)
        if not name:
            name = _extract_name_from_raw(self._raw_text)
        return {
            'name':          name,
            'email':         self._extract_email(),
            'mobile_number': self._extract_phone(),
            'skills':        self._extract_skills(),
            'degree':        self._extract_degree(),
            'no_of_pages':   count_pages(self.pdf_path),
        }

    def _extract_email(self) -> str:
        m = EMAIL_RE.search(self._raw_text)
        return m.group(0) if m else ''

    def _extract_phone(self) -> str:
        m = PHONE_RE.search(self._raw_text)
        return m.group(0).strip() if m else ''

    def _extract_skills(self) -> list:
        text_lower = self._raw_text.lower()
        found = []
        for skill in SKILLS_DB:
            if re.search(r'\b' + re.escape(skill) + r'\b', text_lower):
                found.append(skill.title())
        return list(dict.fromkeys(found))

    def _extract_degree(self) -> list:
        matches = DEGREE_RE.findall(self._raw_text)
        return list(dict.fromkeys(matches))
