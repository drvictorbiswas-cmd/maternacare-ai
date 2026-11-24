"""Safety-critical clinical rules engine for Maternacare AI.

DESIGN RULES (from the brief):
- Never diagnose. Never reassure a possibly serious symptom as 'normal'.
- Never delay emergency referral to ask more questions.
- Danger-sign checks run BEFORE any general chat response.
- Schedules are GUIDANCE only, adapted to stage/risk; never a prescription.
- Sources are recorded, not invented. No dosages are generated.
"""

from datetime import date, timedelta

# ---------------------------------------------------------------------------
# Danger sign catalog. Each entry: keywords (en/hi/bn), urgency, action,
# reason, immediate steps. Triage is keyword-based and deliberately
# over-triggers rather than missing a serious symptom.
# ---------------------------------------------------------------------------
DANGER_SIGNS = [
    {
        "id": "bleeding_pregnancy",
        "match": ["bleeding", "blood", "spotting", "Khun", "खून", "রক্ত", "রক্তপাত", "bleeding from vagina"],
        "stage": "pregnancy",
        "urgency": "emergency",
        "reason_en": "Bleeding in pregnancy can mean miscarriage, ectopic pregnancy or placental problems. It needs urgent assessment.",
        "reason_hi": "Pregnancy mein bleeding miscarriage, ectopic ya placenta ki samasya ka sanket ho sakta hai. Turant jaanch zaroori hai.",
        "reason_bn": "গর্ভকালে রক্তপাত গর্ভপাত, ইকটোপিক বা প্লাসেন্টা সমস্যার লক্ষণ হতে পারে। জরুরি পরীক্ষা দরকার।",
        "action_en": "Go to an emergency department now. Do not wait. If bleeding is heavy with pain or dizziness, call an ambulance.",
        "action_hi": "Abhi emergency department jayein. Wait na karein. Tez bleeding ke saath dard ya chakkar aaye to ambulance call karein.",
        "action_bn": "এখনই জরুরি বিভাগে যান। অপেক্ষা করবেন না। প্রবল রক্তপাতে ব্যথা বা মাথা ঘোরা হলে অ্যাম্বুলেন্স কল করুন।",
        "steps_en": ["Sit or lie down", "Note how much bleeding and since when", "Take your pregnancy records with you", "Do not self-medicate"],
    },
    {
        "id": "severe_headache_vision",
        "match": ["severe headache", "blurred vision", "vision", "dhundhla", "धुँधला", "ঝাপসা", "sir dard", "সিরে ব্যথা", "tej sir dard", "মাথাব্যথা"],
        "stage": "pregnancy,postpartum",
        "urgency": "emergency",
        "reason_en": "A severe headache with blurred vision or upper abdominal pain can be a sign of pre-eclampsia, a serious condition.",
        "reason_hi": "Tez sir dard ke saath dhundhla dikhna ya uper pet dard pre-eclampsia ka sanket ho sakta hai — ye gambhir hai.",
        "reason_bn": "তীব্র মাথাব্যথার সাথে ঝাপসা দৃষ্টি বা ওপরের পেটে ব্যথা প্রি-ইক্ল্যাম্পসিয়ার লক্ষণ হতে পারে — এটি গুরুতর।",
        "action_en": "Seek emergency assessment now. Do not drive yourself if vision is blurred.",
        "action_hi": "Abhi emergency jaanch karayein. Dhundhla dikhe to khud gaadi na chalayein.",
        "action_bn": "এখনই জরুরি পরীক্ষা করুন। দৃষ্টি ঝাপসা হলে নিজে গাড়ি চালাবেন না।",
        "steps_en": ["Sit down and avoid falls", "Check blood pressure if a device is available", "Note symptoms and time", "Go to emergency care"],
    },
    {
        "id": "convulsions",
        "match": ["convulsion", "seizure", "fit", "jhatka", "झटके", "খিঁচুনি", "jhatein"],
        "stage": "pregnancy,postpartum,newborn",
        "urgency": "emergency",
        "reason_en": "Convulsions can indicate eclampsia or another serious condition and need immediate emergency care.",
        "reason_hi": "Jhatke eclampsia ya kisi gambhir samasya ka sanket hain — turant emergency care chahiye.",
        "reason_bn": "খিঁচুনি ইক্ল্যাম্পসিয়া বা অন্য গুরুতর সমস্যার লক্ষণ — সঙ্গে সঙ্গে জরুরি যত্ন দরকার।",
        "action_en": "Call an ambulance NOW. Do not put anything in the person's mouth. Place them on their side and protect from injury.",
        "action_hi": "Abhi ambulance call karein. Muh mein kuch na daalein. Vyakti ko side par litayein aur chot se bachayein.",
        "action_bn": "এখনই অ্যাম্বুলেন্স কল করুন। মুখে কিছু দেবেন না। রোগীকে পাশে শুইয়ে আঘাত থেকে রক্ষা করুন।",
        "steps_en": ["Call emergency services", "Do not restrain or put objects in mouth", "Turn on side", "Time the seizure"],
    },
    {
        "id": "breathing",
        "match": ["breath", "breathing", "saans", "साँस", "শ্বাস", "cannot breathe", "breathless", "chest pain", "সিনে ব্যাথা"],
        "stage": "pregnancy,postpartum,newborn",
        "urgency": "emergency",
        "reason_en": "Difficulty breathing or chest pain can be life-threatening for the mother or baby.",
        "reason_hi": "Saans lene mein dikkat ya seene mein dard jaanleva ho sakta hai — maa aur baby dono ke liye.",
        "reason_bn": "শ্বাসকষ্ট বা বুকে ব্যথা মা ও শিশুর জন্য জীবন-হুমকি হতে পারে।",
        "action_en": "Call emergency services now. Sit upright and stay calm while help arrives.",
        "action_hi": "Abhi emergency call karein. Seedhe baithein aur shaant rahein jab tak madad aaye.",
        "action_bn": "এখনই জরুরি পরিষেবা কল করুন। সোজা বসুন এবং সাহায্য না আসা পর্যন্ত শান্ত থাকুন।",
        "steps_en": ["Call emergency services", "Sit upright", "Loosen tight clothing", "Do not leave the person alone"],
    },
    {
        "id": "reduced_movement",
        "match": ["reduced movement", "less movement", "no movement", "baby not moving", "fetal movement", "kam hulchul", "কম নড়াচড়া", "কম হলচল"],
        "stage": "pregnancy",
        "urgency": "urgent",
        "reason_en": "Reduced fetal movements after they have become established can mean the baby is unwell. It needs same-day assessment.",
        "reason_hi": "Baby ki hulchul kam hona (jab pehle normal thi) baby ki bimari ka sanket ho sakta hai. Aaj hi jaanch karayein.",
        "reason_bn": "শিশুর নড়াচড়া কমে যাওয়া (আগে স্বাভাবিক থাকলে) অসুস্থতার লক্ষণ হতে পারে। আজই পরীক্ষা করুন।",
        "action_en": "Contact your doctor or hospital today for a review. Do not wait for the next appointment.",
        "action_hi": "Aaj hi doctor ya hospital se sampark karein. Agli visit ka intezaar na karein.",
        "action_bn": "আজই ডাক্তার বা হাসপাতালের সাথে যোগাযোগ করুন। পরবর্তী সাক্ষাতের অপেক্ষা করবেন না।",
        "steps_en": ["Note the time of last normal movements", "Have a drink and lie on your left side", "Count movements for 2 hours", "Call your maternity unit with the result"],
    },
    {
        "id": "fluid_leakage",
        "match": ["water broke", "fluid leaking", "leaking fluid", "paani nikal", "पानी निकल", "জল ভাঙা", "pani nikla"],
        "stage": "pregnancy",
        "urgency": "urgent",
        "reason_en": "Fluid leaking from the vagina may mean the waters have broken, which needs hospital assessment.",
        "reason_hi": "Vagina se fluid nikalna matlab pani phat sakta hai — hospital jaanch zaroori hai.",
        "reason_bn": "যোনি থেকে তরল বের হওয়া মানে জল ভেঙে যেতে পারে — হাসপাতালে পরীক্ষা দরকার।",
        "action_en": "Call your maternity unit now and go in for assessment, even if you are not having contractions.",
        "action_hi": "Abhi maternity unit ko call karein aur jaanch ke liye jayein, chahe contraction na ho.",
        "action_bn": "এখনই ম্যাটার্নিটি ইউনিটে কল করুন এবং পরীক্ষার জন্য যান, সংকোচন না হলেও।",
        "steps_en": ["Note the time and colour of the fluid", "Put on a clean pad", "Do not bath or insert anything", "Go to hospital"],
    },
    {
        "id": "postpartum_bleeding",
        "match": ["heavy bleeding", "soaking", "bade khun", "भारी रक्तस्राव", "প্রবল রক্তপাত", "clots"],
        "stage": "postpartum",
        "urgency": "emergency",
        "reason_en": "Very heavy bleeding after birth (soaking a pad in an hour or large clots) can be postpartum haemorrhage.",
        "reason_hi": "Janam ke baad bahut tez bleeding (ek ghante mein pad bheeg jaye ya bade clot) postpartum haemorrhage ho sakta hai.",
        "reason_bn": "প্রসবের পর প্রবল রক্তপাত (এক ঘণ্টায় প্যাড ভিজে যাওয়া বা বড় ক্লট) প্রসব-পরবর্তী রক্তস্রাব হতে পারে।",
        "action_en": "Call emergency services now. This is an emergency.",
        "action_hi": "Abhi emergency call karein. Ye emergency hai.",
        "action_bn": "এখনই জরুরি পরিষেবা কল করুন। এটি জরুরি অবস্থা।",
        "steps_en": ["Call emergency services", "Lie flat with legs raised", "Do not stand up suddenly", "Keep baby with you if possible"],
    },
    {
        "id": "fever_postpartum",
        "match": ["fever", "chills", "bukhar", "बुखार", "জ্বর", "high temperature"],
        "stage": "postpartum,newborn",
        "urgency": "urgent",
        "reason_en": "Fever after birth can mean infection in the mother or newborn and needs prompt assessment.",
        "reason_hi": "Janam ke baad bukhar maa ya baby mein infection ka sanket ho sakta hai — jaldi jaanch chahiye.",
        "reason_bn": "প্রসবের পর জ্বর মা বা শিশুর সংক্রমণের লক্ষণ হতে পারে — দ্রুত পরীক্ষা দরকার।",
        "action_en": "Contact your doctor today. For a newborn with fever, go to hospital immediately.",
        "action_hi": "Aaj hi doctor se sampark karein. Nayi janme baby ko bukhar ho to turant hospital jayein.",
        "action_bn": "আজই ডাক্তারের সাথে কথা বলুন। নবজাতকের জ্বর হলে সঙ্গে সঙ্গে হাসপাতালে যান।",
        "steps_en": ["Record temperature", "Note other symptoms", "Keep the baby warm but not overheated", "Seek same-day care"],
    },
    {
        "id": "leg_swelling",
        "match": ["leg swelling", "one leg", "leg pain", "dard in leg", "पैर में सूजन", "পা ফোলা"],
        "stage": "postpartum",
        "urgency": "emergency",
        "reason_en": "One-sided leg swelling or pain after birth can be a blood clot (DVT), which is serious.",
        "reason_hi": "Janam ke baad ek pair mein sujan ya dard blood clot (DVT) ho sakta hai — gambhir hai.",
        "reason_bn": "প্রসবের পর এক পা ফোলা বা ব্যথা রক্ত জমাট (DVT) হতে পারে — এটি গুরুতর।",
        "action_en": "Go to emergency care now. Do not massage the leg.",
        "action_hi": "Abhi emergency mein jayein. Pair ko massage na karein.",
        "action_bn": "এখনই জরুরি যত্নে যান। পা ম্যাসাজ করবেন না।",
        "steps_en": ["Go to emergency care", "Do not massage the leg", "Note when swelling started", "Avoid long travel"],
    },
    {
        "id": "mental_health",
        "match": ["suicidal", "harm myself", "harm the baby", "khud ko", "बच्चे को नुकसान", "নিজের ক্ষতি", "শিশুর ক্ষতি", " thoughts of harming"],
        "stage": "pregnancy,postpartum",
        "urgency": "emergency",
        "reason_en": "Thoughts of harming yourself or your baby are a psychiatric emergency. Help is available and you deserve support now.",
        "reason_hi": "Khud ya baby ko nuksan pahunchane ke vichaar psychiatric emergency hain. Abhi madad mil sakti hai — aap support ki hakdar hain.",
        "reason_bn": "নিজের বা শিশুর ক্ষতি করার চিন্তা মানসিক জরুরি অবস্থা। এখনই সাহায্য পাওয়া যায় — আপনি সাহায্যের অধিকারী।",
        "action_en": "Call emergency services or a mental-health helpline NOW. Tell someone you trust immediately. You are not alone.",
        "action_hi": "Abhi emergency ya mental-health helpline call karein. Kisi bharose wale ko turant batayein. Aap akeli nahi hain.",
        "action_bn": "এখনই জরুরি বা মানসিক স্বাস্থ্য হেল্পলাইন কল করুন। বিশ্বস্ত কাউকে সঙ্গে সঙ্গে বলুন। আপনি একা নন।",
        "steps_en": ["Call emergency services or helpline", "Tell a trusted person now", "Do not stay alone", "Remove access to harmful means"],
    },
    {
        "id": "newborn_breathing",
        "match": ["baby not breathing", "baby blue", "blue lips", "gasping", "শিশুর শ্বাস", "বেবি নীল"],
        "stage": "newborn",
        "urgency": "emergency",
        "reason_en": "A newborn struggling to breathe or turning blue is a critical emergency.",
        "reason_hi": "Naye janme baby ko saans lene mein dikkat ya hoth neele hona bahut gambhir emergency hai.",
        "reason_bn": "নবজাতকের শ্বাসকষ্ট বা ঠোঁট নীল হওয়া অত্যন্ত গুরুতর জরুরি অবস্থা।",
        "action_en": "Call emergency services immediately. Keep the baby warm and on their side; do not give food or water.",
        "action_hi": "Turant emergency call karein. Baby ko garam rakhein aur side par litayein; khaana ya paani na dein.",
        "action_bn": "সঙ্গে সঙ্গে জরুরি পরিষেবা কল করুন। শিশুকে উষ্ণ রাখুন ও পাশে শুইয়ে দিন; খাবার বা জল দেবেন না।",
        "steps_en": ["Call emergency services", "Keep baby warm", "Place on side", "Nothing by mouth"],
    },
    {
        "id": "newborn_poor_feeding",
        "match": ["not feeding", "won't feed", "poor feeding", "baby not sucking", "খাওয়া না", "খেতে না", "stops feeding"],
        "stage": "newborn",
        "urgency": "urgent",
        "reason_en": "A newborn who will not feed can become unwell quickly and needs same-day assessment.",
        "reason_hi": "Naya janma baby jo feed nahi kar raha, jaldi bimaar ho sakta hai — aaj hi jaanch chahiye.",
        "reason_bn": "নবজাতক যে খাচ্ছে না, দ্রুত অসুস্থ হতে পারে — আজই পরীক্ষা দরকার।",
        "action_en": "Contact a paediatrician or hospital today. Keep trying skin-to-skin and breastfeeding while arranging care.",
        "action_hi": "Aaj hi pediatrician ya hospital se sampark karein. Skin-to-skin aur breastfeeding continue karte rahein.",
        "action_bn": "আজই শিশু বিশেষজ্ঞ বা হাসপাতালের সাথে যোগাযোগ করুন। স্কিন-টু-স্কিন ও বুকের দুধ চালিয়ে যান।",
        "steps_en": ["Try skin-to-skin", "Offer the breast frequently", "Count wet nappies", "Seek same-day review"],
    },
    {
        "id": "jaundice",
        "match": ["jaundice", "yellow", "peela", "पीला", "হলুদ", "yellow skin"],
        "stage": "newborn",
        "urgency": "urgent",
        "reason_en": "Jaundice in the first 24 hours, or worsening jaundice, needs urgent assessment in a newborn.",
        "reason_hi": "Pehle 24 ghanton mein peeliya ya badhta peeliya, naye baby mein turant jaanch chahiye.",
        "reason_bn": "জন্মের প্রথম ২৪ ঘণ্টায় হলুদ বা বৃদ্ধি পাওয়া হলুদ নবজাতকের জরুরি পরীক্ষা প্রয়োজন।",
        "action_en": "Contact your paediatrician today. Jaundice appearing within 24 hours is an emergency.",
        "action_hi": "Aaj hi pediatrician se sampark karein. 24 ghanton ke andar peeliya emergency hai.",
        "action_bn": "আজই শিশু বিশেষজ্ঞের সাথে কথা বলুন। ২৪ ঘণ্টার মধ্যে হলুদ জরুরি।",
        "steps_en": ["Note when yellow colour appeared", "Check if it is spreading", "Keep feeding frequently", "Seek same-day care"],
    },
    {
        "id": "cord_infection",
        "match": ["cord", "navel", "pus", " redness", "लाल", "নাভি", "naff", "umbilical"],
        "stage": "newborn",
        "urgency": "urgent",
        "reason_en": "Redness, pus or smell around the umbilical cord with fever can mean infection and needs prompt care.",
        "reason_hi": "Nabhi ke aas-paas lalima, pus ya gand ke saath bukhar infection ka sanket hai — jaldi care chahiye.",
        "action_en": "Contact your paediatrician today. Keep the cord area clean and dry; do not apply substances.",
        "action_hi": "Aaj hi pediatrician se sampark karein. Nabhi ko saaf aur sukha rakhein; kuch na lagayein.",
        "action_bn": "আজই শিশু বিশেষজ্ঞের সাথে কথা বলুন। নাভির জায়গা পরিষ্কার ও শুকনো রাখুন; কিছু লাগাবেন না।",
        "steps_en": ["Keep area clean and dry", "Do not apply oil or powder", "Note fever or pus", "Seek same-day care"],
    },
]

# ---------------------------------------------------------------------------
# Education by stage / week. Plain language, source-tagged, no dosages.
# ---------------------------------------------------------------------------
EDUCATION = {
    "planning": [
        {"title_en": "Start folic acid early", "title_hi": "Folic acid pehle se shuru karein", "title_bn": "ফলিক অ্যাসিড আগে থেকে শুরু করুন",
         "body_en": "Your doctor may recommend folic acid before pregnancy to lower the chance of birth defects. Ask them about the right dose for you — do not self-dose.",
         "body_hi": "Doctor pregnancy se pehle folic acid suggest kar sakte hain. Apne liye sahi dose unse poochhein — khud se na lein.",
         "body_bn": "গর্ভধারণের আগে ডাক্তার ফলিক অ্যাসিড সুপারিশ করতে পারেন। আপনার জন্য সঠিক ডোজ তাদের জিজ্ঞাসা করুন — নিজে খাবেন না।",
         "source": "WHO / MoHFW preconception guidance"},
        {"title_en": "Review medicines and conditions", "title_hi": "Dawayein aur bimariyon ki samiksha", "title_bn": "ওষুধ ও রোগের পর্যালোচনা",
         "body_en": "If you have diabetes, hypertension or thyroid disease, or take regular medicines, speak to a doctor before pregnancy. Some medicines need to be changed.",
         "body_hi": "Agar diabetes, BP ya thyroid hai ya roz dawayein leti hain, pregnancy se pehle doctor se baat karein. Kuch dawayein badalni pad sakti hain.",
         "body_bn": "ডায়াবেটিস, উচ্চ রক্তচাপ বা থাইরয়েড থাকলে বা নিয়মিত ওষুধ খেলে গর্ভধারণের আগে ডাক্তারের সাথে কথা বলুন।",
         "source": "WHO preconception care"},
    ],
    "t1": [
        {"title_en": "Your first antenatal visit", "title_hi": "Pehli antenatal visit", "title_bn": "প্রথম প্রসব-পূর্ব সাক্ষাৎ",
         "body_en": "In the first trimester, book your first antenatal appointment. Expect blood and urine tests and an early ultrasound to confirm the pregnancy and dates.",
         "body_hi": "Pehle trimester mein pehli antenatal appointment book karein. Blood aur urine tests aur early ultrasound hote hain.",
         "body_bn": "প্রথম ট্রাইমিস্টারে প্রথম প্রসব-পূর্ব সাক্ষাৎ নির্ধারণ করুন। রক্ত ও প্রস্রাব পরীক্ষা এবং early ultrasound হয়।",
         "source": "WHO ANC guidelines / NHM"},
        {"title_en": "Nausea is common", "title_hi": "Matli aam baat hai", "title_bn": "বমি ভাব সাধারণ",
         "body_en": "Nausea in early pregnancy is common. Small, frequent meals and fluids may help. If you cannot keep fluids down or feel very weak, contact your doctor.",
         "body_hi": "Shuruat ki pregnancy mein matli aam hai. Chhote, baar baar khane aur pani se madad mil sakti hai. Pani na tik paye ya bahut kamzori ho to doctor se sampark karein.",
         "body_bn": "গর্ভের শুরুতে বমি ভাব সাধারণ। ছোট ঘন ঘন খাবার ও তরল সাহায্য করতে পারে। পানি ধরে না রাখলে ডাক্তারের সাথে কথা বলুন।",
         "source": "WHO / FIGO patient guidance"},
    ],
    "t2": [
        {"title_en": "Screening tests come due", "title_hi": "Screening tests ka samay", "title_bn": "স্ক্রিনিং পরীক্ষার সময়",
         "body_en": "Around the second trimester, ask about anaemia screening, blood pressure, gestational diabetes screening and the fetal anomaly ultrasound. Your doctor will decide what applies to you.",
         "body_hi": "Dusre trimester mein anaemia, BP, gestational diabetes aur fetal anomaly ultrasound ke baare mein doctor se poochhein. Doctor hi tay karenge kya aapke liye zaroori hai.",
         "body_bn": "দ্বিতীয় ট্রাইমিস্টারে অ্যানিমিয়া, রক্তচাপ, গেস্টেশনাল ডায়াবেটিস ও ভ্রূণ অস্বাভাবিকতা আল্ট্রাসাউন্ড সম্পর্কে ডাক্তারের সাথে কথা বলুন।",
         "source": "WHO ANC / FOGSI"},
        {"title_en": "Notice fetal movements", "title_hi": "Baby ki hulchul par dhyan dein", "title_bn": "শিশুর নড়াচড়া লক্ষ্য করুন",
         "body_en": "Many mothers feel movements between 18–25 weeks. Get to know your baby's normal pattern. If movements become much less later on, contact your maternity unit the same day.",
         "body_hi": "Anni maaaen 18–25 weeks ke beech hulchul mehsoos karti hain. Apne baby ka normal pattern pehchaniye. Baad mein hulchul bahut kam ho to aaj hi maternity unit se sampark karein.",
         "body_bn": "অনেক মা ১৮–২৫ সপ্তাহের মধ্যে নড়াচড়া অনুভব করেন। শিশুর স্বাভাবিক রীতিনীতি জানুন। পরে নড়াচড়া অনেক কমলে আজই যোগাযোগ করুন।",
         "source": "WHO / FIGO"},
    ],
    "t3": [
        {"title_en": "Plan your birth", "title_hi": "Janam ki yojana", "title_bn": "প্রসবের পরিকল্পনা",
         "body_en": "Discuss hospital choice, transport, who will be with you, and what to do if labour starts. Pack your documents and baby's first clothes in advance.",
         "body_hi": "Hospital, transport, saath rehne wale vyakti aur labour shuru hone par kya karna hai — ye sab pehle tay karein. Documents aur baby ke kapde pehle se pack karein.",
         "body_bn": "হাসপাতাল, পরিবহন, সঙ্গে থাকবেন কে এবং প্রসব শুরু হলে কী করবেন — আগে ঠিক করুন। নথি ও শিশুর কাপড় আগে প্যাক করুন।",
         "source": "WHO birth preparedness"},
        {"title_en": "When to go to hospital", "title_hi": "Hospital kab jayein", "title_bn": "কখন হাসপাতালে যাবেন",
         "body_en": "Go to hospital if your waters break, you have regular strong contractions, bleeding, reduced movements, or severe headache/vision changes. Do not delay.",
         "body_hi": "Agar pani phate, regular tez contractions ho, bleeding ho, hulchul kam ho, ya tez sir dard/dhundhla dikhna ho — turant hospital jayein. Deri na karein.",
         "body_bn": "জল ভাঙলে, নিয়মিত শক্ত সংকোচন, রক্তপাত, নড়াচড়া কমা বা তীব্র মাথাব্যথা/ঝাপসা দৃষ্টি হলে হাসপাতালে যান। বিলম্ব করবেন না।",
         "source": "WHO / MoHFW"},
    ],
    "postpartum": [
        {"title_en": "Rest and recovery", "title_hi": "Aaram aur recovery", "title_bn": "বিশ্রাম ও পুনরুদ্ধার",
         "body_en": "After birth your body needs time. Accept help with chores, sleep when the baby sleeps, eat and drink regularly. Gentle movement is usually fine after a vaginal birth — ask your doctor about caesarean recovery.",
         "body_hi": "Janam ke baad sharir ko samay chahiye. Ghar ke kaam mein madad lein, baby jab soye aap bhi soyein, khana-pani regular lein. Normal janam ke baad halki halchal theek hai — C-section ke liye doctor se poochhein.",
         "body_bn": "প্রসবের পর শরীরের সময় লাগে। কাজের সাহায্য নিন, শিশু ঘুমালে আপনিও ঘুমান, নিয়মিত খান ও পান করুন। সাধারণ প্রসবের পর হালকা নড়াচড়া চলতে পারে — সিজারের ক্ষেত্রে ডাক্তারের সাথে কথা বলুন।",
         "source": "WHO postnatal care"},
        {"title_en": "Breastfeeding support is normal", "title_hi": "Breastfeeding mein madad lena normal hai", "title_bn": "বুকের দুধে সাহায্য নেওয়া স্বাভাবিক",
         "body_en": "Early skin-to-skin and breastfeeding help establish milk. Sore nipples or engorgement are common — a lactation counsellor can help. If you have fever, breast redness and pain, seek care for possible mastitis.",
         "body_hi": "Jaldi skin-to-skin aur breastfeeding se dudh banne mein madad milti hai. Nipple dard ya sujan aam hai — lactation counsellor madad kar sakta hai. Bukhar, lalima aur dard ho to mastitis ke liye care lein.",
         "body_bn": "early স্কিন-টু-স্কিন ও বুকের দুধ দুধ উৎপাদনে সাহায্য করে। ব্যথা বা ফোলা সাধারণ — সাহায্য নিন। জ্বর, লালচে ভাব ও ব্যথা হলে মাস্টাইটিসের যত্ন নিন।",
         "source": "WHO infant feeding"},
        {"title_en": "Emotional health matters", "title_hi": "Maanasik sehat bhi zaroori", "title_bn": "মানসিক স্বাস্থ্যও গুরুত্বপূর্ণ",
         "body_en": "Feeling tearful or anxious in the first weeks is common. But if sadness, anxiety, or thoughts of harming yourself or the baby persist or feel overwhelming, tell someone and seek help now — this is treatable.",
         "body_hi": "Pehle hafton mein bhavuk ya chinta hona aam hai. Lekin agar yeh gambhir ho ya khud/baby ko nuksan ke vichaar aayein, abhi kisi ko batayein aur madad lein — ye ilaaj yogya hai.",
         "body_bn": "প্রথম সপ্তাহে কাঁদা বা উদ্বেগ সাধারণ। কিন্তু দুঃখ বা নিজের/শিশুর ক্ষতির চিন্তা ক্রমাগত বা অসহনীয় হলে এখনই কাউকে বলুন ও সাহায্য নিন — এর চিকিৎসা আছে।",
         "source": "WHO maternal mental health"},
    ],
    "newborn": [
        {"title_en": "Keep the baby warm", "title_hi": "Baby ko garam rakhein", "title_bn": "শিশুকে উষ্ণ রাখুন",
         "body_en": "Newborns cannot regulate temperature well. Use skin-to-skin contact, a warm room and appropriate clothing. Avoid overheating.",
         "body_hi": "Naye baby ka sharir taptama control nahi kar paata. Skin-to-skin, garam kamra aur upayukt kapde istemal karein. Zyada garam na karein.",
         "body_bn": "নবজাতক তাপমাত্রা নিয়ন্ত্রণ করতে পারে না। স্কিন-টু-স্কিন, উষ্ণ ঘর ও উপযুক্ত পোশাক ব্যবহার করুন। অতি উত্তাপ এড়িয়ে চলুন।",
         "source": "WHO newborn care"},
        {"title_en": "Cord care: keep it clean and dry", "title_hi": "Nabhi ki dekhbhal: saaf aur sukha", "title_bn": "নাভির যত্ন: পরিষ্কার ও শুকনো",
         "body_en": "Keep the umbilical cord clean and dry. Do not apply oil, powder, herbs or anything to the stump. Seek care for redness, pus or smell with fever.",
         "body_hi": "Nabhi ko saaf aur sukha rakhein. Tel, powder ya jadi-booti kuch na lagayein. Lalima, pus ya gand ke saath bukhar ho to care lein.",
         "body_bn": "নাভি পরিষ্কার ও শুকনো রাখুন। তেল, গুঁড়ো বা ভেষজ কিছু লাগাবেন না। লালচে ভাব, পুঁজ বা গন্ধের সাথে জ্বর হলে যত্ন নিন।",
         "source": "WHO newborn care"},
        {"title_en": "Safe sleep", "title_hi": "Surakshit neend", "title_bn": "নিরাপদ ঘুম",
         "body_en": "Place the baby on their back on a firm, flat surface. Keep pillows, loose blankets and soft toys away from the face. Avoid bed-sharing with an adult on a soft mattress.",
         "body_hi": "Baby ko peeth ke bal seedhi, pakki satah par litayein. Takhiya, dhile kambal aur navar jagah se door rakhein. Naram gaddon par adult ke saath na sulayein.",
         "body_bn": "শিশুকে পিঠের দিকে শক্ত, সমতল জায়গায় শুইয়ে দিন। বালিশ, আলগা কম্বল ও নরম খেলনা মুখ থেকে দূরে রাখুন। নরম বিছানায় বড়দের সাথে শুইয়ে দেবেন না।",
         "source": "UNICEF / WHO safe sleep"},
    ],
    "child": [
        {"title_en": "Complementary feeding around 6 months", "title_hi": "6 mahine ke aas-paas khana shuru", "title_bn": "প্রায় ৬ মাসে পরিপূরক খাবার",
         "body_en": "Around 6 months, start nutritious complementary foods alongside continued breastfeeding. Include a variety of foods; avoid added salt and sugar. Ask your doctor about vitamin supplementation where indicated.",
         "body_hi": "6 mahine ke aas-paas breastfeeding ke saath saath poshtik khana shuru karein. Kismein vibhinnata rakhein; namak-cheeni na daalein. Vitamin ke liye doctor se poochhein.",
         "body_bn": "প্রায় ৬ মাসে বুকের দুধের পাশাপাশি পুষ্টিকর পরিপূরক খাবার শুরু করুন। বিভিন্ন খাবার দিন; লবণ ও চিনি এড়িয়ে চলুন। ভিটামিনের জন্য ডাক্তারের সাথে কথা বলুন।",
         "source": "WHO infant feeding"},
        {"title_en": "Watch developmental milestones", "title_hi": "Vikas ke sanket dekhein", "title_bn": "বিকাশের লক্ষণ লক্ষ্য করুন",
         "body_en": "Notice if your baby loses a skill they had, or is not reaching expected milestones for age. Early support helps. Ask your paediatrician if you are worried — it is always okay to ask.",
         "body_hi": "Agar baby koi seekhi hui cheez bhool jaye ya umar ke hisaab se milestones na paye, dhyan dein. Jaldi madad milti hai. Chinta ho to pediatrician se poochhein — poochhna hamesha theek hai.",
         "body_bn": "শিশু আগে শেখা কোনো ক্ষমতা হারালে বা বয়স-anuyayী মাইলস্টোন না পেলে লক্ষ্য করুন।Early সাহায্য কাজে দেয়। উদ্বেগ হলে শিশু বিশেষজ্ঞের সাথে কথা বলুন — জিজ্ঞাসা করা সবসময় ঠিক।",
         "source": "WHO / CDC milestones"},
    ],
}

# ---------------------------------------------------------------------------
# Traditional practice evaluator — respectful, evidence-tagged, never ridicules.
# ---------------------------------------------------------------------------
TRADITIONS = [
    {
        "name": "Saffron for a fairer baby", "name_hi": "Saffron se gora baby", "name_bn": "জাফরানে ফর্সা শিশু",
        "belief_en": "Eating saffron during pregnancy will make the baby fairer.", "belief_hi": "Pregnancy mein saffron khane se baby gora hoga.", "belief_bn": "গর্ভকালে জাফরান খেলে শিশু ফর্সা হবে।",
        "why_en": "Skin colour is deeply valued in many families, and saffron is a prized, expensive ingredient.", "why_hi": "Rang ko bahut mahatva milta hai aur saffron mehenga, izzat wala masala hai.", "why_bn": "গাত্রবর্ণের প্রতি অনেক পরিবারে গুরুত্ব দেওয়া হয় এবং জাফরান দামি ও সম্মানিত উপাদান।",
        "evidence_en": "A baby's skin colour is inherited from their parents' genes. No food, including saffron, can change it. Saffron in cooking amounts is generally safe, but high-dose supplements are not recommended in pregnancy.", "evidence_hi": "Baby ka rang maa-bap ke genes se aata hai. Koi bhi khana, saffron bhi, rang nahi badal sakta. Khane ki matra mein saffron aam taur par safe hai, par zyada matra ke supplements pregnancy mein na lein.", "evidence_bn": "শিশুর গাত্রবর্ণ বাবা-মায়ের জিন থেকে আসে। কোনো খাবার, এমনকি জাফরানও তা বদলাতে পারে না। রান্নার পরিমাণে জাফরান সাধারণত নিরাপদ, কিন্তু বেশি মাত্রার সাপ্লিমেন্ট গর্ভে নেওয়া উচিত নয়।",
        "benefit": "none", "benefit_en": "No proven benefit for skin colour or baby health.", "risk_en": "Wasted money; high-dose saffron supplements may be unsafe.", "verdict": "insufficient",
        "verdict_en": "Reasonable in food amounts, but the claimed benefit is unproven.", "alternative_en": "Enjoy saffron as a flavouring if you wish. Accept that skin colour is genetic.", "doctor_en": "Before taking any concentrated supplement or herbal medicine in pregnancy.", "source": "Genetics; general food-safety guidance",
    },
    {
        "name": "Milk with ghee in pregnancy", "name_hi": "Pregnancy mein doodh aur ghee", "name_bn": "গর্ভে দুধ ও ঘি",
        "belief_en": "Drinking milk with ghee builds strength and a healthy baby.", "belief_hi": "Doodh mein ghee milane se taqat aur healthy baby hota hai.", "belief_bn": "দুধে ঘি মিশিয়ে খেলে শক্তি ও সুস্থ শিশু হয়।",
        "why_en": "Milk and ghee are traditional nourishing foods associated with strength.", "why_hi": "Doodh aur ghee paramparik poshtik aahar hain jinhe taqat se joda jata hai.", "why_bn": "দুধ ও ঘি ঐতিহ্যবাহী পুষ্টিকর খাবার যা শক্তির সাথে যুক্ত।",
        "evidence_en": "Milk provides protein and calcium; ghee is mostly fat. As part of a balanced diet this is generally safe for most people. It does not guarantee a healthier baby, and excess calories/ghee can be unhelpful, especially with gestational diabetes.",
        "evidence_hi": "Doodh mein protein aur calcium hai; ghee zyadatar charbi hai. Santulit aahar ke hissa ke taur par ye zyadatar logon ke liye safe hai. Isse healthy baby pakka nahi hota; zyada calorie ghee nuksan kar sakta hai, khas kar gestational diabetes mein.",
        "evidence_bn": "দুধে প্রোটিন ও ক্যালসিয়াম আছে; ঘি প্রধানত চর্বি। সুষম খাদ্যের অংশ হিসেবে এটি বেশিরভাগের জন্য নিরাপদ। এতে সুস্থ শিশু নিশ্চিত হয় না; অতিরিক্ত ক্যালোরি ক্ষতিকারক হতে পারে, বিশেষ করে গেস্টেশনাল ডায়াবেটিসে।",
        "benefit": "partial", "benefit_en": "Nutritious as food; no special pregnancy benefit proven.", "risk_en": "Excess saturated fat/calories; problematic if gestational diabetes.", "verdict": "safe",
        "verdict_en": "Generally safe in normal food amounts; not a medical treatment.", "alternative_en": "Plain milk or yogurt with a balanced diet; limit ghee if advised by your doctor.", "doctor_en": "If you have gestational diabetes, high cholesterol or weight concerns.", "source": "General nutrition evidence; WHO healthy diet",
    },
    {
        "name": "Papaya and pineapple to be avoided", "name_hi": "Papaya aur pineapple na khayein", "name_bn": "পেঁপে ও আনারস এড়িয়ে চলা",
        "belief_en": "Ripe or raw papaya and pineapple must be avoided in pregnancy because they cause miscarriage.", "belief_hi": "Pregnancy mein papaya aur pineapple bilkul na khayein — isse garbhapat hota hai.", "belief_bn": "গর্ভে পেঁপে ও আনারস একেবারে খাবেন না — এতে গর্ভপাত হয়।",
        "why_en": "A long-standing belief that certain fruits are 'hot' or abortifacient.", "why_hi": "Purana vichaar ki kuch phal 'garam' ya garbhapat karne wale hote hain.", "why_bn": "পুরোনো বিশ্বাস যে কিছু ফল 'গরম' বা গর্ভপাতকারী।",
        "evidence_en": "Ripe papaya and pineapple are safe as part of a varied diet. Unripe (raw) papaya contains latex, which some guidelines advise limiting in large amounts in pregnancy. There is no good evidence that normal food amounts cause miscarriage.", "evidence_hi": "Pakka papaya aur pineapple santulit aahar mein safe hain. Kacha papaya mein latex hota hai — kuch guidelines pregnancy mein zyada matra se parhez kehte hain. Normal khane se garbhapat ka achha proof nahi hai.", "evidence_bn": "পাকা পেঁপে ও আনারস সুষম খাদ্যে নিরাপদ। কাঁচা পেঁপেতে ল্যাটেক্স আছে — কিছু নির্দেশিকা গর্ভে বেশি পরিমাণ এড়াতে বলে। সাধারণ খেলে গর্ভপাতের ভালো প্রমাণ নেই।",
        "benefit": "none", "benefit_en": "Avoidance of ripe fruit has no proven benefit.", "risk_en": "Unnecessary dietary restriction; raw papaya latex in large amounts may be best limited.", "verdict": "safe",
        "verdict_en": "Ripe fruit is generally safe; limit large amounts of raw papaya.", "alternative_en": "Eat ripe papaya and pineapple in moderation as part of a varied diet.", "doctor_en": "If you have had a previous miscarriage or a high-risk pregnancy — follow your doctor's advice.", "source": "Food-safety guidance; no evidence of abortifacient effect at food doses",
    },
    {
        "name": "Abdominal binding after delivery", "name_hi": "Janam ke baad pet bandhna", "name_bn": "প্রসবের পর পেট বাঁধা",
        "belief_en": "Tying the abdomen after birth restores the figure and supports the body.", "belief_hi": "Janam ke baad pet bandhne se figure aur sharir sambhalta hai.", "belief_bn": "প্রসবের পর পেট বাঁধলে শরীর ও আকৃতি ঠিক হয়।",
        "why_en": "A common postpartum practice believed to reshape the body and provide comfort.", "why_hi": "Postpartum ye aam hai — sharir ko aakar dena aur aaram dena.", "why_bn": "প্রসব-পরবর্তী এটি সাধারণ — শরীরের আকৃতি ও আরামের জন্য।",
        "evidence_en": "There is no good evidence that abdominal binding restores the figure. Tight binding can restrict breathing, reduce circulation, put pressure on the healing uterus/bladder and worsen pain or incontinence. It may interfere with healing after a caesarean.",
        "evidence_hi": "Pet bandhne se figure wapas aata hai — iska achha proof nahi. Bahut kas kar bandhne se saans, rakt-pravah aur dard badh sakta hai; C-section ke baad bhi harm kar sakta hai.",
        "evidence_bn": "পেট বাঁধলে আকৃতি ফিরে আসে — এর ভালো প্রমাণ নেই। আঁটসাঁট বাঁধলে শ্বাস, রক্ত সঞ্চালন ও ব্যথা বাড়তে পারে; সিজারের পরও ক্ষতি হতে পারে।",
        "benefit": "none", "benefit_en": "No proven benefit for healing or figure restoration.", "risk_en": "Restricted breathing, impaired circulation, pain, possible interference with healing.", "verdict": "harmful",
        "verdict_en": "Potentially harmful if tight — especially after caesarean.", "alternative_en": "Gentle movement, a supportive (not tight) belly band only if comfortable and approved by your doctor, and pelvic-floor exercises when advised.", "doctor_en": "Before using any abdominal binder after a caesarean or if you have pain, bleeding or incontinence.", "source": "General postpartum safety reasoning; no evidence of benefit",
    },
    {
        "name": "Giving honey or ghutti to newborns", "name_hi": "Naye baby ko honey ya ghutti", "name_bn": "নবজাতকের মধু বা ঘুটি দেওয়া",
        "belief_en": "A drop of honey or ghutti is given before breastfeeding to cleanse the stomach or bring good health.", "belief_hi": "Breastfeeding se pehle honey ya ghutti di jaati hai pet saaf karne aur achhe swasthya ke liye.", "belief_bn": "বুকের দুধের আগে পেট পরিষ্কার ও স্বাস্থ্যের জন্য মধু বা ঘুটি দেওয়া হয়।",
        "why_en": "A widespread traditional ritual to 'open' the baby's system before milk.", "why_hi": "Doodh se pehle baby ka 'system kholne' ka purana ritual.", "why_bn": "দুধের আগে শিশুর 'সিস্টেম খোলার' পুরোনো রীতি।",
        "evidence_en": "Honey can contain Clostridium botulinum spores, which can cause infant botulism — a rare but serious, potentially fatal illness in babies under 12 months. There is no proven benefit. Nothing should be given before breast milk except medicines prescribed by a doctor.", "evidence_hi": "Honey mein botulism ke beej ho sakte hain jo 12 mahine se chhote baby mein gambhir, jaanleva bimari kar sakte hain. Koi fayda nahi. Doctor ki dawayi chhod kar kuch bhi dene se pehle breast milk hi dein.", "evidence_bn": "মধুতে বোটুলিজমের বীজ থাকতে পারে যা ১২ মাসের কম বয়সী শিশutes গুরুতর, মারাত্মক রোগ করতে পারে। কোনো উপকার নেই। ডাক্তারের ওষুধ ছাড়া বুকের দুধের আগে কিছু দেবেন না।",
        "benefit": "none", "benefit_en": "No proven benefit.", "risk_en": "Infant botulism, a life-threatening illness, in babies under 12 months.", "verdict": "contraindicated",
        "verdict_en": "Contraindicated — never give honey to a baby under 12 months.", "alternative_en": "Put the baby to the breast as soon as possible after birth; only give medicines a doctor prescribes.", "doctor_en": "Immediately if a newborn has poor feeding, weakness, constipation or difficulty breathing after taking honey.", "source": "CDC / WHO infant feeding — honey and infant botulism",
    },
    {
        "name": "Applying substances to the umbilical cord", "name_hi": "Nabhi par tel ya powder lagana", "name_bn": "নাভিতে তেল বা গুঁড়ো লাগানো",
        "belief_en": "Oil, powder, herbal paste or ash is applied to the cord stump to dry or protect it.", "belief_hi": "Nabhi ko sukhane ya bachane ke liye tel, powder, jadi ya raakh lagayi jaati hai.", "belief_bn": "নাভি শুকনো বা রক্ষার জন্য তেল, গুঁড়ো, ভেষজ বা ছাই লাগানো হয়।",
        "why_en": "Traditional practice aimed at drying the cord and preventing infection.", "why_hi": "Purana tareeka nabhi sukhane aur infection se bachane ka.", "why_bn": "নাভি শুকনো ও সংক্রমণ থেকে বাঁচানোর পুরোনো উপায়।",
        "evidence_en": "The cord stump heals best when kept clean and dry and exposed to air. Applying substances can introduce bacteria, delay healing and cause infection. In some places, certain traditional applications have been linked to neonatal tetanus.", "evidence_hi": "Nabhi sabse achhi tab bhari jab saaf, sukhi aur hawa mein rahe. Kuch lagane se bacteria aa sakte hain, bharne mein deri aur infection ho sakta hai. Kuch paramparik cheezon se neonatal tetanus bhi juda hai.", "evidence_bn": "নাভি পরিষ্কার, শুকনো ও বাতাসে রাখলে সবচেয়ে ভালো শায়। কিছু লাগালে ব্যাকটেরিয়া ঢুকে সংক্রমণ হতে পারে। কিছু ঐতিহ্যবাহী প্রয়োগ নবজাতক টিটেনাসের সাথে যুক্ত।",
        "benefit": "none", "benefit_en": "No proven benefit over clean, dry care.", "risk_en": "Infection, delayed healing, tetanus risk with contaminated substances.", "verdict": "harmful",
        "verdict_en": "Potentially harmful — keep the cord clean and dry only.", "alternative_en": "Clean, dry cord care; fold the diaper below the stump; give a sponge bath until it falls off.", "doctor_en": "If there is redness, pus, bad smell, swelling or fever.", "source": "WHO newborn care / neonatal tetanus prevention",
    },
    {
        "name": "Delaying the newborn's first bath", "name_hi": "Naye baby ka pehla naamпани deri se", "name_bn": "নবজাতকের প্রথম স্নান বিলম্বে",
        "belief_en": "The newborn should not be bathed for several days to protect health.", "belief_hi": "Naye baby ko kuch din tak nahana nahi chahiye — sehat ke liye.", "belief_bn": "নবজাতককে কয়েক দিন স্নান করা উচিত নয় — স্বাস্থ্যের জন্য।",
        "why_en": "Concern about chilling, jaundice or weakness after birth.", "why_hi": "Thand, peeliya ya kamzori ka dar.", "why_bn": "ঠান্ডা, হলুদ বা দুর্বলতার ভয়।",
        "evidence_en": "WHO recommends delaying the first bath for at least 24 hours where possible, which helps temperature regulation and breastfeeding. After that, gentle, warm bathing with good drying is fine. Prolonged avoidance of bathing is not necessary if the baby is kept clean and warm.",
        "evidence_hi": "WHO kehta hai pehla naamilapani 24 ghante tak delay karna (jab possible ho) — isse taptama aur breastfeeding mein madad milti hai. Uske baad halka, garam snan aur achha sukhana theek hai. Dinon tak bilkul na nahana zaroori nahi agar baby saaf aur garam rahe.",
        "evidence_bn": "WHO প্রথম স্নান ২৪ ঘণ্টা বিলম্বিত করার সুপারিশ করে (যখন সম্ভব) — এটি তাপমাত্রা ও বুকের দুধে সাহায্য করে। তারপর হালকা উষ্ণ স্নান ও ভালো করে শুকনো করা চলে। পরিচ্ছন্ন ও উষ্ণ রাখলে দিনের পর দিন না ধোয়া জরুরি নয়।",
        "benefit": "partial", "benefit_en": "A short delay (~24h) is supported; longer delay has no proven benefit.", "risk_en": "Poor hygiene if bathing is avoided entirely for many days.", "verdict": "safe",
        "verdict_en": "A ~24-hour delay is reasonable; gentle bathing after that is safe.", "alternative_en": "Delay the first bath about 24 hours, then use warm water and dry the baby thoroughly.", "doctor_en": "If the baby has low temperature, jaundice or feeding problems.", "source": "WHO newborn recommendations",
    },
    {
        "name": "Oil massage for mother/baby", "name_hi": "Maa ya baby ka tel massage", "name_bn": "মা বা শিশুর তেল ম্যাসাজ",
        "belief_en": "Regular oil massage strengthens the body and improves sleep/growth.", "belief_hi": "Roz tel massage se sharir majboot, neeth aur vikas achha hota hai.", "belief_bn": "নিয়মিত তেল ম্যাসাজে শরীর শক্ত, ঘুম ও বৃদ্ধি ভালো হয়।",
        "why_en": "A cherished bonding and self-care ritual in many Indian households.", "why_hi": "Pyar aur apni dekhbhal ka pyaara ritual.", "why_bn": "স্নেহ ও আত্ম-যত্নের প্রিয় রীতি।",
        "evidence_en": "Massage can promote relaxation and bonding. Small studies in preterm infants show possible weight-gain benefits with specific oils and techniques, but evidence in healthy term babies is limited. Avoid strong/unknown herbal oils on newborn skin; use plain, gentle oils and patch-test.",
        "evidence_hi": "Massase se aaram aur bonding badhta hai. Chhote adhayayan mein premature babyon mein kuch phayda dikha hai, par healthy babyon mein proof kam hai. Naye baby ki tvacha par tez/anjan jadi tel na lagayein — simple tel istemal karein.",
        "evidence_bn": "ম্যাসাজে শান্তি ও বন্ধন বাড়ে। ছোট গবেষণায় অকালজাত শিশুতে কিছু উপকার দেখা গেছে, কিন্তু সুস্থ শিশুতে প্রমাণ সীমিত। নবজাতকের ত্বকে শক্ত/অজানা ভেষজ তেল দেবেন না — সাদা, হালকা তেল ব্যবহার করুন।",
        "benefit": "partial", "benefit_en": "Relaxation/bonding supported; strong growth claims unproven.", "risk_en": "Skin irritation or reaction to herbal/essential oils; aspiration if oils given by mouth.", "verdict": "safe",
        "verdict_en": "Generally safe with simple oils; avoid medicated/essential oils on newborns.", "alternative_en": "Gentle massage with plain oil if the baby tolerates it; stop if the skin reacts.", "doctor_en": "If the baby develops a rash, or if you want to use herbal/medicated oils.", "source": "Limited pediatric massage research; general skin-safety guidance",
    },
    {
        "name": "Restricting movement in pregnancy", "name_hi": "Pregnancy mein kam halchal", "name_bn": "গর্ভে শারীরিক চলাচল কমানো",
        "belief_en": "Pregnant women should rest and avoid walking, bending or household work.", "belief_hi": "Pregnant mahila ko aaram karna chahiye — chalna, jhukna ya ghar ka kaam nahi.", "belief_bn": "গর্ভবতীকে বিশ্রাম নেওয়া উচিত — হাঁটা, নোয়া বা বাড়ির কাজ না করা।",
        "why_en": "Protection and fear of harm to the baby.", "why_hi": "Baby ko bachane aur nuksan ke dar se.", "why_bn": "শিশুকে রক্ষা ও ক্ষতির ভয়ে।",
        "evidence_en": "For uncomplicated pregnancies, regular moderate physical activity is generally safe and beneficial. Complete inactivity can worsen fitness, constipation, back pain and glucose control. Some high-risk conditions do require activity restrictions — follow your doctor.",
        "evidence_hi": "Bina complication wali pregnancy mein derdara madhyam vyayam aam taur par safe aur faydemand hai. Bilkol nishkriya rehne se kamzori, kabbaz, peeth dard aur sugar control bigad sakta hai. Kuch high-risk halaton mein doctor activity rok sakte hain — unki baat manein.",
        "evidence_bn": "জটিলতাহীন গর্ভে নিয়মিত মাঝারি শারীরিক কার্যকলাপ সাধারণত নিরাপদ ও উপকারী। সম্পূর্ণ নিষ্ক্রিয়তা শক্তি হ্রাস, কোষ্ঠকাঠিন্য ও রক্তচাপের সমস্যা বাড়াতে পারে। কিছু উচ্চ-ঝুকিমূলক অবস্থায় ডাক্তার নিষেধ করতে পারেন — তাদের মানুন।",
        "benefit": "partial", "benefit_en": "Moderate activity beneficial; complete rest not routinely needed.", "risk_en": "Deconditioning, constipation, worse glucose control with complete inactivity.", "verdict": "safe",
        "verdict_en": "Generally safe to stay moderately active unless your doctor says otherwise.", "alternative_en": "Walking, gentle stretching and normal activities within comfort; stop and seek advice for bleeding, pain, dizziness or contractions.", "doctor_en": "If you have a high-risk pregnancy, bleeding, placenta problems or preterm labour symptoms.", "source": "WHO physical activity in pregnancy",
    },
    {
        "name": "Herbal kadhas / medicines", "name_hi": "Jadi-booti kadha ya dawayein", "name_bn": "ভেষজ কাড়া বা ওষুধ",
        "belief_en": "Herbal decoctions (kadha) are taken to prevent illness, ease labour or 'cleanse' the body in pregnancy/postpartum.", "belief_hi": "Bimari se bachne, janam aasan karne ya sharir saaf karne ke liye kadha piya jata hai.", "belief_bn": "অসুস্থতা এড়াতে, সহজ প্রসব বা শরীর পরিষ্কারের জন্য কাড়া পান করা হয়।",
        "why_en": "Trust in traditional medicine and easy availability.", "why_hi": "Paramparic chikitsa par bharosa aur aasan upalabdhi.", "why_bn": "ঐতিহ্যবাহী চিকিৎসার প্রতি বিশ্বাস ও সহজ প্রাপ্যতা।",
        "evidence_en": "Many herbal products have not been tested for safety in pregnancy or breastfeeding, and some can be harmful or interact with medicines. Their contents and doses are often unstandardised. Never assume 'natural' means safe.", "evidence_hi": "Bahut jadi products ki pregnancy/breastfeeding mein suraksha test nahi hui — kuch nuksan kar sakte hain ya dawayon se interact kar sakte hain. Inki matra aur samagri aksar nishchit nahi. 'Natural' ka matlab 'safe' nahi hota.", "evidence_bn": "অনেক ভেষজ পণ্যের গর্ভ বা স্তন্যপানে নিরাপত্তা পরীক্ষা হয়নি — কিছু ক্ষতি বা ওষুধের সাথে প্রতিক্রিয়া করতে পারে। উপাদান ও মাত্রা প্রায়ই অনির্দিষ্ট। 'প্রাকৃতিক' মানে 'নিরাপদ' নয়।",
        "benefit": "unknown", "benefit_en": "Not proven for the claimed purposes.", "risk_en": "Unknown toxicity, drug interactions, contamination, delayed proper care.", "verdict": "unknown",
        "verdict_en": "Insufficient evidence; safety in pregnancy/breastfeeding not established.", "alternative_en": "Discuss any herbal product with your doctor before taking it. Use clinician-prescribed supplements instead.", "doctor_en": "Always, before taking any herbal medicine while pregnant or breastfeeding.", "source": "General pharmacovigilance / WHO traditional medicine safety",
    },
]

VERDICT_LABELS = {
    "supported": ("Supported by scientific evidence", "वैज्ञानिक प्रमाण से समर्थित", "বৈজ্ঞানিক প্রমাণ দ্বারা সমর্থিত"),
    "safe": ("Reasonable & generally safe, not proven", "सामान्यतः सुरक्षित, प्रमाणित नहीं", "সাধারণত নিরাপদ, প্রমাণিত নয়"),
    "insufficient": ("Insufficient scientific evidence", "पर्याप्त वैज्ञानिक प्रमाण नहीं", "পর্যাপ্ত বৈজ্ঞানিক প্রমাণ নেই"),
    "harmful": ("Potentially harmful", "संभावित रूप से हानिकारक", "সম্ভাব্যভাবে ক্ষতিকারক"),
    "contraindicated": ("Contraindicated in specific circumstances", "विशेष परिस्थितियों में वर्जित", "নির্দিষ্ট পরিস্থিতিতে নিষিদ্ধ"),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def compute_edd(lmp_iso=None, edd_iso=None, weeks=None):
    """Return (edd_date, gestational_days) from LMP, EDD, or weeks."""
    today = date.today()
    if edd_iso:
        edd = date.fromisoformat(edd_iso)
        return edd, max(0, (edd - today).days * -1 + 280)
    if lmp_iso:
        lmp = date.fromisoformat(lmp_iso)
        return lmp + timedelta(days=280), max(0, (today - lmp).days)
    if weeks is not None:
        days = int(float(weeks) * 7)
        return today + timedelta(days=max(0, 280 - days)), days
    return None, None


def stage_from_days(days):
    if days is None:
        return "t1"
    w = days // 7
    if w < 14: return "t1"
    if w < 28: return "t2"
    return "t3"


def trimester_key(stage):
    return {"t1": "trimester_1", "t2": "trimester_2", "t3": "trimester_3"}.get(stage, "trimester_1")


def anc_schedule(edd_iso, high_risk=False):
    """WHO recommends >=8 ANC contacts; NHM has its own schedule.

    This generates a general WHO-aligned guide (8 contacts) anchored to EDD.
    Returns list of dicts — guidance only, never a prescription.
    """
    if not edd_iso:
        return []
    edd = date.fromisoformat(edd_iso)
    # Contact weeks: 12, 20, 26, 30, 34, 36, 38, 40 (WHO 8-contact model)
    weeks = [12, 20, 26, 30, 34, 36, 38, 40]
    out = []
    for n, w in enumerate(weeks, 1):
        due = edd - timedelta(days=(40 - w) * 7)
        out.append({
            "id": f"anc_{n}", "type": "anc_visit",
            "title_en": f"Antenatal visit #{n}", "title_hi": f"Antenatal visit #{n}", "title_bn": f"প্রসব-পূর্ব সাক্ষাৎ #{n}",
            "due": due.isoformat(), "week": w,
            "note_en": "Bring your reports and medicines list. Ask about tests due at this visit.",
            "note_hi": "Reports aur dawayon ki list saath layein. Is visit ke tests ke baare mein poochhein.",
            "note_bn": "রিপোর্ট ও ওষুধের তালিকা সাথে নিন। এই সাক্ষাতের পরীক্ষা সম্পর্কে জিজ্ঞাসা করুন।",
        })
    if high_risk:
        out.insert(0, {
            "id": "anc_risk", "type": "anc_visit",
            "title_en": "Early high-risk review", "title_hi": "Jaldi high-risk review", "title_bn": "প্রারম্ভিক উচ্চ-ঝুকি পর্যালোচনা",
            "due": date.today().isoformat(), "week": 0,
            "note_en": "Because this is a high-risk pregnancy, book an early appointment with your doctor.",
            "note_hi": "High-risk pregnancy hone ke karan doctor se jaldi appointment book karein.",
            "note_bn": "উচ্চ-ঝুকিমূলক গর্ভের কারণে ডাক্তারের সাথে শীঘ্রই সাক্ষাত নির্ধারণ করুন।",
        })
    return out


def immunization_schedule(birth_iso):
    """Indian national immunization schedule — key routine vaccines (guidance only).

    The full schedule is long; this covers core visits. Always follow the
    official MoHFW schedule and your paediatrician.
    """
    if not birth_iso:
        return []
    birth = date.fromisoformat(birth_iso)
    items = [
        (0, "BCG, OPV-0, Hepatitis B birth dose", "BCG, OPV-0, Hepatitis B birth dose", "BCG, OPV-০, হেপাটাইটিস বি জন্ম ডোজ"),
        (42, "OPV-1, Rotavirus-1", "OPV-1, Rotavirus-1", "OPV-১, রোটাভাইরাস-১"),
        (70, "OPV-2, Rotavirus-2", "OPV-2, Rotavirus-2", "OPV-২, রোটাভাইরাস-২"),
        (84, "OPV-3, Rotavirus-3, DTaP/DTwP-1", "OPV-3, Rotavirus-3, DTaP/DTwP-1", "OPV-৩, রোটাভাইরাস-৩, DTaP-১"),
        (180, "Measles/MR-1, JE-1 (where applicable)", "Measles/MR-1, JE-1", "হাম/MR-১, JE-১"),
        (270, "Measles/MR-2, JE-2, DTaP/DTwP booster", "Measles/MR-2, JE-2, booster", "হাম/MR-২, JE-২, বুস্টার"),
        (365, "Booster doses (as per national schedule)", "Booster doses", "বুস্টার ডোজ"),
    ]
    return [{
        "id": f"imm_{i}", "type": "vaccination",
        "title_en": title, "title_hi": title_h, "title_bn": title_b,
        "due": (birth + timedelta(days=d)).isoformat(),
        "note_en": "Follow the official Indian immunization schedule and your paediatrician. Record the date given.",
        "note_hi": "Official Indian schedule aur pediatrician ka palan karein. Di gayi tareekh note karein.",
        "note_bn": "সরকারি ভারতীয় টিকাদান তালিকা ও শিশু বিশেষজ্ঞের নির্দেশ মানুন। দেওয়ার তারিখ নোট করুন।",
    } for i, (d, title, title_h, title_b) in enumerate(items)]


def triage_symptoms(text, stage="pregnancy"):
    """Danger-sign triage. Returns the highest-urgency match with multiling
    reason/action. Over-triggers by design; never returns false reassurance.
    """
    if not text or not text.strip():
        return None
    t = text.lower()
    applicable = set(stage.split(",")) if stage else {"pregnancy"}
    order = {"emergency": 0, "urgent": 1, "routine": 2}
    matches = []
    for sign in DANGER_SIGNS:
        stages = set(sign["stage"].split(","))
        if not (applicable & stages):
            continue
        if any(k.lower() in t for k in sign["match"]):
            matches.append(sign)
    if not matches:
        return None
    matches.sort(key=lambda s: order.get(s["urgency"], 3))
    best = matches[0]
    return {
        "urgency": best["urgency"],
        "id": best["id"],
        "reason_en": best["reason_en"], "reason_hi": best["reason_hi"], "reason_bn": best["reason_bn"],
        "action_en": best["action_en"], "action_hi": best["action_hi"], "action_bn": best["action_bn"],
        "steps_en": best["steps_en"],
        "also": [m["id"] for m in matches[1:]],
    }


def chat_reply(text, lang, profile, tasks):
    """Rule-based orchestrator: decide which module handles the question.

    Order of routing (safety first):
      1. Danger sign -> escalation, no general advice.
      2. Appointment/immunization due -> schedule info.
      3. Tradition keyword -> evaluator.
      4. Education keyword -> stage education.
      5. Fallback -> no invented answers; direct to doctor/safety page.
    """
    t = (text or "").lower()
    stage = profile.get("stage", "pregnancy")
    days = profile.get("days")
    if stage == "pregnancy":
        triage_stage = "pregnancy"
    elif stage == "postpartum":
        triage_stage = "postpartum,newborn"
    else:
        triage_stage = "newborn,child"

    alert = triage_symptoms(text, triage_stage)
    if alert:
        u = alert["urgency"]
        prefix = {
            "emergency": "🚨 EMERGENCY — seek immediate medical care. ",
            "urgent": "⚠️ URGENT — contact your doctor today. ",
        }.get(u, "")
        reason = alert.get(f"reason_{lang}", alert["reason_en"])
        action = alert.get(f"action_{lang}", alert["action_en"])
        steps = " • ".join(alert["steps_en"])
        return {
            "kind": "danger",
            "text_en": f"{prefix}{alert['reason_en']} {alert['action_en']} Immediate steps: {steps}",
            "text_hi": f"{prefix}{reason} {action} Turant kaadam: {steps}",
            "text_bn": f"{prefix}{reason} {action} অবিলম্বে পদক্ষেপ: {steps}",
            "alert": alert,
        }

    # Tradition keywords
    trad_words = ["saffron", "kesar", "जाफरान", "জাফরান", "papaya", "पपीता", "পেঁপে", "pineapple",
                  "ghee", "घी", "ঘি", "honey", "शहद", "মধু", "cord", "nabhi", "नाभि", "নাভি",
                  "bind", "बांध", "বাঁধা", "kadha", "काढ़ा", "কাড়া", "tradition", "parampara", "परंपरा", "ঐতিহ্য",
                  "massage", "मालिश", "ম্যাসাজ", "ghutti", "घुट्टी", "বমি", "rest", "आराम", "বিশ্রাম"]
    if any(w in t for w in trad_words):
        return {
            "kind": "tradition",
            "text_en": "This is a traditional practice question. Open the 'Traditions' tab to see the belief, the evidence, the verdict, the safer alternative, and when to see a doctor — respectfully explained.",
            "text_hi": "Ye parampar ke baare mein sawal hai. 'Parampara' tab kholein — vichaar, evidence, verdict, surakshit vikalp aur doctor se kab milna hai, sab izzat ke saath samjhaya hai.",
            "text_bn": "এটি ঐতিহ্য সম্পর্কে প্রশ্ন। 'ঐতিহ্য' ট্যাব খুলুন — বিশ্বাস, প্রমাণ, সিদ্ধান্ত, নিরাপদ বিকল্প ও ডাক্তারের কাছে কখন যাবেন, সব শ্রদ্ধার সাথে ব্যাখ্যা করা আছে।",
        }

    # Due / appointment keywords
    due_words = ["due", "next", "appointment", "visit", "test", "checkup", "check-up", "vaccine",
                 "immunization", "tick", "calendar", "reminder", "कब", "अगला", "পরবর্তী", "টিকা", "ভ্যাকসিন"]
    if any(w in t for w in due_words):
        open_tasks = [x for x in tasks if not x.get("done")]
        if open_tasks:
            nxt = sorted(open_tasks, key=lambda x: x.get("due", ""))[:3]
            summary = "; ".join(f"{x['title']} ({x['due']})" for x in nxt)
            return {
                "kind": "schedule",
                "text_en": f"From your calendar, these are coming up: {summary}. Open the Calendar tab to mark them done or add your own reminders. Always follow your doctor's own plan.",
                "text_hi": f"Aapke calendar mein aage ye hain: {summary}. Calendar tab mein jaakar done karein ya apne reminders add karein. Doctor ki apni plan hamesha manein.",
                "text_bn": "আপনার ক্যালেন্ডারে পরবর্তী এগুলো আছে: " + summary + ". ক্যালেন্ডার ট্যাবে গিয়ে সম্পন্ন করুন বা নিজের রিমাইন্ডার যোগ করুন। ডাক্তারের নিজস্ব পরিকল্পনা মানুন।",
            }
        return {
            "kind": "schedule",
            "text_en": "No open reminders right now. Open the Calendar tab to see suggested visits and immunizations, or add your own. Follow your doctor's plan above all.",
            "text_hi": "Abhi koi reminder nahi hai. Calendar tab mein suggested visits aur immunizations dekhein ya apne add karein. Doctor ki plan sabse upar.",
            "text_bn": "এখন কোনো রিমাইন্ডার নেই। ক্যালেন্ডার ট্যাবে প্রস্তাবিত সাক্ষাত ও টিকাদান দেখুন বা নিজের যোগ করুন। ডাক্তারের পরিকল্পনাই প্রধান।",
        }

    # Education keywords -> stage-specific content
    edu_words = ["eat", "food", "diet", "खाना", "আহার", "experience", "exercise", "vyayam", "व्यायाम",
                 "breastfeed", "दूध", "বুক", "sleep", "नींद", "�ুম", "week", "सप्ताह", "সপ্তাহ", "baby",
                 "बेबी", "শিশু", "what to do", "kya karein", "কী করব", "normal", "सामान्य", "স্বাভাবিক"]
    if any(w in t for w in edu_words):
        content = education_for(stage, days)
        if content:
            title = content[0].get(f"title_{lang}", content[0]["title_en"])
            body = content[0].get(f"body_{lang}", content[0]["body_en"])
            more = content[1].get(f"title_{lang}", content[1]["title_en"]) if len(content) > 1 else ""
            return {
                "kind": "education",
                "text_en": f"For your current stage: {content[0]['title_en']} — {content[0]['body_en']}" + (f" Also: {more}." if more else ""),
                "text_hi": f"Aapke stage ke liye: {title} — {body}" + (f" Saath hi: {more}." if more else ""),
                "text_bn": f"আপনার পর্যায়ের জন্য: {title} — {body}" + (f" এছাড়া: {more}." if more else ""),
            }

    return {
        "kind": "fallback",
        "text_en": "I don't have a verified answer for that. Ask your doctor or nurse. If it might be urgent, use the Safety page now — I will never delay an emergency referral.",
        "text_hi": "Iska verified jawab mere paas nahi hai. Doctor ya nurse se poochhein. Agar urgent ho sakta hai to abhi Safety page istemal karein — main emergency refer karne mein deri nahi karta.",
        "text_bn": "এর সঠিক উত্তর আমার কাছে নেই। ডাক্তার বা নার্সের সাথে কথা বলুন। জরুরি হতে পারলে এখনই নিরাপত্তা পৃষ্ঠা ব্যবহার করুন — আমি জরুরি রেফারেল বিলম্বিত করব না।",
    }


def education_for(stage, days=None):
    if stage == "pregnancy":
        s = stage_from_days(days)
        return EDUCATION.get(s, EDUCATION["t1"])
    if stage == "postpartum":
        return EDUCATION["postpartum"]
    if stage == "baby":
        return EDUCATION["newborn"] + EDUCATION["child"]
    return EDUCATION["planning"]
