#!/usr/bin/env python3
"""
Headless browser testing module for DynaDock
"""

import time
from pathlib import Path
from urllib.parse import urlparse
from typing import Dict, Any

# Create screenshots directory
SCREENSHOTS_DIR = Path("test_screenshots")


def cleanup_old_screenshots():
    """Remove old screenshots before new test run"""
    import shutil

    if SCREENSHOTS_DIR.exists():
        shutil.rmtree(SCREENSHOTS_DIR)
    SCREENSHOTS_DIR.mkdir(exist_ok=True)
    print(f"🧹 Cleaned screenshots directory: {SCREENSHOTS_DIR}")


def setup_screenshots_dir():
    """Setup screenshots directory with cleanup"""
    cleanup_old_screenshots()
    return SCREENSHOTS_DIR


async def test_domain_headless(
    url: str, timeout: int = 10, verbose: bool = False
) -> Dict[str, Any]:
    """Enhanced domain testing with screenshots and detailed analysis"""

    def log(message: str):
        """Add verbose logging"""
        if verbose:
            print(f"   [BROWSER] {message}")

    log(f"Rozpoczynanie testu przeglądarki dla: {url}")
    log(f"Timeout ustawiony na: {timeout}s")

    try:
        from playwright.async_api import async_playwright

        log("Importowanie Playwright - OK")

        parsed_url = urlparse(url)
        safe_filename = f"{parsed_url.netloc}_{parsed_url.path.replace('/', '_')}_{int(time.time())}"
        log(f"Nazwa pliku zrzutu: {safe_filename}")

        async with async_playwright() as p:
            log("Uruchamianie przeglądarki Chromium...")
            browser = await p.chromium.launch(headless=True)
            log("Przeglądarka uruchomiona - tworzenie kontekstu...")

            context = await browser.new_context(
                ignore_https_errors=False,
                extra_http_headers={},
                viewport={"width": 1280, "height": 720},
            )
            log("Kontekst przeglądarki utworzony (1280x720, HTTPS errors: ON)")

            page = await context.new_page()
            log("Nowa strona utworzona - konfigurowanie event handlers...")

            # Enhanced monitoring
            errors = []
            ssl_errors = []
            network_requests = []
            console_logs = []

            # Set up event handlers
            _setup_page_handlers(
                page, network_requests, errors, ssl_errors, console_logs
            )
            log("Event handlers skonfigurowane")

            # Navigate to the page
            log(f"Nawigacja do strony: {url}")
            start_time = time.time()
            response = await page.goto(
                url, timeout=timeout * 1000, wait_until="domcontentloaded"
            )
            load_time = time.time() - start_time
            log(
                f"Strona załadowana w {load_time:.3f}s, status: {response.status if response else 'N/A'}"
            )

            if response:
                log(f"Przetwarzanie pozytywnej odpowiedzi (status: {response.status})")
                result = await _process_successful_response(
                    page,
                    response,
                    load_time,
                    safe_filename,
                    network_requests,
                    console_logs,
                    errors,
                    ssl_errors,
                )
            else:
                log("Brak odpowiedzi - przetwarzanie błędu")
                result = await _process_failed_response(
                    page, safe_filename, network_requests, errors, ssl_errors
                )

            log("Zamykanie przeglądarki...")
            await browser.close()
            log("Test przeglądarki zakończony")
            return result

    except Exception as e:
        log(f"EXCEPTION w teście przeglądarki: {e}")
        try:
            result = await _process_exception(
                page, e, safe_filename, network_requests, errors, ssl_errors
            )
            await browser.close()
            return result
        except Exception:
            return {
                "success": False,
                "error": f"Browser setup failed: {str(e)}",
                "errors": [],
                "ssl_errors": [],
                "network_requests": [],
            }


def _setup_page_handlers(page, network_requests, errors, ssl_errors, console_logs):
    """Setup event handlers for page monitoring"""

    def handle_request(request):
        network_requests.append(
            {
                "url": request.url,
                "method": request.method,
                "headers": dict(request.headers),
                "timestamp": time.time(),
            }
        )

    def handle_response(response):
        for req in network_requests:
            if req["url"] == response.url:
                req["response_status"] = response.status
                req["response_headers"] = dict(response.headers)
                break

    def handle_page_error(error):
        errors.append(f"Page Error: {error}")

    def handle_request_failed(request):
        failure = request.failure or "Unknown failure"
        if "ssl" in failure.lower() or "certificate" in failure.lower():
            ssl_errors.append(f"SSL Error: {request.url} - {failure}")
        errors.append(f"Request failed: {request.url} - {failure}")

    def handle_console(msg):
        console_logs.append(
            {"type": msg.type, "text": msg.text, "timestamp": time.time()}
        )

    page.on("request", handle_request)
    page.on("response", handle_response)
    page.on("pageerror", handle_page_error)
    page.on("requestfailed", handle_request_failed)
    page.on("console", handle_console)


async def _process_successful_response(
    page,
    response,
    load_time,
    safe_filename,
    network_requests,
    console_logs,
    errors,
    ssl_errors,
):
    """Process successful page response"""
    # Take screenshot
    screenshot_path = SCREENSHOTS_DIR / f"{safe_filename}_success.png"
    await page.screenshot(path=screenshot_path, full_page=True)

    # Get page info
    title = await page.title()
    content = await page.content()

    # Enhanced security analysis
    security_info = await page.evaluate(
        """
        () => {
            const info = {
                protocol: location.protocol,
                host: location.host,
                origin: location.origin,
                userAgent: navigator.userAgent,
                cookieEnabled: navigator.cookieEnabled,
                language: navigator.language
            };
            
            if (location.protocol === 'https:') {
                info.secure = true;
                info.securityState = 'secure';
            } else {
                info.secure = false;
                info.securityState = 'not-secure';
            }
            return info;
        }
    """
    )

    # Page analysis
    page_analysis = await page.evaluate(
        """
        () => {
            return {
                hasErrors: document.querySelector('.error, .err, #error') !== null,
                hasContent: document.body.innerText.length > 100,
                formCount: document.forms.length,
                linkCount: document.links.length,
                imageCount: document.images.length,
                scriptCount: document.scripts.length
            };
        }
    """
    )

    return {
        "success": True,
        "status": response.status,
        "title": title[:80] + "..." if len(title) > 80 else title,
        "content_length": len(content),
        "load_time": round(load_time, 2),
        "screenshot": str(screenshot_path),
        "security_info": security_info,
        "page_analysis": page_analysis,
        "network_requests": network_requests,
        "console_logs": console_logs[-10:],
        "errors": errors,
        "ssl_errors": ssl_errors,
    }


async def _process_failed_response(
    page, safe_filename, network_requests, errors, ssl_errors
):
    """Process failed response"""
    screenshot_path = SCREENSHOTS_DIR / f"{safe_filename}_error.png"
    try:
        await page.screenshot(path=screenshot_path)
    except Exception:
        pass

    return {
        "success": False,
        "error": "No response received",
        "screenshot": str(screenshot_path),
        "network_requests": network_requests,
        "errors": errors,
        "ssl_errors": ssl_errors,
    }


async def _process_exception(
    page, exception, safe_filename, network_requests, errors, ssl_errors
):
    """Process exception during page load"""
    screenshot_path = SCREENSHOTS_DIR / f"{safe_filename}_exception.png"
    try:
        await page.screenshot(path=screenshot_path)
    except Exception:
        pass

    return {
        "success": False,
        "error": str(exception),
        "screenshot": str(screenshot_path),
        "network_requests": network_requests,
        "errors": errors,
        "ssl_errors": ssl_errors,
    }
