@nightyScript(
    name="Message Scheduler",
    author="Hay",
    description="Sends repeating messages to specified channels with independent delays.",
    usage=".sendmessages <name>, triple_quoted_message, <channel_id>, <delay_seconds>"
)
def send_message_script():
    """
    MESSAGE SCHEDULER SCRIPT
    -----------------------
    
    Sends repeating messages to specified channels with independent delays.
    
    COMMANDS:
    .sendmessages <name>, triple_quoted_message, <channel_id>, <delay_seconds> - Start a repeating message task
    .stoptask <name> - Stop a running task
    .listtasks - List all active tasks
    
    EXAMPLES:
    .sendmessages "Ad1", triple_quoted_message, 1234567890123456, 60
    .stoptask "Ad1"
    .listtasks
    
    NOTES:
    - Messages must be wrapped in triple quotes around the message text
    - Each task runs independently with its own delay
    - Tasks persist in configuration data
    """
    
    import asyncio
    
    # Initialize configuration data if missing
    data = getConfigData()
    if data.get("active_tasks") is None:
        updateConfigData("active_tasks", {})
    
    # Store running tasks in memory (not in config)
    running_tasks = {}
    
    # --- Helper Functions ---
    def parse_definition(args: str):
        """
        Expected format:
          .sendmessages "Ad1", \"\"\"Buy now!\"\"\", 1234567890123456, 60
        """
        parts = [p.strip() for p in args.split(",", 3)]
        if len(parts) != 4:
            raise ValueError("Format: <name>, triple_quoted_message, <channel_id>, <delay_seconds>")
    
        name = parts[0].strip('" ')
        msg = parts[1]
        if msg.startswith('"""') and msg.endswith('"""'):
            msg = msg[3:-3]
        else:
            raise ValueError('Message must be wrapped in triple quotes (""" ... """).')
    
        channel_id = parts[2].strip()
        delay = float(parts[3].strip())
        return name, msg, int(channel_id), delay  # <--- return ends function
    
    # async function must be top-level
    async def send_loop(name, channel, message, delay):
        """Loop that repeatedly sends the given message."""
        while True:
            try:
                await channel.send(message)
            except Exception as e:
                print(f"[{name}] Error sending message: {e}", type_="ERROR")
            await asyncio.sleep(delay)
    
    
    # --- Commands ---
    @bot.command(name="sendmessages", description="Starts sending a repeating message to a channel.")
    async def start_send(ctx, *, args: str = ""):
        await ctx.message.delete()

        if not args.strip():
            return await ctx.send(
                "❌ **Missing arguments.**\nUsage: `.sendmessages <name>, \"\"\"<message>\"\"\", <channel_id>, <delay_seconds>`",
                delete_after=12
            )

        try:
            name, msg, channel_id, delay = parse_definition(args)
            data = getConfigData()
            tasks = data.get("active_tasks", {})

            if name in tasks:
                return await ctx.send(f"❌ Task `{name}` already running.", delete_after=10)

            channel = ctx.bot.get_channel(channel_id)
            if not channel:
                return await ctx.send(f"❌ Invalid or inaccessible channel ID: {channel_id}", delete_after=10)


            task = asyncio.create_task(send_loop(name, channel, msg, delay))
            tasks[name] = {
                "channel_id": channel_id,
                "delay": delay,
                "message": msg
            }
            running_tasks[name] = task  # store the actual asyncio.Task in memory only
            updateConfigData("active_tasks", tasks)
            await ctx.send(f"✅ Task `{name}` started — sending every {delay}s to <#{channel_id}>.", delete_after=10)

        except Exception as e:
            await ctx.send(f"⚠️ Error: {e}", delete_after=10)

    @bot.command(name="stoptask", description="Stops a running sendmessages task.")
    async def stop_task(ctx, *, name: str = ""):
        await ctx.message.delete()
        if not name.strip():
            return await ctx.send("❌ **Missing name.** Usage: `.stoptask <name>`", delete_after=10)
    
        data = getConfigData()
        tasks = data.get("active_tasks", {})
    
        if name not in tasks:
            return await ctx.send(f"❌ No task named `{name}` found.", delete_after=10)
    
        # Get the task from the in-memory dictionary, not from config
        task_obj = running_tasks.get(name)
        if task_obj:
            task_obj.cancel()
            running_tasks.pop(name, None)  # Remove from memory
    
        # Remove from config
        tasks.pop(name, None)
        updateConfigData("active_tasks", tasks)
        await ctx.send(f"🛑 Task `{name}` stopped.", delete_after=10)

    @bot.command(name="listtasks", description="Lists all active message tasks.")
    async def list_tasks(ctx):
        await ctx.message.delete()
        data = getConfigData()
        tasks = data.get("active_tasks", {})

        if not tasks:
            return await ctx.send("📭 No active tasks.", delete_after=10)

        lines = [
            f"• {name} → every {info['delay']}s in <#{info['channel_id']}>"
            for name, info in tasks.items()
        ]
        await ctx.send("🧾 **Active Tasks:**\n" + "\n".join(lines), delete_after=15)


# Register the script
send_message_script()
