from datetime import date, timedelta

def run_rollover(supabase, user_id):
    today = date.today()
    yesterday = today - timedelta(days=1)

    # get all pending tasks scheduled for yesterday or earlier
    r = supabase.table("tasks").select("*").eq("user_id", user_id).eq("status", "pending").execute()
    tasks = r.data if r.data else []

    flagged = []

    for task in tasks:
        scheduled_date = task.get("scheduled_date")
        deadline = task.get("deadline")
        rollover_count = task.get("rollover_count", 0)

        if not scheduled_date:
            continue

        scheduled = date.fromisoformat(scheduled_date)

        # only process tasks from before today
        if scheduled >= today:
            continue

        # has deadline and it passed → mark overdue
        if deadline and date.fromisoformat(deadline) < today:
            supabase.table("tasks").update({
                "status": "overdue"
            }).eq("id", task["id"]).execute()

        else:
            # no deadline or deadline not passed → roll over
            new_rollover_count = rollover_count + 1

            supabase.table("tasks").update({
                "scheduled_date": today.isoformat(),
                "rollover_count": new_rollover_count
            }).eq("id", task["id"]).execute()

            # flag if rolled over 5+ days
            if new_rollover_count >= 5:
                flagged.append(task["title"])

    return flagged