"""Seed generic document requirements and agreement templates.

Safe to re-run: existing rows (matched by slug) are left untouched, so edits made in
/admin survive. Replace the wording with the real Ospace documents when they arrive.
"""
from django.core.management.base import BaseCommand

from apps.portal.models import AgreementTemplate, DocumentType

DOCUMENT_TYPES = [
    ("Driver's license", "drivers-license", "Front and back of a valid U.S. driver's license. All four corners visible.", True, True, 10),
    ("Proof of auto insurance", "auto-insurance", "Current insurance card or declarations page showing your name and the vehicle.", True, True, 20),
    ("Vehicle registration", "vehicle-registration", "Current registration for the vehicle you will drive.", True, True, 30),
    ("Profile photo", "profile-photo", "A clear, recent head-and-shoulders photo. Parents and schools will see this.", True, False, 40),
    ("Vehicle photo", "vehicle-photo", "Exterior photo of your vehicle showing the license plate.", True, False, 50),
    ("Drug test result", "drug-test", "Lab result from a certified testing facility, dated within the last 90 days.", True, False, 60),
    ("TB test result", "tb-test", "Tuberculosis screening result, dated within the last 12 months.", True, False, 70),
    ("Social Security card or W-9", "tax-form", "Needed to set up contractor payments. Optional until approval.", False, False, 80),
]

CONTRACTOR_AGREEMENT = """This Independent Contractor Agreement ("Agreement") is entered into on {{date}} between {{company}} ("Ospace") and {{driver_name}} ("Driver"), {{driver_email}}, {{driver_phone}}.

# 1. Relationship of the parties

Driver is an independent contractor and not an employee, partner, agent or joint venturer of Ospace. Driver is free to accept or decline any ride offered through the Ospace platform, to set their own availability, and to provide services to others. Nothing in this Agreement creates an employment relationship. Driver is responsible for their own taxes, insurance and expenses.

# 2. Services

Driver agrees to transport students safely between home and school (or other locations arranged by Ospace) using Driver's own vehicle: {{vehicle}}. Driver will arrive on time, follow the pick-up and drop-off procedures shown in the driver app, and hand students over only to the parent, guardian or school staff member designated for that ride.

# 3. Driver requirements

Driver represents that they are at least 21 years old, hold a valid U.S. driver's license, maintain current auto insurance meeting Texas minimums, and will keep Ospace informed of any change to their license, insurance, vehicle or criminal record. Driver consents to a background check, drug screening and TB screening before approval and periodically thereafter.

# 4. Vehicle

Driver's vehicle must be a four-door vehicle with a model year within the last 15 years, kept clean, mechanically sound, and equipped with working seat belts for every passenger. Driver will not transport more students than there are seat belts.

# 5. Conduct and safety

Driver will never use a mobile phone while driving except through hands-free navigation, will never use alcohol, cannabis or other impairing substances before or during service, will never smoke or vape with a student in the vehicle, and will treat every student, parent and school employee with respect. Driver will report any incident, accident or complaint to Ospace immediately.

# 6. Payment

Ospace pays Driver per completed ride at the rates published in the driver app, with a minimum of $50 for every two completed rides. Payments are issued on the schedule shown in the app. Ospace may deduct amounts for cancelled or incomplete rides as described in the app.

# 7. Confidentiality and privacy

Driver will keep student and family information (names, addresses, schedules, phone numbers, photographs) strictly confidential, will use it only to provide the ride, and will not photograph or record students.

# 8. Term and termination

Either party may end this Agreement at any time with written notice. Ospace may suspend or remove Driver from the platform immediately for any safety concern, complaint, or breach of this Agreement.

# 9. General

This Agreement is governed by the laws of the State of Texas. It is the entire agreement between the parties on this subject and replaces any earlier discussions. By signing electronically below, Driver confirms they have read, understood and agree to this Agreement.
"""

BACKGROUND_CHECK = """{{driver_name}} ({{driver_email}}) authorises {{company}} and its screening partners to obtain consumer reports and investigative consumer reports about me for the purpose of evaluating my application to provide transportation services, and periodically during my engagement.

I understand these reports may include my driving record, criminal history (county, state and federal), sex-offender registry status, identity verification, and other public records, and that they may be obtained from courts, law-enforcement agencies, motor-vehicle departments and other sources.

I have been given a copy of the Summary of Your Rights Under the Fair Credit Reporting Act. I understand I may request a copy of any report obtained, and that if adverse action is taken based on a report I will be given the name of the agency that supplied it and an opportunity to dispute it.

I certify that the information I provide in my application is true and complete. I understand that providing false information is grounds for refusal or termination.

Signed electronically on {{date}}.
"""

SAFETY_POLICY = """As an Ospace driver, {{driver_name}} agrees to the following student safety and conduct standards on {{date}}.

# Before every ride

Confirm the ride details, student name and hand-over contact in the driver app. Inspect the vehicle: seat belts working, interior clean, no loose objects, fuel sufficient. Have a valid license, registration and insurance in the vehicle.

# Pick-up and drop-off

Wait in the designated location. A parent, guardian or teacher brings the student to the vehicle and collects them at the destination. Never leave a student unattended and never release a student to an unverified adult. Do not enter a family's home or a school building. Mark each step in the app as it happens.

# On the road

Every student wears a seat belt for the entire ride. Follow all traffic laws and speed limits. No phone use except hands-free navigation. No smoking, vaping, alcohol or drugs at any time on duty. No unauthorised passengers. Do not make unscheduled stops.

# Behaviour and communication

Be courteous and professional. Keep conversation appropriate for children. Do not exchange personal contact details with students, and do not contact students or families outside the app. Report any concern about a student's welfare to Ospace right away.

# Incidents

In an accident or emergency, first ensure the students are safe, call 911 if anyone is hurt, then notify Ospace immediately through the app or by phone. Cooperate fully with any review.

I understand that breaking these standards may result in immediate removal from the Ospace platform.
"""

PRIVACY_ACK = """I, {{driver_name}}, acknowledge that I have read the {{company}} Privacy Policy and understand how my personal information, documents and location data are collected and used during my application and while providing rides.

I understand that my profile photo, first name and vehicle details will be shown to parents and schools for the rides I accept, and that my GPS location is collected from the moment I check in for a ride until it is completed.

I consent to receive email and SMS messages from Ospace about my application, my rides and platform updates. I may opt out of promotional messages at any time.

Acknowledged electronically on {{date}}.
"""

AGREEMENTS = [
    ("Independent Contractor Agreement", "contractor-agreement", "Terms of driving with Ospace as an independent contractor.", CONTRACTOR_AGREEMENT, True, 10),
    ("Background Check Authorization", "background-check", "Your consent for us to run driving, criminal and identity checks.", BACKGROUND_CHECK, True, 20),
    ("Student Safety & Conduct Policy", "safety-policy", "The standards every Ospace driver follows with students in the car.", SAFETY_POLICY, True, 30),
    ("Privacy Acknowledgement", "privacy-acknowledgement", "How we use your information, and your consent to be contacted.", PRIVACY_ACK, True, 40),
]


class Command(BaseCommand):
    help = "Create the default document types and agreement templates (idempotent)."

    def handle(self, *args, **opts):
        made = 0
        for name, slug, desc, required, has_expiry, order in DOCUMENT_TYPES:
            _, created = DocumentType.objects.get_or_create(
                slug=slug, defaults={"name": name, "description": desc, "required": required, "has_expiry": has_expiry, "sort_order": order}
            )
            made += created
        for title, slug, summary, body, required, order in AGREEMENTS:
            _, created = AgreementTemplate.objects.get_or_create(
                slug=slug, defaults={"title": title, "summary": summary, "body": body.strip(), "required": required, "sort_order": order}
            )
            made += created
        self.stdout.write(self.style.SUCCESS(f"Seed complete: {made} new rows, {len(DOCUMENT_TYPES) + len(AGREEMENTS) - made} already existed."))
