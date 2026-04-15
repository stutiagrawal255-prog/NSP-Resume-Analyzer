"""
Lightweight resume parser — robust extraction even when pdfminer
returns text with collapsed whitespace / missing line-breaks.
"""

import re
import io
from pdfminer.high_level import extract_text_to_fp, extract_text
from pdfminer.layout import LAParams


# ─── Skills database ──────────────────────────────────────────────────────────

SKILLS_DB = [
    # Programming Languages
    'python', 'java', 'javascript', 'js', 'c++', 'c#', 'c', 'ruby', 'go', 'swift',
    'kotlin', 'php', 'typescript', 'scala', 'r', 'matlab', 'perl', 'rust', 'dart',
    # Web
    'html', 'css', 'react', 'react js', 'angular', 'angular js', 'vue', 'vue js',
    'node', 'node js', 'nodejs', 'express', 'django', 'flask', 'fastapi', 'spring',
    'asp.net', 'laravel', 'wordpress', 'magento', 'bootstrap', 'jquery',
    # Cybersecurity
    'penetration testing', 'vulnerability assessment', 'siem', 'wireshark', 'nmap',
    'burp suite', 'metasploit', 'threat detection', 'incident response',
    'network security', 'ethical hacking', 'cryptography', 'intrusion detection',
    # Data Science / ML
    'machine learning', 'deep learning', 'tensorflow', 'keras', 'pytorch', 'scikit-learn',
    'pandas', 'numpy', 'matplotlib', 'seaborn', 'plotly', 'nlp', 'computer vision',
    'data science', 'data analysis', 'data visualization', 'statistical modeling',
    'data mining', 'predictive analysis', 'neural networks', 'transformers',
    # Databases
    'sql', 'mysql', 'postgresql', 'sqlite', 'mongodb', 'redis', 'cassandra',
    'firebase', 'oracle', 'nosql', 'dbms',
    # Cloud / DevOps
    'aws', 'azure', 'gcp', 'google cloud', 'docker', 'kubernetes', 'jenkins',
    'terraform', 'ansible', 'ci/cd', 'git', 'github', 'gitlab', 'linux',
    # Android / iOS
    'android', 'android development', 'flutter', 'kotlin', 'xml', 'kivy',
    'ios', 'ios development', 'swift', 'cocoa', 'xcode', 'objective-c',
    # UI/UX
    'figma', 'adobe xd', 'sketch', 'zeplin', 'balsamiq', 'photoshop',
    'illustrator', 'after effects', 'ui', 'ux', 'prototyping', 'wireframes',
    # Other
    'agile', 'scrum', 'jira', 'rest api', 'graphql', 'microservices',
    'streamlit', 'hadoop', 'spark', 'power bi', 'tableau', 'excel',
    'full stack', 'full-stack', 'object oriented', 'oop', 'system design',
    'normalization', 'algorithms', 'data structures',
]

# ─── Regex patterns ───────────────────────────────────────────────────────────

# KEY FIX: Use [a-z]{2,6} (lowercase only) for TLD, then (?![a-z]) lookahead.
# Real email TLDs are always lowercase (gmail.com, yahoo.co.in).
# Section headers that follow are uppercase (LINKS, GITHUB) so lookahead passes.
# e.g. "gmail.comLINKS" → TLD=com, next='L' (uppercase) → NOT [a-z] → MATCH ✓
# e.g. "gmail.comlinks" → TLD=com, next='l' (lowercase) → IS [a-z]  → tries longer TLD
#      → eventually no valid match, falls back to just "com" if possible
EMAIL_RE  = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-z]{2,6}(?![a-z])')

PHONE_RE  = re.compile(
    r'(?:\+91[\-\s]?)?(?:\d{5}[\-\s]?\d{5}|\d{10}|\(\d{3}\)\s?\d{3}[\-\s]?\d{4}|\d{3}[\-\s]?\d{3}[\-\s]?\d{4})'
)
DEGREE_RE = re.compile(
    r'\b(B\.?\s*Tech|M\.?\s*Tech|B\.?\s*E\b|M\.?\s*E\b|B\.?\s*Sc|M\.?\s*Sc|'
    r'B\.?\s*Com|M\.?\s*Com|BCA|MCA|B\.?\s*A\b|M\.?\s*A\b|MBA|PhD|Ph\.?\s*D|'
    r'Bachelor|Master|Associate|Diploma)\b',
    re.IGNORECASE
)

# Section-header keywords — used to inject newlines into collapsed PDF text
SECTION_KEYWORDS = [
    'contact', 'phone', 'email', 'address',
    'linkedin', 'github', 'links', 'link',
    'experience', 'work experience', 'employment',
    'education', 'academic',
    'skills', 'technical skills', 'languages',
    'projects', 'project',
    'certifications', 'certification', 'achievements',
    'internship', 'internships',
    'interests', 'hobbies', 'objective', 'summary', 'profile',
    # all-caps variants common in PDFs
    'LINKS', 'CONTACT', 'SKILLS', 'EDUCATION', 'EXPERIENCE',
    'PROJECTS', 'CERTIFICATIONS', 'ACHIEVEMENTS', 'INTERNSHIP',
    'LANGUAGES', 'PROFILE', 'SUMMARY', 'OBJECTIVE',
    'Github', 'LinkedIn', 'GitHub',
]

# ─── PDF helpers ──────────────────────────────────────────────────────────────

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text preserving as many line-breaks as possible."""
    try:
        laparams = LAParams(line_margin=0.3, word_margin=0.1, boxes_flow=0.5)
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
        from pdfminer.high_level import extract_pages
        return sum(1 for _ in extract_pages(pdf_path))
    except Exception:
        return 1


# ─── Smart text pre-processing ───────────────────────────────────────────────

def _insert_breaks_before_sections(text: str) -> str:
    """Insert newlines before known section headers to un-collapse PDF text."""
    for kw in SECTION_KEYWORDS:
        for variant in (kw.title(), kw.upper(), kw.capitalize()):
            text = re.sub(r'(?<=[^\n])(' + re.escape(variant) + r')', r'\n\1', text)
    return text


def _clean_lines(text: str):
    """Return non-empty stripped lines from text."""
    text = _insert_breaks_before_sections(text)
    lines = [l.strip() for l in re.split(r'[\n\r]+', text) if l.strip()]
    return lines


# ─── Name extraction ─────────────────────────────────────────────────────────

# Words that are NOT parts of a person's name
SKIP_WORDS = {
    'contact', 'links', 'github', 'linkedin', 'skills', 'experience',
    'education', 'projects', 'certifications', 'achievements', 'internship',
    'languages', 'profile', 'summary', 'objective', 'address', 'phone',
    'email', 'mobile', 'analyst', 'engineer', 'developer', 'manager',
    'intern', 'student', 'undergraduate', 'science', 'technology',
    'information', 'computer', 'engineering', 'cyber', 'security',
}

# Title-Case name: 2–4 words, each starting with uppercase
NAME_RE = re.compile(r'\b([A-Z][a-z]+(?:\s[A-Z][a-z]+){1,3})\b')


def _looks_like_name(text: str) -> bool:
    """Return True if text looks like a 2-4 word person's name."""
    words = text.strip().split()
    if not (2 <= len(words) <= 4):
        return False
    if any(c.isdigit() for c in text) or '@' in text or ',' in text:
        return False
    # Reject if any word is a known non-name word
    if any(w.lower() in SKIP_WORDS for w in words):
        return False
    # All words must start with uppercase
    return all(w[0].isupper() for w in words)


def _extract_name(raw_text: str) -> str:
    """
    Extract person name by walking word-by-word from the very start
    of the cleaned resume header.
    The name is ALWAYS the first thing; we stop at the first job-title
    or section keyword word (Analyst, Engineer, Security, etc.).
    """
    header = raw_text[:800]

    # Remove noise so contact info doesn't confuse us
    header = EMAIL_RE.sub(' ', header)          # remove emails
    header = PHONE_RE.sub(' ', header)          # remove phone numbers
    header = re.sub(r'https?://\S+', ' ', header)  # remove URLs
    header = re.sub(r'[,|\u2022\xb7/\\@#]', ' ', header)  # remove punctuation
    header = re.sub(r'\d+', ' ', header)        # remove all digit sequences
    header = re.sub(r'\s+', ' ', header).strip()

    # Walk word-by-word; collect only valid name words
    # Stop as soon as a word is a job title/section/non-name word
    name_words = []
    for word in header.split()[:10]:
        # Must be Title-Case (Uppercase first, remaining lowercase-dominated)
        if not re.match(r'^[A-Z][a-z]+$', word):
            break
        # Stop at known non-name words (job titles, sections, etc.)
        if word.lower() in SKIP_WORDS:
            break
        name_words.append(word)
        if len(name_words) == 4:   # max 4-word name
            break

    if len(name_words) >= 2:
        return ' '.join(name_words)

    return 'Unknown'


# ─── Main parser class ────────────────────────────────────────────────────────

class ResumeParser:
    """Regex + keyword based resume parser, robust to collapsed PDF text."""

    def __init__(self, pdf_path: str):
        self.pdf_path  = pdf_path
        self._raw_text = extract_text_from_pdf(pdf_path)
        self._lines    = _clean_lines(self._raw_text)
        self._text     = '\n'.join(self._lines)

    def get_extracted_data(self) -> dict:
        return {
            'name':          _extract_name(self._raw_text),
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
            pattern = r'\b' + re.escape(skill) + r'\b'
            if re.search(pattern, text_lower):
                found.append(skill.title())
        return list(dict.fromkeys(found))

    def _extract_degree(self) -> list:
        matches = DEGREE_RE.findall(self._raw_text)
        return list(dict.fromkeys(matches))
