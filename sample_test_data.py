"""
sample_test_data.py
-------------------
Sample test documents and data for testing InvestiAI without real documents.
Run this script to populate the database with realistic test cases.

Usage:
    python sample_test_data.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_db, create_case, save_form_data, update_case

# ─── SAMPLE HINDI DOCUMENT ────────────────────────────────────────────────────

SAMPLE_HINDI_HOSPITAL_RECORD = """अस्पताल विवरण
अस्पताल का नाम: अपोलो मल्टीस्पेशलिटी हॉस्पिटल
पता: 123, दिल्ली रोड, नई दिल्ली - 110001
फोन: 011-45678901

मरीज की जानकारी
मरीज का नाम: राजेश कुमार गुप्ता
आयु: 35 वर्ष
लिंग: पुरुष
पता: 456, राजेंद्र नगर, नई दिल्ली - 110060
मोबाइल: 9876543210

पॉलिसी विवरण
पॉलिसी संख्या: POL-2024-DL-789456
बीमा कंपनी: भारतीय जीवन बीमा निगम
नामिनी: सुनीता गुप्ता (पत्नी)

अस्पताल में भर्ती का विवरण
भर्ती तिथि: 12 मार्च 2025
छुट्टी तिथि: 20 मार्च 2025
वार्ड संख्या: जनरल वार्ड - 3बी

निदान और उपचार
मुख्य निदान: डेंगू बुखार (Dengue Fever - Confirmed)
डॉक्टर का नाम: डॉ. अनिल कुमार वर्मा
योग्यता: MBBS, MD (Medicine)
पंजीकरण संख्या: MCI-2015-45678

दावा राशि: ₹50,000 (पचास हजार रुपये)
उपचार अवधि: 8 दिन

घटना विवरण
घटना की तारीख: 10 मार्च 2025
घटना का स्थान: घर पर

बीमारी के लक्षण: तेज बुखार, सिरदर्द, जोड़ों में दर्द, प्लेटलेट्स में कमी

जांच रिपोर्ट:
- NS1 Antigen: पॉजिटिव
- CBC: प्लेटलेट्स 45,000 (कम)
- Dengue IgM: पॉजिटिव
- Widal Test: निगेटिव

दवाइयां:
- IV Fluids (Ringer's Lactate)
- Tab. Paracetamol 650mg
- Platelet Transfusion (2 यूनिट)"""


# ─── SAMPLE GUJARATI DOCUMENT ────────────────────────────────────────────────

SAMPLE_GUJARATI_CLAIM_FORM = """વીમા દાવો ફોર્મ
ઇન્સ્યોરન્સ ક્લેઇમ ફોર્મ - Gujarat Insurance Corporation

દાવેદારની વ્યક્તિગત માહિતી
દાવેદારનું નામ: સુરેશ ભાઈ ચીમનભાઈ પટેલ
ઉંમર: 42 વર્ષ
જન્મ તારીખ: 15 જૂન 1982
સરનામું: 45, ગાંધી રોડ, નવા વાડજ, અમદાવાદ - 380013
ફોન નંબર: 9865432107
ઇ-મેઇલ: suresh.patel@gmail.com

વીમા પૉલિસી વિગતો
પૉલિસી નંબર: POL-2023-GUJ-4521-B
વીમા કંપની: સ્ટાર હેલ્થ ઇન્સ્યોરન્સ
પૉલિસી ચાલુ તારીખ: 1 જાન્યુઆરી 2023
પૉલિસી સમાપ્તિ: 31 ડિસેમ્બર 2025
વીમા રકમ: ₹5,00,000

હૉસ્પિટલ માહિતી
હૉસ્પિટલ: સિવિલ હૉસ્પિટલ, અમદાવાદ
સરનામું: 115, ઇ.ડી.સી. ઇસ્ટ, ઓ.એન.જી.સી. ચોકડી, અમદાવાદ - 380016
ફોન: 079-22682021

દાખલ થવાની તારીખ: 5 ફેબ્રુઆરી 2025
રજા મળ્યાની તારીખ: 12 ફેબ્રુઆરી 2025
સારવાર અવધિ: 7 દિવસ

ડૉક્ટરની વિગતો
ઉપચાર કરનાર ડૉક્ટર: ડૉ. રાકેશ ભટ્ટ
લાયકાત: MBBS, MD (Internal Medicine)
ડૉ. નંબર: GUJ-MED-2018-9876

નિદાન
મુખ્ય નિદાન: ટાઇફોઇડ ફીવર (Enteric Fever)
ગૌણ નિદાન: ડિહાઇડ્રેશન

ઘટના તારીખ: 1 ફેબ્રુઆરી 2025
ઘટના: ઘર ખાતે ભોજન બાદ અચાનક તાવ

દાવાની માહિતી
કુલ દાવા રકમ: ₹35,000
હૉસ્પિટલ બિલ: ₹28,500
દવાઓ ખર્ચ: ₹4,500
ડૉ. ફી: ₹2,000"""


# ─── SAMPLE ENGLISH DOCUMENT ─────────────────────────────────────────────────

SAMPLE_ENGLISH_INVESTIGATION_NOTES = """INSURANCE INVESTIGATION NOTES
Case Reference: INV-2025-MH-0042
Date of Investigation: 25 March 2025
Investigator: Ravi Sharma (Senior Investigator)

CLAIMANT DETAILS
Name: Priya Anand Mehta
Age: 28 years
Address: 78, Linking Road, Bandra West, Mumbai - 400050
Phone: 9123456789
Email: priya.mehta@email.com

POLICY INFORMATION
Policy Number: POL-2024-MH-112233
Insurance Company: ICICI Lombard General Insurance
Policy Start: 15 June 2024
Policy End: 14 June 2025
Sum Insured: INR 3,00,000

HOSPITALIZATION DETAILS
Hospital: Fortis Hospital, Mulund
Hospital Address: Mulund Goregaon Link Road, Mulund West, Mumbai - 400080
Phone: 022-67674000
Registration No: MH/HOSP/2015/4521

Date of Incident: 15 January 2025
Admission Date: 16 January 2025
Discharge Date: 22 January 2025
Duration: 7 days
Ward: Semi-Private Room 204

Treating Doctor: Dr. Ramesh Subramaniam Nair
Qualification: MBBS, MS (General Surgery)
Registration: MCI/2010/78965

DIAGNOSIS
Primary: Acute Appendicitis
Secondary: Post-operative wound infection

TREATMENT PROVIDED
- Emergency appendectomy performed on 17 January 2025
- IV antibiotics (Augmentin 1.2g TDS x 5 days)
- Post-operative wound care
- IV fluids and analgesics

CLAIM DETAILS
Total Claim Amount: INR 75,000
Breakdown:
- Hospital charges: INR 45,000
- Surgery charges: INR 22,000
- Medicines: INR 5,000
- Doctor's fees: INR 3,000

INVESTIGATION FINDINGS
During field investigation:
1. Hospital was visited and records verified
2. Dr. Nair was contacted - confirmed treatment
3. Pharmacy bills cross-checked with discharge summary
4. Inconsistency noted: Bill dated 16 Jan but admission noted as 16 Jan evening

SUSPICIOUS INDICATORS
- Minor date inconsistency in billing (1 day)
- Policy taken only 7 months before claim (relatively new)
- Claim is first claim under this policy

PRELIMINARY ASSESSMENT
Case appears genuine. Appendicitis confirmed by surgical record. 
Minor billing date inconsistency likely administrative error.
Recommend: Standard verification, request original histopathology report."""


# ─── SEED TEST CASES ─────────────────────────────────────────────────────────

def seed_test_cases():
    """Populate database with 3 realistic test cases."""
    print("Initializing database...")
    init_db()

    test_cases = [
        {
            "case_id": "INV-2025-TEST01",
            "claimant_name": "Rajesh Kumar Gupta",
            "policy_number": "POL-2024-DL-789456",
            "status": "In Progress",
            "notes": "Dengue fever case. Documents in Hindi. Hospital: Apollo Delhi.",
            "form_data": {
                "claimant_name": "Rajesh Kumar Gupta",
                "age": "35 years",
                "address": "456, Rajendra Nagar, New Delhi - 110060",
                "phone": "9876543210",
                "policy_number": "POL-2024-DL-789456",
                "hospital_name": "Apollo Multispeciality Hospital, Delhi",
                "hospital_address": "123, Delhi Road, New Delhi - 110001",
                "claim_amount": "₹50,000",
                "incident_date": "10 March 2025",
                "admission_date": "12 March 2025",
                "discharge_date": "20 March 2025",
                "diagnosis": "Dengue Fever (Confirmed)",
                "doctor_name": "Dr. Anil Kumar Verma",
                "investigator_notes": "NS1 Antigen positive. Platelet count 45,000. Treatment appears consistent with diagnosis.",
                "suspicious_indicators": "None identified. Case appears genuine.",
                "insurance_company": "LIC of India",
            }
        },
        {
            "case_id": "INV-2025-TEST02",
            "claimant_name": "Suresh Patel",
            "policy_number": "POL-2023-GUJ-4521-B",
            "status": "Open",
            "notes": "Typhoid case. Documents in Gujarati. Civil Hospital Ahmedabad.",
            "form_data": {
                "claimant_name": "Suresh Chimanbhai Patel",
                "age": "42 years",
                "address": "45, Gandhi Road, Nava Wadaj, Ahmedabad - 380013",
                "phone": "9865432107",
                "policy_number": "POL-2023-GUJ-4521-B",
                "hospital_name": "Civil Hospital, Ahmedabad",
                "hospital_address": "115, EDC East, ONGC Chokdi, Ahmedabad - 380016",
                "claim_amount": "₹35,000",
                "incident_date": "1 February 2025",
                "admission_date": "5 February 2025",
                "discharge_date": "12 February 2025",
                "diagnosis": "Typhoid Fever (Enteric Fever)",
                "doctor_name": "Dr. Rakesh Bhatt",
                "investigator_notes": "Policy active for 2 years. This is second claim in 6 months.",
                "suspicious_indicators": "Second claim in 6 months. Previous claim also for fever. Recommend verification of Widal test reports.",
                "insurance_company": "Star Health Insurance",
            }
        },
        {
            "case_id": "INV-2025-TEST03",
            "claimant_name": "Priya Mehta",
            "policy_number": "POL-2024-MH-112233",
            "status": "Escalated",
            "notes": "Appendicitis case. English documents. Fortis Mumbai. Minor billing inconsistency found.",
            "form_data": {
                "claimant_name": "Priya Anand Mehta",
                "age": "28 years",
                "address": "78, Linking Road, Bandra West, Mumbai - 400050",
                "phone": "9123456789",
                "policy_number": "POL-2024-MH-112233",
                "hospital_name": "Fortis Hospital, Mulund",
                "hospital_address": "Mulund Goregaon Link Road, Mulund West, Mumbai - 400080",
                "claim_amount": "INR 75,000",
                "incident_date": "15 January 2025",
                "admission_date": "16 January 2025",
                "discharge_date": "22 January 2025",
                "diagnosis": "Acute Appendicitis",
                "doctor_name": "Dr. Ramesh Nair",
                "investigator_notes": "Emergency appendectomy performed. First claim on relatively new policy (7 months old).",
                "suspicious_indicators": "Policy taken 7 months before claim. Minor billing date inconsistency noted (1 day). New policy + immediate high-value claim.",
                "insurance_company": "ICICI Lombard",
            }
        },
    ]

    created = 0
    for tc in test_cases:
        try:
            create_case(
                tc["case_id"],
                tc["claimant_name"],
                tc["policy_number"],
                "InvestiAI Demo",
                tc["notes"]
            )
            update_case(tc["case_id"], status=tc["status"])
            save_form_data(tc["case_id"], tc["form_data"])
            created += 1
            print(f"✅ Created test case: {tc['case_id']} — {tc['claimant_name']}")
        except Exception as e:
            print(f"⚠️  Case {tc['case_id']} may already exist: {e}")

    print(f"\n✅ Done! {created} test cases created.")
    print("\nLogin and open any test case to explore the full workflow.")
    print("Default credentials: admin / admin123")
    print("\nTest case IDs:")
    for tc in test_cases:
        print(f"  - {tc['case_id']}")


if __name__ == "__main__":
    seed_test_cases()
    print("\n🚀 Run the app with: streamlit run app.py")
