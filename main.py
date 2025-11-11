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

    import discord

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
                        print(f"[{task.name}] Error sending message: {exc}", type_="ERROR")
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

    def build_embed(
        *,
        title: str,
        description: str,
        color: int,
        fields: Optional[Dict[str, str]] = None,
    ) -> discord.Embed:
        embed = discord.Embed(title=title, description=description, color=color)
        if fields:
            for name, value in fields.items():
                embed.add_field(name=name, value=value, inline=True)
        embed.set_footer(text="Message Scheduler • .sendmessages help for usage")
        return embed

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
        parts = [p.strip() for p in args.split(",", 3)]
        if len(parts) != 4:
            raise ValueError(
                "Format: <name>, \"\"\"<message>\"\"\", <channel>, <delay_seconds>"
            )

        name = parts[0].strip('" ')
        raw_message = parts[1]
        if raw_message.startswith('"""') and raw_message.endswith('"""'):
            message = raw_message[3:-3]
        else:
            raise ValueError('Message must be wrapped in triple quotes (""" ... """).')

        channel_token = parts[2].strip()
        if channel_token.startswith("<#") and channel_token.endswith(">"):
            channel_token = channel_token[2:-1]

        delay = float(parts[3])

        return ScheduledTask(
            name=name,
            channel_id=int(channel_token),
            delay=delay,
            message=message,
        )

    def help_embed() -> discord.Embed:
        lines = [
            "`.sendmessages <name>, \"\"\"<message>\"\"\", <channel>, <delay>`",
            "`.stoptask <name>`",
            "`.listtasks`",
        ]
        return build_embed(
            title="Message Scheduler Help",
            description="Quick reference for managing repeating messages.",
            color=0x5865F2,
            fields={"Commands": "\n".join(lines)},
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
            return await ctx.send(embed=help_embed(), delete_after=20)

        try:
            task = parse_definition(args)
            existing = manager.get(task.name)
            if existing:
                embed = build_embed(
                    title="Task name already in use",
                    description=f"A task called `{task.name}` already exists."
                    " Choose another name or stop the existing one first.",
                    color=0xFEE75C,
                    fields={
                        "Current target": f"<#{existing.channel_id}>",
                        "Delay": format_delay(existing.delay),
                    },
                )
                return await ctx.send(embed=embed, delete_after=15)

            await manager.start(ctx, task)

            preview = (task.message[:150] + "…") if len(task.message) > 150 else task.message
            embed = build_embed(
                title="Task scheduled!",
                description=f"`{task.name}` will post on repeat.",
                color=0x57F287,
                fields={
                    "Channel": f"<#{task.channel_id}>",
                    "Interval": format_delay(task.delay),
                    "Preview": preview or "(message is empty)",
                },
            )
            await ctx.send(embed=embed, delete_after=20)

        except Exception as exc:
            embed = build_embed(
                title="Could not schedule task",
                description=str(exc),
                color=0xED4245,
            )
            await ctx.send(embed=embed, delete_after=15)

    @bot.command(name="stoptask", description="Stops a running sendmessages task.")
    async def stop_task(ctx, *, name: str = ""):
        await ctx.message.delete()

        if not name.strip():
            embed = build_embed(
                title="Task name required",
                description="Usage: `.stoptask <name>`",
                color=0xFEE75C,
            )
            return await ctx.send(embed=embed, delete_after=12)

        if manager.stop(name):
            embed = build_embed(
                title="Task stopped",
                description=f"`{name}` will no longer send messages.",
                color=0xED4245,
            )
        else:
            embed = build_embed(
                title="Task not found",
                description=f"No task called `{name}` exists.",
                color=0xFEE75C,
            )
        await ctx.send(embed=embed, delete_after=12)

    @bot.command(name="listtasks", description="Lists all active message tasks.")
    async def list_tasks(ctx):
        await ctx.message.delete()

        tasks = manager.list()
        if not tasks:
            embed = build_embed(
                title="No active tasks",
                description="Use `.sendmessages` to start one.",
                color=0x5865F2,
            )
            return await ctx.send(embed=embed, delete_after=12)

        description_lines = []
        for task in tasks.values():
            description_lines.append(
                f"**{task.name}** • {format_delay(task.delay)} • <#{task.channel_id}>"
            )

        embed = build_embed(
            title="Active message tasks",
            description="\n".join(description_lines),
            color=0x5865F2,
        )
        await ctx.send(embed=embed, delete_after=20)

    @bot.command(name="taskinfo", description="Shows message contents for a scheduled task.")
    async def task_info(ctx, *, name: str = ""):
        await ctx.message.delete()

        if not name.strip():
            embed = build_embed(
                title="Task name required",
                description="Usage: `.taskinfo <name>`",
                color=0xFEE75C,
            )
            return await ctx.send(embed=embed, delete_after=12)

        task = manager.get(name)
        if not task:
            embed = build_embed(
                title="Task not found",
                description=f"No task called `{name}` exists.",
                color=0xED4245,
            )
            return await ctx.send(embed=embed, delete_after=12)

        embed = build_embed(
            title=f"Details for `{name}`",
            description="Preview of the repeating message.",
            color=0x57F287,
            fields={
                "Channel": f"<#{task.channel_id}>",
                "Interval": format_delay(task.delay),
            },
        )
        embed.add_field(name="Message", value=task.message or "(message is empty)", inline=False)
        await ctx.send(embed=embed, delete_after=30)


# Register the script
send_message_script()
