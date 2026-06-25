import pytz

class GlobalVar():
    """
    When this file is included
    This line APP_CLIENT_ID = os.getenv('') will run
    """
    g_my_timezone        = pytz.timezone("Asia/Singapore")

    """
    For command processing
    My rules, the list index contains the following
    [0] - Function name, execute this function
    [1] - parameters to pass to function specified [0]
    [2] - The payload ENUM, this is for handling function that sends requests,
        - It will make sure after running that function specified in [0], handle the incoming message first.
    [3] - For debugging [2] purposes, this holds the comment to tell me the
        - one whom trigger this task to keep waiting for server reply is triggered by whom
        - to the server. If this is set, [0] shall be None
    """
    g_task_queue    = []
    GENERATED_PATH  = "./generated/" # Path for putting generated files
