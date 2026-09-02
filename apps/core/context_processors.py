def branding(request):
    try:
        from .models import SystemSettings
        s = SystemSettings.get_solo()
        return {
            "brand": {
                "org": s.organization_name or "NovaTIP",
                "login_title": s.login_title or "NovaTIP",
                "login_subtitle": s.login_subtitle or "Threat Intelligence Platform",
                "logo": s.logo,
                "prefix": s.local_id_prefix,
                "setup_completed": s.setup_completed,
            }
        }
    except Exception:
        return {
            "brand": {
                "org": "NovaTIP",
                "login_title": "NovaTIP",
                "login_subtitle": "Threat Intelligence Platform",
                "logo": None,
                "prefix": "",
                "setup_completed": False,
            }
        }
