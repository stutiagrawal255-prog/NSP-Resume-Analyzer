"""
Lightweight resume parser to replace pyresparser.
Works without spacy/blis/thinc (no C++ build tools required).
Uses pdfminer.six for PDF extraction and regex for NLP.
"""

import re
import io
from pdfminer.high_level import extract_text_to_fp
from pdfminer.layout import LAParams


# ─── Common skills database ────────────────────────────────────────────────

SKILLS_DB = [
    # Programming Languages
    'python', 'java', 'javascript', 'js', 'c++', 'c#', 'c', 'ruby', 'go', 'swift',
    'kotlin', 'php', 'typescript', 'scala', 'r', 'matlab', 'perl', 'rust', 'dart',
    # Web
    'html', 'css', 'react', 'react js', 'angular', 'angular js', 'vue', 'vue js',
    'node', 'node js', 'nodejs', 'express', 'django', 'flask', 'fastapi', 'spring',
    'asp.net', 'laravel', 'wordpress', 'magento', 'php', 'bootstrap', 'jquery',
    # Data Science / ML
    'machine learning', 'deep learning', 'tensorflow', 'keras', 'pytorch', 'scikit-learn',
    'pandas', 'numpy', 'matplotlib', 'seaborn', 'plotly', 'nlp', 'computer vision',
    'data science', 'data analysis', 'data visualization', 'statistical modeling',
    'data mining', 'predictive analysis', 'neural networks', 'transformers',
    # Databases
    'sql', 'mysql', 'postgresql', 'sqlite', 'mongodb', 'redis', 'cassandra',
    'firebase', 'oracle', 'nosql',
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
]


# ─── Name patterns ─────────────────────────────────────────────────────────

NAME_PATTERN = re.compile(
    r'^([A-Z][a-zA-Z\-\']+(?:\s[A-Z][a-zA-Z\-\']+){1,3})',
    re.MULTILINE
)

EMAIL_PATTERN = re.compile(
    r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}'
)

PHONE_PATTERN = re.compile(
    r'(?:\+91[\-\s]?)?(?:\d{5}[\-\s]?\d{5}|\d{10}|\(\d{3}\)\s?\d{3}[\-\s]?\d{4}|\d{3}[\-\s]?\d{3}[\-\s]?\d{4})'
)

DEGREE_PATTERN = re.compile(
    r'\b(B\.?Tech|M\.?Tech|B\.?E|M\.?E|B\.?Sc|M\.?Sc|B\.?Com|M\.?Com|BCA|MCA|'
    r'B\.?A|M\.?A|MBA|PhD|Ph\.?D|Bachelor|Master|Associate|Diploma)\b',
    re.IGNORECASE
)


# ─── PDF text extraction ────────────────────────────────────────────────────

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract all text from a PDF file using pdfminer.six."""
    output = io.StringIO()
    with open(pdf_path, 'rb') as f:
        extract_text_to_fp(f, output, laparams=LAParams(), output_type='text', codec='utf-8')
    return output.getvalue()


def count_pages(pdf_path: str) -> int:
    """Count number of pages in a PDF."""
    try:
        from pdfminer.high_level import extract_pages
        return sum(1 for _ in extract_pages(pdf_path))
    except Exception:
        return 1


# ─── Main parser ────────────────────────────────────────────────────────────

class ResumeParser:
    """Simple regex/keyword based resume parser."""

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self._text = extract_text_from_pdf(pdf_path)
        self._lines = [l.strip() for l in self._text.splitlines() if l.strip()]

    def get_extracted_data(self) -> dict:
        return {
            'name':          self._extract_name(),
            'email':         self._extract_email(),
            'mobile_number': self._extract_phone(),
            'skills':        self._extract_skills(),
            'degree':        self._extract_degree(),
            'no_of_pages':   count_pages(self.pdf_path),
        }

    # ── private helpers ──────────────────────────────────────────────────

    def _extract_name(self) -> str:
        """Try to get name from first meaningful line."""
        skip = {'curriculum vitae', 'resume', 'cv', 'profile', 'bio-data'}
        for line in self._lines[:10]:
            if line.lower() in skip:
                continue
            m = NAME_PATTERN.match(line)
            if m:
                return m.group(1).strip()
        return self._lines[0] if self._lines else 'Unknown'

    def _extract_email(self) -> str:
        m = EMAIL_PATTERN.search(self._text)
        return m.group(0) if m else ''

    def _extract_phone(self) -> str:
        m = PHONE_PATTERN.search(self._text)
        return m.group(0).strip() if m else ''

    def _extract_skills(self) -> list:
        text_lower = self._text.lower()
        found = []
        for skill in SKILLS_DB:
            pattern = r'\b' + re.escape(skill) + r'\b'
            if re.search(pattern, text_lower):
                found.append(skill.title())
        return list(dict.fromkeys(found))  # preserve order, deduplicate

    def _extract_degree(self) -> list:
        matches = DEGREE_PATTERN.findall(self._text)
        return list(dict.fromkeys(matches))
