@nightyScript(
    name="Message Scheduler",
    author="Hay",
    description="Sends repeating messages to specified channels with independent delays.",
    usage=".sendmessages <name>, triple_quoted_message, <channel>, <delay_seconds>"
)
def send_message_script():
    """Utility commands for orchestrating repeating Nighty messages."""

    import asyncio
    from dataclasses import dataclass
    from typing import Dict, Optional

    # ---------------------------------------------------------------------
    # Data models & helpers
    # ---------------------------------------------------------------------
    @dataclass
    class ScheduledTask:
        name: str
        channel_id: int
        delay: float
        message: str

        def to_config(self) -> Dict[str, str]:
            return {
                "channel_id": self.channel_id,
                "delay": self.delay,
                "message": self.message,
            }

    class TaskManager:
        def __init__(self):
            self.running: Dict[str, asyncio.Task] = {}
            self.tasks: Dict[str, ScheduledTask] = self._load_tasks()

        # --------------------------- persistence ---------------------------
        def _load_tasks(self) -> Dict[str, ScheduledTask]:
            data = getConfigData()
            stored = data.get("active_tasks") or {}
            tasks: Dict[str, ScheduledTask] = {}
            for name, raw in stored.items():
                try:
                    tasks[name] = ScheduledTask(
                        name=name,
                        channel_id=int(raw["channel_id"]),
                        delay=float(raw["delay"]),
                        message=str(raw["message"]),
                    )
                except (KeyError, TypeError, ValueError):
                    # Skip malformed entries while keeping the rest intact.
                    continue
            return tasks

        def save(self) -> None:
            updateConfigData(
                "active_tasks",
                {name: task.to_config() for name, task in self.tasks.items()},
            )

        # ---------------------------- runtime -----------------------------
        async def start(self, ctx, task: ScheduledTask) -> None:
            channel = ctx.bot.get_channel(task.channel_id)
            if channel is None:
                raise ValueError(
                    f"Channel `{task.channel_id}` is not accessible. Try re-inviting the bot or checking permissions."
                )

            async def send_loop():
                while True:
                    try:
                        await channel.send(task.message)
                    except Exception as exc:  # pragma: no cover - runtime safeguard
                        print(f"[{task.name}] Error sending message: {exc}")
                    await asyncio.sleep(task.delay)

            if task.name in self.running:
                self.running[task.name].cancel()

            loop_task = asyncio.create_task(send_loop())
            self.running[task.name] = loop_task
            self.tasks[task.name] = task
            self.save()

        def stop(self, name: str) -> bool:
            stopped = False
            task = self.running.pop(name, None)
            if task:
                task.cancel()
                stopped = True

            if name in self.tasks:
                self.tasks.pop(name, None)
                self.save()
                stopped = True

            return stopped

        def get(self, name: str) -> Optional[ScheduledTask]:
            return self.tasks.get(name)

        def list(self) -> Dict[str, ScheduledTask]:
            return dict(self.tasks)

    manager = TaskManager()

    INFO_ICON = ":information_source:"
    SUCCESS_ICON = ":white_check_mark:"
    WARNING_ICON = ":warning:"
    ERROR_ICON = ":x:"

    def build_message(
        *,
        title: str,
        body: str = "",
        highlights: Optional[Dict[str, str]] = None,
        footer: Optional[str] = "Message Scheduler — try `.sendmessages help`",
        icon: str = INFO_ICON,
    ) -> str:
        lines = [f"{icon} **{title}**"]

        body = body.strip()
        if body:
            lines.append(body)

        if highlights:
            for name, value in highlights.items():
                value_lines = str(value).splitlines() or [""]
                if len(value_lines) == 1:
                    lines.append(f"> **{name}:** {value_lines[0]}")
                else:
                    lines.append(f"> **{name}:**")
                    for line in value_lines:
                        lines.append(f"> {line}")

        if footer:
            lines.append("")
            lines.append(f"*{footer}*")

        return "\n".join(lines)

    def format_delay(seconds: float) -> str:
        seconds = float(seconds)
        if seconds < 60:
            return f"{seconds:.0f} seconds"
        minutes, sec = divmod(seconds, 60)
        if minutes < 60:
            return f"{int(minutes)}m {int(sec)}s"
        hours, minutes = divmod(minutes, 60)
        return f"{int(hours)}h {int(minutes)}m"

    def parse_definition(args: str) -> ScheduledTask:
        # Expected format: <name>, """<message>""", <channel>, <delay_seconds>
        if "," not in args:
            raise ValueError(
                "Format: <name>, \"\"\"<message>\"\"\", <channel>, <delay_seconds>"
            )

        name_token, remainder = args.split(",", 1)
        name = name_token.strip().strip('"')
        remainder = remainder.lstrip()

        if not remainder.startswith('"""'):
            raise ValueError('Message must be wrapped in triple quotes (""" ... """).')

        end_index = remainder.find('"""', 3)
        if end_index == -1:
            raise ValueError('Message must be wrapped in triple quotes (""" ... """).')

        message = remainder[3:end_index]
        remainder = remainder[end_index + 3 :].lstrip()

        if not remainder.startswith(","):
            raise ValueError(
                "Format: <name>, \"\"\"<message>\"\"\", <channel>, <delay_seconds>"
            )

        remainder = remainder[1:].lstrip()
        parts = [part.strip() for part in remainder.split(",", 1)]
        if len(parts) != 2:
            raise ValueError(
                "Format: <name>, \"\"\"<message>\"\"\", <channel>, <delay_seconds>"
            )

        channel_token, delay_token = parts
        if channel_token.startswith("<#") and channel_token.endswith(">"):
            channel_token = channel_token[2:-1]

        delay = float(delay_token)

        return ScheduledTask(
            name=name,
            channel_id=int(channel_token),
            delay=delay,
            message=message,
        )

    def help_message() -> str:
        lines = [
            "`.sendmessages <name>, \"\"\"<message>\"\"\", <channel>, <delay_seconds>`",
            "`.stoptask <name>`",
            "`.listtasks`",
            "`.taskinfo <name>`",
        ]
        return build_message(
            title="Message Scheduler Help",
            body="Here are the available commands:",
            highlights={"Commands": "\n".join(lines)},
            icon=INFO_ICON,
        )

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------
    @bot.command(
        name="sendmessages",
        description="Starts sending a repeating message to a channel.",
    )
    async def start_send(ctx, *, args: str = ""):
        await ctx.message.delete()

        if not args.strip() or args.strip().lower() in {"help", "?"}:
            return await ctx.send(help_message(), delete_after=20)

        try:
            task = parse_definition(args)
            existing = manager.get(task.name)
            if existing:
                message = build_message(
                    title="Task name already in use",
                    body=(
                        f"A task called `{task.name}` already exists. Choose another name or"
                        " stop the existing task first."
                    ),
                    highlights={
                        "Current target": f"<#{existing.channel_id}>",
                        "Delay": format_delay(existing.delay),
                    },
                    icon=WARNING_ICON,
                )
                return await ctx.send(message, delete_after=15)

            await manager.start(ctx, task)

            preview = (task.message[:150] + "…") if len(task.message) > 150 else task.message
            preview_block = f"```{preview}```" if preview else "(message is empty)"
            message = build_message(
                title="Task scheduled!",
                body=f"`{task.name}` will now post on repeat.",
                highlights={
                    "Channel": f"<#{task.channel_id}>",
                    "Interval": format_delay(task.delay),
                    "Preview": preview_block,
                },
                icon=SUCCESS_ICON,
            )
            await ctx.send(message, delete_after=20)

        except Exception as exc:
            message = build_message(
                title="Could not schedule task",
                body=str(exc),
                icon=ERROR_ICON,
            )
            await ctx.send(message, delete_after=15)

    @bot.command(name="stoptask", description="Stops a running sendmessages task.")
    async def stop_task(ctx, *, name: str = ""):
        await ctx.message.delete()

        if not name.strip():
            message = build_message(
                title="Task name required",
                body="Usage: `.stoptask <name>`",
                icon=WARNING_ICON,
            )
            return await ctx.send(message, delete_after=12)

        if manager.stop(name):
            message = build_message(
                title="Task stopped",
                body=f"`{name}` will no longer send messages.",
                icon=SUCCESS_ICON,
            )
        else:
            message = build_message(
                title="Task not found",
                body=f"No task called `{name}` exists.",
                icon=WARNING_ICON,
            )
        await ctx.send(message, delete_after=12)

    @bot.command(name="listtasks", description="Lists all active message tasks.")
    async def list_tasks(ctx):
        await ctx.message.delete()

        tasks = manager.list()
        if not tasks:
            message = build_message(
                title="No active tasks",
                body="Use `.sendmessages` to start one.",
            )
            return await ctx.send(message, delete_after=12)

        description_lines = []
        for task in tasks.values():
            description_lines.append(
                f"**{task.name}** • {format_delay(task.delay)} • <#{task.channel_id}>"
            )

        message = build_message(
            title="Active message tasks",
            body="\n".join(description_lines),
        )
        await ctx.send(message, delete_after=20)

    @bot.command(name="taskinfo", description="Shows message contents for a scheduled task.")
    async def task_info(ctx, *, name: str = ""):
        await ctx.message.delete()

        if not name.strip():
            message = build_message(
                title="Task name required",
                body="Usage: `.taskinfo <name>`",
                icon=WARNING_ICON,
            )
            return await ctx.send(message, delete_after=12)

        task = manager.get(name)
        if not task:
            message = build_message(
                title="Task not found",
                body=f"No task called `{name}` exists.",
                icon=WARNING_ICON,
            )
            return await ctx.send(message, delete_after=12)

        message_preview = task.message or "(message is empty)"
        message_block = f"```{message_preview}```" if message_preview else "(message is empty)"
        message = build_message(
            title=f"Details for `{name}`",
            body="Here is the current message preview:",
            highlights={
                "Channel": f"<#{task.channel_id}>",
                "Interval": format_delay(task.delay),
                "Message": message_block,
            },
            icon=SUCCESS_ICON,
        )
        await ctx.send(message, delete_after=30)


# Register the script
send_message_script()
