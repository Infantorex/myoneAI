"""Natural language intent detection and parser for PC Tools (Phase 8 & 9).

Translates Tamil, English, and mixed Tanglish spoken commands into structured ToolCalls.
"""

import logging
import re
from typing import Any, Dict, Optional, Tuple

from app.security.policies import is_command_blocked
from app.tools.schemas import ToolCall

logger = logging.getLogger("myoneAI.tools.intent")


def parse_tool_intent(user_text: str) -> Optional[ToolCall]:
    """Parse user speech or text into a structured ToolCall if tool intent is recognized.

    Args:
        user_text: Spoken or typed user input string.

    Returns:
        ToolCall object if matched, or None if prompt is a general conversation query.
    """
    if not user_text or not user_text.strip():
        return None

    clean = user_text.strip()
    clean_lower = clean.lower()

    # 1. Blocked Command Check
    if is_command_blocked(clean):
        return ToolCall(tool="execute_shell", arguments={"raw_command": clean})

    # 2. Performance & Slowness Diagnosis ("Why is my laptop slow?", "லேப்டாப் ஏன் ஸ்லோவா இருக்கு?")
    if (
        re.search(r"(?i)\b(?:why\s+is\s+(?:my\s+)?(?:laptop|pc|computer|system)\s+slow|laptop\s+slow|pc\s+slow|diagnose\s+(?:laptop|system|pc))\b", clean_lower)
        or re.search(r"(?i)(?:லேப்டாப்|சிஸ்டம்)\s+(?:ஏன்\s+)?(?:ஸ்லோவா|மெதுவாக)\s+இருக்கு", clean)
    ):
        return ToolCall(tool="diagnose_system_performance", arguments={})

    # 3. Top Resource Consuming Processes ("Which app is using the most RAM?", "What's using most memory?")
    if (
        re.search(r"(?i)\b(?:which\s+app\s+is\s+using\s+the\s+most\s+(?:ram|memory|cpu)|what(?:'s|\s+is)\s+using\s+(?:the\s+)?most\s+(?:ram|memory|cpu)|top\s+processes|top\s+apps)\b", clean_lower)
        or re.search(r"(?i)(?:எந்த\s+ஆப்|எந்த\s+செயலி)\s+அதிக\s+(?:ram|நினைவகம்|cpu)", clean)
    ):
        sort_by = "cpu" if "cpu" in clean_lower else "memory"
        return ToolCall(tool="get_top_processes", arguments={"limit": 5, "sort_by": sort_by})

    # 4. Network Status ("Am I connected to the internet?", "Check internet", "Network status", "Internet connected-ஆ?")
    if (
        re.search(r"(?i)\b(?:am\s+i\s+connected\s+to\s+(?:the\s+)?internet|check\s+(?:network|internet|connection)|network\s+status|internet\s+status|is\s+internet\s+working)\b", clean_lower)
        or re.search(r"(?i)(?:இணைய\s+இணைப்பு|internet\s+(?:இருக்கா|connected-ஆ))", clean)
    ):
        return ToolCall(tool="get_network_status", arguments={})

    # 5. Application Launching ("Open Chrome", "Chrome open பண்ணு", "Open Calculator")
    app_open_match = re.search(
        r"(?i)\b(?:open|launch|start|run)\s+(?:application\s+)?([a-zA-Z0-9_\-\s]+)",
        clean,
    )
    tamil_app_open = re.search(
        r"(?i)([a-zA-Z0-9_\-\s]+)\s+(?:open\s+பண்ணு|திற|open\s+செய்யவும்|run\s+பண்ணு)",
        clean,
    )

    if (app_open_match or tamil_app_open) and not re.search(r"(?i)\b(?:website|site|url|folder|file|screenshot|system|ram|cpu|disk|battery|network)\b", clean_lower):
        raw_app = app_open_match.group(1).strip() if app_open_match else tamil_app_open.group(1).strip()
        raw_app = re.sub(r"(?i)\b(?:please|now|app|application)\b", "", raw_app).strip()
        if raw_app and len(raw_app) < 30:
            if "." in raw_app and not raw_app.endswith((".exe", ".app")):
                return ToolCall(tool="open_website", arguments={"url": raw_app})
            return ToolCall(tool="open_application", arguments={"application": raw_app.lower()})

    # 6. Application Termination ("Close Chrome", "Chrome close பண்ணு")
    app_close_match = re.search(
        r"(?i)\b(?:close|quit|exit|terminate|kill)\s+(?:application\s+)?([a-zA-Z0-9_\-\s]+)",
        clean,
    )
    tamil_app_close = re.search(
        r"(?i)([a-zA-Z0-9_\-\s]+)\s+(?:close\s+பண்ணு|மூடு|close\s+செய்யவும்)",
        clean,
    )
    if app_close_match or tamil_app_close:
        raw_app = app_close_match.group(1).strip() if app_close_match else tamil_app_close.group(1).strip()
        raw_app = re.sub(r"(?i)\b(?:please|now|app|application)\b", "", raw_app).strip()
        if raw_app and len(raw_app) < 30:
            return ToolCall(tool="close_application", arguments={"application": raw_app.lower()})

    # 7. Web Search ("Search Google for Python tutorials", "Search for weather")
    search_match = re.search(
        r"(?i)\b(?:search\s+(?:google\s+)?(?:for\s+)?|google\s+)(.+)",
        clean,
    )
    tamil_search = re.search(
        r"(?i)(.+)\s+(?:google-ல்\s+தேடு|தேடு|search\s+பண்ணு)",
        clean,
    )
    if search_match or tamil_search:
        q = search_match.group(1).strip() if search_match else tamil_search.group(1).strip()
        if q and not re.search(r"(?i)\b(?:memory|memories)\b", q):
            return ToolCall(tool="search_web_browser", arguments={"query": q})

    # 8. Open Website ("Open YouTube", "Open github.com", "Open https://...")
    web_match = re.search(
        r"(?i)\b(?:open\s+(?:website|site|url)\s+|go\s+to\s+)([a-zA-Z0-9_\-\.:/]+)",
        clean,
    )
    if web_match:
        url_target = web_match.group(1).strip()
        return ToolCall(tool="open_website", arguments={"url": url_target})

    # 9. Screenshot ("Take a screenshot", "Screenshot எடு", "Capture screen")
    if re.search(r"(?i)\b(?:take\s+(?:a\s+)?screenshot|capture\s+screen|screen\s+capture)\b|screenshot\s+எடு", clean_lower):
        return ToolCall(tool="take_screenshot", arguments={})

    # 10. Media & Volume Controls
    if re.search(r"(?i)\b(?:volume\s+up|increase\s+volume|raise\s+volume)\b|volume\s+(?:கூட்டு|அதிகரி)", clean_lower):
        return ToolCall(tool="volume_up", arguments={"step_percent": 10})

    if re.search(r"(?i)\b(?:volume\s+down|decrease\s+volume|lower\s+volume)\b|volume\s+(?:குறை|இறக்கு)", clean_lower):
        return ToolCall(tool="volume_down", arguments={"step_percent": 10})

    if re.search(r"(?i)\b(?:mute|unmute|toggle\s+mute)\b|சத்தத்தை\s+நிறுத்து", clean_lower):
        return ToolCall(tool="toggle_mute", arguments={})

    if re.search(r"(?i)\b(?:play\s+music|pause\s+music|play\s*/\s*pause|media\s+play)\b|பாடல்\s+(?:இயக்கு|நிறுத்து)", clean_lower):
        return ToolCall(tool="media_play_pause", arguments={})

    if re.search(r"(?i)\b(?:next\s+track|next\s+song)\b|அடுத்த\s+பாடல்", clean_lower):
        return ToolCall(tool="media_next", arguments={})

    if re.search(r"(?i)\b(?:previous\s+track|prev\s+song)\b|முந்தைய\s+பாடல்", clean_lower):
        return ToolCall(tool="media_previous", arguments={})

    # 11. Battery Status ("Jarvis, check battery", "battery status", "பேட்டரி எவ்வளவு?", "battery எவ்வளவு?")
    if (
        re.search(r"(?i)\b(?:check\s+battery|battery\s+status|battery\s+percentage|how\s+much\s+battery|battery\s+level|what(?:'s|\s+is)\s+my\s+battery)\b", clean_lower)
        or re.search(r"(?i)(?:பேட்டரி|battery)\s+(?:எவ்வளவு|status|நிலை|இருக்க)", clean)
    ):
        return ToolCall(tool="get_battery_status", arguments={})

    # 12. CPU Status ("Jarvis, what's my CPU usage?", "check cpu", "cpu usage")
    if (
        re.search(r"(?i)\b(?:check\s+cpu|cpu\s+usage|cpu\s+load|processor\s+usage|what(?:'s|\s+is)\s+my\s+cpu\s+usage)\b", clean_lower)
        or re.search(r"(?i)cpu\s*(?:பயன்பாடு|usage|எவ்வளவு|நிலை)", clean)
    ):
        return ToolCall(tool="get_cpu_usage", arguments={})

    # 13. RAM / Memory Status ("How much RAM am I using?", "check ram", "check memory", "ram usage")
    if (
        re.search(r"(?i)\b(?:how\s+much\s+ram(?:\s+am\s+i\s+using)?|check\s+ram|check\s+memory|ram\s+usage|memory\s+usage|what(?:'s|\s+is)\s+my\s+ram\s+usage)\b", clean_lower)
        or re.search(r"(?i)(?:ram|memory)\s*(?:பயன்பாடு|usage|எவ்வளவு|நிலை|என்ன)", clean)
    ):
        return ToolCall(tool="get_ram_usage", arguments={})

    # 14. Disk Storage Status ("How much storage do I have?", "check disk", "check storage", "disk space", "வட்டு சேமிப்பகம்")
    if (
        re.search(r"(?i)\b(?:how\s+much\s+storage(?:\s+do\s+i\s+have)?|check\s+disk|check\s+storage|disk\s+usage|storage\s+usage|disk\s+space|free\s+space)\b", clean_lower)
        or re.search(r"(?i)(?:disk|வட்டு|சேமிப்பகம்)", clean)
    ):
        return ToolCall(tool="get_disk_usage", arguments={})

    # 15. Overall System Health ("Jarvis, how is my laptop?", "Check my system", "Check laptop", "System status", "லேப்டாப் நிலை என்ன?")
    if (
        re.search(r"(?i)\b(?:how\s+is\s+my\s+laptop|check\s+(?:my\s+)?(?:system|laptop|pc)|system\s+status|system\s+info|system\s+specs)\b", clean_lower)
        or re.search(r"(?i)லேப்டாப்\s+(?:நிலை|எப்படி\s+இருக்கு)", clean)
    ):
        return ToolCall(tool="get_system_status", arguments={})

    # 16. Filesystem Actions ("Open folder", "Open file", "Delete file")
    delete_file_match = re.search(
        r"(?i)\b(?:delete\s+file|remove\s+file|delete)\s+([a-zA-Z0-9_\-\.\/\\]+)",
        clean,
    )
    if delete_file_match and not re.search(r"(?i)\b(?:memory|memories|conversation)\b", clean_lower):
        fpath = delete_file_match.group(1).strip()
        return ToolCall(tool="delete_file", arguments={"file_path": fpath})

    open_dir_match = re.search(
        r"(?i)\b(?:open\s+folder|open\s+directory)\s*([a-zA-Z0-9_\-\.\/\\]*)",
        clean,
    )
    if open_dir_match:
        dir_p = open_dir_match.group(1).strip() or None
        return ToolCall(tool="open_directory", arguments={"directory": dir_p} if dir_p else {})

    open_file_match = re.search(
        r"(?i)\b(?:open\s+file)\s+([a-zA-Z0-9_\-\.\/\\]+)",
        clean,
    )
    if open_file_match:
        f_p = open_file_match.group(1).strip()
        return ToolCall(tool="open_file", arguments={"file_path": f_p})

    return None
