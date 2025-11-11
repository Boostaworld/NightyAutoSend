@nightyScript(
    name="Message Scheduler",
    author="Hay",
    description="Sends repeating messages to specified channels with independent delays.",
    usage=".sendmessages <name>, triple_quoted_message, <channel>, <delay_seconds>"
)
def send_message_script():
    """Nighty helper for repeating messages."""

    import asyncio
    from typing import Any, Dict, Optional

    INFO = ":information_source:"
    OK = ":white_check_mark:"
    WARN = ":warning:"
    BAD = ":x:"

    def fmt(title: str, body: str = "", extra: Optional[Dict[str, str]] = None, footer: Optional[str] = "Message Scheduler — `.sendmessages help`", icon: str = INFO) -> str:
        lines = [f"{icon} **{title.strip()}**"]
        body = body.strip()
        if body:
            lines.append(body)
        if extra:
            for key, value in extra.items():
                chunk = str(value).strip()
                if "\n" in chunk:
                    lines.append(f"> **{key}:**")
                    for row in chunk.splitlines():
                        lines.append(f"> {row}")
                else:
                    lines.append(f"> **{key}:** {chunk}")
        if footer:
            lines.append("")
            lines.append(f"*{footer}*")
        return "\n".join(lines)

    def help_text() -> str:
        commands = "\n".join(
            [
                "`.sendmessages <name>, \"\"\"<message>\"\"\", <channel>, <delay_seconds>`",
                "`.stoptask <name>`",
                "`.listtasks`",
                "`.taskinfo <name>`",
            ]
        )
        return fmt("Message Scheduler Help", "Here are the available commands:", {"Commands": commands})

    def format_delay(seconds: float) -> str:
        seconds = float(seconds)
        if seconds < 60:
            return f"{seconds:.0f}s"
        minutes, sec = divmod(seconds, 60)
        if minutes < 60:
            return f"{int(minutes)}m {int(sec)}s"
        hours, minutes = divmod(minutes, 60)
        return f"{int(hours)}h {int(minutes)}m"

    # --------------------------------------------------------------
    # persistence
    # --------------------------------------------------------------
    def load_jobs() -> Dict[str, Dict[str, Any]]:
        saved = {}
        raw = getConfigData().get("active_tasks", {})
        for name, data in raw.items():
            try:
                saved[name] = {
                    "channel_id": int(data["channel_id"]),
                    "delay": float(data["delay"]),
                    "message": str(data["message"]),
                }
            except (KeyError, TypeError, ValueError):
                continue
        return saved

    def save_jobs(tasks: Dict[str, Dict[str, Any]]) -> None:
        updateConfigData("active_tasks", tasks)

    tasks: Dict[str, Dict[str, Any]] = load_jobs()
    running: Dict[str, asyncio.Task] = {}

    async def start_job(ctx, name: str, info: Dict[str, Any]) -> None:
        channel_id = int(info["channel_id"])
        delay = float(info["delay"])
        message = str(info["message"])

        channel = ctx.bot.get_channel(channel_id)
        if channel is None:
            raise ValueError(f"Channel `{channel_id}` is not accessible. Check permissions and that the bot can see it.")

        async def repeater():
            while True:
                try:
                    await channel.send(message)
                except Exception as exc:  # noqa: BLE001 - surfaced for debugging
                    print(f"[{name}] failed to send message: {exc}")
                await asyncio.sleep(delay)

        if name in running:
            running[name].cancel()

        running[name] = asyncio.create_task(repeater())
        tasks[name] = {"channel_id": channel_id, "delay": delay, "message": message}
        save_jobs(tasks)

    def kill_job(name: str) -> bool:
        removed = False
        task = running.pop(name, None)
        if task:
            task.cancel()
            removed = True
        if name in tasks:
            tasks.pop(name)
            save_jobs(tasks)
            removed = True
        return removed

    def parse_line(arg_line: str) -> tuple[str, Dict[str, Any]]:
        parts = [segment.strip() for segment in arg_line.split(",", 3)]
        if len(parts) != 4:
            raise ValueError("Format: <name>, \"\"\"<message>\"\"\", <channel>, <delay_seconds>")

        name = parts[0].strip().strip('"')
        raw_message = parts[1]
        if raw_message.startswith('"""') and raw_message.endswith('"""'):
            message = raw_message[3:-3]
        else:
            raise ValueError('Message must be wrapped in triple quotes (""" ... """).')

        channel_token = parts[2]
        if channel_token.startswith("<#") and channel_token.endswith(">"):
            channel_token = channel_token[2:-1]

        delay_value = float(parts[3])
        if delay_value <= 0:
            raise ValueError("Delay must be greater than zero seconds.")

        return name, {"channel_id": int(channel_token), "delay": delay_value, "message": message}

    # --------------------------------------------------------------
    # commands
    # --------------------------------------------------------------
    @bot.command(name="sendmessages", description="Starts sending a repeating message to a channel.")
    async def sendmessages(ctx, *, args: str = ""):
        await ctx.message.delete()

        if not args.strip() or args.strip().lower() in {"help", "?"}:
            return await ctx.send(help_text(), delete_after=20)

        try:
            name, info = parse_line(args)
        except Exception as exc:  # noqa: BLE001 - provide friendly feedback
            return await ctx.send(fmt("Could not schedule task", str(exc), icon=BAD), delete_after=15)

        existing = tasks.get(name)
        if existing:
            note = fmt(
                "Task name already in use",
                f"A task called `{name}` already exists. Choose another name or stop the existing task first.",
                {
                    "Current target": f"<#{existing['channel_id']}>",
                    "Delay": format_delay(existing["delay"]),
                },
                icon=WARN,
            )
            return await ctx.send(note, delete_after=15)

        try:
            await start_job(ctx, name, info)
        except Exception as exc:  # noqa: BLE001 - runtime surprises should be surfaced
            return await ctx.send(fmt("Could not start task", str(exc), icon=BAD), delete_after=15)

        preview = info["message"]
        if len(preview) > 200:
            preview = preview[:197] + "…"
        preview_block = f"```{preview}```" if preview else "(message is empty)"

        confirmation = fmt(
            "Task scheduled!",
            f"`{name}` will now post on repeat.",
            {
                "Channel": f"<#{info['channel_id']}>",
                "Interval": format_delay(info["delay"]),
                "Preview": preview_block,
            },
            icon=OK,
        )
        await ctx.send(confirmation, delete_after=20)

    @bot.command(name="stoptask", description="Stops a running sendmessages task.")
    async def stoptask(ctx, *, name: str = ""):
        await ctx.message.delete()

        if not name.strip():
            return await ctx.send(fmt("Task name required", "Usage: `.stoptask <name>`", icon=WARN), delete_after=12)

        if kill_job(name):
            message = fmt("Task stopped", f"`{name}` will no longer send messages.", icon=OK)
        else:
            message = fmt("Task not found", f"No task called `{name}` exists.", icon=WARN)
        await ctx.send(message, delete_after=12)

    @bot.command(name="listtasks", description="Lists all active message tasks.")
    async def listtasks(ctx):
        await ctx.message.delete()

        if not tasks:
            return await ctx.send(fmt("No active tasks", "Use `.sendmessages` to start one."), delete_after=12)

        rows = [f"**{task_name}** • {format_delay(data['delay'])} • <#{data['channel_id']}>" for task_name, data in tasks.items()]
        await ctx.send(fmt("Active message tasks", "\n".join(rows)), delete_after=20)

    @bot.command(name="taskinfo", description="Shows message contents for a scheduled task.")
    async def taskinfo(ctx, *, name: str = ""):
        await ctx.message.delete()

        if not name.strip():
            return await ctx.send(fmt("Task name required", "Usage: `.taskinfo <name>`", icon=WARN), delete_after=12)

        info = tasks.get(name)
        if not info:
            return await ctx.send(fmt("Task not found", f"No task called `{name}` exists.", icon=WARN), delete_after=12)

        preview = info["message"] or "(message is empty)"
        preview_block = f"```{preview}```" if preview else "(message is empty)"
        await ctx.send(
            fmt(
                f"Details for `{name}`",
                "Here is the current message preview:",
                {
                    "Channel": f"<#{info['channel_id']}>",
                    "Interval": format_delay(info["delay"]),
                    "Message": preview_block,
                },
                icon=OK,
            ),
            delete_after=30,
        )


# Register the script
send_message_script()
