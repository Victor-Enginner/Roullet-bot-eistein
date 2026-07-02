import time
from typing import Optional
from playwright.sync_api import sync_playwright, Error


class LiveCapture:
    """Captura em tempo real com MutationObserver injetado no DOM."""

    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    )

    def __init__(
        self,
        url: str,
        headless: bool = False,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: int = 10_000,
        poll_interval: float = 0.003,
    ):
        self.url = url
        self.headless = headless
        self.user_agent = user_agent
        self.timeout = timeout
        self.poll_interval = poll_interval

        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

        self.running = False
        self.last_number: Optional[str] = None

    def _get_mutation_script(self) -> str:
        return """
        // Anti-detect
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
        Object.defineProperty(navigator, 'languages', { get: () => ['pt-BR','pt'] });

        window.skynet_last_number = null;
        window.skynet_new_number = false;

        const target = document.querySelector('.roulette-history') ||
                       document.querySelector('[class*="roulette-history"]') ||
                       document.querySelector('[data-testid="roulette-history-extended"]');

        if (!target) {
            console.warn('SkynetCapture: container não encontrado para MutationObserver.');
        }

        const observer = new MutationObserver((mutations) => {
            for (const mutation of mutations) {
                for (const node of mutation.addedNodes) {
                    if (node.nodeType !== Node.ELEMENT_NODE) continue;

                    const candidate = node.textContent?.trim() || '';
                    const normalized = candidate.replace(/[^0-9]/g, '');
                    if (normalized && !isNaN(normalized)) {
                        window.skynet_last_number = normalized;
                        window.skynet_new_number = true;
                        return;
                    }
                }
            }
        });

        if (target) {
            if (window.skynet_observer) {
                window.skynet_observer.disconnect();
            }
            window.skynet_observer = observer;
            observer.observe(target, { childList: true, subtree: true });
            console.log('SkynetCapture MutationObserver ativo.');
        }
        """

    def start(self) -> bool:
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    f'--user-agent={self.user_agent}',
                ],
            )
            self.context = self.browser.new_context(
                user_agent=self.user_agent,
                ignore_https_errors=True,
                viewport={'width': 1920, 'height': 1080},
                timezone_id='America/Sao_Paulo',
                device_scale_factor=1,
            )
            self.page = self.context.new_page()

            self.page.goto(self.url, timeout=self.timeout)
            self.page.wait_for_selector('.roulette-history', timeout=self.timeout)
            self.page.add_init_script(self._get_mutation_script())
            # Execute once after load to guarantee observer initialization
            self.page.evaluate(self._get_mutation_script())

            self.running = True
            return True

        except Exception as exc:
            print(f'Erro LiveCapture.start: {exc}')
            self.stop()
            return False

    def get_latest_number(self) -> Optional[int]:
        if not self.running or not self.page:
            return None

        try:
            value = self.page.evaluate('() => window.skynet_new_number ? window.skynet_last_number : null')
            if value is None:
                return None

            if isinstance(value, str) and value.isdigit():
                if value == self.last_number:
                    # Sem mudança concreta
                    self.page.evaluate('() => { window.skynet_new_number = false; }')
                    return None

                self.last_number = value
                self.page.evaluate('() => { window.skynet_new_number = false; }')
                return int(value)

            return None

        except Error as e:
            print(f'Playwright Error no get_latest_number: {e}')
            return None
        except Exception as e:
            print(f'Erro no get_latest_number: {e}')
            return None

    def stop(self):
        self.running = False
        try:
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
        except Exception:
            pass

    def run(self, callback):
        """Loop de captura ininterrupta. callback(number: int)."""
        if not self.start():
            return

        try:
            while self.running:
                number = self.get_latest_number()
                if number is not None:
                    callback(number)
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            self.stop()
        finally:
            self.stop()
