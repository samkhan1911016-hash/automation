#!/usr/bin/env python3
"""
DoorDash সাইনআপ অটোমেশন - Version 4 Fix
Chrome DevTools Protocol দিয়ে সাইনআপ ফর্ম ভরা হয়
Error handling এবং retry logic সহ
"""

import json
import urllib.request
import websocket
import itertools
import time
import sys

DEBUG_URL = "http://127.0.0.1:9222/json"

FIRST_NAME = "Arif"
LAST_NAME = "Hossen"
EMAIL = "agyyhu67@gmail.com"
PASSWORD = "Arif589@#67"

counter = itertools.count(1)

# রঙ কোড
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def read_numbers():
    """number.txt থেকে নাম্বার পড়ুন"""
    try:
        with open("number.txt", "r", encoding="utf-8") as f:
            numbers = [line.strip() for line in f if line.strip()]
        print(f"{GREEN}✓ {len(numbers)} নাম্বার পড়া হয়েছে{RESET}")
        return numbers
    except FileNotFoundError:
        print(f"{RED}✗ number.txt ফাইল পাওয়া যায়নি{RESET}")
        return []
    except Exception as e:
        print(f"{RED}✗ number.txt পড়তে ত্রুটি: {e}{RESET}")
        return []


def save_numbers(numbers):
    """নাম্বার সংরক্ষণ করুন"""
    try:
        with open("number.txt", "w", encoding="utf-8") as f:
            if numbers:
                f.write("\n".join(numbers))
        return True
    except Exception as e:
        print(f"{RED}✗ নাম্বার সংরক্ষণ করতে ব্যর্থ: {e}{RESET}")
        return False


def get_next_phone():
    """পরবর্তী ফোন নাম্বার পান এবং সরান"""
    try:
        numbers = read_numbers()
        if not numbers:
            print(f"{RED}❌ number.txt এ আর নাম্বার নেই{RESET}")
            return None

        phone = numbers.pop(0)
        save_numbers(numbers)
        print(f"{GREEN}✓ ব্যবহার করছি ফোন: {phone}{RESET}")
        return phone
    except Exception as e:
        print(f"{RED}✗ নাম্বার পেতে ত্রুটি: {e}{RESET}")
        return None


def get_chrome_tab():
    """Chrome ডেবাগিং এন্ডপয়েন্ট থেকে সাইনআপ ট্যাব খুঁজুন"""
    try:
        with urllib.request.urlopen(DEBUG_URL, timeout=10) as response:
            tabs = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as e:
        print(f"{RED}✗ Chrome endpoint সংযোগ করতে ব্যর্থ: {e}{RESET}")
        return None
    except Exception as e:
        print(f"{RED}✗ Chrome endpoint ত্রুটি: {e}{RESET}")
        return None

    # সাইনআপ ট্যাব খুঁজুন
    tab = next(
        (
            item for item in tabs
            if item.get("type") == "page"
            and "identity.doordash.com/auth/user/signup" in item.get("url", "")
        ),
        None
    )

    if not tab:
        print(f"{YELLOW}⚠ সাইনআপ ট্যাব খুঁজে পাওয়া যায়নি{RESET}")
        print(f"খোলা ট্যাবগুলি:")
        for item in tabs:
            if item.get("type") == "page":
                print(f"  - {item.get('title')} | {item.get('url')}")
        return None

    print(f"{GREEN}✓ লক্ষ্য ট্যাব পাওয়া গেছে{RESET}")
    print(f"  শিরোনাম: {tab.get('title')}")
    print(f"  URL: {tab.get('url')}")
    return tab


def evaluate_js(ws, expression):
    """JavaScript expression কার্যকর করুন এবং ফলাফল ফেরত দিন"""
    try:
        command_id = next(counter)

        ws.send(json.dumps({
            "id": command_id,
            "method": "Runtime.evaluate",
            "params": {
                "expression": expression,
                "returnByValue": True,
                "awaitPromise": True
            }
        }))

        timeout_count = 0
        while timeout_count < 100:
            try:
                message = json.loads(ws.recv())
            except Exception as recv_error:
                print(f"{RED}✗ WebSocket receive ত্রুটি: {recv_error}{RESET}")
                return None

            if message.get("id") != command_id:
                continue

            if "error" in message:
                print(f"{RED}✗ Runtime error: {message['error']}{RESET}")
                return None

            result = message.get("result", {}).get("result", {})

            if "exceptionDetails" in message.get("result", {}):
                details = message["result"]["exceptionDetails"]
                print(f"{RED}✗ JavaScript exception: {details}{RESET}")
                return None

            return result.get("value")

        print(f"{RED}✗ JavaScript execution timeout{RESET}")
        return None

    except Exception as e:
        print(f"{RED}✗ JavaScript evaluate ত্রুটি: {e}{RESET}")
        return None


def fill_form_field(ws, selector, value, field_name):
    """ফর্ম ফিল্ড ভরুন"""
    try:
        expression = """
        (() => {
            const el = document.querySelector(SELECTOR);

            if (!el || el.disabled) {
                return "FIELD_NOT_AVAILABLE";
            }

            const setter = Object.getOwnPropertyDescriptor(
                HTMLInputElement.prototype, "value"
            ).set;

            setter.call(el, VALUE);

            el.dispatchEvent(
                new Event("input", {bubbles: true})
            );
            el.dispatchEvent(
                new Event("change", {bubbles: true})
            );

            return "OK";
        })()
        """.replace("SELECTOR", json.dumps(selector)).replace("VALUE", json.dumps(value))

        result = evaluate_js(ws, expression)
        
        if result == "OK":
            print(f"{GREEN}✓ {field_name} ভরা হয়েছে{RESET}")
            return True
        elif result == "FIELD_NOT_AVAILABLE":
            print(f"{RED}✗ {field_name} ফিল্ড উপলব্ধ নয়{RESET}")
            return False
        else:
            print(f"{YELLOW}⚠ {field_name} ভরা হয়েছে কিন্তু অনিশ্চিত (ফলাফল: {result}){RESET}")
            return False

    except Exception as e:
        print(f"{RED}✗ ফিল্ড ভরতে ত্রুটি ({field_name}): {e}{RESET}")
        return False


def open_country_selector(ws):
    """দেশ নির্বাচক খুলুন"""
    try:
        country_expression = """
        (() => {
            const phone = document.querySelector('input[aria-label="Mobile Number"]');
            if (!phone) return "PHONE_FIELD_NOT_FOUND";

            const rect = phone.getBoundingClientRect();
            const candidates = Array.from(document.querySelectorAll('button, [role="button"]'))
                .filter(el => {
                    const r = el.getBoundingClientRect();
                    return r.width > 0 &&
                           r.height > 0 &&
                           Math.abs(r.top - rect.top) < 80 &&
                           r.left < rect.left;
                });

            candidates.sort((a, b) =>
                b.getBoundingClientRect().left - a.getBoundingClientRect().left
            );

            if (!candidates.length) return "COUNTRY_SELECTOR_NOT_FOUND";
            candidates[0].click();
            return "COUNTRY_SELECTOR_OPENED";
        })()
        """
        
        result = evaluate_js(ws, country_expression)
        
        if result == "COUNTRY_SELECTOR_OPENED":
            print(f"{GREEN}✓ দেশ নির্বাচক খোলা হয়েছে{RESET}")
            return True
        else:
            print(f"{RED}✗ দেশ নির্বাচক খোলা ব্যর্থ: {result}{RESET}")
            return False

    except Exception as e:
        print(f"{RED}✗ দেশ নির্বাচক ত্রুটি: {e}{RESET}")
        return False


def select_italy(ws):
    """ইতালি +39 নির্বাচন করুন"""
    try:
        italy_expression = """
        (() => {
            const elements = Array.from(document.querySelectorAll(
                'button, [role="button"], li, [role="option"], [role="listitem"], div'
            ));

            const matches = elements.filter(el => {
                const text = (el.innerText || el.textContent || "")
                    .replace(/\\s+/g, " ")
                    .trim();

                const r = el.getBoundingClientRect();
                return /^Italy\\s*\\+39$/.test(text) && r.width > 0 && r.height > 0;
            });

            if (!matches.length) return "ITALY_NOT_FOUND";

            matches.sort((a, b) => {
                const ra = a.getBoundingClientRect();
                const rb = b.getBoundingClientRect();
                return (ra.width * ra.height) - (rb.width * rb.height);
            });

            matches[0].click();
            return "ITALY_SELECTED";
        })()
        """
        
        result = evaluate_js(ws, italy_expression)
        
        if result == "ITALY_SELECTED":
            print(f"{GREEN}✓ ইতালি +39 নির্বাচন করা হয়েছে{RESET}")
            return True
        else:
            print(f"{RED}✗ ইতালি নির্বাচন ব্যর্থ: {result}{RESET}")
            return False

    except Exception as e:
        print(f"{RED}✗ ইতালি নির্বাচন ত্রুটি: {e}{RESET}")
        return False


def click_signup_button(ws):
    """Sign Up বাটন ক্লিক করুন"""
    try:
        signup_expression = """
        (() => {
            const candidates = Array.from(document.querySelectorAll('button, input[type="submit"]'));
            const matches = candidates.filter(el => {
                const text = (el.innerText || el.value || el.textContent || "").trim();
                const rect = el.getBoundingClientRect();
                const style = getComputedStyle(el);

                return text === "Sign Up" &&
                       rect.width > 0 &&
                       rect.height > 0 &&
                       style.visibility !== "hidden" &&
                       style.display !== "none";
            });

            if (!matches.length) return "SIGN_UP_BUTTON_NOT_FOUND";

            matches.sort((a, b) => {
                const ra = a.getBoundingClientRect();
                const rb = b.getBoundingClientRect();
                return (rb.width * rb.height) - (ra.width * ra.height);
            });

            const button = matches[0];
            if (button.disabled) return "SIGN_UP_BUTTON_DISABLED";

            button.click();
            return "SIGN_UP_CLICKED";
        })()
        """
        
        result = evaluate_js(ws, signup_expression)
        
        if result == "SIGN_UP_CLICKED":
            print(f"{GREEN}✓ Sign Up বাটন ক্লিক করা হয়েছে{RESET}")
            return True
        else:
            print(f"{RED}✗ Sign Up বাটন ক্লিক ব্যর্থ: {result}{RESET}")
            return False

    except Exception as e:
        print(f"{RED}✗ Sign Up ক্লিক ত্রুটি: {e}{RESET}")
        return False


def monitor_response(ws):
    """প্রতিক্রিয়া মনিটর করুন এবং হ্যান্ডল করুন"""
    try:
        max_attempts = 10
        attempt = 0

        while attempt < max_attempts:
            attempt += 1
            print(f"\n{BLUE}🔍 মনিটরিং চেষ্টা {attempt}/{max_attempts}...{RESET}")
            time.sleep(1)

            # এরর চেক করুন
            error_check_expr = """
            (() => {
                const pageText = document.body.innerText || document.body.textContent || "";
                return pageText.includes("This action is not allowed") ? "ERROR_FOUND" : "NO_ERROR";
            })()
            """
            error_result = evaluate_js(ws, error_check_expr)

            if error_result == "ERROR_FOUND":
                print(f"{RED}❌ 'This action is not allowed' সনাক্ত করা হয়েছে!{RESET}")
                time.sleep(1)

                # ফোন নাম্বার ক্লিয়ার করুন
                clear_phone_expr = """
                (() => {
                    const el = document.querySelector('input[aria-label="Mobile Number"]');
                    if (!el) return "PHONE_FIELD_NOT_FOUND";

                    const setter = Object.getOwnPropertyDescriptor(
                        HTMLInputElement.prototype, "value"
                    ).set;

                    setter.call(el, "");
                    el.dispatchEvent(new Event("input", {bubbles: true}));
                    el.dispatchEvent(new Event("change", {bubbles: true}));
                    return "PHONE_CLEARED";
                })()
                """
                clear_result = evaluate_js(ws, clear_phone_expr)
                print(f"{GREEN}✅ ফোন নাম্বার ক্লিয়ার: {clear_result}{RESET}")
                return True

            # ভেরিফিকেশন চেক করুন
            verification_check_expr = """
            (() => {
                const pageText = document.body.innerText || document.body.textContent || "";
                return pageText.includes("Phone Number Verification") ? "VERIFICATION_FOUND" : "NO_VERIFICATION";
            })()
            """
            verification_result = evaluate_js(ws, verification_check_expr)

            if verification_result == "VERIFICATION_FOUND":
                print(f"{YELLOW}📱 'Phone Number Verification' স্ক্রিন সনাক্ত করা হয়েছে!{RESET}")
                time.sleep(1)

                # Cancel বাটন ক্লিক করুন
                cancel_expr = """
                (() => {
                    const allButtons = Array.from(document.querySelectorAll('button'));
                    let cancelButton = null;

                    for (const btn of allButtons) {
                        const text = (btn.innerText || btn.textContent || "").trim();
                        if (text === "Cancel") {
                            cancelButton = btn;
                            break;
                        }
                    }

                    if (!cancelButton) return "CANCEL_BUTTON_NOT_FOUND";
                    cancelButton.click();
                    return "CANCEL_CLICKED";
                })()
                """
                cancel_result = evaluate_js(ws, cancel_expr)
                print(f"{GREEN}Cancel বাটন অ্যাকশন: {cancel_result}{RESET}")

                time.sleep(2)

                # ফোন নাম্বার ক্লিয়ার করুন
                clear_phone_expr = """
                (() => {
                    const el = document.querySelector('input[aria-label="Mobile Number"]');
                    if (!el) return "PHONE_FIELD_NOT_FOUND";

                    const setter = Object.getOwnPropertyDescriptor(
                        HTMLInputElement.prototype, "value"
                    ).set;

                    setter.call(el, "");
                    el.dispatchEvent(new Event("input", {bubbles: true}));
                    el.dispatchEvent(new Event("change", {bubbles: true}));
                    return "PHONE_CLEARED";
                })()
                """
                clear_result = evaluate_js(ws, clear_phone_expr)
                print(f"{GREEN}✅ ফোন নাম্বার ক্লিয়ার: {clear_result}{RESET}")
                return True

            print(f"{YELLOW}⏸ এখনো এরর বা ভেরিফিকেশন স্ক্রিন সনাক্ত হয়নি...{RESET}")

        print(f"{GREEN}✓ মনিটরিং সম্পন্ন{RESET}")
        return True

    except Exception as e:
        print(f"{RED}✗ মনিটরিং ত্রুটি: {e}{RESET}")
        return False


def process_phone(phone):
    """একটি ফোন নাম্বার প্রক্রিয়া করুন"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}ফোন প্রসেস করছি: {phone}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")

    ws = None

    try:
        # Chrome tab পান
        tab = get_chrome_tab()
        if not tab:
            print(f"{RED}✗ Chrome tab পাওয়া যায়নি{RESET}")
            return False

        # WebSocket সংযোগ করুন
        try:
            ws = websocket.create_connection(
                tab["webSocketDebuggerUrl"],
                timeout=15,
                suppress_origin=True
            )
            print(f"{GREEN}✓ WebSocket সংযোগ সফল{RESET}")
        except Exception as ws_error:
            print(f"{RED}✗ WebSocket সংযোগ ব্যর্থ: {ws_error}{RESET}")
            return False

        # ফর্ম ফিল্ড ভরুন
        fields = [
            ('input[autocomplete="given-name"]', FIRST_NAME, "First Name"),
            ('input[autocomplete="family-name"]', LAST_NAME, "Last Name"),
            ('input[autocomplete="email"]', EMAIL, "Email"),
            ('input[aria-label="Mobile Number"]', phone, "Mobile Number"),
            ('input[autocomplete="new-password"]', PASSWORD, "Password"),
        ]

        for selector, value, field_name in fields:
            if not fill_form_field(ws, selector, value, field_name):
                print(f"{RED}✗ {field_name} ভরা যায়নি, থামছি{RESET}")
                return False

        time.sleep(1)

        # দেশ নির্বাচক খুলুন
        if not open_country_selector(ws):
            print(f"{RED}✗ দেশ নির্বাচক খোলা যায়নি{RESET}")
            return False

        time.sleep(1)

        # ইতালি নির্বাচন করুন
        if not select_italy(ws):
            print(f"{RED}✗ ইতালি নির্বাচন করা যায়নি{RESET}")
            return False

        time.sleep(1)

        # Sign Up বাটন ক্লিক করুন
        if not click_signup_button(ws):
            print(f"{RED}✗ Sign Up বাটন ক্লিক করা যায়নি{RESET}")
            return False

        time.sleep(2)

        # প্রতিক্রিয়া মনিটর করুন
        if not monitor_response(ws):
            print(f"{RED}✗ প্রতিক্রিয়া মনিটর ব্যর্থ{RESET}")
            return False

        print(f"\n{GREEN}✅ ফোন প্রসেস সম্পন্ন: {phone}{RESET}")
        return True

    except Exception as e:
        print(f"{RED}✗ ফোন প্রসেস ত্রুটি: {e}{RESET}")
        return False

    finally:
        if ws is not None:
            try:
                ws.close()
                print(f"{GREEN}✓ WebSocket বন্ধ করা হয়েছে{RESET}")
            except:
                pass

        time.sleep(1)


def main():
    """মূল লুপ"""
    print(f"{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}DoorDash সাইনআপ অটোমেশন - Version 4 Fix{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

    try:
        while True:
            phone = get_next_phone()
            if phone is None:
                print(f"{RED}✗ আর কোনো নাম্বার নেই{RESET}")
                break

            if not process_phone(phone):
                print(f"{YELLOW}⚠ ফোন প্রসেস ব্যর্থ: {phone}{RESET}")

            print(f"{GREEN}🔁 পরবর্তী নাম্বার চলছে...{RESET}\n")

        print(f"\n{GREEN}🎯 সকল নাম্বার প্রসেস করা হয়েছে.{RESET}")

    except KeyboardInterrupt:
        print(f"\n{YELLOW}[থামানো হয়ে��ে]{RESET} ব্যবহারকারী বন্ধ করেছেন।")
        sys.exit(0)

    except Exception as e:
        print(f"\n{RED}[গুরুতর ত্রুটি]{RESET} {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
