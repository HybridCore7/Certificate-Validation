# 🧾 Certificate Validation & Tiering System  

An intelligent **AI-powered certificate verification system** that validates digital certificates, extracts skills, detects fake certificates, and classifies them into tiers based on issuer credibility.  

---

## 🚀 Overview  

This project automates the validation of digital certificates using **OCR**, **NLP**, and **rule-based tiering**.  
It can:  
- Extract all text from certificate images  
- Identify the subject and skills  
- Detect fake or real certificates  
- Assign a credibility tier (Tier-1, Tier-2, Tier-3)  

---

## ✨ Features  

✅ **OCR-Based Text Extraction**  
Extracts text from images using Tesseract OCR.  

✅ **Skill & Tag Extraction**  
Uses NLP to detect course topics or technologies.  
> Example: “Data Analysis with Python” → Tags: `Python`, `Data Analysis`  

✅ **Fake vs Real Validation**  
Authenticity check using issuer name patterns, signature presence, and design markers.  

✅ **Tier Classification**  
Ranks certificates by credibility of issuer:  
- 🥇 **Tier 1:** Global verified organizations (IBM, Google, Microsoft)  
- 🥈 **Tier 2:** Trusted EdTech platforms (Coursera, Udemy, edX)  
- 🥉 **Tier 3:** Local or unverifiable sources  

✅ **Structured JSON Output**  
Returns a clean structured response:
```json
{
  "issuer": "IBM",
  "tags": ["Python", "Data Analysis"],
  "status": "Real",
  "tier": "Tier 1"
}
 |
| Optional ML      | Scikit-Learn  |
