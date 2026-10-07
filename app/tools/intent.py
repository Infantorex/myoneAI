"""Natural language intent detection and parser for PC Tools (Phases 8, 9 & 10).

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

    # ==========================================================================
    # 2. Phase 10: Productivity & Personal Tasks
    # ==========================================================================

    # 2.1 Bulk Deletions (Requires Confirmation)
    if re.search(r"(?i)\b(?:delete\s+all\s+(?:my\s+)?tasks|clear\s+all\s+tasks)\b", clean_lower):
        return ToolCall(tool="clear_all_tasks", arguments={})
    if re.search(r"(?i)\b(?:delete\s+all\s+(?:my\s+)?reminders|clear\s+all\s+reminders)\b", clean_lower):
        return ToolCall(tool="clear_all_reminders", arguments={})
    if re.search(r"(?i)\b(?:delete\s+all\s+(?:my\s+)?notes|clear\s+all\s+notes)\b", clean_lower):
        return ToolCall(tool="clear_all_notes", arguments={})

    # 2.2 Timers
    # Cancel Timer ("Cancel my timer", "Stop timer", "Cancel timer", "timer cancel பண்ணு")
    if re.search(r"(?i)\b(?:cancel|stop)\s+(?:my\s+)?timer\b|timer\s+(?:cancel|நிறுத்து)", clean_lower):
        return ToolCall(tool="cancel_timer", arguments={})

    # Check Timer Status ("How much time is left?", "Timer status", "Check timer", "timer எவ்வளவு நேரம் இருக்கு?")
    if (
        re.search(r"(?i)\b(?:how\s+much\s+time\s+(?:is\s+)?left|timer\s+status|check\s+timer|time\s+left\s+on\s+timer)\b", clean_lower)
        or re.search(r"(?i)timer\s+(?:status|நிலை|எவ்வளவு)", clean)
    ):
        return ToolCall(tool="get_timer_status", arguments={})

    # Set / Create Timer ("Set a timer for 10 minutes", "Start a 30 minute timer", "10 minutes timer வை", "timer வை")
    timer_create_match = re.search(
        r"(?i)\b(?:set|start)\s+(?:a\s+)?timer\s+(?:for\s+)?(\d+(?:\.\d+)?\s*(?:m|min|mins|minute|minutes|s|sec|secs|second|seconds|h|hr|hrs|hour|hours)?)",
        clean,
    )
    tamil_timer_match = re.search(
        r"(?i)(\d+(?:\.\d+)?\s*(?:m|min|mins|minute|minutes|நிமிடம்|வினாடி|மணி)?)\s*timer\s*வை",
        clean,
    )
    if timer_create_match or tamil_timer_match:
        dur_raw = timer_create_match.group(1).strip() if timer_create_match else tamil_timer_match.group(1).strip()
        return ToolCall(tool="create_timer", arguments={"duration_text": dur_raw})

    # 2.3 Reminders
    # Cancel Reminder ("Cancel my reminder", "Cancel reminder for meeting", "reminder cancel பண்ணு")
    cancel_rem_match = re.search(
        r"(?i)\b(?:cancel|delete)\s+(?:my\s+)?reminder(?:\s+for|\s+about)?\s*(.*)",
        clean,
    )
    if (cancel_rem_match and ("cancel" in clean_lower or "delete" in clean_lower) and "reminder" in clean_lower) or "reminder cancel" in clean_lower:
        msg_raw = cancel_rem_match.group(1).strip() if cancel_rem_match else ""
        return ToolCall(tool="cancel_reminder", arguments={"message": msg_raw} if msg_raw else {})

    # List Reminders ("What reminders do I have?", "List reminders", "Show reminders", "என்ன reminders இருக்கு?")
    if (
        re.search(r"(?i)\b(?:what\s+(?:are\s+my\s+)?reminders(?:\s+do\s+i\s+have)?|list\s+reminders|show\s+(?:my\s+)?reminders)\b", clean_lower)
        or re.search(r"(?i)(?:reminders|நினைவூட்டல்)\s*(?:என்ன|காட்டு)", clean)
    ):
        return ToolCall(tool="list_reminders", arguments={})

    # Create Reminder ("Remind me to submit the report at 6 PM", "Remind me at 6 PM to submit my report", "நாளைக்கு PPT submit பண்ணணும், reminder வை")
    rem_create_match = re.search(
        r"(?i)\b(?:remind\s+me\s+(?:to\s+|about\s+|at\s+)?|set\s+a\s+reminder\s+(?:to\s+|for\s+)?)(.+)",
        clean,
    )
    tamil_rem_match = re.search(
        r"(?i)(.+)\s+(?:reminder\s+வை|நினைவூட்டு|reminder\s+வைக்கவும்)",
        clean,
    )
    if rem_create_match or tamil_rem_match:
        rem_text = rem_create_match.group(1).strip() if rem_create_match else tamil_rem_match.group(1).strip()
        return ToolCall(tool="create_reminder", arguments={"message": rem_text})

    # 2.4 Notes
    # Search Notes ("Search my notes for PCB", "Search notes Arduino")
    search_notes_match = re.search(
        r"(?i)\b(?:search\s+(?:my\s+)?notes?\s+(?:for\s+)?)(.+)",
        clean,
    )
    if search_notes_match:
        query_kw = search_notes_match.group(1).strip()
        return ToolCall(tool="search_notes", arguments={"query": query_kw})

    # List Notes ("Show my notes", "List notes", "Show my project notes", "குறிப்புகளை காட்டு")
    if (
        re.search(r"(?i)\b(?:show\s+(?:my\s+)?notes?|list\s+(?:my\s+)?notes?|read\s+(?:my\s+)?notes?)\b", clean_lower)
        or re.search(r"(?i)குறிப்புகளை\s*காட்டு", clean)
    ):
        return ToolCall(tool="list_notes", arguments={})

    # Delete Note ("Delete note Arduino", "Delete note: ...")
    delete_note_match = re.search(
        r"(?i)\b(?:delete|remove)\s+note\s*(?::\s*)?(.+)",
        clean,
    )
    if delete_note_match:
        n_title = delete_note_match.group(1).strip()
        return ToolCall(tool="delete_note", arguments={"title": n_title})

    # Create Note ("Take a note: buy Arduino components", "Note: buy Arduino components", "Remember this note: ...", "குறிப்பு எடு: ...")
    create_note_match = re.search(
        r"(?i)\b(?:take\s+a\s+note|remember\s+this\s+note|new\s+note|create\s+note)\s*(?::\s*)?(.+)",
        clean,
    )
    tamil_note_match = re.search(
        r"(?i)(?:குறிப்பு\s+எடு|note\s+எடு)\s*(?::\s*)?(.+)",
        clean,
    )
    if create_note_match or tamil_note_match:
        n_content = create_note_match.group(1).strip() if create_note_match else tamil_note_match.group(1).strip()
        return ToolCall(tool="create_note", arguments={"content": n_content})

    # 2.5 Tasks
    # Complete Task ("Mark PCB design as completed", "Mark the project task as complete", "Complete task PPT", "இந்த task complete பண்ணு")
    complete_task_match = re.search(
        r"(?i)\b(?:mark\s+(?:the\s+)?([a-zA-Z0-9_\-\s]+)\s+(?:task\s+)?as\s+(?:completed|complete|done)|complete\s+task\s+([a-zA-Z0-9_\-\s]+))\b",
        clean,
    )
    tamil_task_complete = re.search(
        r"(?i)(.+)\s+(?:task\s+complete\s+பண்ணு|பணி\s+முடிந்தது|task\s+முடிந்தது)",
        clean,
    )
    if complete_task_match or tamil_task_complete:
        if complete_task_match:
            t_title = (complete_task_match.group(1) or complete_task_match.group(2)).strip()
        else:
            t_title = tamil_task_complete.group(1).strip()
        t_title = re.sub(r"(?i)\b(?:this|the|my|task)\b", "", t_title).strip()
        return ToolCall(tool="complete_task", arguments={"title": t_title} if t_title else {})

    # Delete Task ("Delete the presentation task", "Delete task PCB", "task delete பண்ணு")
    delete_task_match = re.search(
        r"(?i)\b(?:delete\s+(?:the\s+)?([a-zA-Z0-9_\-\s]+)\s+task|delete\s+task\s+([a-zA-Z0-9_\-\s]+))\b",
        clean,
    )
    tamil_task_delete = re.search(
        r"(?i)(.+)\s+(?:task\s+delete\s+பண்ணு|பணி\s+நீக்கு)",
        clean,
    )
    if delete_task_match or tamil_task_delete:
        if delete_task_match:
            t_title = (delete_task_match.group(1) or delete_task_match.group(2)).strip()
        else:
            t_title = tamil_task_delete.group(1).strip()
        t_title = re.sub(r"(?i)\b(?:this|the|my|task)\b", "", t_title).strip()
        return ToolCall(tool="delete_task", arguments={"title": t_title} if t_title else {})

    # List Tasks ("What are my tasks?", "What are my tasks today?", "Show today's tasks", "List tasks", "இன்னைக்கு என்ன tasks இருக்கு?")
    if (
        re.search(r"(?i)\b(?:what\s+(?:are\s+my\s+)?tasks(?:\s+today)?|show\s+(?:today's\s+|my\s+)?tasks|list\s+(?:my\s+)?tasks)\b", clean_lower)
        or (re.search(r"(?i)(?:tasks|பணிகள்)", clean_lower) and re.search(r"(?i)(?:என்ன|காட்டு|இருக்கு|list|show)", clean))
    ):
        return ToolCall(tool="list_tasks", arguments={})

    # Create Task ("Add a task to finish my PPT", "Add project meeting to my tasks", "Create a high priority task for PCB design", "PPT complete பண்ணணும், task add பண்ணு")
    create_task_match1 = re.search(
        r"(?i)\b(?:add\s+(?:a\s+)?task\s+(?:to\s+|for\s+)?|create\s+(?:a\s+)?(?:high\s+priority\s+|low\s+priority\s+)?task\s+(?:to\s+|for\s+)?)(.+)",
        clean,
    )
    create_task_match2 = re.search(
        r"(?i)\badd\s+(.+)\s+to\s+my\s+tasks\b",
        clean,
    )
    tamil_task_create = re.search(
        r"(?i)(.+)\s+(?:task\s+add\s+பண்ணு|பணியை\s+சேர்|task\s+சேர்)",
        clean,
    )
    if create_task_match1 or create_task_match2 or tamil_task_create:
        if create_task_match1:
            t_title = create_task_match1.group(1).strip()
        elif create_task_match2:
            t_title = create_task_match2.group(1).strip()
        else:
            t_title = tamil_task_create.group(1).strip()

        priority = "HIGH" if "high priority" in clean_lower else ("LOW" if "low priority" in clean_lower else "MEDIUM")
        return ToolCall(tool="create_task", arguments={"title": t_title, "priority": priority})

    # ==========================================================================
    # 3. Phase 9: System Monitoring & Telemetry
    # ==========================================================================

    # 3.1 Performance & Slowness Diagnosis ("Why is my laptop slow?", "லேப்டாப் ஏன் ஸ்லோவா இருக்கு?")
    if (
        re.search(r"(?i)\b(?:why\s+is\s+(?:my\s+)?(?:laptop|pc|computer|system)\s+slow|laptop\s+slow|pc\s+slow|diagnose\s+(?:laptop|system|pc))\b", clean_lower)
        or re.search(r"(?i)(?:லேப்டாப்|சிஸ்டம்)\s+(?:ஏன்\s+)?(?:ஸ்லோவா|மெதுவாக)\s+இருக்கு", clean)
    ):
        return ToolCall(tool="diagnose_system_performance", arguments={})

    # 3.2 Top Resource Consuming Processes ("Which app is using the most RAM?", "What's using most memory?")
    if (
        re.search(r"(?i)\b(?:which\s+app\s+is\s+using\s+the\s+most\s+(?:ram|memory|cpu)|what(?:'s|\s+is)\s+using\s+(?:the\s+)?most\s+(?:ram|memory|cpu)|top\s+processes|top\s+apps)\b", clean_lower)
        or re.search(r"(?i)(?:எந்த\s+ஆப்|எந்த\s+செயலி)\s+அதிக\s+(?:ram|நினைவகம்|cpu)", clean)
    ):
        sort_by = "cpu" if "cpu" in clean_lower else "memory"
        return ToolCall(tool="get_top_processes", arguments={"limit": 5, "sort_by": sort_by})

    # 3.3 Network Status ("Am I connected to the internet?", "Check internet", "Network status", "Internet connected-ஆ?")
    if (
        re.search(r"(?i)\b(?:am\s+i\s+connected\s+to\s+(?:the\s+)?internet|check\s+(?:network|internet|connection)|network\s+status|internet\s+status|is\s+internet\s+working)\b", clean_lower)
        or re.search(r"(?i)(?:இணைய\s+இணைப்பு|internet\s+(?:இருக்கா|connected-ஆ))", clean)
    ):
        return ToolCall(tool="get_network_status", arguments={})

    # 3.4 Battery Status ("Jarvis, check battery", "battery status", "பேட்டரி எவ்வளவு?", "battery எவ்வளவு?")
    if (
        re.search(r"(?i)\b(?:check\s+battery|battery\s+status|battery\s+percentage|how\s+much\s+battery|battery\s+level|what(?:'s|\s+is)\s+my\s+battery)\b", clean_lower)
        or re.search(r"(?i)(?:பேட்டரி|battery)\s+(?:எவ்வளவு|status|நிலை|இருக்க)", clean)
    ):
        return ToolCall(tool="get_battery_status", arguments={})

    # 3.5 CPU Status ("Jarvis, what's my CPU usage?", "check cpu", "cpu usage")
    if (
        re.search(r"(?i)\b(?:check\s+cpu|cpu\s+usage|cpu\s+load|processor\s+usage|what(?:'s|\s+is)\s+my\s+cpu\s+usage)\b", clean_lower)
        or re.search(r"(?i)cpu\s*(?:பயன்பாடு|usage|எவ்வளவு|நிலை)", clean)
    ):
        return ToolCall(tool="get_cpu_usage", arguments={})

    # 3.6 RAM / Memory Status ("How much RAM am I using?", "check ram", "check memory", "ram usage")
    if (
        re.search(r"(?i)\b(?:how\s+much\s+ram(?:\s+am\s+i\s+using)?|check\s+ram|check\s+memory|ram\s+usage|memory\s+usage|what(?:'s|\s+is)\s+my\s+ram\s+usage)\b", clean_lower)
        or re.search(r"(?i)(?:ram|memory)\s*(?:பயன்பாடு|usage|எவ்வளவு|நிலை|என்ன)", clean)
    ):
        return ToolCall(tool="get_ram_usage", arguments={})

    # 3.7 Disk Storage Status ("How much storage do I have?", "check disk", "check storage", "disk space", "வட்டு சேமிப்பகம்")
    if (
        re.search(r"(?i)\b(?:how\s+much\s+storage(?:\s+do\s+i\s+have)?|check\s+disk|check\s+storage|disk\s+usage|storage\s+usage|disk\s+space|free\s+space)\b", clean_lower)
        or re.search(r"(?i)(?:disk|வட்டு|சேமிப்பகம்)", clean)
    ):
        return ToolCall(tool="get_disk_usage", arguments={})

    # 3.8 Overall System Health ("Jarvis, how is my laptop?", "Check my system", "Check laptop", "System status", "லேப்டாப் நிலை என்ன?")
    if (
        re.search(r"(?i)\b(?:how\s+is\s+my\s+laptop|check\s+(?:my\s+)?(?:system|laptop|pc)|system\s+status|system\s+info|system\s+specs)\b", clean_lower)
        or re.search(r"(?i)லேப்டாப்\s+(?:நிலை|எப்படி\s+இருக்கு)", clean)
    ):
        return ToolCall(tool="get_system_status", arguments={})

    # ==========================================================================
    # 4. Phase 8: Applications, Web, Filesystem, Media, Screenshot
    # ==========================================================================

    # 4.1 Application Launching ("Open Chrome", "Chrome open பண்ணு", "Open Calculator")
    app_open_match = re.search(
        r"(?i)\b(?:open|launch|start|run)\s+(?:application\s+)?([a-zA-Z0-9_\-\s]+)",
        clean,
    )
    tamil_app_open = re.search(
        r"(?i)([a-zA-Z0-9_\-\s]+)\s+(?:open\s+பண்ணு|திற|open\s+செய்யவும்|run\s+பண்ணு)",
        clean,
    )

    if (app_open_match or tamil_app_open) and not re.search(r"(?i)\b(?:website|site|url|folder|file|screenshot|system|ram|cpu|disk|battery|network|task|reminder|note|timer)\b", clean_lower):
        raw_app = app_open_match.group(1).strip() if app_open_match else tamil_app_open.group(1).strip()
        raw_app = re.sub(r"(?i)\b(?:please|now|app|application)\b", "", raw_app).strip()
        if raw_app and len(raw_app) < 30:
            if "." in raw_app and not raw_app.endswith((".exe", ".app")):
                return ToolCall(tool="open_website", arguments={"url": raw_app})
            return ToolCall(tool="open_application", arguments={"application": raw_app.lower()})

    # 4.2 Application Termination ("Close Chrome", "Chrome close பண்ணு")
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
        if raw_app and len(raw_app) < 30 and not re.search(r"(?i)\b(?:task|reminder|note|timer)\b", raw_app):
            return ToolCall(tool="close_application", arguments={"application": raw_app.lower()})

    # 4.3 Web Search ("Search Google for Python tutorials", "Search for weather")
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
        if q and not re.search(r"(?i)\b(?:memory|memories|note|notes|task|tasks)\b", q):
            return ToolCall(tool="search_web_browser", arguments={"query": q})

    # 4.4 Open Website ("Open YouTube", "Open github.com", "Open https://...")
    web_match = re.search(
        r"(?i)\b(?:open\s+(?:website|site|url)\s+|go\s+to\s+)([a-zA-Z0-9_\-\.:/]+)",
        clean,
    )
    if web_match:
        url_target = web_match.group(1).strip()
        return ToolCall(tool="open_website", arguments={"url": url_target})

    # 4.5 Screenshot ("Take a screenshot", "Screenshot எடு", "Capture screen")
    if re.search(r"(?i)\b(?:take\s+(?:a\s+)?screenshot|capture\s+screen|screen\s+capture)\b|screenshot\s+எடு", clean_lower):
        return ToolCall(tool="take_screenshot", arguments={})

    # 4.6 Media & Volume Controls
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

    # 4.7 Filesystem Actions ("Open folder", "Open file", "Delete file")
    delete_file_match = re.search(
        r"(?i)\b(?:delete\s+file|remove\s+file|delete)\s+([a-zA-Z0-9_\-\.\/\\]+)",
        clean,
    )
    if delete_file_match and not re.search(r"(?i)\b(?:memory|memories|conversation|task|reminder|note|timer)\b", clean_lower):
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
