import MetaTrader5 as mt5
from globalpy import GlobalVar
import time
from datetime import datetime, timedelta
import threading
import calendar
import numpy as np
import csv
import os

if not mt5.initialize():
    raise RuntimeError(mt5.last_error())

# For MT5, if your desktop already logged in, then usually you dont need to login
# And if already logged in, account_info() should have infos
ACCOUNT = 12345678
PASSWORD = "password"
SERVER = "Broker-Server"
if mt5.account_info() is None:
    print("Logging in...")
    if not mt5.login(
        ACCOUNT,
        password=PASSWORD,
        server=SERVER
    ):
        raise RuntimeError(mt5.last_error())

print("MT5 API is ready.")

def showHelp(*args):
    required_arguments = 0
    if len(args) < required_arguments:
        print(f"Missing arguments, required: {required_arguments}")
        return

    for cmd, (func, desc) in defined_commands.items():
        print(f"{cmd:10} - {desc}")

def User_Disconnect(*args):
    required_arguments = 0
    if len(args) < required_arguments:
        print(f"Missing arguments, required: {required_arguments}")
        return

    stop_event.set()
    mt5.shutdown()
    print(f"User_Disconnect: Program Exitted.")

def Request_History_Bar_Data(*args):
    """
    [command] [symbolname] [year] [month]
    eg: bar btcusd 2026 05
    Get BRCUSD Year 2026 May whole month data

    Give symbol name like this "btcusd", "ethusd"
    Also i tested with 2 weeks, 3 weeks, the request ok woh lol
    I really dk what is the maximum limit per request for MT5
    But if i put 1 week, average array received is 10k, if i put 2 weeks 3 weeks,
    can go up to 20k 30k, also ok lol

    If you see that when you request for hsitory bar, and only get 1 bar
    Check your MT5 desktop, scroll to the left see how far it goes
    Apparently the API only able to retrieve whatever your MT5 desktop can see
    Maybe 1 option is go to MT5 desktop -> Tools -> Options -> Charts -> Max bars in chart -> Choose Unlimited
    After that, right click on chart -> Refresh
    Then, press "Home" to go to the earliest charts you can see
    So, still same lol, no further bars shown, welp, rips
    Update: Now it works lol, after i open my PC next day, now it goes back all the way to 2018 wow

    Btw, the code actually just copy from the MT5 logged in on your desktop
    Hence, the timezone also follow desktop one, cannot contorl
    MT5 desktop, the timezone, cannot modify, it was specified by your broker
    So you will notice the UNIX time macam off when you convert
    i thnk the correct timezone to use is UTC, but i dont care lah
    """
    required_arguments = 0
    if len(args) < required_arguments:
        print(f"Missing arguments, required: {required_arguments}")
        return

    symbol, year, month = args[0], args[1], args[2]

    symbol = symbol.upper()
    filename = symbol + "-" + str(year) + "-" + str(month)
    year = int(year)
    month = int(month)
    timeframe = mt5.TIMEFRAME_M1

    # Start / end of month (timezone aware)
    from_dt = GlobalVar.g_my_timezone.localize(datetime(year, month, 1))
    last_day = calendar.monthrange(year, month)[1]
    to_dt = GlobalVar.g_my_timezone.localize(datetime(year, month, last_day, 23, 59, 59))

    # build chunks (1 week)
    chunks = []
    current_start = from_dt
    while current_start < to_dt:
        current_end = current_start + timedelta(weeks=1)
        if current_end > to_dt:
            current_end = to_dt
        chunks.append((current_start, current_end))
        current_start = current_end + timedelta(seconds=1)

    monthly = []
    for dt_from, dt_to in chunks:
        print(f"Requesting Symbol:{symbol}, from:{dt_from}, to:{dt_to}")

        rates = mt5.copy_rates_range(
            symbol,
            timeframe,
            dt_from,
            dt_to
        )

        if rates is None:
            print("Data null!")
            continue

        print(f"Chunk received: {len(rates)} bars")
        monthly.append(rates)

    merged = np.concatenate(monthly)
    print("Total bars:", len(merged))

    write_to_file = GlobalVar.GENERATED_PATH + filename + ".csv"

    os.makedirs(GlobalVar.GENERATED_PATH, exist_ok=True)
    os.makedirs(GlobalVar.GENERATED_PATH + "weekly/", exist_ok=True)

    with open(write_to_file, "w", newline="") as f:
        writer = csv.writer(f)
        # Got this from https://www.mql5.com/en/docs/python_metatrader5/mt5copyratesrange_py
        writer.writerow(["time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"])
        for week_no, weekly in enumerate(monthly, start=1):
            # Write into weekly
            write_to_file_weekly = GlobalVar.GENERATED_PATH + "weekly/" + filename + "-" + f"{week_no:02d}" + ".csv"
            with open(write_to_file_weekly, "w", newline="") as f:
                writer_weekly = csv.writer(f)
                writer_weekly.writerow(["time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"])
                for bar in weekly:
                    writer_weekly.writerow(bar)
                    writer.writerow(bar)
    print(f"Wrote history bar data to {write_to_file}")

defined_commands = {
    "help": (showHelp,"Show Help"),
    "qq": (User_Disconnect,"Disconnect, terminate script"),
    "bar": (Request_History_Bar_Data, "Get Historic Bar Data")
}

def executeUserCommand():
    try:
        while not stop_event.is_set():
            while len(GlobalVar.g_task_queue) == 0:
                current_time = time.time()
                dt = datetime.fromtimestamp(current_time, GlobalVar.g_my_timezone)
                formatted_time = dt.strftime("%H%M")
                print("\n=====================================\n")
                userInput = input(f"[{formatted_time}] Cmd (Rmb Termux eats 1 char): ")
                print(f"Cmd typed: {userInput}")

                userInputSplit = userInput.split(" ")
                if not userInputSplit:
                    print("Command split error: ", userInput)
                    continue

                user_typed_command = userInputSplit[0]
                parameters = None
                try:
                    parameters = [parameter if parameter[0] != "*" else parameter[1:] for parameter in userInputSplit[1:]]
                except:
                    print("Invalid parameters: ", userInput)
                    continue

                if user_typed_command not in defined_commands:
                    print("Invalid Command: ", userInput)
                    continue

                # commands[command] returns "(showHelp,"")"
                # Hence, function_to_execute gets showHelp
                # _ gets ""
                function_to_execute, _ = defined_commands[user_typed_command]
                GlobalVar.g_task_queue.append([function_to_execute, parameters, None, None])
        print(f"executeUserCommand Thread stopped")

    # !CTRL C!
    # To detech & handle CTRL C, but this will not work
    # Due to `reactor.run` is being treated as main thread
    except KeyboardInterrupt:
        print(f"CTRL C is pressed")
    # Detect CTRL D
    except EOFError:
        print(f"Disconnect & Terminate script")
        User_Disconnect()

def processCommand():
    while not stop_event.is_set():
        while len(GlobalVar.g_task_queue) != 0:

            # Usually [2] is waiting for server to reply
            # Wait until server finish replying
            # There's a reason why i dont use current_task = GlobalVar.g_task_queue[0]
            # and then check current_task instead
            # Because once received server reply, i will modify the GlobalVar.g_task_queue
            # If i use current_task, forever stuck in loop
            if GlobalVar.g_task_queue[0][2] is not None:
                while GlobalVar.g_task_queue[0][2] is not None:
                    continue
                # One done replying, this task is done, next
                GlobalVar.g_task_queue.pop(0)
                continue

            current_task = GlobalVar.g_task_queue[0]

            # [0] is function, if is None, means the current task
            # is waiting for server to reply to me
            function = current_task[0]
            parameters = current_task[1]
            if parameters is None:
                parameters = []

            # Run the function
            function(*parameters)

            # After run the function only then you pop it
            # if not ah, the executeUserCommand thread will
            # prompt for user input before you finish executing
            # the previous command
            GlobalVar.g_task_queue.pop(0)
    print(f"processCommand Thread stopped")

stop_event = threading.Event()
thread_user_input = threading.Thread(target=executeUserCommand)
thread_user_input.start()
thread_process_command = threading.Thread(target=processCommand)
thread_process_command.start()



