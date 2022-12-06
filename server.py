"""Make some requests to OpenAI's chatbot"""

import time
import os
import flask
from retry import retry
import shutil

from flask import g

from playwright.sync_api import sync_playwright

os.chdir(os.path.dirname(os.path.abspath(__file__)))
workdir = os.getcwd()
print(f"workdir:{workdir}")

APP = flask.Flask(__name__)
PLAY = sync_playwright().start()
# add proxy 127.0.0.1:7890
BROWSER = PLAY.chromium.launch_persistent_context(
    user_data_dir=os.path.join(workdir, "browser_files"),
    headless=False,
    # proxy={"server": "http://127.0.0.1:7890"},
)


PAGE = BROWSER.new_page()


def screenshot(page, name):
    page.screenshot(path=os.path.join(
        workdir, "screenshots", f"screenshot_{name}.png"))


@retry(tries=2, delay=3, max_delay=5)
def login(PAGE):
    if os.path.exists(os.path.join(workdir, "screenshots")):
        shutil.rmtree(os.path.join(workdir, "screenshots"))
    os.mkdir(os.path.join(workdir, "screenshots"))

    time.sleep(1)

    try:
        print("Logging in...")
        PAGE.goto("https://chat.openai.com/auth/login")
        screenshot(PAGE, "1")
        PAGE.get_by_role("button", name="Log in").click()
        time.sleep(1)
        screenshot(PAGE, "2")
        PAGE.get_by_label("Email address").click()
        PAGE.get_by_label("Email address").fill("kevinfinley@163.com")
        PAGE.locator("button[name=\"action\"]").click()
        screenshot(PAGE, "2.5")
        with open(os.path.join(workdir, "html.html"), "w") as f:
            f.write(PAGE.content())
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

            screenshot(PAGE, "2.6")
        except:
            pass
        with open(os.path.join(workdir, "html2.html"), "w") as f:
            f.write(PAGE.content())
            
        PAGE.get_by_label("Password").fill("Tvcq_5tM.tww49G")
        PAGE.get_by_role("button", name="Continue").click()
        screenshot(PAGE, "3")
    except Exception as e:
        # screenshot
        screenshot(PAGE, "login_error")

        # # save html
        # with open(os.path.join(workdir, "html.html"), "w") as f:
        #     f.write(PAGE.content())
        raise e

    print("Logged in, waiting for 2FA...")
    try:
        PAGE.wait_for_selector("button[name=\"Next\"]", timeout=3000)
        PAGE.get_by_role("button", name="Next").click()
        screenshot(PAGE, "4")
    except:
        pass
    try:
        # set timeout 5s
        PAGE.wait_for_selector("button[name=\"Next\"]", timeout=3000)
        PAGE.get_by_role("button", name="Next").click()
        screenshot(PAGE, "5")
    except:
        pass

    # screenshot
    screenshot(PAGE, "6")

    # # save html
    # with open(os.path.join(workdir, "html.html"), "w") as f:
    #     f.write(PAGE.content())

    print("All set!")
    return True


# PAGE.get_by_role("textbox").click()
# PAGE.get_by_role("textbox").fill("hi")
# PAGE.get_by_role("textbox").press("Enter")
# PAGE.get_by_text("Hello! How can I help you today? Is there something you need to know or would li").click()
# PAGE.get_by_role("textbox").click()
# PAGE.get_by_role("textbox").fill("how are you?")
# PAGE.get_by_role("textbox").press("Enter")


def get_input_box():
    """Get the child textarea of `PromptTextarea__TextareaWrapper`"""
    return PAGE.query_selector("textarea")


def is_logged_in():
    # See if we have a textarea with data-id="root"
    return get_input_box() is not None


def send_message(message):
    # Send the message
    box = get_input_box()
    box.click()
    box.fill(message)
    box.press("Enter")


def get_last_message():
    """Get the latest message"""
    # capture a screen shot

    # page_elements = PAGE.query_selector_all("div[class*='ConversationItem__Message']")
    page_elements = PAGE.query_selector_all(
        "div[class*='relative lg:w-[calc(100%-115px)] w-full flex flex-col']")
    last_element = page_elements[-1]
    return last_element.inner_text()


@retry(tries=2, delay=3)
@APP.route("/chat", methods=["GET"])
def chat():
    message = flask.request.args.get("q")
    print("Sending message: ", message)
    send_message(message)
    # TODO: there are about ten million ways to be smarter than this
    # wait for the response
    wait_cnt = 0
    last_response = message
    response = message
    for _ in range(10):
        response = get_last_message()
        if response != last_response:
            last_response = response
            wait_cnt = 0
        else:
            wait_cnt += 1
            if wait_cnt >= 3:
                break
        time.sleep(1)
    print("Response: ", response)
    return response


@retry(tries=2, delay=3)
@APP.route("/chat", methods=["POST"])
def chat_post():
    # the request should be a json object with a key "message"
    message = flask.request.json["message"]
    print("Sending message: ", message)
    send_message(message)
    # wait for the response
    wait_cnt = 0
    last_response = message
    response = message
    for _ in range(10):
        response = get_last_message()
        if response != last_response:
            last_response = response
            wait_cnt = 0
        else:
            wait_cnt += 1
            if wait_cnt >= 3:
                break
        time.sleep(1)
    print("Response: ", response)
    return response


@retry(tries=2, delay=5)
def start_browser():
    PAGE.goto("https://chat.openai.com/")
    if not is_logged_in():
        try:
            login(PAGE)
        except Exception as e:
            print(f"Error: {e}")
            raise e
        print("Please log in to OpenAI Chat")
        print("Press enter when you're done")
        input()
    # else:
    print("Logged in")
    APP.run(port=9999, threaded=False)


if __name__ == "__main__":
    start_browser()
