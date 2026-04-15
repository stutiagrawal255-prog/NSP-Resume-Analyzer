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

EMAIL_RE    = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')
PHONE_RE    = re.compile(r'(?:\+91[\-\s]?)?(?:\d{5}[\-\s]?\d{5}|\d{10}|\(\d{3}\)\s?\d{3}[\-\s]?\d{4}|\d{3}[\-\s]?\d{3}[\-\s]?\d{4})')
DEGREE_RE   = re.compile(
    r'\b(B\.?Tech|M\.?Tech|B\.?E|M\.?E|B\.?Sc|M\.?Sc|B\.?Com|M\.?Com|'
    r'BCA|MCA|B\.?A|M\.?A|MBA|PhD|Ph\.?D|Bachelor|Master|Associate|Diploma)\b',
    re.IGNORECASE
)

# Section-header keywords — used to split the blob into logical blocks
SECTION_KEYWORDS = [
    'contact', 'phone', 'email', 'address', 'linkedin', 'github',
    'experience', 'work experience', 'employment',
    'education', 'academic',
    'skills', 'technical skills', 'languages',
    'projects', 'project',
    'certifications', 'certification', 'achievements',
    'internship', 'internships',
    'interests', 'hobbies', 'objective', 'summary', 'profile', 'links',
]

# ─── PDF helpers ──────────────────────────────────────────────────────────────

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text preserving as many line-breaks as possible."""
    try:
        # Try with generous line-margin so nearby lines aren't merged
        laparams = LAParams(line_margin=0.3, word_margin=0.1, boxes_flow=0.5)
        text = extract_text(pdf_path, laparams=laparams)
        if text and len(text.strip()) > 20:
            return text
    except Exception:
        pass
    # Fallback
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
    """
    Insert newlines before known section headers so collapsed text gets split.
    e.g. '...git.LinkedinGithubSkills' -> '...git.\nLinkedin\nGithub\nSkills'
    """
    # Insert newline before each Section keyword that appears mid-word-run
    for kw in SECTION_KEYWORDS:
        # Capitalised variants
        for variant in (kw.title(), kw.upper(), kw.capitalize()):
            # Only insert break if the keyword is preceded by a non-space char
            text = re.sub(r'(?<=[^\n])(' + re.escape(variant) + r')', r'\n\1', text)
    return text


def _clean_lines(text: str):
    """Return non-empty stripped lines from text."""
    text = _insert_breaks_before_sections(text)
    lines = [l.strip() for l in re.split(r'[\n\r]+', text) if l.strip()]
    return lines


# ─── Name extraction ─────────────────────────────────────────────────────────

# Pattern: 2-4 words all starting with capital letter
NAME_PATTERN = re.compile(
    r'^([A-Z][a-zA-Z\'\-]+(?:\s[A-Z][a-zA-Z\'\-]+){1,3})$'
)

SKIP_LINES = {
    'curriculum vitae', 'resume', 'cv', 'profile', 'bio-data',
    'contact', 'skills', 'experience', 'education', 'projects',
    'certifications', 'achievements', 'summary', 'objective',
    'links', 'linkedin', 'github',
}

def _extract_name(lines) -> str:
    """
    Walk first 15 lines looking for a short Title-Case line
    that looks like a human name.
    """
    for line in lines[:15]:
        # Skip if line is too long (likely a sentence) or too short
        if len(line) > 50 or len(line) < 3:
            continue
        if line.lower() in SKIP_LINES:
            continue
        # Skip lines containing digits (phone, date)
        if re.search(r'\d', line):
            continue
        # Skip lines containing @ (email)
        if '@' in line:
            continue
        m = NAME_PATTERN.match(line)
        if m:
            return m.group(1).strip()
    # Second pass: just grab first sensible token if nothing matched
    for line in lines[:5]:
        parts = line.split()
        if 2 <= len(parts) <= 4 and all(p[0].isupper() for p in parts if p):
            if not any(c.isdigit() for c in line) and '@' not in line:
                return line
    return 'Unknown'


# ─── Main parser class ────────────────────────────────────────────────────────

class ResumeParser:
    """Regex + keyword based resume parser, robust to collapsed PDF text."""

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self._raw_text = extract_text_from_pdf(pdf_path)
        self._lines    = _clean_lines(self._raw_text)
        # Re-join the cleaned lines for regex searches
        self._text     = '\n'.join(self._lines)

    def get_extracted_data(self) -> dict:
        return {
            'name':          _extract_name(self._lines),
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
        return list(dict.fromkeys(found))  # deduplicate, preserve order

    def _extract_degree(self) -> list:
        matches = DEGREE_RE.findall(self._raw_text)
        return list(dict.fromkeys(matches))
