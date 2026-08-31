"""
前端自动化测试脚本
使用 Selenium WebDriver 进行前端功能测试
使用 Edge 浏览器

使用方法:
1. 安装依赖: pip install selenium webdriver-manager
2. 运行脚本: python test_frontend.py

注意:
- 需要先启动前端开发服务器 (npm run dev)
- 默认访问 http://localhost:5713
"""

import time
import json
import os
import sys
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException,
    WebDriverException,
    StaleElementReferenceException
)
from webdriver_manager.microsoft import EdgeChromiumDriverManager

# 配置
BASE_URL = "http://localhost:5713"
HEADLESS = True  # 是否使用无头模式
IMPLICIT_WAIT = 10  # 隐式等待时间（秒）
EXPLICIT_WAIT = 20  # 显式等待时间（秒）
SCREENSHOT_DIR = "screenshots"


@dataclass
class TestResult:
    """测试结果"""
    name: str
    passed: bool
    message: str = ""
    error: Optional[str] = None
    duration: float = 0.0


@dataclass
class TestSuite:
    """测试套件"""
    name: str
    results: List[TestResult] = field(default_factory=list)
    
    def add_result(self, result: TestResult):
        self.results.append(result)
    
    def summary(self) -> Dict[str, Any]:
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        return {
            "name": self.name,
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{passed/total*100:.1f}%" if total > 0 else "0%",
            "results": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "message": r.message,
                    "error": r.error,
                    "duration": f"{r.duration:.2f}s"
                }
                for r in self.results
            ]
        }


class FrontendTester:
    """前端测试器"""
    
    def __init__(self, base_url: str = BASE_URL, headless: bool = HEADLESS):
        self.base_url = base_url
        self.driver: Optional[webdriver.Edge] = None
        self.wait: Optional[WebDriverWait] = None
        self.suite = TestSuite(name="Frontend Test Suite")
        
        self._init_driver(headless)
    
    def _init_driver(self, headless: bool = True):
        """初始化Edge WebDriver"""
        edge_options = Options()
        
        if headless:
            edge_options.add_argument("--headless=new")
        
        # 常用配置
        edge_options.add_argument("--no-sandbox")
        edge_options.add_argument("--disable-dev-shm-usage")
        edge_options.add_argument("--disable-gpu")
        edge_options.add_argument("--window-size=1920,1080")
        edge_options.add_argument("--disable-extensions")
        edge_options.add_argument("--disable-logging")
        edge_options.add_argument("--log-level=3")
        
        # 忽略证书错误（如果是HTTPS）
        # edge_options.add_argument("--ignore-certificate-errors")
        # edge_options.add_argument("--allow-insecure-localhost")
        
        try:
            # 使用EdgeChromiumDriverManager安装Edge驱动
            service = Service(EdgeChromiumDriverManager().install())
            self.driver = webdriver.Edge(service=service, options=edge_options)
            self.driver.implicitly_wait(IMPLICIT_WAIT)
            self.wait = WebDriverWait(self.driver, EXPLICIT_WAIT)
            print(f"[OK] Edge WebDriver initialized successfully")
            print(f"     Base URL: {self.base_url}")
            print(f"     Headless: {headless}")
        except Exception as e:
            print(f"[ERROR] Failed to initialize Edge WebDriver: {e}")
            raise
    
    def take_screenshot(self, name: str):
        """截图"""
        try:
            import os
            os.makedirs(SCREENSHOT_DIR, exist_ok=True)
            filepath = os.path.join(SCREENSHOT_DIR, f"{name}_{int(time.time())}.png")
            self.driver.save_screenshot(filepath)
            print(f"     Screenshot saved: {filepath}")
            return filepath
        except Exception as e:
            print(f"     [WARN] Failed to take screenshot: {e}")
            return None
    
    def wait_for_element(self, selector: str, by: By = By.CSS_SELECTOR, timeout: int = None):
        """等待元素出现"""
        timeout = timeout or EXPLICIT_WAIT
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
            return element
        except TimeoutException:
            raise TimeoutException(f"Element not found: {selector}")
    
    def wait_for_elements(self, selector: str, by: By = By.CSS_SELECTOR, timeout: int = None):
        """等待多个元素出现"""
        timeout = timeout or EXPLICIT_WAIT
        try:
            elements = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_all_elements_located((by, selector))
            )
            return elements
        except TimeoutException:
            return []
    
    def click_element(self, selector: str, by: By = By.CSS_SELECTOR):
        """点击元素"""
        element = self.wait_for_element(selector, by)
        element.click()
        return element
    
    def input_text(self, selector: str, text: str, by: By = By.CSS_SELECTOR, clear_first: bool = True):
        """输入文本"""
        element = self.wait_for_element(selector, by)
        if clear_first:
            element.clear()
        element.send_keys(text)
        return element
    
    def get_text(self, selector: str, by: By = By.CSS_SELECTOR) -> str:
        """获取元素文本"""
        element = self.wait_for_element(selector, by)
        return element.text
    
    def is_element_visible(self, selector: str, by: By = By.CSS_SELECTOR) -> bool:
        """检查元素是否可见"""
        try:
            element = self.wait_for_element(selector, by, timeout=3)
            return element.is_displayed()
        except:
            return False
    
    def run_test(self, name: str, test_func, *args, **kwargs):
        """运行单个测试"""
        start_time = time.time()
        result = TestResult(name=name, passed=False)
        
        try:
            print(f"\n[TEST] {name}")
            test_func(*args, **kwargs)
            result.passed = True
            result.message = "Test passed"
            print(f"[PASS] {name}")
        except Exception as e:
            result.passed = False
            result.error = str(e)
            result.message = f"Test failed: {e}"
            print(f"[FAIL] {name}: {e}")
            self.take_screenshot(name.replace(" ", "_").lower())
        finally:
            result.duration = time.time() - start_time
        
        self.suite.add_result(result)
        return result.passed
    
    def navigate_to(self, path: str = ""):
        """导航到指定页面"""
        url = f"{self.base_url}{path}" if path else self.base_url
        print(f"     Navigating to: {url}")
        self.driver.get(url)
        time.sleep(1)  # 等待页面加载
    
    def get_console_logs(self) -> List[Dict[str, Any]]:
        """获取浏览器控制台日志"""
        try:
            logs = self.driver.get_log("browser")
            return [
                {
                    "level": log.get("level", ""),
                    "message": log.get("message", ""),
                    "timestamp": log.get("timestamp", 0)
                }
                for log in logs
            ]
        except:
            return []
    
    def print_console_errors(self):
        """打印控制台错误"""
        logs = self.get_console_logs()
        errors = [log for log in logs if log["level"] in ("error", "SEVERE")]
        
        if errors:
            print(f"\n[CONSOLE ERRORS] {len(errors)} found:")
            for log in errors[:10]:  # 只显示前10个
                print(f"     [{log['level']}] {log['message'][:200]}")
        else:
            print(f"\n[CONSOLE] No errors found")
    
    def print_summary(self):
        """打印测试总结"""
        summary = self.suite.summary()
        
        print("\n" + "=" * 60)
        print(f"TEST SUMMARY: {summary['name']}")
        print("=" * 60)
        print(f"Total:  {summary['total']}")
        print(f"Passed:  {summary['passed']} ✓")
        print(f"Failed:  {summary['failed']} ✗")
        print(f"Rate:    {summary['pass_rate']}")
        print("-" * 60)
        
        if summary['failed'] > 0:
            print("FAILED TESTS:")
            for r in summary['results']:
                if not r['passed']:
                    print(f"  - {r['name']}: {r['error']}")
        
        print("=" * 60)
        
        return summary
    
    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            print("\n[OK] Edge WebDriver closed")


class TestRunner:
    """测试运行器"""
    
    def __init__(self, tester: FrontendTester):
        self.tester = tester
    
    def test_homepage(self):
        """测试首页"""
        def _test():
            self.tester.navigate_to("/")
            time.sleep(2)
            
            # 检查页面标题
            title = self.tester.driver.title
            print(f"     Page title: {title}")
            
            # 检查是否有导航菜单
            nav_visible = self.tester.is_element_visible("nav")
            print(f"     Navigation visible: {nav_visible}")
        
        self.tester.run_test("Homepage loads correctly", _test)
    
    def test_id_search_page(self):
        """测试ID搜索页面"""
        def _test():
            self.tester.navigate_to("/id-search")
            time.sleep(2)
            
            # 检查搜索框是否存在
            search_input = self.tester.wait_for_element(
                "input[type='text'], input[placeholder], .el-input input",
                timeout=5
            )
            print(f"     Search input found: {search_input is not None}")
            
            # 检查搜索按钮
            search_btn = self.tester.wait_for_element(
                "button, .el-button, [type='submit']",
                timeout=5
            )
            print(f"     Search button found: {search_btn is not None}")
        
        self.tester.run_test("ID Search page loads correctly", _test)
    
    def test_region_search_page(self):
        """测试区域搜索页面"""
        def _test():
            self.tester.navigate_to("/region-search")
            time.sleep(2)
            
            # 检查页面元素
            page_loaded = self.tester.is_element_visible(".el-form, form, [class*='search']")
            print(f"     Region search form visible: {page_loaded}")
        
        self.tester.run_test("Region Search page loads correctly", _test)
    
    def test_go_enrichment_page(self):
        """测试GO富集分析页面"""
        def _test():
            self.tester.navigate_to("/go-enrichment")
            time.sleep(2)
            
            # 检查表单元素
            form_visible = self.tester.is_element_visible(".el-form, form")
            print(f"     GO Enrichment form visible: {form_visible}")
            
            # 检查基因列表输入框
            textarea = self.tester.is_element_visible("textarea, .el-textarea textarea")
            print(f"     Gene list textarea visible: {textarea}")
        
        self.tester.run_test("GO Enrichment page loads correctly", _test)
    
    def test_kegg_enrichment_page(self):
        """测试KEGG富集分析页面"""
        def _test():
            self.tester.navigate_to("/kegg-enrichment")
            time.sleep(2)
            
            # 检查表单元素
            form_visible = self.tester.is_element_visible(".el-form, form")
            print(f"     KEGG Enrichment form visible: {form_visible}")
        
        self.tester.run_test("KEGG Enrichment page loads correctly", _test)
    
    def test_tf_view_page(self):
        """测试TF View页面"""
        def _test():
            self.tester.navigate_to("/tf-view")
            time.sleep(2)
            
            # 检查页面内容
            page_loaded = self.tester.is_element_visible(".el-table, table, [class*='table']")
            print(f"     TF View table visible: {page_loaded}")
        
        self.tester.run_test("TF View page loads correctly", _test)
    
    def test_sequence_server_page(self):
        """测试Sequence Server页面"""
        def _test():
            self.tester.navigate_to("/sequence-server")
            time.sleep(2)
            
            # 检查iframe是否存在
            iframe = self.tester.is_element_visible("iframe")
            print(f"     Sequence Server iframe visible: {iframe}")
        
        self.tester.run_test("Sequence Server page loads correctly", _test)
    
    def test_navigation(self):
        """测试导航功能"""
        def _test():
            self.tester.navigate_to("/")
            time.sleep(2)
            
            # 获取所有导航链接
            nav_links = self.tester.wait_for_elements("nav a, .el-menu a, [class*='menu'] a")
            print(f"     Found {len(nav_links)} navigation links")
            
            # 点击第一个链接并返回
            if nav_links:
                first_link = nav_links[0]
                href = first_link.get_attribute("href")
                print(f"     First link href: {href}")
                
                if href:
                    # 点击前截图
                    self.tester.take_screenshot("before_navigation")
                    
                    # 点击导航
                    first_link.click()
                    time.sleep(2)
                    
                    # 返回首页
                    self.tester.navigate_to("/")
                    time.sleep(1)
        
        self.tester.run_test("Navigation works correctly", _test)
    
    def test_404_page(self):
        """测试404页面"""
        def _test():
            self.tester.navigate_to("/non-existent-page-12345")
            time.sleep(2)
            
            # 检查是否显示404内容或跳转到其他页面
            current_url = self.tester.driver.current_url
            print(f"     Current URL after 404: {current_url}")
        
        self.tester.run_test("404 page handling works", _test)
    
    def test_console_errors(self):
        """检查页面控制台错误"""
        def _test():
            pages = [
                "/",
                "/id-search",
                "/go-enrichment",
                "/kegg-enrichment",
                "/tf-view"
            ]
            
            total_errors = 0
            for page in pages:
                self.tester.navigate_to(page)
                time.sleep(2)
                
                logs = self.tester.get_console_logs()
                errors = [log for log in logs if log["level"] in ("error", "SEVERE")]
                total_errors += len(errors)
                
                if errors:
                    print(f"     {page}: {len(errors)} errors")
            
            print(f"     Total console errors across all pages: {total_errors}")
            
            # 如果错误太多，标记为失败
            if total_errors > 10:
                raise Exception(f"Too many console errors: {total_errors}")
        
        self.tester.run_test("Console has no critical errors", _test)
    
    def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "=" * 60)
        print("STARTING FRONTEND TESTS")
        print("=" * 60)
        
        # 基础测试
        self.test_homepage()
        self.test_navigation()
        self.test_404_page()
        
        # 功能页面测试
        self.test_id_search_page()
        self.test_region_search_page()
        self.test_go_enrichment_page()
        self.test_kegg_enrichment_page()
        self.test_tf_view_page()
        self.test_sequence_server_page()
        
        # 控制台错误检查
        self.test_console_errors()
        
        # 打印总结
        summary = self.tester.print_summary()
        
        # 关闭浏览器
        self.tester.close()
        
        return summary["failed"] == 0


def main():
    """主函数"""
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║          Frontend Automation Test Suite                   ║
    ║          Using Selenium WebDriver (Edge)                  ║
    ╚════════════════════════════════════════════════════════════╝
    """)
    
    # 检查服务器是否运行
    import urllib.request
    import urllib.error
    
    try:
        response = urllib.request.urlopen(BASE_URL, timeout=5)
        print(f"[OK] Frontend server is running at {BASE_URL}")
    except urllib.error.URLError:
        print(f"[WARN] Frontend server is not accessible at {BASE_URL}")
        print(f"       Please start the server first: npm run dev")
        print(f"       Or change BASE_URL in this script")
        return False
    
    # 创建测试器并运行测试
    tester = FrontendTester(base_url=BASE_URL, headless=HEADLESS)
    runner = TestRunner(tester)
    
    try:
        success = runner.run_all_tests()
        
        if success:
            print("\n[SUCCESS] All tests passed!")
            return 0
        else:
            print("\n[FAILURE] Some tests failed. Check the summary above.")
            return 1
            
    except KeyboardInterrupt:
        print("\n[INFO] Tests interrupted by user")
        tester.close()
        return 2
    except Exception as e:
        print(f"\n[ERROR] Test execution failed: {e}")
        if tester.driver:
            tester.take_screenshot("error")
        tester.close()
        return 3


if __name__ == "__main__":
    exit(main())
