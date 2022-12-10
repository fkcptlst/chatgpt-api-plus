# coding:utf-8

import time
import re
import os
import flask
from retry import retry
import shutil

from tqdm import tqdm

from flask import g, request

from playwright.sync_api import sync_playwright

try:
    from .chat_logger import ChatLogger
except ImportError:
    from chat_logger import ChatLogger

os.chdir(os.path.dirname(os.path.abspath(__file__)))
workdir = os.getcwd()
print(f"workdir:{workdir}")

APP = flask.Flask(__name__)
PLAY = sync_playwright().start()
# add proxy 127.0.0.1:7890
BROWSER = PLAY.chromium.launch_persistent_context(
    user_data_dir=os.path.join(workdir, "browser_files"),
    headless=False,
    proxy={"server": "http://localhost:7890"},
)

chat_logger = ChatLogger(os.path.join(workdir, "conversations"), "chatgpt")

PAGE = BROWSER.new_page()


def screenshot(page, name):
    page.screenshot(path=os.path.join(
        workdir, "screenshots", f"screenshot_{name}.png"))


def savepage(page, name):
    with open(os.path.join(workdir, "htmls", f"{name}.html"), "w", encoding='utf-8') as f:
        f.write(page.content())


def record_page(page, name):
    time.sleep(1)

    savepage(page, name)
    screenshot(page, name)


@retry(tries=2, delay=3, max_delay=5)
def login(PAGE):
    if os.path.exists(os.path.join(workdir, "screenshots")):
        shutil.rmtree(os.path.join(workdir, "screenshots"))
    os.mkdir(os.path.join(workdir, "screenshots"))

    if os.path.exists(os.path.join(workdir, "htmls")):
        shutil.rmtree(os.path.join(workdir, "htmls"))
    os.mkdir(os.path.join(workdir, "htmls"))

    time.sleep(1)

    try:
        print("Logging in...")
        PAGE.goto("https://chat.openai.com/auth/login")
        record_page(PAGE, "1")
        PAGE.get_by_role("button", name="Log in").click()
        print("Log in clicked")
        time.sleep(2)
        record_page(PAGE, "2")
        PAGE.get_by_label("Email address").click()
        PAGE.get_by_label("Email address").fill("kevinfinley@163.com")
        PAGE.locator("button[name=\"action\"]").click()
        print("Email filled")
        time.sleep(2)
        record_page(PAGE, "2.1")
        # try select img alt="captcha", if exist, then  store img to screenshot folder
        try:
            # captcha_img = PAGE.get_by_alt("captcha")
            # captcha_img.screenshot(path=os.path.join(workdir, "screenshots", f"screenshot_captcha.png"))
            # print("captcha exist, please check screenshot folder")
            # captcha = input("please input captcha:")
            # PAGE.get_by_label("Captcha").click()
            # PAGE.get_by_label("Captcha").fill(captcha)

            PAGE.get_by_label("Enter the code shown above").click()
            captcha = input("please input captcha:")
            PAGE.get_by_label("Enter the code shown above").fill(captcha)
            PAGE.locator("button[name=\"action\"]").click()

            print("Captcha filled")
            time.sleep(2)
            record_page(PAGE, "2.1.1")
        except:
            pass
        print("after checking captcha")
        record_page(PAGE, "2.2")

        PAGE.get_by_label("Password").fill("Tvcq_5tM.tww49G")
        PAGE.get_by_role("button", name="Continue").click()
        print("Password filled")
        time.sleep(2)
        record_page(PAGE, "2.9")
    except Exception as e:
        # screenshot
        record_page(PAGE, "login_error")
        raise e
    record_page(PAGE, "3")
    print("Logged in, waiting for 2FA...")
    try:
        # PAGE.wait_for_selector("button[name=\"Next\"]", timeout=5000)
        PAGE.get_by_role("button", name="Next").click()
        record_page(PAGE, "3.1")
    except:
        pass
    try:
        # set timeout 5s
        # PAGE.wait_for_selector("button[name=\"Next\"]", timeout=5000)
        PAGE.get_by_role("button", name="Next").click()
        record_page(PAGE, "3.2")
    except:
        pass

    try:
        PAGE.get_by_role("button", name="Done").click()
        record_page(PAGE, "3.3")
    except:
        pass

    print("2FA done")
    time.sleep(2)
    record_page(PAGE, "4")

    print("All set!")
    return True


def get_input_box():
    """Get the child textarea of `PromptTextarea__TextareaWrapper`"""
    return PAGE.query_selector("textarea")


def is_logged_in():
    # See if we have a textarea with data-id="root"
    return get_input_box() is not None


def send_message(message):
    global PAGE
    # Send the message
    # screenshot(PAGE, "send_msg")
    # savepage(PAGE, "send_msg")
    box = get_input_box()
    box.click()
    box.fill(message)
    box.press("Enter")
    screenshot(PAGE, "sent_msg")
    savepage(PAGE, "sent_msg")


def get_last_message():
    """Get the latest message"""
    record_page(PAGE, "get_last_msg")
    page_elements = PAGE.query_selector_all(
        "div[class*='relative lg:w-[calc(100%-115px)] w-full flex flex-col']")
    last_element = page_elements[-1]
    text = last_element.inner_text()
    # substute warning message: Contents may violate our content policy
    text = re.sub(r"Contents.*content policy", "", text)
    text = re.sub(r"This content .* content policy", "", text)
    text = re.sub(r"If you believe this to be in error.*our research in this area", "", text)
    return text


@retry(tries=2, delay=3)
@APP.route("/chat", methods=["GET"])
def chat():
    message = flask.request.args.get("q")
    print("Sending message: ", message)
    send_message(message)
    # TODO: there are about ten million ways to be smarter than this
    # wait for the response
    wait_cnt = 0
    last_response = ""
    response = message
    for _ in range(15):
        response = get_last_message()
        if len(response) > len(last_response):
            last_response = response
            wait_cnt = 0
        else:
            wait_cnt += 1
            if wait_cnt >= 3:
                break
        time.sleep(1)
    print("Response: ", response)
    return response


@retry(tries=3, delay=3)
@APP.route("/chat", methods=["POST"])
def chat_post():
    timeout_interval = 30

    print(f"Received POST request")
    # the request should be a json object with a key "message"
    incoming_request = request.form.to_dict()
    print("Received request: ", incoming_request)

    message = incoming_request["message"]
    print("Sending message: ", message)
    send_message(message)
    # wait for the response
    wait_cnt = 0
    prev_max_len = 0
    prev_max_len_response = ""
    for _ in tqdm(range(timeout_interval), leave=True):
        response = get_last_message()
        if len(response) > prev_max_len:
            prev_max_len = len(response)
            prev_max_len_response = response
            print(f"len of response: {len(response)}, len of prev_max_len_response: {prev_max_len}")
            wait_cnt = 0
        elif len(response) < prev_max_len - 10:  # content policy removed, 10 is arbitrary magic number
            break
        elif response == b'\xe2\x80\x8b' or len(response) <= 3:
            wait_cnt = 0
        else:
            wait_cnt += 1
            print(f"wait_cnt: {wait_cnt}")
            if wait_cnt >= 4:
                break
        time.sleep(1)

    # response = get_last_message()

    # time.sleep(10)

    print("Response: ", prev_max_len_response)
    print(f"len of response: {len(prev_max_len_response)}")
    # print response in bytes
    print("Response in bytes: ", prev_max_len_response.encode("utf-8"))
    chat_logger.record_conversation({"you": message, "ai": prev_max_len_response})
    return prev_max_len_response


@APP.route("/refresh", methods=["GET"])
def refresh():
    global PAGE
    global chat_logger
    PAGE.reload()
    login(PAGE)
    if is_logged_in():
        chat_logger.start_new_conversation()
        return "OK"
    else:
        return "FAIL"


@APP.route("/reset", methods=["GET"])
def reset():
    global PAGE
    global chat_logger
    PAGE.get_by_text("Reset Thread").click()
    if is_logged_in():
        chat_logger.start_new_conversation()
        return "OK"
    else:
        return "FAIL"


@retry(tries=2, delay=5)
def start_browser():
    global PAGE
    global chat_logger
    PAGE.goto("https://chat.openai.com/")
    if not is_logged_in():
        try:
            login(PAGE)
        except Exception as e:
            print(f"Error: {e}")
            raise e
        print("logged in smoothly")
        # print("Please log in to OpenAI Chat")
        # print("Press enter when you're done")
        # input()
    # else:
    print("Logged in")
    chat_logger.start_new_conversation()
    APP.run(port=9999, threaded=False)


if __name__ == "__main__":
    start_browser()
