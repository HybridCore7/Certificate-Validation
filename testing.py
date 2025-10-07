import re
import os
import sys
import json
import argparse
from PIL import Image, ImageOps, ImageFilter
import pytesseract
import fitz  # PyMuPDF
from rapidfuzz import process as rfp

# ========================
# Config
# ========================
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
CUSTOM_TEMP = r"C:\TempOCR"
os.makedirs(CUSTOM_TEMP, exist_ok=True)
os.environ['TMP'] = CUSTOM_TEMP
os.environ['TEMP'] = CUSTOM_TEMP

GENERIC_VERIFY_REGEX = r"(https?:\/\/[^\s]+|\b[A-Z0-9]{5,12}\b)"
TIME_REGEX = r"(\d+\.?\d*)\s*(?:total\s*)?(hours|hrs|h|weeks|week|months|month)"

# ========================
# Issuer DB
# ========================
ISSUER_DB = {
    "udemy":20,"coursera":30,"edx":40,"aws":80,"google":75,"microsoft":75,"linkedin":25,
    "kaggle":50,"pluralsight":35,"datacamp":30,"simplilearn":25,"harvard":95,"stanford":95,
    "mit":95,"iit":95,"oxford":90,"cambridge":90,"yale":90,"princeton":90,"columbia":90,
    "caltech":95,"cornell":90,"ucla":85,"nyu":85,"geeksforgeeks":20,"codechef":20,"hackerrank":20,
    "leetcode":20,"freecodecamp":15,"sololearn":15,"nptel":40,"greatlearning":25,"upgrad":25,
    "coursera-google":75,"coursera-aws":80,"aws-developer":80,"google-ai":75,"deepmind":85,
    "ibm":70,"oracle":65,"sap":60,"accenture":50,"tcs":50,"infosys":50,"wipro":50,"capgemini":50,
    "nasa":95,"spacex":95,"tesla":90,"facebook":75,"meta":75,"twitter":70,"apple":80,
    "geeksforgeeks-cs":20
}

ISSUER_ALIASES = {
    "bm developer skills network":"ibm",
    "ibm skills":"ibm",
    "oracle university":"oracle",
    "geeksforgeeks":"geeksforgeeks",
    "gfg":"geeksforgeeks",
    "coursera google":"coursera-google",
    "coursera aws":"coursera-aws"
}

PROJECT_KEYWORDS = ["capstone", "project", "portfolio", "hands-on", "lab", "practical"]
ASSESSMENT_KEYWORDS = ["exam", "proctored", "invigilat", "graded", "assess", "final exam", "passing"]
PREREQ_KEYWORDS = ["prerequisite", "prereq", "prior knowledge", "experience required", "requirement"]

# ========================
# Load skills from external JSON
# ========================
with open("skills_db.json", "r", encoding="utf-8") as f:
    SKILL_TAGS = json.load(f)["skills"]

# ========================
# Utilities
# ========================
def preprocess_pil_image(img: Image.Image) -> Image.Image:
    img = img.convert("L")
    img = ImageOps.autocontrast(img)
    img = img.filter(ImageFilter.MedianFilter(size=3))
    img = img.filter(ImageFilter.SHARPEN)
    max_dim = 2500
    if max(img.size) > max_dim:
        scale = max_dim / max(img.size)
        img = img.resize((int(img.size[0]*scale), int(img.size[1]*scale)), Image.LANCZOS)
    return img

def ocr_image(img: Image.Image) -> str:
    img = preprocess_pil_image(img)
    return pytesseract.image_to_string(img)

# ========================
# PDF/Image extraction
# ========================
def extract_text_from_pdf(file_path: str) -> str:
    text = ""
    try:
        doc = fitz.open(file_path)
        for page in doc:
            page_text = page.get_text()
            if page_text and page_text.strip():
                text += page_text + "\n"
            else:
                mat = fitz.Matrix(2,2)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                text += ocr_image(img) + "\n"
    except Exception as e:
        print("PDF extraction error:", e)
    return text

def extract_text_from_image(img_path: str) -> str:
    try:
        img = Image.open(img_path)
        return ocr_image(img)
    except Exception as e:
        print("OCR Image error:", e)
        return ""

# ========================
# Feature extraction
# ========================
def find_verification_link(text: str):
    match = re.search(GENERIC_VERIFY_REGEX, text, re.IGNORECASE)
    return match.group(0).strip() if match else None

def fuzzy_lookup_issuer(ocr_text: str, issuer_db: dict):
    text = ocr_text.lower()
    for alias, name in ISSUER_ALIASES.items():
        if alias in text:
            return name, issuer_db.get(name, 25)
    best = rfp.extractOne(text, list(issuer_db.keys()), score_cutoff=30)
    if best:
        return best[0], issuer_db.get(best[0], 25)
    return None, 25

def extract_time_commitment(ocr_text: str):
    m = re.search(TIME_REGEX, ocr_text, re.IGNORECASE)
    if not m: return 0
    val = float(m.group(1))
    unit = m.group(2).lower()
    if "week" in unit: return val*10
    if "month" in unit: return val*40
    return val

def detect_keywords(ocr_text: str, keywords: list) -> bool:
    text = ocr_text.lower()
    return any(k in text for k in keywords)

def guess_verification_method(ocr_text: str, verification_link: str):
    text = ocr_text.lower()
    if 'proct' in text or 'invigil' in text:
        return 'proctored'
    if 'blockchain' in text:
        return 'blockchain'
    if verification_link:
        if any(x in verification_link.lower() for x in ['verify', 'certificate', 'registry', 'credentials']):
            return 'registry'
        return 'simple_link'
    return 'none'

def extract_skills(text: str):
    found_skills = []
    lower_text = text.lower()
    for skill in SKILL_TAGS:
        # match whole word/phrase only
        if re.search(r"\b" + re.escape(skill.lower()) + r"\b", lower_text):
            found_skills.append(skill)
    return list(set(found_skills))

# ========================
# Tier calculation
# ========================
def compute_certificate_tier(features, issuer_db=None):
    if issuer_db is None: issuer_db = ISSUER_DB
    issuer_rep = features.get("issuer_rep", 25)
    time_h = float(features.get("duration_hours", 0))
    assessment = float(features.get("assessment_rigor", 20))
    proj_req = int(features.get("has_project", 0))
    proj_comp = float(features.get("project_complexity", 0))
    prereq = int(features.get("prerequisites_required", 0))
    industry = float(features.get("industry_recognition", 20))
    time_score = max(0, min(100, (time_h/200.0)*100))
    verify_bonus = 10 if features.get("verified", False) else 0
    project_score = proj_comp if proj_req else 0
    weights = {"issuer_rep":0.35,"assessment":0.25,"project":0.20,"time":0.10,"industry":0.10,"prereq":0.0}
    composite = (
        issuer_rep*weights["issuer_rep"]+
        assessment*weights["assessment"]+
        project_score*weights["project"]+
        time_score*weights["time"]+
        industry*weights["industry"]+
        (prereq*100)*weights["prereq"]
    )
    composite += verify_bonus
    score = max(0, min(100, composite))
    if score >= 80: tier=1
    elif score >= 60: tier=2
    elif score >= 40: tier=3
    else: tier=4
    return {"score":round(score,2),"tier":tier}

# ========================
# Main analyze function
# ========================
def analyze_certificate(file_path: str, issuer_db=None):
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf": text = extract_text_from_pdf(file_path)
    elif ext in [".png", ".jpg", ".jpeg", ".webp"]: text = extract_text_from_image(file_path)
    else: return {"error":"Unsupported file format"}
    
    verification_link = find_verification_link(text)
    issuer_name, issuer_rep = fuzzy_lookup_issuer(text, issuer_db or ISSUER_DB)
    duration = extract_time_commitment(text)
    project_present = detect_keywords(text, PROJECT_KEYWORDS)
    project_complexity = 70 if project_present and ('capstone' in text.lower() or 'portfolio' in text.lower()) else (40 if project_present else 0)
    assessment_present = detect_keywords(text, ASSESSMENT_KEYWORDS)
    assessment_rigor = 80 if 'proct' in text.lower() or 'invigil' in text.lower() else (60 if assessment_present else 20)
    prereq_present = detect_keywords(text, PREREQ_KEYWORDS)
    verified = bool(verification_link)
    verification_reason = guess_verification_method(text, verification_link)
    
    # Extract skills and meaningful tags
    skills = extract_skills(text)
    tags = []
    if issuer_name:
        tags.append(issuer_name)
    tags.extend(skills)
    tags = list(set(tags))  # remove duplicates

    features = {
        "issuer": issuer_name or "unknown",
        "issuer_rep": issuer_rep,
        "duration_hours": duration,
        "has_project": int(project_present),
        "project_complexity": project_complexity,
        "assessment_rigor": assessment_rigor,
        "prerequisites_required": int(prereq_present),
        "industry_recognition": issuer_rep,
        "verified": verified,
        "verification_reason": verification_reason,
        "tags": {
            "project": project_present,
            "assessment": assessment_present,
            "prerequisite": prereq_present
        }
    }
    
    result = compute_certificate_tier(features, issuer_db)
    
    output = {
        "file": file_path,
        "issuer": issuer_name or "unknown",
        "features": features,
        "skills": skills,
        "tags": tags,
        "result": result,
        "raw_text_snippet": text[:500]
    }
    return output

# ========================
# CLI
# ========================
if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Certificate file path (PDF/Image)")
    parser.add_argument("--save-json", required=False, help="Save output JSON to file")
    args = parser.parse_args()
    
    res = analyze_certificate(args.file)
    if args.save_json:
        with open(args.save_json, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=4)
        print(f"[+] Saved output to {args.save_json}")
    else:
        print(json.dumps(res, indent=4))
