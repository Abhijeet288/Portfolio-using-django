import os
import json
import re
import time
import requests
from datetime import datetime, timedelta

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.core.cache import cache
from django.db.models import Count
from django.db.models.functions import TruncDate

from Base.models import Contact, VisitorLog, ResumeDownload, SkillEndorsement, ChatLog

# ─────────────────────────────────────────────
#  GEMINI AI SETUP
# ─────────────────────────────────────────────
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
GITHUB_USERNAME = os.getenv('GITHUB_USERNAME', 'Abhijeet288')

ABHI_CV_CONTEXT = """
You are Abhi-AI, the personal AI assistant embedded in Abhijeet Sahoo's developer portfolio website.
Your ONLY purpose is to answer questions about Abhijeet Sahoo based on his CV and profile below.
Be friendly, professional, and concise. Use emojis occasionally. Format responses with line breaks for readability.
Never answer questions unrelated to Abhijeet's professional profile.

=== ABHIJEET SAHOO — FULL PROFILE ===

NAME: Abhijeet Sahoo
TITLE: Full Stack Software Developer | Mobile Application Developer
LOCATION: Odisha, India
EMAIL: sahooabhijeet500@gmail.com
PHONE: +91-9337370441
LINKEDIN: https://www.linkedin.com/in/abhijeetsahoo288/
GITHUB: https://github.com/Abhijeet288
AVAILABILITY: Open to full-time, freelance and remote opportunities

SUMMARY:
Full Stack Software Developer with experience in React.js, React Native, Node.js, Express, and Django.
Specializes in building web and mobile applications, REST APIs, real-time chat systems, and admin dashboards.
Experienced in scalable applications with authentication, wallet systems, analytics dashboards, and push notifications.

SKILLS:
- Languages: JavaScript, Python
- Web: React.js, Django, MERN Stack, HTML5, CSS3, Bootstrap
- Mobile: React Native, Android Studio
- Backend: Node.js, Express, WebSockets, Agora Engine
- Databases: SQL, MySQL, MongoDB
- Tools: Git, GitHub, Excel, Power Query

Proficiency: React Native (90%), JavaScript (85%), Python (80%), React.js (80%), SQL/MySQL (80%), Node.js/Express (78%), Django (75%), MongoDB (72%)

WORK EXPERIENCE:
1. Software Development Engineer-I @ Web_Bocket Pvt Ltd (July 2025 – Present) [Full-Time, Current]
   - Contributed to development and maintenance of a live dating application
   - Blended new features, optimized APIs, fixed UI/UX issues
   - Integrated backend functionalities in admin panel (user management, analytics, moderation)
   - Worked on bug fixes, API integration, and performance optimization

2. Software Consultant – App Development @ OneWholesale (May 2025 – July 2025) [Consultant]
   - Developed OneWholesale, a farmer-focused e-commerce app
   - Built responsive UI, integrated authentication & product management APIs
   - Optimized app performance and state management

3. Hardware Testing Engineer @ IONICS Power Solutions Pvt Ltd (June 2023 – August 2024) [Full-Time]
   - Testing X-ray generators
   - Customer troubleshooting and support

4. React-Native App Developer @ Apptimates Software Pvt. Ltd. (Feb 2023 – June 2023) [Internship]
   - Mobile app development with React Native
   - Optimized app performance by 45%
   - Triaged 20+ bugs

5. Full Stack Python Development Training (Aug 2024 – May 2025) [Training]
   - HTML, CSS, JavaScript, Bootstrap, Python, Django, MySQL

PROJECTS:
1. VHEECO – Admin Dashboard (React.js, Node.js, Express, MongoDB) [Live]
   - Admin dashboard for document service management with user, agent, wallet, reporting modules
   - REST APIs & database models for service transactions
   - Analytics dashboard monitoring downloads, revenue, system activity

2. Heart Connect – Dating App (React Native, Node.js, Express, WebSockets) [Live]
   - Enhanced push notification system for real-time user activity
   - Real-time chat using WebSockets
   - API refactoring and optimization

3. Drive Safe – NFC Business Card (React Native, Node.js, Express) [Live]
   - Digital NFC business card mobile application
   - Profile sharing and business information management

4. OneWholesale – Farmer E-Commerce (React Native, Node.js) [Live]
   - Farmer-focused e-commerce for buying, selling, renting agricultural products

5. Visiting Card Generator (React Native, Animations, QR Code) [Open Source]
   - App with QR scanner, linear gradients, animations, FlatList

6. Snake Game with Django (Django, Python, JavaScript) [Open Source]
   - Browser-based snake game with Django backend for score tracking and auth

EDUCATION:
- B.Tech – Electronics & Telecommunication Engineering, Trident Academy of Technology (2019–2023), Score: 81%
- Class 12th – CBSE, Prabhujee English Medium School (2018–2019), Score: 61.2%
- Class 10th – CBSE, Prabhujee English Medium School (Score: 79.8%)

CERTIFICATIONS:
- React-Native Mobile Application Development (Certified)
- HTML, CSS & JavaScript Essentials Bootcamp (Certified)
- Python Certified Course (Certified)

LEADERSHIP:
- Hackathon Volunteer – Assisted teams to participate and perform
- TECHFEST Event Host – Organized and hosted college tech festival event
"""


def _get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def _call_gemini(prompt, system_context=None):
    """Call Gemini 1.5 Flash API via REST."""
    if not GEMINI_API_KEY:
        return None, "GEMINI_API_KEY not configured. Please set it in your environment variables."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

    contents = []
    if system_context:
        contents.append({"role": "user", "parts": [{"text": system_context + "\n\nUser question: " + prompt}]})
    else:
        contents.append({"role": "user", "parts": [{"text": prompt}]})

    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 800,
            "topP": 0.9,
        },
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ]
    }

    try:
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        text = data['candidates'][0]['content']['parts'][0]['text']
        return text, None
    except requests.exceptions.Timeout:
        return None, "AI response timed out. Please try again."
    except requests.exceptions.RequestException as e:
        return None, f"AI service error: {str(e)}"
    except (KeyError, IndexError):
        return None, "Unexpected response from AI service."


# ─────────────────────────────────────────────
#  MAIN PAGE VIEW
# ─────────────────────────────────────────────
def contact_view(request):
    # Fetch skill endorsement counts for template
    endorsements = SkillEndorsement.objects.values('skill_name').annotate(
        count=Count('id')
    ).order_by('skill_name')
    endorsement_map = {e['skill_name']: e['count'] for e in endorsements}

    # Total resume downloads
    download_count = ResumeDownload.objects.count()

    # Total visitors
    visitor_count = VisitorLog.objects.count()

    if request.method == "POST":
        name    = request.POST.get('name', '').strip()
        email   = request.POST.get('email', '').strip()
        number  = request.POST.get('number', '').strip()
        content = request.POST.get('content', '').strip()

        if not (2 <= len(name) <= 50):
            messages.error(request, 'Name must be between 2 and 50 characters.')
            return render(request, 'home.html', {'endorsements': endorsement_map, 'download_count': download_count})

        if not re.match(r'^[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}$', email):
            messages.error(request, 'Please enter a valid email address.')
            return render(request, 'home.html', {'endorsements': endorsement_map, 'download_count': download_count})

        if not (6 <= len(number) <= 15):
            messages.error(request, 'Please enter a valid phone number.')
            return render(request, 'home.html', {'endorsements': endorsement_map, 'download_count': download_count})

        Contact(name=name, email=email, number=number, content=content).save()
        messages.success(request, 'Thanks for reaching out! 🚀 I\'ll get back to you soon.')

    return render(request, 'home.html', {
        'endorsements': endorsement_map,
        'download_count': download_count,
        'visitor_count': visitor_count,
    })


# ─────────────────────────────────────────────
#  REAL AI CHATBOT — Gemini Powered
# ─────────────────────────────────────────────
@csrf_exempt
@require_http_methods(["POST"])
def chat_view(request):
    try:
        body = json.loads(request.body)
        user_message = body.get('message', '').strip()
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': 'Invalid request'}, status=400)

    if not user_message:
        return JsonResponse({'error': 'Empty message'}, status=400)

    if len(user_message) > 500:
        return JsonResponse({'error': 'Message too long (max 500 chars)'}, status=400)

    ip = _get_client_ip(request)

    # Rate limiting: max 20 messages per IP per hour
    rate_key = f"chat_rate_{ip}"
    msg_count = cache.get(rate_key, 0)
    if msg_count >= 20:
        return JsonResponse({
            'reply': "⚠️ You've reached the chat limit for this hour. Please try again later or contact Abhijeet directly at sahooabhijeet500@gmail.com"
        })
    cache.set(rate_key, msg_count + 1, 3600)

    # Call Gemini
    reply, error = _call_gemini(user_message, ABHI_CV_CONTEXT)

    if error:
        # Fallback to keyword responses if AI fails
        reply = _fallback_response(user_message)

    # Log the chat
    try:
        ChatLog.objects.create(
            ip_address=ip,
            user_message=user_message,
            bot_response=reply
        )
    except Exception:
        pass

    return JsonResponse({'reply': reply})


def _fallback_response(q):
    """Simple keyword fallback if Gemini is unavailable."""
    q = q.lower()
    if any(k in q for k in ['skill', 'tech', 'stack']):
        return "Abhijeet's tech stack: React Native (90%), JavaScript (85%), Python/Django (80%), React.js (80%), Node.js/Express (78%), SQL/MongoDB. Full Stack across web & mobile! 🛠️"
    if any(k in q for k in ['experience', 'work', 'job']):
        return "Currently SDE-I at Web_Bocket Pvt Ltd (July 2025). Previously Software Consultant at OneWholesale, React Native Intern at Apptimates Software. 3+ years coding experience 💼"
    if any(k in q for k in ['project', 'built', 'app']):
        return "6 key projects: VHEECO Admin Dashboard, Heart Connect Dating App, Drive Safe NFC App, OneWholesale E-Commerce, Visiting Card Generator, Snake Game with Django 🚀"
    if any(k in q for k in ['contact', 'hire', 'email']):
        return "📧 sahooabhijeet500@gmail.com | 📱 +91-9337370441 | LinkedIn: abhijeetsahoo288 | Open to full-time & freelance opportunities!"
    return "I'm Abhi-AI, Abhijeet's portfolio assistant! Ask me about his skills, experience, projects, education, or how to contact him. 🤖"


# ─────────────────────────────────────────────
#  AI RESUME MATCHER — Gemini Powered
# ─────────────────────────────────────────────
@csrf_exempt
@require_http_methods(["POST"])
def match_resume_view(request):
    try:
        body = json.loads(request.body)
        job_description = body.get('job_description', '').strip()
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': 'Invalid request'}, status=400)

    if not job_description:
        return JsonResponse({'error': 'Job description is required'}, status=400)

    if len(job_description) < 50:
        return JsonResponse({'error': 'Please provide a more detailed job description (at least 50 characters)'}, status=400)

    if len(job_description) > 5000:
        return JsonResponse({'error': 'Job description too long (max 5000 characters)'}, status=400)

    ip = _get_client_ip(request)

    # Rate limiting: 5 matches per IP per hour
    rate_key = f"match_rate_{ip}"
    count = cache.get(rate_key, 0)
    if count >= 5:
        return JsonResponse({'error': 'Rate limit reached. Max 5 matches per hour.'}, status=429)
    cache.set(rate_key, count + 1, 3600)

    prompt = f"""You are an expert technical recruiter and career coach.

Analyze this candidate's profile against the job description and return ONLY a valid JSON response (no markdown, no code blocks, just raw JSON).

CANDIDATE PROFILE:
{ABHI_CV_CONTEXT}

JOB DESCRIPTION:
{job_description}

Return this exact JSON structure:
{{
  "match_score": <integer 0-100>,
  "match_label": "<Excellent Match|Strong Match|Good Match|Partial Match|Low Match>",
  "strengths": [<list of 3-5 specific matching skills/experiences as strings>],
  "gaps": [<list of 1-3 gaps or missing requirements as strings, or empty array if no major gaps>],
  "summary": "<2-3 sentence personalized pitch for why Abhijeet fits this role>",
  "recommendation": "<one sentence hiring recommendation>"
}}"""

    reply_text, error = _call_gemini(prompt)

    if error:
        return JsonResponse({'error': f'AI service unavailable: {error}'}, status=503)

    # Extract JSON from response
    try:
        # Strip markdown code blocks if present
        clean = reply_text.strip()
        if clean.startswith('```'):
            clean = re.sub(r'^```(?:json)?\n?', '', clean)
            clean = re.sub(r'\n?```$', '', clean)
        result = json.loads(clean)
    except (json.JSONDecodeError, ValueError):
        # Try to extract JSON from mixed text
        match = re.search(r'\{.*\}', reply_text, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group())
            except Exception:
                return JsonResponse({'error': 'Could not parse AI response. Please try again.'}, status=500)
        else:
            return JsonResponse({'error': 'Unexpected AI response format. Please try again.'}, status=500)

    return JsonResponse(result)


# ─────────────────────────────────────────────
#  GITHUB STATS
# ─────────────────────────────────────────────
def github_stats_view(request):
    cache_key = 'github_stats'
    cached = cache.get(cache_key)
    if cached:
        return JsonResponse(cached)

    try:
        headers = {}
        github_token = os.getenv('GITHUB_TOKEN', '')
        if github_token:
            headers['Authorization'] = f'token {github_token}'

        user_resp = requests.get(
            f'https://api.github.com/users/{GITHUB_USERNAME}',
            headers=headers, timeout=10
        )
        user_data = user_resp.json()

        repos_resp = requests.get(
            f'https://api.github.com/users/{GITHUB_USERNAME}/repos?per_page=100&sort=updated',
            headers=headers, timeout=10
        )
        repos_data = repos_resp.json()

        # Aggregate language stats
        lang_counts = {}
        total_stars = 0
        total_forks = 0
        recent_repos = []

        for repo in repos_data:
            if isinstance(repo, dict):
                total_stars += repo.get('stargazers_count', 0)
                total_forks += repo.get('forks_count', 0)
                lang = repo.get('language')
                if lang:
                    lang_counts[lang] = lang_counts.get(lang, 0) + 1
                if not repo.get('fork', True):
                    recent_repos.append({
                        'name': repo.get('name', ''),
                        'description': repo.get('description', '') or '',
                        'url': repo.get('html_url', ''),
                        'stars': repo.get('stargazers_count', 0),
                        'language': repo.get('language', ''),
                        'updated': repo.get('updated_at', ''),
                    })

        # Top languages
        top_langs = sorted(lang_counts.items(), key=lambda x: x[1], reverse=True)[:6]

        stats = {
            'username': GITHUB_USERNAME,
            'name': user_data.get('name', GITHUB_USERNAME),
            'avatar': user_data.get('avatar_url', ''),
            'bio': user_data.get('bio', ''),
            'public_repos': user_data.get('public_repos', 0),
            'followers': user_data.get('followers', 0),
            'following': user_data.get('following', 0),
            'total_stars': total_stars,
            'total_forks': total_forks,
            'top_languages': [{'name': l[0], 'count': l[1]} for l in top_langs],
            'recent_repos': recent_repos[:6],
            'profile_url': f'https://github.com/{GITHUB_USERNAME}',
        }

        cache.set(cache_key, stats, 3600)  # cache 1 hour
        return JsonResponse(stats)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ─────────────────────────────────────────────
#  RESUME DOWNLOAD TRACKER
# ─────────────────────────────────────────────
@csrf_exempt
@require_http_methods(["POST"])
def track_download_view(request):
    ip = _get_client_ip(request)
    ua = request.META.get('HTTP_USER_AGENT', '')

    # Avoid duplicate tracking (same IP within 5 minutes)
    rate_key = f"dl_rate_{ip}"
    if not cache.get(rate_key):
        ResumeDownload.objects.create(ip_address=ip, user_agent=ua)
        cache.set(rate_key, True, 300)

    total = ResumeDownload.objects.count()
    return JsonResponse({'success': True, 'total_downloads': total})


# ─────────────────────────────────────────────
#  SKILL ENDORSEMENT
# ─────────────────────────────────────────────
@csrf_exempt
@require_http_methods(["POST"])
def endorse_view(request):
    try:
        body = json.loads(request.body)
        skill_name = body.get('skill', '').strip()
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': 'Invalid request'}, status=400)

    VALID_SKILLS = [
        'JavaScript', 'Python', 'React Native', 'React.js',
        'Node.js / Express', 'Django', 'SQL / MySQL', 'MongoDB'
    ]

    if skill_name not in VALID_SKILLS:
        return JsonResponse({'error': 'Invalid skill'}, status=400)

    ip = _get_client_ip(request)

    # 1 endorsement per skill per IP
    already = SkillEndorsement.objects.filter(skill_name=skill_name, ip_address=ip).exists()
    if already:
        count = SkillEndorsement.objects.filter(skill_name=skill_name).count()
        return JsonResponse({'already_endorsed': True, 'count': count})

    SkillEndorsement.objects.create(skill_name=skill_name, ip_address=ip)
    count = SkillEndorsement.objects.filter(skill_name=skill_name).count()
    return JsonResponse({'success': True, 'count': count})


# ─────────────────────────────────────────────
#  ANALYTICS API (for admin dashboard widget)
# ─────────────────────────────────────────────
def analytics_view(request):
    # Only accessible to staff/superuser
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    today = datetime.now().date()
    last_30 = today - timedelta(days=30)

    # Visits per day (last 30 days)
    visits_by_day = list(
        VisitorLog.objects.filter(visited_at__date__gte=last_30)
        .annotate(date=TruncDate('visited_at'))
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date')
        .values('date', 'count')
    )

    # Top countries
    top_countries = list(
        VisitorLog.objects.values('country')
        .annotate(count=Count('id'))
        .order_by('-count')[:10]
        .values('country', 'count')
    )

    # Devices
    devices = list(
        VisitorLog.objects.values('device')
        .annotate(count=Count('id'))
        .order_by('-count')
        .values('device', 'count')
    )

    return JsonResponse({
        'total_visitors': VisitorLog.objects.count(),
        'total_downloads': ResumeDownload.objects.count(),
        'total_contacts': Contact.objects.count(),
        'total_endorsements': SkillEndorsement.objects.count(),
        'visits_by_day': [{'date': str(v['date']), 'count': v['count']} for v in visits_by_day],
        'top_countries': list(top_countries),
        'devices': list(devices),
    })
